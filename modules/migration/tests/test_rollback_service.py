"""Unit and integration tests for RollbackService (instant rollback engine)."""

from datetime import datetime
import json
from unittest.mock import MagicMock, patch
import pytest

from modules.core.context import set_current_tenant, clear_current_tenant
from modules.migration.models.migration import (
    RollbackMigrationRequest,
    RollbackMigrationResponse,
)
from modules.migration.services.rollback_service import (
    ROLLBACK_DEPENDENCY_ORDER,
    RollbackService,
    rollback_service,
)
from modules.migration.services.dry_run_service import dry_run_service


@pytest.fixture
def mock_db_rollback():
    """Mock database connections, repositories, and cursor for RollbackService tests."""
    mock_batch_repo = MagicMock()
    mock_items_repo = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.fetchall.return_value = []
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch("modules.migration.services.rollback_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.rollback_service.BATCH_ITEMS_REPO", mock_items_repo), \
         patch("packages.database.connection.get_connection", return_value=mock_conn), \
         patch("packages.database.connection.release_connection"), \
         patch("modules.core.repositories.base.get_connection", return_value=mock_conn), \
         patch("modules.core.repositories.base.release_connection"):
        yield {
            "batch_repo": mock_batch_repo,
            "items_repo": mock_items_repo,
            "conn": mock_conn,
            "cursor": mock_cursor,
        }


class TestRollbackSingleEntity:
    def test_rollback_committed_products_success(self, mock_db_rollback):
        batch_id = 401
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-PROD-401",
            "status": "Committed",
            "entity_type": "products",
            "total_rows": 2,
            "inserted_rows": 2,
            "business_id": 5,
        }

        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 1, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 101, "status": "Inserted"},
            {"id": 2, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 102, "status": "Inserted"},
        ]

        svc = RollbackService()
        result = svc.rollback_batch(batch_id=batch_id, reason="Testing product rollback", business_id=5)

        assert isinstance(result, RollbackMigrationResponse)
        assert result.batch_id == batch_id
        assert result.batch_key == "BATCH-PROD-401"
        assert result.status == "RolledBack"
        assert result.total_deleted == 2
        assert result.deleted_by_entity == {"products": 2}
        assert "rolled back successfully" in result.message

        # Verify BATCH_REPO.update called to set status to RolledBack and inserted_rows to 0
        mock_db_rollback["batch_repo"].update.assert_called_once()
        call_kwargs = mock_db_rollback["batch_repo"].update.call_args[1]
        assert call_kwargs["payload"]["status"] == "RolledBack"
        assert call_kwargs["payload"]["inserted_rows"] == 0

        # Verify each item was updated to RolledBack
        assert mock_db_rollback["items_repo"].update.call_count == 2
        first_item_call = mock_db_rollback["items_repo"].update.call_args_list[0][1]
        assert first_item_call["id_val"] == 1
        assert first_item_call["payload"]["status"] == "RolledBack"

    def test_rollback_with_request_model(self, mock_db_rollback):
        batch_id = 402
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-CUST-402",
            "status": "Committed",
            "entity_type": "customers",
            "total_rows": 1,
            "inserted_rows": 1,
            "business_id": 10,
        }

        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 10, "batch_id": batch_id, "entity_type": "customers", "target_table": "t0010", "target_id": 201, "status": "Inserted"},
        ]

        req = RollbackMigrationRequest(batch_id=batch_id, reason="Customer list erroneous", business_id=10)
        svc = RollbackService()
        result = svc.rollback(req)

        assert result.status == "RolledBack"
        assert result.total_deleted == 1
        assert result.deleted_by_entity == {"customers": 1}

    def test_rollback_with_dict_payload(self, mock_db_rollback):
        batch_id = 403
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-DICT-403",
            "status": "Committed",
            "entity_type": "suppliers",
            "total_rows": 1,
            "inserted_rows": 1,
            "business_id": 1,
        }

        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 15, "batch_id": batch_id, "entity_type": "suppliers", "target_table": "t0011", "target_id": 301, "status": "Inserted"},
        ]

        svc = RollbackService()
        result = svc.rollback({"batch_id": batch_id, "business_id": 1})

        assert result.status == "RolledBack"
        assert result.total_deleted == 1


