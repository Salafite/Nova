"""Integration tests for Commit and Rollback lifecycle in Legacy ERP Migration Bridge.

Validates:
1. Full multi-entity commit -> rollback lifecycle with foreign key dependency ordering.
2. Foreign key resolution across dependent entities in a single batch.
3. Audit tracking in Nova.t0104_items with target_table, target_id, and source_key.
4. Preview generation and reverse-dependency deletion order during rollback.
5. Verification of rollback completeness and unrolled item detection.
6. Multi-tenant data isolation and cross-tenant access rejection.
7. Safe rollback for uncommitted/preview batches and idempotent repeated rollback.
"""

from datetime import datetime
import json
from unittest.mock import MagicMock, call, patch
import pytest

from modules.core.context import clear_current_tenant, set_current_tenant, tenant_context
from modules.migration.models.migration import (
    CommitMigrationRequest,
    CommitMigrationResponse,
    RollbackMigrationRequest,
    RollbackMigrationResponse,
)
from modules.migration.services.commit_service import (
    COMMIT_DEPENDENCY_ORDER,
    CommitService,
    commit_service,
)
from modules.migration.services.dry_run_service import dry_run_service
from modules.migration.services.rollback_service import (
    ROLLBACK_DEPENDENCY_ORDER,
    RollbackService,
    rollback_service,
)


@pytest.fixture
def mock_db_pipeline():
    """Mock database infrastructure for full commit and rollback integration tests."""
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
         patch("modules.migration.services.rollback_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.rollback_service.BATCH_ITEMS_REPO", mock_items_repo), \
         patch("modules.migration.services.dry_run_service.BATCH_REPO", mock_batch_repo), \
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


# ==============================================================================
# 1. Full Multi-Entity Commit -> Rollback Lifecycle Tests
# ==============================================================================

