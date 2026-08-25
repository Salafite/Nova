"""Unit and integration tests for packages/mcp/servers/migration_mcp.py.

Tests:
1. Tool handler functions:
   - _test_legacy_connection
   - _discover_legacy_schema
   - _run_migration_dry_run
   - _get_migration_reconciliation
   - _commit_migration_batch (Tier 2)
   - _rollback_migration_batch (Tier 2)
2. Resource handler functions:
   - _list_migration_batches
   - _list_supported_connectors
3. Tool registration and metadata:
   - register_tools() registers all 6 tools with correct tiers and schemas
   - register_tools() registers resources
4. Propose/Confirm lifecycle for Tier 2 tools:
   - propose_action and confirm_action for commit_migration_batch
   - propose_action and confirm_action for rollback_migration_batch
5. Tenant context propagation:
   - User dict with business_id passed to MCP calls
"""

import pytest
from unittest.mock import patch, MagicMock

from modules.migration.models.migration import (
    CommitMigrationResponse,
    ConnectionTestResponse,
    DryRunResult,
    ReconciliationReport,
    RollbackMigrationResponse,
    SchemaDiscoveryResponse,
    TableMetadata,
)
from packages.mcp.servers import migration_mcp
from packages.mcp.servers.migration_mcp import register_tools
from packages.mcp.registry import (
    call_tool,
    confirm_action,
    get_tools,
    list_resources,
    propose_action,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry tools, resources, and pending actions before and after each test."""
    from packages.mcp import registry
    registry._tools.clear()
    registry._resources.clear()
    registry._pending_actions.clear()
    yield
    registry._tools.clear()
    registry._resources.clear()
    registry._pending_actions.clear()


@pytest.fixture
def mock_migration_svc():
    """Fixture providing a mocked MigrationService."""
    with patch.object(migration_mcp, "_migration_svc", MagicMock()) as mock_svc:
        yield mock_svc


class TestConnectionTools:
    """Tests for connection testing and schema discovery tools."""

    def test_test_legacy_connection(self, mock_migration_svc):
        mock_response = ConnectionTestResponse(
            success=True,
            message="Connection successful (lat: 12ms)",
            latency_ms=12.5,
            server_version="Microsoft SQL Server 2019",
            database_name="LegacyFoodDB",
            tables_count=18,
            tables=["tblProducts", "tblCustomers", "tblOrders"],
        )
        mock_migration_svc.test_connection.return_value = mock_response

        res = migration_mcp._test_legacy_connection(
            source_type="sqlserver",
            config={"host": "192.168.1.50", "database": "LegacyFoodDB"},
        )
        assert res["success"] is True
        assert res["database_name"] == "LegacyFoodDB"
        assert res["tables_count"] == 18
        assert "tblProducts" in res["tables"]
        mock_migration_svc.test_connection.assert_called_once()

    def test_discover_legacy_schema(self, mock_migration_svc):
        mock_response = SchemaDiscoveryResponse(
            success=True,
            database_name="LegacyFoodDB",
            tables_count=2,
            tables=["tblProducts", "tblCustomers"],
            schemas={
                "tblProducts": TableMetadata(
                    table_name="tblProducts",
                    column_names=["ProdID", "ProdName", "UnitPrice"],
                    primary_key=["ProdID"],
                )
            },
        )
        mock_migration_svc.discover_schema.return_value = mock_response

        res = migration_mcp._discover_legacy_schema(
            source_type="sqlserver",
            config={"host": "localhost", "database": "LegacyFoodDB"},
            table_filter=["tblProducts"],
        )
        assert res["success"] is True
        assert res["tables_count"] == 2
        assert "tblProducts" in res["schemas"]
        assert res["schemas"]["tblProducts"]["primary_key"] == ["ProdID"]
        mock_migration_svc.discover_schema.assert_called_once()


class TestDryRunTools:
    """Tests for run_migration_dry_run tool."""

    def test_run_migration_dry_run_from_request(self, mock_migration_svc):
        mock_result = DryRunResult(
            batch_key="DRY-2026-001",
            batch_id=42,
            success=True,
            total_source_rows=150,
            valid_rows_count=140,
            error_rows_count=5,
            ready_for_commit=True,
        )
        mock_migration_svc.run_dry_run.return_value = mock_result

        with patch("packages.mcp.servers.migration_mcp.get_current_user", return_value={"id": 1, "business_id": 99}):
            res = migration_mcp._run_migration_dry_run(
                source_type="sqlserver",
                config={"host": "localhost", "database": "LegacyERP"},
                selected_entities=["products", "customers"],
                sample_limit=100,
            )
            assert res["batch_id"] == 42
            assert res["batch_key"] == "DRY-2026-001"
            assert res["valid_rows_count"] == 140
            assert res["error_rows_count"] == 5
            mock_migration_svc.run_dry_run.assert_called_once()

    def test_run_migration_dry_run_from_in_memory_records(self, mock_migration_svc):
        mock_result = DryRunResult(
            batch_key="DRY-2026-002",
            batch_id=43,
            success=True,
            total_source_rows=10,
            valid_rows_count=10,
            ready_for_commit=True,
        )
        mock_migration_svc.run_dry_run_from_records.return_value = mock_result

        records = {
            "products": [
                {"name": "Burger Bun", "sku": "BUN-01", "price": 5.0},
                {"name": "Patty Beef", "sku": "PAT-01", "price": 12.0},
            ]
        }
        res = migration_mcp._run_migration_dry_run(
            source_type="csv_dump",
            records_by_entity=records,
            cleansing_options={"enable_phantom_detection": True},
        )
        assert res["batch_id"] == 43
        assert res["valid_rows_count"] == 10
        mock_migration_svc.run_dry_run_from_records.assert_called_once()


class TestReconciliationTools:
    """Tests for get_migration_reconciliation tool."""

    def test_get_migration_reconciliation_found(self, mock_migration_svc):
        mock_report = ReconciliationReport(
            batch_key="BATCH-42",
            overall_status="Passed",
            unresolved_errors_count=0,
            recommendations=["All opening balances and inventory valuations matched legacy source."],
        )
        mock_migration_svc.get_reconciliation_report.return_value = mock_report

        res = migration_mcp._get_migration_reconciliation(batch_id=42, tolerance=0.01)
        assert res["batch_key"] == "BATCH-42"
        assert res["overall_status"] == "Passed"
        assert res["unresolved_errors_count"] == 0
        mock_migration_svc.get_reconciliation_report.assert_called_with(
            batch_id_or_key=42,
            business_id=None,
        )

    def test_get_migration_reconciliation_with_batch_key(self, mock_migration_svc):
        mock_report = ReconciliationReport(
            batch_key="MIG-KEY-123",
            overall_status="PassedWithWarnings",
            unresolved_errors_count=2,
            recommendations=["Check negative inventory adjustments."],
        )
        mock_migration_svc.get_reconciliation_report.return_value = mock_report

        res = migration_mcp._get_migration_reconciliation(batch_key="MIG-KEY-123")
        assert res["batch_key"] == "MIG-KEY-123"
        assert res["overall_status"] == "PassedWithWarnings"

    def test_get_migration_reconciliation_not_found(self, mock_migration_svc):
        mock_migration_svc.get_reconciliation_report.return_value = None

        res = migration_mcp._get_migration_reconciliation(batch_id=999)
        assert res["overall_status"] == "NotFound"
        assert "not found" in res["message"]

    def test_get_migration_reconciliation_missing_args(self):
        with pytest.raises(ValueError, match="Either batch_id or batch_key must be provided"):
            migration_mcp._get_migration_reconciliation()


class TestCommitAndRollbackTools:
    """Tests for commit_migration_batch and rollback_migration_batch tools."""

    def test_commit_migration_batch(self, mock_migration_svc):
        mock_migration_svc.commit.return_value = {
            "batch_id": 10,
            "batch_key": "BATCH-10",
            "status": "Committed",
            "total_inserted": 55,
            "inserted_rows": 55,
            "inserted_by_entity": {"products": 30, "customers": 25},
            "message": "Migration committed successfully",
        }

        with patch("packages.mcp.servers.migration_mcp.get_current_user", return_value={"id": 5, "business_id": 12}):
            res = migration_mcp._commit_migration_batch(batch_id=10, force=True)
            assert res["status"] == "Committed"
            assert res["total_inserted"] == 55
            assert res["inserted_by_entity"]["products"] == 30
            mock_migration_svc.commit.assert_called_with(
                request=10,
                business_id=12,
                force=True,
            )

    def test_rollback_migration_batch(self, mock_migration_svc):
        mock_migration_svc.rollback.return_value = {
            "batch_id": 10,
            "batch_key": "BATCH-10",
            "status": "RolledBack",
            "total_deleted": 55,
            "deleted_rows": 55,
            "deleted_by_entity": {"products": 30, "customers": 25},
            "message": "Migration batch rolled back successfully",
        }

        with patch("packages.mcp.servers.migration_mcp.get_current_user", return_value={"id": 5, "business_id": 12}):
            res = migration_mcp._rollback_migration_batch(batch_id=10, reason="Data format error")
            assert res["status"] == "RolledBack"
            assert res["total_deleted"] == 55
            mock_migration_svc.rollback.assert_called_with(
                request=10,
                reason="Data format error",
                business_id=12,
            )


class TestResources:
    """Tests for MCP migration resources."""

    def test_list_migration_batches_resource(self, mock_migration_svc):
        mock_migration_svc.list_batches.return_value = {
            "items": [{"id": 1, "batch_key": "B1", "status": "Committed"}],
            "total": 1,
            "page": 1,
            "page_size": 50,
        }
        res = migration_mcp._list_migration_batches()
        assert res["total"] == 1
        assert res["items"][0]["batch_key"] == "B1"
        mock_migration_svc.list_batches.assert_called_with(
            limit=50,
            offset=0,
            business_id=None,
        )

    def test_list_supported_connectors_resource(self, mock_migration_svc):
        mock_migration_svc.list_supported_connectors.return_value = [
            {"source_type": "sqlserver", "display_name": "Microsoft SQL Server"},
            {"source_type": "csv_dump", "display_name": "Multi-table CSV & SQL Dump"},
        ]
        res = migration_mcp._list_supported_connectors()
        assert len(res) == 2
        assert res[0]["source_type"] == "sqlserver"


class TestToolRegistrationAndRegistryIntegration:
    """Tests verifying tools and resources are correctly registered with tiers."""

    def test_register_tools_registers_all(self):
        register_tools()
        tools = get_tools()
        tool_names = [t.name for t in tools]
        expected = [
            "test_legacy_connection",
            "discover_legacy_schema",
            "run_migration_dry_run",
            "get_migration_reconciliation",
            "commit_migration_batch",
            "rollback_migration_batch",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} was not registered"

        tier2_tools = [t.name for t in tools if t.tier == "tier2"]
        assert "commit_migration_batch" in tier2_tools
        assert "rollback_migration_batch" in tier2_tools

        tier1_tools = [t.name for t in tools if t.tier == "tier1" and t.name != "confirm_action"]
        assert "test_legacy_connection" in tier1_tools
        assert "discover_legacy_schema" in tier1_tools
        assert "run_migration_dry_run" in tier1_tools
        assert "get_migration_reconciliation" in tier1_tools

        resources = list_resources()
        resource_uris = [r.uri for r in resources]
        assert "nova://migration/batches" in resource_uris
        assert "nova://migration/connectors" in resource_uris

    def test_tier2_propose_and_confirm_commit(self, mock_migration_svc):
        register_tools()
        mock_migration_svc.commit.return_value = {
            "batch_id": 7,
            "status": "Committed",
            "total_inserted": 20,
            "message": "Committed successfully",
        }

        # Step 1: Propose (Tier 2 should not execute handler)
        proposal = propose_action(
            "commit_migration_batch",
            {"batch_id": 7, "force": False},
            user={"id": 1, "business_id": 10},
        )
        assert "action_id" in proposal
        assert proposal["tool"] == "commit_migration_batch"
        mock_migration_svc.commit.assert_not_called()

        # Step 2: Confirm (Executes proposed action)
        result = confirm_action(proposal["action_id"], user={"id": 1, "business_id": 10})
        assert result["status"] == "Committed"
        assert result["total_inserted"] == 20
        mock_migration_svc.commit.assert_called_once()

    def test_tier2_propose_and_confirm_rollback(self, mock_migration_svc):
        register_tools()
        mock_migration_svc.rollback.return_value = {
            "batch_id": 7,
            "status": "RolledBack",
            "total_deleted": 20,
            "message": "Rolled back successfully",
        }

        # Step 1: Propose
        proposal = propose_action(
            "rollback_migration_batch",
            {"batch_id": 7, "reason": "Test rollback"},
            user={"id": 1, "business_id": 10},
        )
        assert "action_id" in proposal
        mock_migration_svc.rollback.assert_not_called()

        # Step 2: Confirm
        result = confirm_action(proposal["action_id"], user={"id": 1, "business_id": 10})
        assert result["status"] == "RolledBack"
        assert result["total_deleted"] == 20
        mock_migration_svc.rollback.assert_called_once()

    def test_direct_call_tool_with_tenant_scoping(self, mock_migration_svc):
        register_tools()
        mock_migration_svc.test_connection.return_value = ConnectionTestResponse(
            success=True,
            message="OK",
            tables_count=3,
        )

        user_context = {"id": 42, "username": "admin", "business_id": 77}
        res = call_tool("test_legacy_connection", {"source_type": "sqlserver", "config": {}}, user=user_context)
        assert res["success"] is True
        assert res["tables_count"] == 3
