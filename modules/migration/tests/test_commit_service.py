"""Unit and integration tests for CommitService (atomic one-click commit pipeline)."""

from datetime import datetime
import json
from unittest.mock import MagicMock, patch
import pytest

from modules.core.context import set_current_tenant, clear_current_tenant
from modules.migration.models.migration import (
    CommitMigrationRequest,
    CommitMigrationResponse,
)
from modules.migration.services.commit_service import (
    COMMIT_DEPENDENCY_ORDER,
    CommitService,
    commit_service,
)
from modules.migration.services.dry_run_service import dry_run_service


@pytest.fixture
def mock_db_commit():
    """Mock database connections, repositories, and cursor for CommitService tests."""
    mock_batch_repo = MagicMock()
    mock_items_repo = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.fetchall.return_value = []
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch("modules.migration.services.commit_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.commit_service.BATCH_ITEMS_REPO", mock_items_repo), \
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


class TestCommitSingleEntity:
    def test_commit_products_success(self, mock_db_commit):
        batch_id = 201
        mock_db_commit["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-PROD-01",
            "status": "Preview",
            "entity_type": "products",
            "total_rows": 2,
            "business_id": 5,
        }

        # Stage data in in-memory staging
        dry_run_service._in_memory_staging[batch_id] = {
            "products": [
                {"name": "Espresso Blend", "sku": "ESP-001", "price": 15.0, "cost_price": 7.5, "category": "Coffee"},
                {"name": "Filter Roast", "sku": "FLT-001", "price": 12.0, "cost_price": 6.0, "category": "Coffee"},
            ]
        }

        svc = CommitService()
        result = svc.commit_batch(batch_id=batch_id, business_id=5)

        assert isinstance(result, CommitMigrationResponse)
        assert result.batch_id == batch_id
        assert result.batch_key == "BATCH-PROD-01"
        assert result.status == "Committed"
        assert result.total_inserted == 2
        assert result.inserted_by_entity == {"products": 2}
        assert "Migration committed successfully" in result.message

        # Verify BATCH_REPO.update called to set status to Committed
        mock_db_commit["batch_repo"].update.assert_called_once()
        call_kwargs = mock_db_commit["batch_repo"].update.call_args[1]
        assert call_kwargs["payload"]["status"] == "Committed"
        assert call_kwargs["payload"]["inserted_rows"] == 2

        # Verify items recorded
        assert mock_db_commit["items_repo"].create.call_count == 2

    def test_commit_with_request_model(self, mock_db_commit):
        batch_id = 202
        mock_db_commit["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-CUST-01",
            "status": "Preview",
            "entity_type": "customers",
            "total_rows": 1,
            "business_id": 10,
        }

        dry_run_service._in_memory_staging[batch_id] = {
            "customers": [
                {"name": "Arabian Roastery", "phone": "+966501234567", "balance": 2500.0}
            ]
        }

        req = CommitMigrationRequest(batch_id=batch_id, business_id=10, force=False)
        svc = CommitService()
        result = svc.commit(req)

        assert result.status == "Committed"
        assert result.total_inserted == 1
        assert result.inserted_by_entity == {"customers": 1}


class TestCommitMultiEntityDependencyOrdering:
    def test_multi_entity_dependency_resolution(self, mock_db_commit):
        batch_id = 203
        mock_db_commit["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-MULTI-01",
            "status": "Preview",
            "entity_type": "multi_entity",
            "total_rows": 6,
            "business_id": 1,
        }

        # Multi-entity staged data
        dry_run_service._in_memory_staging[batch_id] = {
            "sales_order_items": [
                {"sales_order_id": 1, "product_id": "SKU-P1", "qty": 10.0, "unit_price": 20.0, "line_total": 200.0}
            ],
            "warehouses": [
                {"name": "Central Depot", "location": "Riyadh"}
            ],
            "products": [
                {"name": "Specialty Coffee", "sku": "SKU-P1", "price": 20.0, "cost_price": 10.0}
            ],
            "customers": [
                {"name": "Cafe Mocha", "phone": "+966551122334", "balance": 500.0}
            ],
            "sales_orders": [
                {"order_number": "SO-MIG-001", "customer_id": 1, "grand_total": 200.0, "warehouse_id": 1}
            ],
            "inventory_opening": [
                {"product_id": "SKU-P1", "warehouse_id": 1, "qty": 100.0}
            ],
        }

        svc = CommitService()
        result = svc.commit_batch(batch_id=batch_id, business_id=1)

        assert result.status == "Committed"
        assert result.total_inserted == 6
        assert len(result.inserted_by_entity) == 6
        assert result.inserted_by_entity["products"] == 1
        assert result.inserted_by_entity["warehouses"] == 1
        assert result.inserted_by_entity["customers"] == 1
        assert result.inserted_by_entity["sales_orders"] == 1
        assert result.inserted_by_entity["sales_order_items"] == 1
        assert result.inserted_by_entity["inventory_opening"] == 1

        # Check total tracking items created
        assert mock_db_commit["items_repo"].create.call_count == 6

    def test_dependency_order_list_completeness(self):
        # Verify that parent entities precede child entities in dependency order
        wh_idx = COMMIT_DEPENDENCY_ORDER.index("warehouses")
        prod_idx = COMMIT_DEPENDENCY_ORDER.index("products")
        cust_idx = COMMIT_DEPENDENCY_ORDER.index("customers")
        so_idx = COMMIT_DEPENDENCY_ORDER.index("sales_orders")
        so_items_idx = COMMIT_DEPENDENCY_ORDER.index("sales_order_items")
        inv_idx = COMMIT_DEPENDENCY_ORDER.index("inventory_opening")
        pl_idx = COMMIT_DEPENDENCY_ORDER.index("price_lists")
        pl_items_idx = COMMIT_DEPENDENCY_ORDER.index("price_list_items")

        assert wh_idx < inv_idx
        assert prod_idx < inv_idx
        assert prod_idx < so_items_idx
        assert cust_idx < so_idx
        assert so_idx < so_items_idx
        assert pl_idx < pl_items_idx


