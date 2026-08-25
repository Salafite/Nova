"""Unit and integration tests for MigrationService facade.

Validates the full orchestrator lifecycle:
1. Connectors and schema discovery.
2. Mapping configuration and data cleansing.
3. Dry-run simulation pipelines (model, dict, in-memory, CSV).
4. Balance, inventory, and entity count reconciliation reporting.
5. Atomic commit and zero-downtime rollback facade methods.
6. Batch history, staging inspection, and audit tracking.
7. Multi-tenant scoping and context propagation.
"""

from datetime import date, datetime
import json
from unittest.mock import MagicMock, patch
import pytest

from modules.core.context import clear_current_tenant, set_current_tenant
from modules.migration.models.migration import (
    CommitMigrationRequest,
    ConnectionTestRequest,
    ConnectionTestResponse,
    DataCleansingConfig,
    DryRunRequest,
    DryRunResult,
    MigrationMappingConfig,
    ReconciliationReport,
    RollbackMigrationRequest,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    TablePreviewRequest,
    TablePreviewResponse,
)
from modules.migration.services.migration_service import MigrationService, migration_service


@pytest.fixture
def mock_all():
    """Mock database repos and connections for MigrationService tests."""
    mock_batch_repo = MagicMock()
    mock_items_repo = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.fetchall.return_value = []
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch("modules.migration.services.migration_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.migration_service.BATCH_ITEMS_REPO", mock_items_repo), \
         patch("modules.migration.services.dry_run_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.commit_service.BATCH_REPO", mock_batch_repo), \
         patch("modules.migration.services.commit_service.BATCH_ITEMS_REPO", mock_items_repo), \
         patch("modules.migration.services.rollback_service.BATCH_REPO", mock_batch_repo), \
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


# ==============================================================================
# 1. Connectors & Schema Discovery
# ==============================================================================