class TestFullMultiEntityCommitRollbackLifecycle:
    """Test full multi-entity batch lifecycle: Staging -> Commit -> Tracking -> Preview -> Rollback -> Verification."""

    def test_complete_end_to_end_commit_and_rollback_cycle(self, mock_db_pipeline):
        batch_id = 9001
        tenant_id = 42

        # 1. Prepare Staged Data for all major ERP entities
        staged_dataset = {
            "warehouses": [
                {"name": "Main Warehouse", "location": "Riyadh Logistics Park", "_source_key": "WH-01"}
            ],
            "categories": [
                {"name": "Beverages", "description": "Hot & Cold Drinks", "_source_key": "CAT-01"}
            ],
            "uoms": [
                {"name": "Kilogram", "code": "KG", "symbol": "kg", "_source_key": "UOM-KG"}
            ],
            "chart_of_accounts": [
                {"account_code": "1101", "account_name": "Accounts Receivable", "account_type": "Asset", "_source_key": "ACC-1101"}
            ],
            "price_lists": [
                {"name": "Wholesale Price List", "code": "PL-WHOLESALE", "currency": "SAR", "_source_key": "PL-01"}
            ],
            "products": [
                {"name": "Ethiopian Yirgacheffe", "sku": "COF-ETH-001", "price": 45.0, "cost_price": 25.0, "category": "Beverages", "_source_key": "PROD-ETH"}
            ],
            "product_barcodes": [
                {"sku": "COF-ETH-001", "barcode": "628100000001", "barcode_type": "EAN13", "is_primary": True, "_source_key": "BAR-01"}
            ],
            "customers": [
                {"name": "Specialty Cafe", "phone": "+966501112233", "email": "buyer@specialtycafe.com", "balance": 1500.0, "_source_key": "CUST-SPEC"}
            ],
            "suppliers": [
                {"name": "Bean Importers Ltd", "phone": "+966504445566", "email": "sales@beanimporters.com", "rating": 5, "_source_key": "SUPP-BEAN"}
            ],
            "price_list_items": [
                {"code": "PL-WHOLESALE", "sku": "COF-ETH-001", "unit_price": 40.0, "min_qty": 5.0, "_source_key": "PLI-01"}
            ],
            "inventory_opening": [
                {"sku": "COF-ETH-001", "code": "WH-01", "qty": 150.0, "reserved_qty": 0.0, "_source_key": "INV-01"}
            ],
            "customer_opening_balances": [
                {"name": "Specialty Cafe", "invoice_number": "OPEN-INV-001", "total_amount": 1500.0, "status": "Posted", "_source_key": "BAL-01"}
            ],
            "sales_orders": [
                {"name": "Specialty Cafe", "order_number": "SO-2026-001", "grand_total": 800.0, "status": "Confirmed", "_source_key": "SO-001"}
            ],
            "sales_order_items": [
                {"order_number": "SO-2026-001", "sku": "COF-ETH-001", "qty": 20.0, "unit_price": 40.0, "line_total": 800.0, "_source_key": "SOI-001"}
            ],
            "purchase_orders": [
                {"name": "Bean Importers Ltd", "order_number": "PO-2026-001", "total": 2500.0, "status": "Approved", "_source_key": "PO-001"}
            ],
            "purchase_order_items": [
                {"order_number": "PO-2026-001", "sku": "COF-ETH-001", "qty": 100.0, "unit_price": 25.0, "line_total": 2500.0, "_source_key": "POI-001"}
            ],
            "payments": [
                {"name": "Specialty Cafe", "invoice_number": "OPEN-INV-001", "amount": 500.0, "payment_method": "Bank Transfer", "reference": "TRX-001", "_source_key": "PAY-001"}
            ],
        }

        # Stage data
        dry_run_service._in_memory_staging[batch_id] = staged_dataset

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FULL-9001",
            "status": "Preview",
            "entity_type": "multi_entity",
            "total_rows": len(staged_dataset),
            "business_id": tenant_id,
        }

        # Track inserted tracking items and repo creations
        created_items = []

        def mock_items_create(payload, **kwargs):
            item_id = len(created_items) + 1
            item_record = {
                "id": item_id,
                "batch_id": payload.get("batch_id"),
                "entity_type": payload.get("entity_type"),
                "target_table": payload.get("target_table"),
                "target_id": payload.get("target_id"),
                "source_key": payload.get("source_key"),
                "status": payload.get("status", "Inserted"),
                "business_id": payload.get("business_id"),
            }
            created_items.append(item_record)
            return item_record

        mock_db_pipeline["items_repo"].create.side_effect = mock_items_create

        # --- STEP 1: COMMIT EXECUTION ---
        commit_svc = CommitService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )

        commit_res = commit_svc.commit(
            request=CommitMigrationRequest(batch_id=batch_id, business_id=tenant_id)
        )

        assert isinstance(commit_res, CommitMigrationResponse)
        assert commit_res.status == "Committed"
        assert commit_res.total_inserted == 17
        assert len(commit_res.inserted_by_entity) == 17
        assert len(created_items) == 17

        # Verify batch status updated to Committed in DB
        mock_db_pipeline["batch_repo"].update.assert_called_once()
        commit_update_args = mock_db_pipeline["batch_repo"].update.call_args[1]
        assert commit_update_args["payload"]["status"] == "Committed"
        assert commit_update_args["payload"]["inserted_rows"] == 17

        # --- STEP 2: PRE-ROLLBACK PREVIEW ---
        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FULL-9001",
            "status": "Committed",
            "entity_type": "multi_entity",
            "total_rows": 17,
            "inserted_rows": 17,
            "business_id": tenant_id,
        }
        mock_db_pipeline["items_repo"].list.return_value = created_items

        rollback_svc = RollbackService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )

        preview = rollback_svc.get_rollback_preview(batch_id=batch_id, business_id=tenant_id)
        assert preview["batch_id"] == batch_id
        assert preview["total_records_to_delete"] == 17
        assert preview["can_rollback"] is True

        # Verify reverse dependency deletion ordering in preview:
        # Child entities (payments, items) must appear before parent entities (orders, products, warehouses)
        deletion_order = preview["deletion_order"]
        assert deletion_order.index("payments") < deletion_order.index("customer_opening_balances")
        assert deletion_order.index("sales_order_items") < deletion_order.index("sales_orders")
        assert deletion_order.index("purchase_order_items") < deletion_order.index("purchase_orders")
        assert deletion_order.index("sales_orders") < deletion_order.index("customers")
        assert deletion_order.index("purchase_orders") < deletion_order.index("suppliers")
        assert deletion_order.index("inventory_opening") < deletion_order.index("products")
        assert deletion_order.index("products") < deletion_order.index("warehouses")

        # --- STEP 3: ROLLBACK EXECUTION ---
        deleted_sql_tables: list[str] = []

        def mock_cursor_execute(sql, params=None):
            if "DELETE FROM" in sql:
                table_name = sql.split("DELETE FROM ")[1].split(" ")[0].replace('"', '').replace('Nova.', '')
                deleted_sql_tables.append(table_name)

        mock_db_pipeline["cursor"].execute.side_effect = mock_cursor_execute

        # Track items update
        updated_item_statuses = {}

        def mock_item_update(id_val, payload, **kwargs):
            updated_item_statuses[id_val] = payload.get("status")
            return {"id": id_val, **payload}

        mock_db_pipeline["items_repo"].update.side_effect = mock_item_update

        rollback_res = rollback_svc.rollback(
            RollbackMigrationRequest(batch_id=batch_id, reason="Customer requested dry-run rollback", business_id=tenant_id)
        )

        assert isinstance(rollback_res, RollbackMigrationResponse)
        assert rollback_res.status == "RolledBack"
        assert rollback_res.total_deleted == 17
        assert len(rollback_res.deleted_by_entity) == 17

        # Verify reverse deletion sequence in executed SQL:
        # t0091 (payments) -> t0015 (po_items) -> t0014 (po) -> t0013 (so_items) -> t0012 (so) ->
        # t0090 (balances) -> t0009 (inventory) -> t0084 (pl_items) -> t0011 (suppliers) ->
        # t0010 (customers) -> t0004 (barcodes) -> t0003 (products) -> t0083 (price_lists) ->
        # t0026 (chart) -> t0002 (uoms) -> t0001 (categories) -> t0008 (warehouses)
        assert deleted_sql_tables.index("t0091") < deleted_sql_tables.index("t0090")
        assert deleted_sql_tables.index("t0013") < deleted_sql_tables.index("t0012")
        assert deleted_sql_tables.index("t0015") < deleted_sql_tables.index("t0014")
        assert deleted_sql_tables.index("t0012") < deleted_sql_tables.index("t0010")
        assert deleted_sql_tables.index("t0009") < deleted_sql_tables.index("t0003")
        assert deleted_sql_tables.index("t0003") < deleted_sql_tables.index("t0008")

        # Verify all tracking items were marked 'RolledBack'
        assert len(updated_item_statuses) == 17
        assert all(status == "RolledBack" for status in updated_item_statuses.values())

        # Verify batch status updated to RolledBack and inserted_rows reset to 0
        last_batch_update = mock_db_pipeline["batch_repo"].update.call_args[1]
        assert last_batch_update["payload"]["status"] == "RolledBack"
        assert last_batch_update["payload"]["inserted_rows"] == 0

        # --- STEP 4: VERIFY ROLLBACK COMPLETENESS ---
        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FULL-9001",
            "status": "RolledBack",
            "business_id": tenant_id,
        }
        # Update items with RolledBack status
        for item in created_items:
            item["status"] = "RolledBack"
        mock_db_pipeline["items_repo"].list.return_value = created_items

        verification = rollback_svc.verify_rollback(batch_id=batch_id, business_id=tenant_id)
        assert verification["verified"] is True
        assert verification["unrolled_items_count"] == 0


