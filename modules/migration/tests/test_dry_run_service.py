"""Unit and integration tests for DryRunService and staging pipeline."""

import json
from unittest.mock import MagicMock, patch
import pytest

from modules.migration.connectors.csv_dump import CsvDumpConnector
from modules.migration.connectors.sqlserver import MockSQLServerEngine, SQLServerConnector
from modules.migration.models.migration import (
    DataCleansingConfig,
    DryRunRequest,
    DryRunResult,
    MigrationMappingConfig,
    RowValidationError,
)
from modules.migration.services.dry_run_service import DryRunService, dry_run_service


@pytest.fixture(autouse=True)
def mock_db():
    mock_batch_repo = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.fetchall.return_value = []
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_context

    with patch("modules.migration.services.dry_run_service.BATCH_REPO", mock_batch_repo), \
         patch("packages.database.connection.get_connection", return_value=mock_conn), \
         patch("packages.database.connection.release_connection"), \
         patch("modules.core.repositories.base.get_connection", return_value=mock_conn), \
         patch("modules.core.repositories.base.release_connection"):
        yield {"batch_repo": mock_batch_repo, "conn": mock_conn, "cursor": mock_cursor}


class TestDryRunFromCSV:
    def test_valid_csv_products_dry_run(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 101, "batch_key": "DRYRUN01"}

        csv_data = (
            "ItemName,ItemCode,SellingPrice,CostPrice,Category,StockQty\n"
            "Espresso Roast,ESP-001,15.50,8.20,Coffee,100\n"
            "Cappuccino Blend,CAP-001,18.00,9.50,Coffee,50\n"
        )
        svc = DryRunService()
        result = svc.run_dry_run_from_csv(
            csv_content=csv_data,
            entity_type="products",
            column_mapping={
                "ItemName": "name",
                "ItemCode": "sku",
                "SellingPrice": "price",
                "CostPrice": "cost_price",
                "Category": "category",
            },
        )

        assert isinstance(result, DryRunResult)
        assert result.success is True
        assert result.total_source_rows == 2
        assert result.valid_rows_count == 2
        assert result.error_rows_count == 0
        assert result.ready_for_commit is True
        assert "products" in result.entity_summaries
        assert len(result.sample_transformed["products"]) == 2
        assert result.sample_transformed["products"][0]["name"] == "Espresso Roast"
        assert result.sample_transformed["products"][0]["sku"] == "ESP-001"

    def test_csv_with_missing_required_and_invalid_data(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 102, "batch_key": "DRYRUN02"}

        csv_data = (
            "ItemName,ItemCode,SellingPrice\n"
            ",ESP-001,15.50\n"  # Missing name
            "Valid Product,,12.00\n"  # Missing SKU -> Cleansing should auto-generate SKU, or flag error
            "Another Product,SKU-999,invalid_num\n"
        )
        svc = DryRunService()
        result = svc.run_dry_run_from_csv(
            csv_content=csv_data,
            entity_type="products",
            column_mapping={
                "ItemName": "name",
                "ItemCode": "sku",
                "SellingPrice": "price",
            },
        )

        assert result.total_source_rows == 3
        # First row has missing name which is required
        assert result.error_rows_count >= 1
        assert len(result.validation_errors) >= 1
        assert any(e.error_type == "missing_required" for e in result.validation_errors)
        assert result.ready_for_commit is False