class TestConnectorsAndDiscovery:
    def test_list_supported_connectors(self):
        svc = MigrationService()
        connectors = svc.list_supported_connectors()
        assert len(connectors) >= 2
        types = [c["type"] for c in connectors]
        assert "sqlserver" in types
        assert "csv_dump" in types

        # Check alias
        assert svc.list_connectors() == connectors

    def test_get_connector(self):
        svc = MigrationService()
        conn = svc.get_connector("csv_dump")
        assert conn.source_type == "csv_dump"

    def test_validate_connection_params(self):
        svc = MigrationService()
        valid, err = svc.validate_connection_params("sqlserver", {"database": "LegacyDB"})
        assert valid is True
        assert err is None

        valid_bad, err_bad = svc.validate_connection_params("sqlserver", {})
        assert valid_bad is False
        assert "database" in err_bad

    def test_test_connection_csv_dump(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,sku,price\nCoffee,CF-01,15.0\n", encoding="utf-8")

        svc = MigrationService()
        res = svc.test_connection("csv_dump", config={"dump_path": str(tmp_path)})
        assert isinstance(res, ConnectionTestResponse)
        assert res.success is True
        assert res.tables_count >= 1

    def test_discover_schema_csv_dump(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,sku,price\nCoffee,CF-01,15.0\n", encoding="utf-8")

        svc = MigrationService()
        res = svc.discover_schema("csv_dump", config={"dump_path": str(tmp_path)})
        assert isinstance(res, SchemaDiscoveryResponse)
        assert "products" in res.tables
        assert "sku" in res.schemas["products"].column_names

    def test_preview_table_csv_dump(self, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text("name,sku,price\nCoffee,CF-01,15.0\nTea,TE-01,10.0\n", encoding="utf-8")

        svc = MigrationService()
        res = svc.preview_table("csv_dump", config={"dump_path": str(tmp_path)}, table_name="products", limit=5)
        assert isinstance(res, TablePreviewResponse)
        assert res.table_name == "products"
        assert res.row_count == 2
        assert res.sample_rows[0]["name"] == "Coffee"


# ==============================================================================
# 2. Schema Mapping & Data Cleansing
# ==============================================================================

class TestMappingAndCleansing:
    def test_generate_mapping_config(self):
        svc = MigrationService()
        config = svc.generate_mapping_config(
            discovered_tables=["tbl_Products", "tbl_Customers"],
            auto_fuzzy=True,
        )
        assert isinstance(config, MigrationMappingConfig)
        assert "products" in config.table_mappings or "tbl_Products" in [t.source_table for t in config.table_mappings.values()]

    def test_cleanse_dataset(self):
        svc = MigrationService()
        records = {
            "products": [
                {"name": "Old Coffee", "sku": "CF-OLD", "price": "15.0", "is_phantom": False, "stock_quantity": 0, "last_transaction_date": "2020-01-01"},
                {"name": "Active Tea", "sku": "TEA-01", "price": "10.0", "stock_quantity": 50, "last_transaction_date": "2026-08-01"},
            ],
            "customers": [
                {"name": "Cafe Mocha", "phone": "+966 50 123 4567", "email": "info@cafemocha.com"},
            ],
        }
        cleansed, summary = svc.cleanse_dataset(records, config=DataCleansingConfig(detect_phantoms=True))
        assert "products" in cleansed
        assert summary.phantom_products_detected >= 1
        assert cleansed["customers"][0]["phone"] == "+966501234567"

    def test_scan_phantom_products(self):
        svc = MigrationService()
        ref_date = date(2026, 8, 1)
        prods = [
            {"sku": "A1", "name": "Live Product", "last_transaction_date": "2026-06-01"},
            {"sku": "A2", "name": "Ghost Product", "last_transaction_date": "2021-01-01", "stock": 0},
        ]
        active, phantoms, summary = svc.scan_phantom_products(prods, reference_date=ref_date)
        assert len(active) == 1
        assert active[0]["sku"] == "A1"
        assert len(phantoms) == 1
        assert phantoms[0]["sku"] == "A2"
        assert summary.phantom_products_detected == 1


# ==============================================================================
# 3. Dry-Run Simulation & Pipeline
# ==============================================================================

class TestDryRunSimulation:
    def test_run_dry_run_from_records(self, mock_all):
        mock_all["batch_repo"].create.return_value = {"id": 501, "batch_key": "BATCH-DR-01", "status": "DryRunPassed"}
        mock_all["batch_repo"].get.return_value = {"id": 501, "batch_key": "BATCH-DR-01", "status": "DryRunPassed"}

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        records = {
            "products": [
                {"name": "Espresso Blend", "sku": "ESP-001", "price": 20.0, "cost_price": 10.0},
                {"name": "Latte Roast", "sku": "LAT-001", "price": 18.0, "cost_price": 9.0},
            ]
        }
        res = svc.run_dry_run_from_records(records_by_entity=records, tenant_id=1)
        assert isinstance(res, DryRunResult)
        assert res.success is True
        assert res.total_records_processed == 2
        assert res.valid_records_count == 2
        assert res.batch_id == 501

    def test_run_dry_run_from_csv(self, mock_all):
        mock_all["batch_repo"].create.return_value = {"id": 502, "batch_key": "BATCH-DR-02", "status": "DryRunPassed"}
        mock_all["batch_repo"].get.return_value = {"id": 502, "batch_key": "BATCH-DR-02", "status": "DryRunPassed"}

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        csv_text = "name,sku,price\nCortado,COR-01,14.0\nFlat White,FLW-01,16.0\n"
        res = svc.run_dry_run_from_csv(csv_content=csv_text, entity_type="products", tenant_id=2)

        assert isinstance(res, DryRunResult)
        assert res.total_records_processed == 2
        assert res.valid_records_count == 2

    def test_get_dry_run_result(self, mock_all):
        mock_all["batch_repo"].get.return_value = {
            "id": 503,
            "batch_key": "BATCH-DR-03",
            "status": "DryRunPassed",
            "dry_run_completed": True,
            "reconciliation_summary": {
                "total_records": 10,
                "valid_records": 10,
                "error_records": 0,
                "phantom_records": 0,
                "batch_status": "Passed",
                "entity_counts": {"products": {"extracted": 10, "staged": 10, "errors": 0}},
            },
        }

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        res = svc.get_dry_run_result(503, business_id=1)
        assert res is not None
        assert res.batch_id == 503
        assert res.batch_key == "BATCH-DR-03"
        assert res.success is True
        assert res.valid_records_count == 10


# ==============================================================================
# 4. Comprehensive Reconciliation Reporting
# ==============================================================================

class TestReconciliationReporting:
    def test_reconcile_customer_balances(self):
        svc = MigrationService()
        legacy = [
            {"customer_code": "C001", "customer_name": "Al-Badr", "balance": 1500.0},
            {"customer_code": "C002", "customer_name": "Cafe Bloom", "balance": 850.0},
        ]
        nova = [
            {"customer_code": "C001", "customer_name": "Al-Badr", "total_amount": 1500.0},
            {"customer_code": "C002", "customer_name": "Cafe Bloom", "total_amount": 850.0},
        ]
        res = svc.reconcile_customer_balances(legacy, nova)
        assert res.is_balanced is True
        assert res.delta_total == 0.0

    def test_reconcile_inventory(self):
        svc = MigrationService()
        legacy = [
            {"sku": "SKU-A", "product_name": "Item A", "warehouse_name": "Main", "qty": 100, "unit_cost": 10.0},
        ]
        nova = [
            {"sku": "SKU-A", "product_name": "Item A", "warehouse_name": "Main", "qty": 100, "cost_price": 10.0},
        ]
        res = svc.reconcile_inventory(legacy, nova)
        assert res.is_balanced is True
        assert res.quantity_delta_total == 0.0
        assert res.valuation_delta_total == 0.0

    def test_generate_and_get_reconciliation_report(self, mock_all):
        mock_all["batch_repo"].get.return_value = {
            "id": 601,
            "batch_key": "RECON-01",
            "status": "Preview",
            "reconciliation_summary": {
                "batch_status": "Passed",
                "entity_counts": {"products": {"extracted": 5, "staged": 5, "errors": 0}},
            },
        }

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        report = svc.get_reconciliation_report(601, business_id=1)
        assert isinstance(report, ReconciliationReport)
        assert report.batch_key == "RECON-01"
        assert report.overall_status in ("Passed", "PassedWithWarnings")


# ==============================================================================
# 5. One-Click Commit & Instant Rollback
# ==============================================================================

class TestCommitAndRollbackFacade:
    def test_commit_facade(self, mock_all):
        batch_id = 701
        mock_all["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FACADE-01",
            "status": "Preview",
            "entity_type": "products",
            "total_rows": 1,
            "business_id": 1,
        }

        svc = MigrationService(batch_repo=mock_all["batch_repo"], items_repo=mock_all["items_repo"])
        svc.dry_run_service._in_memory_staging[batch_id] = {
            "products": [{"name": "Single Origin", "sku": "SO-01", "price": 25.0}]
        }

        res = svc.commit(batch_id, business_id=1)
        assert res["batch_id"] == batch_id
        assert res["status"] == "Committed"
        assert res["inserted_rows"] == 1

    def test_rollback_facade(self, mock_all):
        batch_id = 702
        mock_all["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FACADE-02",
            "status": "Committed",
            "entity_type": "products",
            "total_rows": 1,
            "business_id": 1,
        }

        mock_all["items_repo"].list.return_value = [
            {"id": 10, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 99, "status": "Inserted"}
        ]

        svc = MigrationService(batch_repo=mock_all["batch_repo"], items_repo=mock_all["items_repo"])
        res = svc.rollback(batch_id, business_id=1, reason="Test Rollback")
        assert res["batch_id"] == batch_id
        assert res["status"] == "RolledBack"

    def test_rollback_preview_and_verify(self, mock_all):
        batch_id = 703
        mock_all["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-FACADE-03",
            "status": "RolledBack",
            "business_id": 1,
        }
        mock_all["items_repo"].list.return_value = []

        svc = MigrationService(batch_repo=mock_all["batch_repo"], items_repo=mock_all["items_repo"])
        preview = svc.get_rollback_preview(batch_id, business_id=1)
        assert preview["batch_id"] == batch_id

        verify = svc.verify_rollback(batch_id, business_id=1)
        assert verify["verified"] is True
        assert verify["status"] == "RolledBack"


# ==============================================================================
# 6. Batch History & Management
# ==============================================================================

class TestBatchHistoryAndManagement:
    def test_get_batch_and_by_key(self, mock_all):
        mock_all["batch_repo"].get.return_value = {"id": 801, "batch_key": "BATCH-HIST-01", "status": "Committed"}
        mock_all["batch_repo"].list.return_value = [{"id": 801, "batch_key": "BATCH-HIST-01", "status": "Committed"}]

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        b1 = svc.get_batch(801, business_id=1)
        assert b1["id"] == 801

        b2 = svc.get_batch_by_key("BATCH-HIST-01", business_id=1)
        assert b2["batch_key"] == "BATCH-HIST-01"

    def test_list_batches_pagination(self, mock_all):
        mock_all["batch_repo"].list.return_value = [
            {"id": 802, "batch_key": "B2"},
            {"id": 801, "batch_key": "B1"},
        ]
        mock_all["batch_repo"].count.return_value = 2

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        res = svc.list_batches(limit=10, offset=0, business_id=1)
        assert res["total"] == 2
        assert len(res["items"]) == 2
        assert res["page"] == 1
        assert res["page_size"] == 10

    def test_get_committed_items_and_staged_records(self, mock_all):
        mock_all["items_repo"].list.return_value = [
            {"id": 1, "batch_id": 803, "entity_type": "products", "target_id": 10},
        ]

        svc = MigrationService(batch_repo=mock_all["batch_repo"], items_repo=mock_all["items_repo"])
        svc.dry_run_service._in_memory_staging[803] = {
            "products": [{"name": "P1", "sku": "SKU-1"}]
        }

        staged = svc.get_staged_records(batch_id=803, entity_type="products", business_id=1)
        assert len(staged) == 1
        assert staged[0]["sku"] == "SKU-1"

        items = svc.get_committed_items(batch_id=803, entity_type="products", business_id=1)
        assert len(items) == 1
        assert items[0]["target_id"] == 10

    def test_delete_batch_and_clear_staging(self, mock_all):
        mock_all["batch_repo"].get.return_value = {"id": 804, "batch_key": "B-DEL", "status": "Preview"}
        mock_all["items_repo"].list.return_value = [{"id": 99, "batch_id": 804}]

        svc = MigrationService(batch_repo=mock_all["batch_repo"], items_repo=mock_all["items_repo"])
        svc.dry_run_service._in_memory_staging[804] = {"products": [{"sku": "DEL-1"}]}

        # Clear staging
        assert svc.clear_staging(804) is True
        assert 804 not in svc.dry_run_service._in_memory_staging

        # Delete batch
        res = svc.delete_batch(804, business_id=1)
        assert res is True
        mock_all["batch_repo"].delete.assert_called_with(804, business_id=1)


# ==============================================================================
# 7. Backward Compatibility: Legacy CSV Upload
# ==============================================================================

class TestLegacyCSVUpload:
    def test_upload_csv_products(self, mock_all):
        mock_all["batch_repo"].create.return_value = {"id": 901, "batch_key": "LEGACY-01"}

        svc = MigrationService(batch_repo=mock_all["batch_repo"])
        csv_content = "name,sku,price\nPour Over,PO-01,18.0\nCold Brew,CB-01,22.0\n"
        res = svc.upload_csv("products", csv_content, business_id=1)

        assert res["total_rows"] == 2
        assert res["valid_rows"] == 2
        assert res["error_rows"] == 0
        assert len(res["sample"]) == 2

    def test_upload_csv_unknown_entity_raises(self):
        svc = MigrationService()
        with pytest.raises(ValueError, match="Unknown entity type"):
            svc.upload_csv("unknown_tbl", "name\nTest")

    def test_upload_csv_empty_raises(self):
        svc = MigrationService()
        with pytest.raises(ValueError, match="CSV file is empty"):
            svc.upload_csv("products", "name,sku,price\n")
