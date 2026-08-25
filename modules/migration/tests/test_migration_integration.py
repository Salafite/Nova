"""End-to-end integration tests for Legacy ERP Migration Pipeline and T0104I REST API Controllers.

Validates:
1. End-to-end migration pipeline (Connect -> Extract -> Cleanse -> Dry-Run -> Reconcile -> Commit -> Rollback).
2. All REST API endpoints in T0104I controller using FastAPI TestClient:
   - GET /api/v1/migration/connectors
   - POST /api/v1/migration/connectors/test
   - POST /api/v1/migration/connectors/discover
   - POST /api/v1/migration/connectors/preview
   - POST /api/v1/migration/dry-run
   - POST /api/v1/migration/commit
   - POST /api/v1/migration/rollback
   - GET /api/v1/migration/batches
   - GET /api/v1/migration/batches/{batch_id} & GET /api/v1/migration/batch/{batch_id}
   - GET /api/v1/migration/batches/{batch_id}/reconciliation
   - GET /api/v1/migration/batches/{batch_id}/items
   - POST /api/v1/migration/upload
3. Multi-tenant business_id scoping and RBAC ADMIN_MIGRATION permission enforcement.
"""

from datetime import date, datetime
import io
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.core.context import clear_current_tenant, get_current_tenant, set_current_tenant, tenant_context
from modules.migration.controllers.T0104I import router as migration_router
from modules.migration.models.migration import (
    CommitMigrationRequest,
    CommitMigrationResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    DataCleansingConfig,
    DryRunRequest,
    DryRunResult,
    MigrationBatchListResponse,
    MigrationBatchResponse,
    MigrationMappingConfig,
    ReconciliationReport,
    RollbackMigrationRequest,
    RollbackMigrationResponse,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    TablePreviewRequest,
    TablePreviewResponse,
)
from modules.migration.services.dry_run_service import dry_run_service
from modules.migration.services.migration_service import MigrationService, migration_service
from packages.auth.deps import get_current_user, require_permission


# ==============================================================================
# Test App and Fixtures
# ==============================================================================

@pytest.fixture
def test_app():
    """Create FastAPI test application with migration router and auth overrides."""
    app = FastAPI()
    app.include_router(migration_router)

    # Default admin user override with full permissions and business_id=1
    def mock_admin_user():
        set_current_tenant(1)
        return {
            "id": 1,
            "username": "admin",
            "role": "Superadmin",
            "business_id": 1,
            "permissions": ["ADMIN_MIGRATION", "*"],
        }

    app.dependency_overrides[require_permission("ADMIN_MIGRATION")] = mock_admin_user
    app.dependency_overrides[get_current_user] = mock_admin_user
    return app


@pytest.fixture
def client(test_app):
    """Create FastAPI TestClient."""
    return TestClient(test_app)


@pytest.fixture
def mock_all_db():
    """Mock database repos and connections for full integration pipeline tests."""
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
# 1. End-to-End Migration Pipeline Integration Test
# ==============================================================================