# ==============================================================================
# 2. Multi-Tenant Data Isolation in Commit & Rollback
# ==============================================================================

class TestMultiTenantCommitRollbackIsolation:
    """Verify tenant data boundaries during commit and rollback operations."""

    def test_commit_stamps_tenant_business_id(self, mock_db_pipeline):
        batch_id = 9101
        tenant_id = 55

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-TENANT-55",
            "status": "Preview",
            "entity_type": "products",
            "total_rows": 1,
            "business_id": tenant_id,
        }

        dry_run_service._in_memory_staging[batch_id] = {
            "products": [{"name": "Tenant Filter Roast", "sku": "TEN-55-01", "price": 30.0}]
        }

        created_items = []
        mock_db_pipeline["items_repo"].create.side_effect = lambda p, **kw: created_items.append(p) or {"id": 1, **p}

        with tenant_context(tenant_id):
            svc = CommitService(
                batch_repo=mock_db_pipeline["batch_repo"],
                items_repo=mock_db_pipeline["items_repo"],
            )
            res = svc.commit(batch_id)

        assert res.status == "Committed"
        assert len(created_items) == 1
        assert created_items[0]["business_id"] == tenant_id

    def test_tenant_mismatch_blocks_commit_and_rollback(self, mock_db_pipeline):
        batch_id = 9102
        owner_tenant = 10
        intruder_tenant = 99

        # get() with intruder_tenant returns None, get_unscoped() returns the batch with owner_tenant
        mock_db_pipeline["batch_repo"].get.return_value = None
        mock_db_pipeline["batch_repo"].get_unscoped.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-PRIVATE-10",
            "business_id": owner_tenant,
            "status": "Preview",
        }

        commit_svc = CommitService(batch_repo=mock_db_pipeline["batch_repo"])
        rollback_svc = RollbackService(batch_repo=mock_db_pipeline["batch_repo"])

        # Commit blocked
        with pytest.raises(ValueError, match="belongs to a different tenant organization"):
            commit_svc.commit_batch(batch_id=batch_id, business_id=intruder_tenant)

        # Rollback blocked
        with pytest.raises(ValueError, match="belongs to a different tenant organization"):
            rollback_svc.rollback_batch(batch_id=batch_id, business_id=intruder_tenant)

    def test_rollback_only_deletes_records_belonging_to_active_tenant(self, mock_db_pipeline):
        batch_id = 9103
        tenant_id = 77

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-TENANT-77",
            "status": "Committed",
            "entity_type": "products",
            "total_rows": 1,
            "inserted_rows": 1,
            "business_id": tenant_id,
        }

        mock_db_pipeline["items_repo"].list.return_value = [
            {"id": 1, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 999, "status": "Inserted"}
        ]

        executed_sql_queries = []

        def mock_execute(sql, params=None):
            executed_sql_queries.append((sql, params))

        mock_db_pipeline["cursor"].execute.side_effect = mock_execute

        svc = RollbackService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )
        res = svc.rollback_batch(batch_id=batch_id, business_id=tenant_id)

        assert res.status == "RolledBack"
        assert res.total_deleted == 1

        # Verify SQL query includes business_id check: WHERE id = %s AND (business_id = %s OR business_id IS NULL)
        delete_queries = [q for q, p in executed_sql_queries if "DELETE FROM" in q]
        assert len(delete_queries) >= 1
        delete_sql, delete_params = executed_sql_queries[0]
        assert "business_id = %s" in delete_sql
        assert delete_params == (999, tenant_id)