class TestDryRunFromRecords:
    def test_multi_entity_dry_run_and_reconciliation(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 103, "batch_key": "DRYRUN03"}

        records = {
            "products": [
                {"name": "Burger Bun", "sku": "BUN-01", "price": 2.50, "cost_price": 1.00, "category": "Bakery"},
                {"name": "Beef Patty", "sku": "PAT-01", "price": 5.00, "cost_price": 2.80, "category": "Meat"},
            ],
            "customers": [
                {"name": "Fast Bites Cafe", "phone": "+966501234567", "email": "info@fastbites.com", "balance": 1500.0},
                {"name": "Gourmet Diner", "phone": "0559876543", "email": "contact@gourmet.sa", "balance": 3200.0},
            ],
            "suppliers": [
                {"name": "Almarai Co", "phone": "0112345678", "email": "sales@almarai.com", "category": "Dairy"},
            ],
            "inventory_opening": [
                {"product_id": 1, "warehouse_id": 1, "qty": 200.0},
                {"product_id": 2, "warehouse_id": 1, "qty": 150.0},
            ],
            "customer_opening_balances": [
                {"invoice_number": "OB-001", "partner_id": 1, "total_amount": 1500.0},
                {"invoice_number": "OB-002", "partner_id": 2, "total_amount": 3200.0},
            ],
        }

        svc = DryRunService()
        result = svc.run_dry_run_from_records(
            records_by_entity=records,
            tenant_id=42,
        )

        assert result.success is True
        assert result.total_source_rows == 9
        assert result.valid_rows_count == 9
        assert result.error_rows_count == 0
        assert result.ready_for_commit is True

        # Check reconciliation summary
        recon = result.reconciliation_summary
        assert recon is not None
        assert recon["customer_receivables"]["staged_receivables_total"] == 4700.0
        assert recon["customer_receivables"]["variance"] == 0.0
        assert recon["inventory_balances"]["staged_quantity_total"] == 350.0

    def test_phantom_products_detected_and_metrics(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 104, "batch_key": "DRYRUN04"}

        products = [
            {"name": "Active Latte", "sku": "LAT-01", "price": 4.0, "last_transaction_date": "2026-08-01", "qty": 50},
            {"name": "Dead Coffee Syrup", "sku": "DEAD-01", "price": 10.0, "last_transaction_date": "2020-01-01", "qty": 0},
            {"name": "Ghost Item", "sku": "GHOST-01", "price": 5.0, "is_phantom": True, "qty": 0},
        ]

        svc = DryRunService()
        clean_cfg = DataCleansingConfig(
            enable_phantom_detection=True,
            phantom_inactivity_months=12,
            phantom_action="flag",
        )

        result = svc.run_dry_run_from_records(
            records_by_entity={"products": products},
            cleansing_config=clean_cfg,
        )

        assert result.success is True
        assert result.phantom_products_count == 2
        assert result.cleansing_summary.phantom_products_detected == 2

    def test_negative_stock_clamping_and_reconciliation(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 105, "batch_key": "DRYRUN05"}

        inv_records = [
            {"product_id": 1, "warehouse_id": 1, "qty": -25.0},
            {"product_id": 2, "warehouse_id": 1, "qty": 100.0},
        ]

        svc = DryRunService()
        result = svc.run_dry_run_from_records(
            records_by_entity={"inventory_opening": inv_records},
            cleansing_config=DataCleansingConfig(clamp_negative_stock=True),
        )

        assert result.success is True
        assert result.cleansing_summary.clamped_numeric_values >= 1
        recon = result.reconciliation_summary
        assert recon["inventory_balances"]["negative_stock_items"] == 1
        # Staged qty clamped to 0.0 + 100.0 = 100.0
        assert recon["inventory_balances"]["staged_quantity_total"] == 100.0


class TestSQLServerConnectorDryRun:
    def test_sqlserver_connector_full_dry_run(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 106, "batch_key": "DRYRUN06"}

        mock_engine = MockSQLServerEngine(
            tables_data={
                "tbl_items": [
                    {"item_code": "PROD-101", "item_name": "Premium Beans", "price": "22.50", "cost": "12.00", "group": "Coffee"},
                    {"item_code": "PROD-102", "item_name": "Paper Cups", "price": "0.15", "cost": "0.05", "group": "Packaging"},
                ],
                "tbl_customers": [
                    {"cust_name": "Star cafe", "phone": "0501112233", "balance": "500.00"},
                ],
            }
        )
        connector = SQLServerConnector(
            database="LegacyFNB_DB",
            mock_engine=mock_engine,
        )

        svc = DryRunService()
        req = DryRunRequest(
            source_type="sqlserver",
            connection_config={"database": "LegacyFNB_DB"},
            cleansing_config=DataCleansingConfig(normalize_text_casing=True),
        )

        result = svc.run_dry_run(request=req, connector=connector)

        assert result.success is True
        assert result.total_source_rows == 3
        assert result.valid_rows_count == 3
        assert result.error_rows_count == 0
        assert "products" in result.entity_summaries
        assert "customers" in result.entity_summaries