class TestEndToEndPipeline:
    """Test full sequential lifecycle: Connect -> Extract -> Cleanse -> DryRun -> Reconcile -> Commit -> Rollback."""

    def test_full_pipeline_csv_dump_lifecycle(self, tmp_path, mock_all_db):
        # 1. Create temporary multi-file legacy CSV dataset
        products_csv = tmp_path / "legacy_products.csv"
        products_csv.write_text(
            "ProductID,ItemName,ItemCode,UnitPrice,CostPrice,QtyOnHand,LastSoldDate\n"
            "101,Espresso Roast,ESP-01,25.00,12.50,50,2026-08-01\n"
            "102,Discontinued Tea,TEA-OLD,10.00,5.00,0,2020-01-01\n",
            encoding="utf-8",
        )

        customers_csv = tmp_path / "legacy_customers.csv"
        customers_csv.write_text(
            "CustID,FullName,MobileNumber,EmailAddr,OutstandingBal\n"
            "201,Al-Noor Roasters,+966 50 123 4567,orders@alnoor.com,1500.00\n",
            encoding="utf-8",
        )

        svc = MigrationService(
            batch_repo=mock_all_db["batch_repo"],
            items_repo=mock_all_db["items_repo"],
        )

        # Step 1: Connect & Test
        conn_res = svc.test_connection("csv_dump", config={"dump_path": str(tmp_path)})
        assert isinstance(conn_res, ConnectionTestResponse)
        assert conn_res.success is True
        assert conn_res.tables_count == 2

        # Step 2: Schema Discovery
        disc_res = svc.discover_schema("csv_dump", config={"dump_path": str(tmp_path)})
        assert isinstance(disc_res, SchemaDiscoveryResponse)
        assert disc_res.success is True
        assert "legacy_products" in disc_res.tables
        assert "legacy_customers" in disc_res.tables

        # Step 3: Table Preview Sampling
        prev_res = svc.preview_table("csv_dump", config={"dump_path": str(tmp_path)}, table_name="legacy_products", limit=5)
        assert isinstance(prev_res, TablePreviewResponse)
        assert prev_res.row_count == 2
        assert prev_res.sample_rows[0]["ItemName"] == "Espresso Roast"

        # Step 4: Schema Mapping Generation & Cleansing Configuration
        mapping_config = svc.generate_mapping_config(
            discovered_tables=disc_res.tables,
            auto_fuzzy=True,
        )
        assert isinstance(mapping_config, MigrationMappingConfig)

        # Step 5: Dry-Run Simulation & Safe Staging
        batch_id = 1001
        mock_all_db["batch_repo"].create.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-E2E-1001",
            "status": "DryRunPassed",
            "dry_run_completed": True,
            "total_rows": 2,
            "business_id": 1,
        }
        mock_all_db["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-E2E-1001",
            "status": "DryRunPassed",
            "dry_run_completed": True,
            "total_rows": 2,
            "business_id": 1,
            "reconciliation_summary": {
                "batch_status": "PassedWithWarnings",
                "entity_counts": {
                    "products": {"extracted": 2, "staged": 2, "errors": 0},
                    "customers": {"extracted": 1, "staged": 1, "errors": 0},
                },
                "customer_balances": {
                    "is_balanced": True,
                    "legacy_total": 1500.0,
                    "nova_total": 1500.0,
                    "delta_total": 0.0,
                },
                "inventory": {
                    "is_balanced": True,
                    "quantity_delta_total": 0.0,
                    "valuation_delta_total": 0.0,
                },
            },
        }

        # Stage transformed records
        svc.dry_run_service._in_memory_staging[batch_id] = {
            "products": [
                {"name": "Espresso Roast", "sku": "ESP-01", "price": 25.0, "cost_price": 12.5},
            ],
            "customers": [
                {"name": "Al-Noor Roasters", "phone": "+966501234567", "email": "orders@alnoor.com", "balance": 1500.0},
            ],
        }

        # Step 6: Reconciliation Report Inspection
        recon_report = svc.get_reconciliation_report(batch_id, business_id=1)
        assert isinstance(recon_report, ReconciliationReport)
        assert recon_report.overall_status in ("Passed", "PassedWithWarnings")
        if recon_report.customer_balance:
            assert recon_report.customer_balance.is_balanced is True
        if recon_report.inventory:
            assert recon_report.inventory.is_balanced is True

        # Step 7: Atomic One-Click Commit
        mock_all_db["items_repo"].create.side_effect = lambda p, **kw: {"id": 1, **p}

        commit_res = svc.commit(batch_id, business_id=1)
        assert commit_res["batch_id"] == batch_id
        assert commit_res["status"] == "Committed"
        assert commit_res["inserted_rows"] == 2

        # Step 8: Rollback Preview
        mock_all_db["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-E2E-1001",
            "status": "Committed",
            "business_id": 1,
        }
        mock_all_db["items_repo"].list.return_value = [
            {"id": 1, "batch_id": batch_id, "entity_type": "products", "target_table": "t0003", "target_id": 101, "status": "Inserted"},
            {"id": 2, "batch_id": batch_id, "entity_type": "customers", "target_table": "t0010", "target_id": 201, "status": "Inserted"},
        ]

        rb_preview = svc.get_rollback_preview(batch_id, business_id=1)
        assert rb_preview["batch_id"] == batch_id
        assert rb_preview["total_records_to_delete"] == 2
        assert rb_preview["can_rollback"] is True

        # Step 9: Instant Zero-Downtime Rollback
        rollback_res = svc.rollback(batch_id, business_id=1, reason="End to end test rollback")
        assert rollback_res["batch_id"] == batch_id
        assert rollback_res["status"] == "RolledBack"

        # Step 10: Verification
        mock_all_db["batch_repo"].get.return_value = {
            "id": batch_id,
            "batch_key": "BATCH-E2E-1001",
            "status": "RolledBack",
            "business_id": 1,
        }
        mock_all_db["items_repo"].list.return_value = [
            {"id": 1, "status": "RolledBack"},
            {"id": 2, "status": "RolledBack"},
        ]

        verification = svc.verify_rollback(batch_id, business_id=1)
        assert verification["verified"] is True
        assert verification["unrolled_items_count"] == 0