class TestCommitValidationAndErrors:
    def test_batch_not_found(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = None
        mock_db_commit["batch_repo"].get_unscoped.return_value = None

        svc = CommitService()
        with pytest.raises(ValueError, match="not found"):
            svc.commit_batch(batch_id=999)

    def test_batch_cross_tenant_mismatch(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = None
        mock_db_commit["batch_repo"].get_unscoped.return_value = {"id": 100, "business_id": 99}

        svc = CommitService()
        with pytest.raises(ValueError, match="belongs to a different tenant organization"):
            svc.commit_batch(batch_id=100, business_id=1)

    def test_batch_already_committed(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = {
            "id": 101,
            "status": "Committed",
            "business_id": 1,
        }

        svc = CommitService()
        with pytest.raises(ValueError, match="already committed"):
            svc.commit_batch(batch_id=101)

    def test_batch_wrong_status_without_force(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = {
            "id": 102,
            "status": "RolledBack",
            "business_id": 1,
        }

        svc = CommitService()
        with pytest.raises(ValueError, match="expected Preview"):
            svc.commit_batch(batch_id=102, force=False)

    def test_batch_with_validation_errors_blocks_commit_without_force(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = {
            "id": 103,
            "status": "Preview",
            "error_details": [
                {"severity": "error", "message": "Missing SKU in row 2"}
            ],
            "business_id": 1,
        }

        svc = CommitService()
        with pytest.raises(ValueError, match="unresolved validation errors"):
            svc.commit_batch(batch_id=103, force=False)

    def test_batch_with_validation_errors_allowed_with_force(self, mock_db_commit):
        batch_id = 104
        mock_db_commit["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FORCE-01",
            "status": "Preview",
            "error_details": [
                {"severity": "error", "message": "Missing SKU in row 2"}
            ],
            "business_id": 1,
        }

        dry_run_service._in_memory_staging[batch_id] = {
            "products": [{"name": "Valid Product", "sku": "VAL-01"}]
        }

        svc = CommitService()
        result = svc.commit_batch(batch_id=batch_id, force=True)
        assert result.status == "Committed"
        assert result.total_inserted == 1

    def test_missing_staged_records_raises_error(self, mock_db_commit):
        batch_id = 105
        mock_db_commit["batch_repo"].get.return_value = {
            "id": batch_id,
            "status": "Preview",
            "business_id": 1,
        }
        # Clear staging
        if batch_id in dry_run_service._in_memory_staging:
            del dry_run_service._in_memory_staging[batch_id]

        svc = CommitService()
        with pytest.raises(ValueError, match="No staged records found"):
            svc.commit_batch(batch_id=batch_id)


class TestQueriesAndSummary:
    def test_get_committed_items(self, mock_db_commit):
        mock_db_commit["items_repo"].list.return_value = [
            {"id": 1, "batch_id": 301, "entity_type": "products", "target_table": "t0003", "target_id": 10},
            {"id": 2, "batch_id": 301, "entity_type": "products", "target_table": "t0003", "target_id": 11},
        ]

        svc = CommitService()
        items = svc.get_committed_items(batch_id=301, entity_type="products", business_id=1)

        assert len(items) == 2
        mock_db_commit["items_repo"].list.assert_called_once_with(
            filters={"batch_id": 301, "entity_type": "products"},
            order_by="id",
            limit=None,
            offset=0,
            business_id=1,
        )

    def test_get_batch_summary(self, mock_db_commit):
        mock_db_commit["batch_repo"].get.return_value = {
            "id": 302,
            "batch_key": "SUMMARY-01",
            "status": "Committed",
            "entity_type": "multi_entity",
            "total_rows": 2,
            "inserted_rows": 2,
            "dry_run_completed": True,
        }
        mock_db_commit["items_repo"].list.return_value = [
            {"id": 1, "entity_type": "products"},
            {"id": 2, "entity_type": "customers"},
        ]

        svc = CommitService()
        summary = svc.get_batch_summary(batch_id=302, business_id=1)

        assert summary is not None
        assert summary["batch_id"] == 302
        assert summary["status"] == "Committed"
        assert summary["committed_items_count"] == 2
        assert summary["entity_counts"] == {"products": 1, "customers": 1}