# ==============================================================================
# 3. Edge Cases, Idempotency & Staging Purging
# ==============================================================================

class TestCommitAndRollbackEdgeCases:
    """Test cancellation of dry runs, idempotency, and staging cleanup."""

    def test_rollback_dry_run_batch_cleans_in_memory_staging(self, mock_db_pipeline):
        batch_id = 9201

        dry_run_service._in_memory_staging[batch_id] = {
            "products": [{"name": "Staged Tea", "sku": "TEA-STG-01"}]
        }

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-DRY-9201",
            "status": "DryRunPassed",
            "entity_type": "products",
            "total_rows": 1,
            "inserted_rows": 0,
            "business_id": 1,
        }

        svc = RollbackService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )
        res = svc.rollback_batch(batch_id=batch_id, reason="Dry run rejected by reviewer")

        assert res.status == "RolledBack"
        assert res.total_deleted == 0
        assert "cancelled and rolled back successfully" in res.message
        # Verify in-memory staging was purged
        assert batch_id not in dry_run_service._in_memory_staging

    def test_repeated_rollback_is_idempotent(self, mock_db_pipeline):
        batch_id = 9202

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-RERUN-9202",
            "status": "RolledBack",
            "entity_type": "products",
            "total_rows": 5,
            "inserted_rows": 0,
            "business_id": 1,
        }

        svc = RollbackService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )
        res = svc.rollback_batch(batch_id=batch_id)

        assert res.status == "RolledBack"
        assert res.total_deleted == 0
        assert "already rolled back" in res.message
        # No DB updates or deletions triggered
        mock_db_pipeline["batch_repo"].update.assert_not_called()

    def test_verify_rollback_reports_unrolled_records(self, mock_db_pipeline):
        batch_id = 9203

        mock_db_pipeline["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FAIL-9203",
            "status": "RolledBack",
            "business_id": 1,
        }

        # Item 1 is RolledBack, Item 2 is still Inserted
        mock_db_pipeline["items_repo"].list.return_value = [
            {"id": 1, "target_id": 10, "entity_type": "products", "status": "RolledBack"},
            {"id": 2, "target_id": 11, "entity_type": "products", "status": "Inserted"},
        ]

        svc = RollbackService(
            batch_repo=mock_db_pipeline["batch_repo"],
            items_repo=mock_db_pipeline["items_repo"],
        )
        report = svc.verify_rollback(batch_id=batch_id, business_id=1)

        assert report["verified"] is False
        assert report["unrolled_items_count"] == 1
        assert report["unrolled_items"][0]["id"] == 2