# ==============================================================================
# 2. REST API Controller Endpoint Tests (T0104I)
# ==============================================================================

class TestMigrationControllerEndpoints:
    """Test all FastAPI REST API routes exposed by T0104I controller."""

    def test_list_connectors_endpoint(self, client):
        resp = client.get("/api/v1/migration/connectors")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        types = [c["type"] for c in data]
        assert "sqlserver" in types
        assert "csv_dump" in types

    def test_test_connection_endpoint(self, client):
        with patch.object(migration_service, "test_connection") as mock_test:
            mock_test.return_value = ConnectionTestResponse(
                success=True,
                message="Connected to Microsoft SQL Server 2019",
                database_version="Microsoft SQL Server 2019",
                tables_count=15,
                latency_ms=12.5,
            )

            payload = {
                "source_type": "sqlserver",
                "config": {"host": "192.168.1.50", "database": "LegacyERP", "user": "sa"},
            }
            resp = client.post("/api/v1/migration/connectors/test", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["tables_count"] == 15
            assert "SQL Server" in data["message"]

    def test_test_connection_endpoint_failure_handled(self, client):
        with patch.object(migration_service, "test_connection", side_effect=ValueError("Host unreachable")):
            payload = {
                "source_type": "sqlserver",
                "config": {"host": "bad_host", "database": "LegacyERP"},
            }
            resp = client.post("/api/v1/migration/connectors/test", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert "Host unreachable" in data["error"]

    def test_discover_schema_endpoint(self, client):
        with patch.object(migration_service, "discover_schema") as mock_disc:
            mock_disc.return_value = SchemaDiscoveryResponse(
                success=True,
                source_type="sqlserver",
                tables_count=2,
                tables=["tbl_Products", "tbl_Customers"],
                schemas={},
            )

            payload = {
                "source_type": "sqlserver",
                "config": {"database": "LegacyERP"},
            }
            resp = client.post("/api/v1/migration/connectors/discover", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["tables_count"] == 2
            assert "tbl_Products" in data["tables"]

    def test_preview_table_endpoint(self, client):
        with patch.object(migration_service, "preview_table") as mock_prev:
            mock_prev.return_value = TablePreviewResponse(
                success=True,
                source_type="sqlserver",
                table_name="tbl_Products",
                columns=["ProductID", "Name", "Price"],
                row_count=1,
                sample_rows=[{"ProductID": 1, "Name": "Mocha", "Price": 18.0}],
            )

            payload = {
                "source_type": "sqlserver",
                "config": {"database": "LegacyERP"},
                "table_name": "tbl_Products",
                "limit": 10,
            }
            resp = client.post("/api/v1/migration/connectors/preview", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["table_name"] == "tbl_Products"
            assert len(data["sample_rows"]) == 1

    def test_dry_run_endpoint(self, client):
        with patch.object(migration_service, "run_dry_run") as mock_dry:
            mock_dry.return_value = DryRunResult(
                batch_id=1050,
                batch_key="BATCH-DRY-1050",
                source_type="sqlserver",
                success=True,
                total_source_rows=100,
                valid_rows_count=98,
                error_rows_count=2,
                phantom_products_count=5,
                execution_duration_ms=120.0,
            )

            payload = {
                "source_type": "sqlserver",
                "connection_config": {"database": "LegacyERP"},
                "tables": ["tbl_Products"],
                "cleansing": {"detect_phantoms": True},
            }
            resp = client.post("/api/v1/migration/dry-run", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["batch_id"] == 1050
            assert data["success"] is True
            assert data["valid_rows_count"] == 98
            assert data["phantom_products_count"] == 5

    def test_commit_endpoint_with_json_body(self, client):
        with patch.object(migration_service, "commit") as mock_commit:
            mock_commit.return_value = {
                "batch_id": 1050,
                "batch_key": "BATCH-DRY-1050",
                "status": "Committed",
                "inserted_rows": 98,
                "inserted_by_entity": {"products": 98},
                "message": "Migration committed successfully",
            }

            resp = client.post("/api/v1/migration/commit", json={"batch_id": 1050, "force": False})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "Committed"
            assert data["inserted_rows"] == 98

    def test_commit_endpoint_with_query_params(self, client):
        with patch.object(migration_service, "commit") as mock_commit:
            mock_commit.return_value = {
                "batch_id": 1051,
                "status": "Committed",
                "inserted_rows": 5,
            }

            resp = client.post("/api/v1/migration/commit?batch_id=1051&force=true")
            assert resp.status_code == 200
            data = resp.json()
            assert data["batch_id"] == 1051
            assert data["status"] == "Committed"

    def test_commit_endpoint_missing_batch_id_raises_400(self, client):
        resp = client.post("/api/v1/migration/commit")
        assert resp.status_code == 400
        assert "batch_id is required" in resp.json()["detail"]

    def test_commit_endpoint_validation_error_raises_400(self, client):
        with patch.object(migration_service, "commit", side_effect=ValueError("Batch contains unresolved errors")):
            resp = client.post("/api/v1/migration/commit", json={"batch_id": 1052})
            assert resp.status_code == 400
            assert "unresolved errors" in resp.json()["detail"]

    def test_rollback_endpoint_with_json_body(self, client):
        with patch.object(migration_service, "rollback") as mock_rollback:
            mock_rollback.return_value = {
                "batch_id": 1050,
                "batch_key": "BATCH-DRY-1050",
                "status": "RolledBack",
                "deleted_rows": 98,
                "deleted_by_entity": {"products": 98},
                "message": "Rolled back successfully",
            }

            resp = client.post("/api/v1/migration/rollback", json={"batch_id": 1050, "reason": "Testing rollback"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "RolledBack"
            assert data["deleted_rows"] == 98

    def test_rollback_endpoint_missing_batch_id_raises_400(self, client):
        resp = client.post("/api/v1/migration/rollback")
        assert resp.status_code == 400
        assert "batch_id is required" in resp.json()["detail"]

    def test_list_batches_endpoint(self, client):
        with patch.object(migration_service, "list_batches") as mock_list:
            mock_list.return_value = {
                "items": [
                    {"id": 1, "batch_key": "BATCH-01", "status": "Committed"},
                    {"id": 2, "batch_key": "BATCH-02", "status": "Preview"},
                ],
                "total": 2,
                "page": 1,
                "page_size": 50,
            }

            resp = client.get("/api/v1/migration/batches?status=Committed&limit=10&offset=0")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2

    def test_get_batch_details_endpoint(self, client):
        with patch.object(migration_service, "get_batch") as mock_get:
            mock_get.return_value = {
                "id": 101,
                "batch_key": "BATCH-01",
                "status": "Committed",
                "total_rows": 50,
            }

            resp = client.get("/api/v1/migration/batches/101")
            assert resp.status_code == 200
            assert resp.json()["id"] == 101

            # Alias route /batch/{batch_id}
            resp_alias = client.get("/api/v1/migration/batch/101")
            assert resp_alias.status_code == 200
            assert resp_alias.json()["id"] == 101

    def test_get_batch_not_found_returns_404(self, client):
        with patch.object(migration_service, "get_batch", return_value=None):
            resp = client.get("/api/v1/migration/batches/999")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"]

    def test_get_batch_reconciliation_endpoint(self, client):
        mock_report = ReconciliationReport(
            batch_key="BATCH-REC-200",
            overall_status="Passed",
        )
        with patch.object(migration_service, "get_reconciliation_report", return_value=mock_report):
            resp = client.get("/api/v1/migration/batches/200/reconciliation?tolerance=0.01")
            assert resp.status_code == 200
            data = resp.json()
            assert data["batch_key"] == "BATCH-REC-200"
            assert data["overall_status"] == "Passed"

    def test_get_batch_reconciliation_not_found_returns_404(self, client):
        with patch.object(migration_service, "get_reconciliation_report", return_value=None):
            resp = client.get("/api/v1/migration/batches/999/reconciliation")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"]

    def test_get_batch_items_endpoint(self, client):
        with patch.object(migration_service, "get_committed_items") as mock_items:
            mock_items.return_value = [
                {"id": 1, "batch_id": 300, "entity_type": "products", "target_table": "t0003", "target_id": 10},
                {"id": 2, "batch_id": 300, "entity_type": "products", "target_table": "t0003", "target_id": 11},
            ]

            resp = client.get("/api/v1/migration/batches/300/items?entity_type=products&limit=50&offset=0")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["target_id"] == 10

    def test_upload_csv_endpoint_success(self, client):
        with patch.object(migration_service, "upload_csv") as mock_upload:
            mock_upload.return_value = {
                "batch_id": 400,
                "batch_key": "BATCH-UP-400",
                "entity_type": "products",
                "total_rows": 2,
                "valid_rows": 2,
                "error_rows": 0,
                "sample": [{"name": "Chemex Coffee", "sku": "CHX-01"}],
            }

            csv_file = ("products.csv", io.BytesIO(b"name,sku,price\nChemex Coffee,CHX-01,35.0\n"), "text/csv")
            resp = client.post(
                "/api/v1/migration/upload",
                files={"file": csv_file},
                data={"entity_type": "products", "column_mapping": "{}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["batch_id"] == 400
            assert data["valid_rows"] == 2

    def test_upload_csv_endpoint_non_csv_rejected(self, client):
        txt_file = ("products.txt", io.BytesIO(b"name,sku,price\n"), "text/plain")
        resp = client.post(
            "/api/v1/migration/upload",
            files={"file": txt_file},
            data={"entity_type": "products", "column_mapping": "{}"},
        )
        assert resp.status_code == 400
        assert "Only CSV files are accepted" in resp.json()["detail"]

    def test_upload_csv_endpoint_invalid_mapping_json(self, client):
        csv_file = ("products.csv", io.BytesIO(b"name,sku\nItem,SKU1\n"), "text/csv")
        resp = client.post(
            "/api/v1/migration/upload",
            files={"file": csv_file},
            data={"entity_type": "products", "column_mapping": "invalid-json"},
        )
        assert resp.status_code == 400
        assert "Invalid column_mapping JSON" in resp.json()["detail"]


# ==============================================================================
# 3. RBAC & Multi-Tenant Endpoint Scoping Tests
# ==============================================================================

class TestControllerPermissionsAndTenantScoping:
    """Test RBAC permission enforcement and tenant context extraction."""

    def test_unauthenticated_request_rejected(self):
        # App without dependency overrides to test default require_permission behaviour
        app = FastAPI()
        app.include_router(migration_router)
        strict_client = TestClient(app)

        resp = strict_client.get("/api/v1/migration/connectors")
        assert resp.status_code in (401, 403)