class TestRollbackMultiEntityOrdering:
    def test_multi_entity_reverse_dependency_order(self, mock_db_rollback):
        batch_id = 404
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-MULTI-404",
            "status": "Committed",
            "entity_type": "multi_entity",
            "total_rows": 6,
            "inserted_rows": 6,
            "business_id": 1,
        }

        # Track deletion calls to verify order
        deleted_order: list[str] = []

        def mock_cursor_execute(sql, params=None):
            # Capture table name from sql DELETE FROM "Nova".<table_name>
            if "DELETE FROM" in sql:
                tbl = sql.split("DELETE FROM ")[1].split(" ")[0].replace('"', '').replace('Nova.', '')
                deleted_order.append(tbl)

        mock_db_rollback["cursor"].execute.side_effect = mock_cursor_execute

        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 1, "batch_id": batch_id, "entity_type": "warehouses", "target_table": "t0008", "target_id": 1, "status": "Inserted"},
            {"id": 2, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 10, "status": "Inserted"},
            {"id": 3, "batch_id": batch_id, "entity_type": "customers", "target_table": "t0010", "target_id": 20, "status": "Inserted"},
            {"id": 4, "batch_id": batch_id, "entity_type": "sales_orders", "target_table": "t0012", "target_id": 30, "status": "Inserted"},
            {"id": 5, "batch_id": batch_id, "entity_type": "sales_order_items", "target_table": "t0013", "target_id": 40, "status": "Inserted"},
            {"id": 6, "batch_id": batch_id, "entity_type": "inventory_opening", "target_table": "t0009", "target_id": 50, "status": "Inserted"},
        ]

        svc = RollbackService()
        result = svc.rollback_batch(batch_id=batch_id, business_id=1)

        assert result.status == "RolledBack"
        assert result.total_deleted == 6
        assert len(result.deleted_by_entity) == 6

        # Verify exact reverse dependency order:
        # sales_order_items (t0013) before sales_orders (t0012)
        # inventory_opening (t0009) before products (t0003) & warehouses (t0008)
        # sales_orders (t0012) before customers (t0010)
        # products & customers before warehouses
        so_items_pos = deleted_order.index("t0013")
        so_pos = deleted_order.index("t0012")
        inv_pos = deleted_order.index("t0009")
        cust_pos = deleted_order.index("t0010")
        prod_pos = deleted_order.index("t0003")
        wh_pos = deleted_order.index("t0008")

        assert so_items_pos < so_pos
        assert so_pos < cust_pos
        assert inv_pos < prod_pos
        assert prod_pos < wh_pos
        assert cust_pos < wh_pos

    def test_reverse_dependency_list_structure(self):
        # Line items / payments before orders / invoices / balances before master tables
        pay_idx = ROLLBACK_DEPENDENCY_ORDER.index("payments")
        po_items_idx = ROLLBACK_DEPENDENCY_ORDER.index("purchase_order_items")
        po_idx = ROLLBACK_DEPENDENCY_ORDER.index("purchase_orders")
        so_items_idx = ROLLBACK_DEPENDENCY_ORDER.index("sales_order_items")
        so_idx = ROLLBACK_DEPENDENCY_ORDER.index("sales_orders")
        open_bal_idx = ROLLBACK_DEPENDENCY_ORDER.index("customer_opening_balances")
        inv_idx = ROLLBACK_DEPENDENCY_ORDER.index("inventory_opening")
        pl_items_idx = ROLLBACK_DEPENDENCY_ORDER.index("price_list_items")
        cust_idx = ROLLBACK_DEPENDENCY_ORDER.index("customers")
        prod_idx = ROLLBACK_DEPENDENCY_ORDER.index("products")
        wh_idx = ROLLBACK_DEPENDENCY_ORDER.index("warehouses")

        assert pay_idx < open_bal_idx
        assert po_items_idx < po_idx
        assert so_items_idx < so_idx
        assert so_idx < cust_idx
        assert open_bal_idx < cust_idx
        assert inv_idx < prod_idx
        assert pl_items_idx < prod_idx
        assert prod_idx < wh_idx


