"""Unit tests for migration domain Pydantic models."""

import pytest
from datetime import datetime

from modules.migration.models import (
    SQLServerConnectionConfig,
    CsvDumpConnectionConfig,
    ConnectorConfig,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ColumnMetadata,
    TableMetadata,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    TablePreviewRequest,
    TablePreviewResponse,
    FieldMappingRule,
    TableMappingRule,
    MigrationMappingConfig,
    DataCleansingConfig,
    CleansingLogItem,
    CleansingSummary,
    DryRunRequest,
    RowValidationError,
    DryRunResult,
    CustomerBalanceItem,
    CustomerBalanceReconciliation,
    WarehouseStockItem,
    WarehouseReconciliationSummary,
    InventoryReconciliation,
    EntityCountReconciliation,
    ReconciliationReport,
    CommitMigrationRequest,
    CommitMigrationResponse,
    RollbackMigrationRequest,
    RollbackMigrationResponse,
    MigrationBatchResponse,
    MigrationBatchItemResponse,
    MigrationBatchListResponse,
)


class TestConnectionConfigs:
    def test_sqlserver_connection_config_defaults(self):
        config = SQLServerConnectionConfig(database="LegacyERP")
        assert config.host == "localhost"
        assert config.port == 1433
        assert config.database == "LegacyERP"
        assert config.user == "sa"
        assert config.trust_server_certificate is True
        assert config.timeout == 30
        assert config.schema_name == "dbo"

    def test_csv_dump_connection_config(self):
        config = CsvDumpConnectionConfig(
            dump_path="/tmp/dumps",
            delimiter=",",
            encoding="utf-8",
            quote_char='"',
            has_header=True
        )
        assert config.dump_path == "/tmp/dumps"
        assert config.delimiter == ","
        assert config.encoding == "utf-8"

    def test_generic_connector_config(self):
        sql_config = SQLServerConnectionConfig(database="TestDB")
        connector = ConnectorConfig(source_type="sqlserver", sqlserver=sql_config)
        assert connector.source_type == "sqlserver"
        assert connector.sqlserver.database == "TestDB"

    def test_connection_test_request_response(self):
        req = ConnectionTestRequest(source_type="sqlserver", config={"database": "TestDB"})
        assert req.source_type == "sqlserver"
        res = ConnectionTestResponse(
            success=True,
            message="Connected successfully",
            latency_ms=12.5,
            server_version="Microsoft SQL Server 2019",
            database_name="TestDB",
            tables_count=5,
            tables=["Customers", "Items", "Sales", "Invoices", "Suppliers"]
        )
        assert res.success is True
        assert res.tables_count == 5
        assert len(res.tables) == 5


class TestSchemaDiscoveryModels:
    def test_column_metadata(self):
        col = ColumnMetadata(
            name="CustomerID",
            data_type="INT",
            is_primary_key=True,
            is_nullable=False
        )
        assert col.name == "CustomerID"
        assert col.is_primary_key is True
        assert col.is_nullable is False

    def test_table_metadata(self):
        col1 = ColumnMetadata(name="id", is_primary_key=True)
        col2 = ColumnMetadata(name="name", data_type="NVARCHAR")
        table = TableMetadata(
            table_name="Customers",
            columns=[col1, col2],
            column_names=["id", "name"],
            primary_key=["id"],
            row_count_estimate=1200
        )
        assert table.table_name == "Customers"
        assert len(table.columns) == 2
        assert table.row_count_estimate == 1200

    def test_schema_discovery_request_response(self):
        req = SchemaDiscoveryRequest(source_type="sqlserver", config={"database": "TestDB"})
        assert req.table_filter is None
        res = SchemaDiscoveryResponse(
            success=True,
            database_name="TestDB",
            tables_count=1,
            tables=["Customers"],
            schemas={"Customers": TableMetadata(table_name="Customers")}
        )
        assert res.success is True
        assert "Customers" in res.schemas

    def test_table_preview_request_response(self):
        req = TablePreviewRequest(source_type="sqlserver", config={}, table_name="Customers", limit=10)
        assert req.limit == 10
        res = TablePreviewResponse(
            table_name="Customers",
            columns=["id", "name"],
            sample_rows=[{"id": 1, "name": "Acme Corp"}],
            row_count=1
        )
        assert res.row_count == 1
        assert res.sample_rows[0]["name"] == "Acme Corp"


class TestMappingModels:
    def test_field_mapping_rule(self):
        rule = FieldMappingRule(
            source_field="CustName",
            target_field="name",
            target_type="string",
            transform="trim",
            is_required=True
        )
        assert rule.source_field == "CustName"
        assert rule.target_field == "name"
        assert rule.transform == "trim"

    def test_table_mapping_rule(self):
        rule = TableMappingRule(
            entity_type="customers",
            target_tcode="T0010",
            target_table="t0010",
            source_table="tbl_Customers",
            field_mappings={"CustName": "name", "CustPhone": "phone"},
            enabled=True
        )
        assert rule.target_tcode == "T0010"
        assert rule.field_mappings["CustName"] == "name"

    def test_migration_mapping_config(self):
        config = MigrationMappingConfig(
            mappings={
                "customers": TableMappingRule(
                    entity_type="customers",
                    target_tcode="T0010",
                    target_table="t0010",
                    source_table="tbl_Customers"
                )
            },
            auto_fuzzy_match=True
        )
        assert "customers" in config.mappings
        assert config.auto_fuzzy_match is True