class TestStagingManagement:
    def test_staged_records_retrieval_and_clearing(self, mock_db):
        mock_db["batch_repo"].create.return_value = {"id": 201, "batch_key": "STAGE01"}

        svc = DryRunService()
        records = {
            "products": [
                {"name": f"Product {i}", "sku": f"SKU-{i:03d}", "price": 10.0 + i}
                for i in range(1, 15)
            ]
        }

        result = svc.run_dry_run_from_records(records_by_entity=records)
        assert result.valid_rows_count == 14

        # Retrieve in chunks / pages
        batch_id = 201
        p1 = svc.get_staged_records(batch_id=batch_id, entity_type="products", limit=5, offset=0)
        assert len(p1) == 5
        assert p1[0]["sku"] == "SKU-001"

        p2 = svc.get_staged_records(batch_id=batch_id, entity_type="products", limit=5, offset=5)
        assert len(p2) == 5
        assert p2[0]["sku"] == "SKU-006"

        # Clear staging
        cleared = svc.clear_staging(batch_id=batch_id)
        assert cleared is True
        assert len(svc.get_staged_records(batch_id=batch_id)) == 0

    def test_get_dry_run_result_from_batch_repo(self, mock_db):
        mock_db["batch_repo"].get.return_value = {
            "id": 301,
            "batch_key": "FETCH01",
            "entity_type": "products",
            "total_rows": 10,
            "dry_run_completed": True,
            "reconciliation_summary": {
                "total_valid_rows": 9,
                "total_error_rows": 1,
                "entity_counts": {"products": {"valid_rows": 9}},
            },
            "error_details": [
                {
                    "row_index": 5,
                    "entity_type": "products",
                    "error_type": "missing_required",
                    "message": "Missing required field 'name'",
                    "severity": "error",
                }
            ],
        }

        svc = DryRunService()
        res = svc.get_dry_run_result(batch_id_or_key=301)

        assert res is not None
        assert res.batch_key == "FETCH01"
        assert res.valid_rows_count == 9
        assert res.error_rows_count == 1
        assert len(res.validation_errors) == 1
        assert res.validation_errors[0].error_type == "missing_required"

    def test_get_dry_run_result_by_batch_key(self, mock_db):
        mock_db["batch_repo"].list.return_value = [
            {
                "id": 401,
                "batch_key": "KEY_XYZ",
                "entity_type": "customers",
                "total_rows": 5,
                "dry_run_completed": True,
                "reconciliation_summary": {"total_valid_rows": 5, "total_error_rows": 0},
                "error_details": [],
            }
        ]

        svc = DryRunService()
        res = svc.get_dry_run_result(batch_id_or_key="KEY_XYZ")
        assert res is not None
        assert res.batch_key == "KEY_XYZ"
        assert res.valid_rows_count == 5

    def test_get_dry_run_result_not_found(self, mock_db):
        mock_db["batch_repo"].get.return_value = None
        mock_db["batch_repo"].list.return_value = []

        svc = DryRunService()
        res = svc.get_dry_run_result(batch_id_or_key=999999)
        assert res is None

    def test_connection_failure_handling(self, mock_db):
        mock_connector = MagicMock()
        mock_connector.test_connection.return_value = MagicMock(
            success=False,
            message="Database unreachable",
            error="Connection refused: 1433",
        )
        mock_connector.__enter__.return_value = mock_connector
        mock_connector.__exit__.return_value = None

        svc = DryRunService()
        result = svc.run_dry_run_from_connector(connector=mock_connector)

        assert result.success is False
        assert result.ready_for_commit is False
        assert len(result.validation_errors) == 1
        assert result.validation_errors[0].error_type == "connection_failed"
        assert "Connection refused" in result.validation_errors[0].message