class TestRollbackUncommittedAndPreviewBatches:
    def test_rollback_preview_batch(self, mock_db_rollback):
        batch_id = 405
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-PREV-405",
            "status": "Preview",
            "entity_type": "products",
            "total_rows": 10,
            "inserted_rows": 0,
            "business_id": 1,
        }

        # Stage data in in-memory staging
        dry_run_service._in_memory_staging[batch_id] = {
            "products": [{"name": "Staged Only", "sku": "STG-01"}]
        }

        svc = RollbackService()
        result = svc.rollback_batch(batch_id=batch_id, reason="User cancelled preview")

        assert result.status == "RolledBack"
        assert result.total_deleted == 0
        assert "cancelled and rolled back successfully" in result.message

        # Verify staging data was purged
        assert batch_id not in dry_run_service._in_memory_staging

        # Verify batch status updated to RolledBack
        mock_db_rollback["batch_repo"].update.assert_called_once()
        call_kwargs = mock_db_rollback["batch_repo"].update.call_args[1]
        assert call_kwargs["payload"]["status"] == "RolledBack"
        assert call_kwargs["payload"]["inserted_rows"] == 0

    def test_rollback_dry_run_passed_batch(self, mock_db_rollback):
        batch_id = 406
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-DRY-406",
            "status": "DryRunPassed",
            "entity_type": "customers",
            "total_rows": 5,
            "inserted_rows": 0,
            "business_id": 2,
        }

        svc = RollbackService()
        result = svc.rollback_batch(batch_id=batch_id, business_id=2)

        assert result.status == "RolledBack"
        assert result.total_deleted == 0

    def test_rollback_already_rolled_back_batch_is_idempotent(self, mock_db_rollback):
        batch_id = 407
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-ALREADY-407",
            "status": "RolledBack",
            "entity_type": "products",
            "total_rows": 5,
            "inserted_rows": 0,
            "business_id": 1,
        }

        svc = RollbackService()
        result = svc.rollback_batch(batch_id=batch_id)

        assert result.status == "RolledBack"
        assert result.total_deleted == 0
        assert "already rolled back" in result.message
        # Should not call update again
        mock_db_rollback["batch_repo"].update.assert_not_called()


class TestRollbackValidationAndSecurity:
    def test_batch_not_found_raises_error(self, mock_db_rollback):
        mock_db_rollback["batch_repo"].get.return_value = None
        mock_db_rollback["batch_repo"].get_unscoped.return_value = None

        svc = RollbackService()
        with pytest.raises(ValueError, match="not found"):
            svc.rollback_batch(batch_id=9999)

    def test_batch_tenant_mismatch_raises_error(self, mock_db_rollback):
        mock_db_rollback["batch_repo"].get.return_value = None
        mock_db_rollback["batch_repo"].get_unscoped.return_value = {"id": 500, "business_id": 88}

        svc = RollbackService()
        with pytest.raises(ValueError, match="belongs to a different tenant organization"):
            svc.rollback_batch(batch_id=500, business_id=1)


class TestRollbackPreviewAndVerification:
    def test_get_rollback_preview(self, mock_db_rollback):
        batch_id = 408
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-PREV-408",
            "status": "Committed",
            "entity_type": "multi_entity",
            "business_id": 1,
        }

        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 1, "entity_type": "products", "status": "Inserted"},
            {"id": 2, "entity_type": "products", "status": "Inserted"},
            {"id": 3, "entity_type": "customers", "status": "Inserted"},
            {"id": 4, "entity_type": "sales_orders", "status": "Inserted"},
        ]

        svc = RollbackService()
        preview = svc.get_rollback_preview(batch_id=batch_id, business_id=1)

        assert preview["batch_id"] == batch_id
        assert preview["batch_key"] == "BATCH-PREV-408"
        assert preview["total_records_to_delete"] == 4
        assert preview["entity_counts"] == {"products": 2, "customers": 1, "sales_orders": 1}
        assert preview["can_rollback"] is True

        # Verify sales_orders precedes customers and products in deletion_order
        assert preview["deletion_order"].index("sales_orders") < preview["deletion_order"].index("customers")
        assert preview["deletion_order"].index("sales_orders") < preview["deletion_order"].index("products")

    def test_verify_rollback_passed(self, mock_db_rollback):
        batch_id = 409
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-VER-409",
            "status": "RolledBack",
            "business_id": 1,
        }

        # All items are marked RolledBack
        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 1, "status": "RolledBack"},
            {"id": 2, "status": "RolledBack"},
        ]

        svc = RollbackService()
        verification = svc.verify_rollback(batch_id=batch_id, business_id=1)

        assert verification["verified"] is True
        assert verification["unrolled_items_count"] == 0

    def test_verify_rollback_incomplete_detected(self, mock_db_rollback):
        batch_id = 410
        mock_db_rollback["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-VER-410",
            "status": "RolledBack",
            "business_id": 1,
        }

        # One item still marked Inserted
        mock_db_rollback["items_repo"].list.return_value = [
            {"id": 1, "status": "RolledBack"},
            {"id": 2, "status": "Inserted"},
        ]

        svc = RollbackService()
        verification = svc.verify_rollback(batch_id=batch_id, business_id=1)

        assert verification["verified"] is False
        assert verification["unrolled_items_count"] == 1