class TestCleansingModels:
    def test_data_cleansing_config(self):
        config = DataCleansingConfig(
            enable_phantom_detection=True,
            phantom_inactivity_months=12,
            phantom_action="flag",
            default_uom="PCS"
        )
        assert config.enable_phantom_detection is True
        assert config.phantom_inactivity_months == 12
        assert config.default_uom == "PCS"

    def test_cleansing_log_and_summary(self):
        log_item = CleansingLogItem(
            entity_type="products",
            source_key="SKU-001",
            rule="phantom_zero_stock",
            original_value=0,
            cleansed_value=None,
            action_taken="flag",
            message="Zero stock product flagged as phantom"
        )
        summary = CleansingSummary(
            total_records_processed=100,
            phantom_products_detected=5,
            logs_sample=[log_item]
        )
        assert summary.total_records_processed == 100
        assert summary.phantom_products_detected == 5
        assert len(summary.logs_sample) == 1


class TestDryRunAndReconciliationModels:
    def test_dry_run_request_result(self):
        req = DryRunRequest(source_type="sqlserver", connection_config={"database": "TestDB"})
        assert req.source_type == "sqlserver"

        err = RowValidationError(
            row_index=1,
            source_key="CUST-01",
            entity_type="customers",
            error_type="missing_required",
            message="Customer name is required"
        )
        result = DryRunResult(
            batch_key="BATCH-2026-001",
            success=True,
            total_source_rows=150,
            valid_rows_count=149,
            error_rows_count=1,
            validation_errors=[err],
            ready_for_commit=True
        )
        assert result.success is True
        assert result.valid_rows_count == 149
        assert len(result.validation_errors) == 1

    def test_customer_balance_reconciliation(self):
        item = CustomerBalanceItem(
            customer_key="CUST-001",
            customer_name="Client A",
            legacy_balance=1500.0,
            nova_balance=1500.0,
            delta=0.0,
            is_matched=True
        )
        recon = CustomerBalanceReconciliation(
            total_legacy_receivables=1500.0,
            total_nova_receivables=1500.0,
            total_receivables_delta=0.0,
            customers_count=1,
            matched_count=1,
            mismatched_count=0,
            discrepancies=[],
            is_reconciled=True
        )
        assert recon.is_reconciled is True
        assert recon.total_receivables_delta == 0.0

    def test_inventory_reconciliation(self):
        wh_summary = WarehouseReconciliationSummary(
            warehouse_name="Main Warehouse",
            legacy_total_quantity=500.0,
            nova_total_quantity=500.0,
            quantity_delta=0.0,
            legacy_total_valuation=10000.0,
            nova_total_valuation=10000.0,
            valuation_delta=0.0,
            item_count=20
        )
        inv_recon = InventoryReconciliation(
            total_legacy_quantity=500.0,
            total_nova_quantity=500.0,
            total_quantity_delta=0.0,
            total_legacy_valuation=10000.0,
            total_nova_valuation=10000.0,
            total_valuation_delta=0.0,
            warehouse_summaries={"Main Warehouse": wh_summary},
            is_reconciled=True
        )
        assert inv_recon.is_reconciled is True
        assert "Main Warehouse" in inv_recon.warehouse_summaries

    def test_reconciliation_report(self):
        report = ReconciliationReport(
            batch_key="BATCH-001",
            report_date=datetime.now(),
            overall_status="Passed",
            entity_counts={
                "customers": EntityCountReconciliation(
                    entity_type="customers",
                    source_count=100,
                    staged_count=100,
                    match_status="Matched"
                )
            }
        )
        assert report.overall_status == "Passed"
        assert report.entity_counts["customers"].source_count == 100


class TestCommitAndRollbackModels:
    def test_commit_request_response(self):
        req = CommitMigrationRequest(batch_id=42, business_id=1, force=False)
        assert req.batch_id == 42
        assert req.business_id == 1

        res = CommitMigrationResponse(
            batch_id=42,
            batch_key="BATCH-001",
            status="Committed",
            total_inserted=150,
            inserted_by_entity={"customers": 50, "products": 100}
        )
        assert res.status == "Committed"
        assert res.total_inserted == 150

    def test_rollback_request_response(self):
        req = RollbackMigrationRequest(batch_id=42, reason="Incorrect data mapping", business_id=1)
        assert req.batch_id == 42
        assert req.reason == "Incorrect data mapping"

        res = RollbackMigrationResponse(
            batch_id=42,
            batch_key="BATCH-001",
            status="RolledBack",
            total_deleted=150,
            deleted_by_entity={"customers": 50, "products": 100}
        )
        assert res.status == "RolledBack"
        assert res.total_deleted == 150

    def test_migration_batch_responses(self):
        batch = MigrationBatchResponse(
            id=1,
            batch_key="BATCH-001",
            entity_type="all",
            source_type="sqlserver",
            total_rows=200,
            inserted_rows=200,
            status="Committed",
            dry_run_completed=True
        )
        assert batch.id == 1
        assert batch.status == "Committed"

        item = MigrationBatchItemResponse(
            id=10,
            batch_id=1,
            entity_type="products",
            target_table="t0003",
            target_id=101,
            source_key="SKU-001",
            status="Inserted",
            business_id=1
        )
        assert item.target_id == 101
        assert item.status == "Inserted"

        batch_list = MigrationBatchListResponse(
            items=[batch],
            total=1,
            page=1,
            page_size=50
        )
        assert batch_list.total == 1
        assert len(batch_list.items) == 1
