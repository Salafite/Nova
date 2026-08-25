"""MCP Migration Server for Legacy ERP Database Connector & Migration Bridge.

Exposes AI tools for natural language migration operations:
- test_legacy_connection (Tier 1): Test connection to legacy database or dump.
- discover_legacy_schema (Tier 1): Discover tables, columns, primary/foreign keys, and row counts.
- run_migration_dry_run (Tier 1): Run dry-run simulation without touching production tables.
- get_migration_reconciliation (Tier 1): Retrieve customer balance and inventory reconciliation report.
- commit_migration_batch (Tier 2 - Propose/Confirm): Transactional commit with rollback tracking.
- rollback_migration_batch (Tier 2 - Propose/Confirm): Zero-downtime rollback in reverse FK order.
"""

from typing import Any, Dict, List, Optional, Union
import json
import logging

from modules.core.context import get_current_tenant
from modules.migration.models.migration import (
    CommitMigrationRequest,
    ConnectionTestRequest,
    DataCleansingConfig,
    DryRunRequest,
    MigrationMappingConfig,
    RollbackMigrationRequest,
    SchemaDiscoveryRequest,
    TablePreviewRequest,
)
from modules.migration.services.migration_service import (
    MigrationService,
    migration_service as default_migration_service,
)
from packages.mcp.registry import register_tool, register_resource, get_current_user
from packages.mcp.types import Tool, Resource

logger = logging.getLogger(__name__)

_migration_svc: MigrationService = default_migration_service


def register_tools() -> None:
    """Register all MCP tools and resources for the migration module."""
    register_tool(
        Tool(
            name="test_legacy_connection",
            description="Test connectivity to a legacy database (e.g. SQL Server) or multi-table CSV / SQL dump directory",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "description": "Legacy connector source type: 'sqlserver', 'csv_dump', 'sqldump' (default 'sqlserver')",
                        "enum": ["sqlserver", "csv_dump", "sqldump"],
                    },
                    "config": {
                        "type": "object",
                        "description": "Connection parameters such as host, port, database, user, password, trust_server_certificate, dump_path",
                    },
                },
            },
        ),
        _test_legacy_connection,
    )
    register_tool(
        Tool(
            name="discover_legacy_schema",
            description="Discover legacy database tables, column definitions, data types, primary keys, and row counts",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "description": "Legacy connector source type: 'sqlserver', 'csv_dump', 'sqldump' (default 'sqlserver')",
                        "enum": ["sqlserver", "csv_dump", "sqldump"],
                    },
                    "config": {
                        "type": "object",
                        "description": "Connection parameters",
                    },
                    "table_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of table names to introspect",
                    },
                },
            },
        ),
        _discover_legacy_schema,
    )
    register_tool(
        Tool(
            name="run_migration_dry_run",
            description="Run an end-to-end dry-run migration simulation: extract, cleanse, transform, and stage legacy data into temporary batch tables with zero production impact",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "description": "Legacy connector source type ('sqlserver', 'csv_dump', 'sqldump')",
                        "enum": ["sqlserver", "csv_dump", "sqldump"],
                    },
                    "config": {
                        "type": "object",
                        "description": "Connection parameters",
                    },
                    "table_mappings": {
                        "type": "object",
                        "description": "Optional table-to-entity mapping rules",
                    },
                    "cleansing_options": {
                        "type": "object",
                        "description": "Optional data cleansing parameters (phantom_inactivity_months, deduplicate_skus, sanitize_contacts, etc.)",
                    },
                    "selected_entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of entities to migrate (e.g. ['products', 'customers', 'suppliers'])",
                    },
                    "sample_limit": {
                        "type": "integer",
                        "description": "Optional maximum number of records to sample per entity",
                    },
                    "records_by_entity": {
                        "type": "object",
                        "description": "Optional in-memory dataset grouped by entity to simulate",
                    },
                },
            },
        ),
        _run_migration_dry_run,
    )
    register_tool(
        Tool(
            name="get_migration_reconciliation",
            description="Get comprehensive balance and inventory reconciliation reports for a migration batch, identifying customer receivable deltas and inventory stock/valuation variances",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "batch_id": {
                        "type": "integer",
                        "description": "Migration batch ID (from table Nova.t0104)",
                    },
                    "batch_key": {
                        "type": "string",
                        "description": "Unique batch key identifier (alternative to batch_id)",
                    },
                    "tolerance": {
                        "type": "number",
                        "description": "Variance tolerance threshold (default 0.01)",
                    },
                },
            },
        ),
        _get_migration_reconciliation,
    )
    register_tool(
        Tool(
            name="commit_migration_batch",
            description="Commit staged migration batch into active Nova ERP business tables in dependency order with record-level rollback tracking. [REQUIRES CONFIRMATION]",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "batch_id": {
                        "type": "integer",
                        "description": "Migration batch ID to commit into production",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force commit even if non-critical validation warnings or variances exist (default false)",
                    },
                },
                "required": ["batch_id"],
            },
        ),
        _commit_migration_batch,
    )
    register_tool(
        Tool(
            name="rollback_migration_batch",
            description="Instantly roll back a committed or preview migration batch with zero downtime, deleting inserted records in reverse dependency order. [REQUIRES CONFIRMATION]",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "batch_id": {
                        "type": "integer",
                        "description": "Migration batch ID to roll back",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional audit reason for rolling back the batch",
                    },
                },
                "required": ["batch_id"],
            },
        ),
        _rollback_migration_batch,
    )
    register_resource(
        Resource(
            uri="nova://migration/batches",
            name="Migration Batches",
            description="List of recent legacy ERP migration batches",
        ),
        _list_migration_batches,
    )
    register_resource(
        Resource(
            uri="nova://migration/connectors",
            name="Supported Connectors",
            description="List of supported legacy database connectors and extractors",
        ),
        _list_supported_connectors,
    )


def _get_active_tenant_id() -> Optional[int]:
    """Resolve active tenant ID from MCP user context or contextvars."""
    current_user = get_current_user()
    tenant_id = None
    if isinstance(current_user, dict):
        tenant_id = current_user.get("business_id")
        if tenant_id is None:
            tenant_id = current_user.get("tenant_id")
    if tenant_id is None:
        tenant_id = get_current_tenant()
    return tenant_id


def _test_legacy_connection(
    source_type: str = "sqlserver",
    config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Handler for test_legacy_connection tool."""
    conn_config = dict(config or {})
    conn_config.update(kwargs)
    res = _migration_svc.test_connection(source_type=source_type, config=conn_config)
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _discover_legacy_schema(
    source_type: str = "sqlserver",
    config: Optional[Dict[str, Any]] = None,
    table_filter: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Handler for discover_legacy_schema tool."""
    conn_config = dict(config or {})
    conn_config.update(kwargs)
    res = _migration_svc.discover_schema(
        source_type=source_type,
        config=conn_config,
        table_filter=table_filter,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _run_migration_dry_run(
    source_type: str = "sqlserver",
    config: Optional[Dict[str, Any]] = None,
    table_mappings: Optional[Dict[str, Any]] = None,
    cleansing_options: Optional[Dict[str, Any]] = None,
    selected_entities: Optional[List[str]] = None,
    sample_limit: Optional[int] = None,
    records_by_entity: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Handler for run_migration_dry_run tool."""
    tenant_id = _get_active_tenant_id()
    conn_config = dict(config or {})
    conn_config.update(kwargs)

    if records_by_entity:
        cleansing_cfg = DataCleansingConfig(**cleansing_options) if cleansing_options else None
        res = _migration_svc.run_dry_run_from_records(
            records_by_entity=records_by_entity,
            cleansing_config=cleansing_cfg,
            source_type=source_type,
            connection_config=conn_config,
            tenant_id=tenant_id,
        )
    else:
        req = DryRunRequest(
            source_type=source_type,
            connection_config=conn_config,
            selected_entities=selected_entities,
            sample_limit=sample_limit,
            tenant_id=tenant_id,
        )
        if cleansing_options:
            req.cleansing_config = DataCleansingConfig(**cleansing_options)
        if table_mappings:
            if isinstance(table_mappings, MigrationMappingConfig):
                req.mapping_config = table_mappings
            elif isinstance(table_mappings, dict):
                req.mapping_config = _migration_svc.mapping_engine.generate_mapping_config(
                    discovered_tables=list(table_mappings.keys()),
                    custom_overrides=table_mappings if any(isinstance(v, dict) for v in table_mappings.values()) else None,
                )
        res = _migration_svc.run_dry_run(request=req, tenant_id=tenant_id)

    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _get_migration_reconciliation(
    batch_id: Optional[int] = None,
    batch_key: Optional[str] = None,
    tolerance: float = 0.01,
) -> Dict[str, Any]:
    """Handler for get_migration_reconciliation tool."""
    tenant_id = _get_active_tenant_id()
    identifier = batch_id if batch_id is not None else batch_key
    if identifier is None:
        raise ValueError("Either batch_id or batch_key must be provided")

    res = _migration_svc.get_reconciliation_report(
        batch_id_or_key=identifier,
        business_id=tenant_id,
    )
    if res is None:
        return {
            "batch_key": str(identifier),
            "overall_status": "NotFound",
            "message": f"Migration batch '{identifier}' not found or has no reconciliation report available.",
        }
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _commit_migration_batch(
    batch_id: int,
    force: bool = False,
) -> Dict[str, Any]:
    """Handler for commit_migration_batch tool (Tier 2 - Propose/Confirm)."""
    tenant_id = _get_active_tenant_id()
    res = _migration_svc.commit(
        request=batch_id,
        business_id=tenant_id,
        force=force,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _rollback_migration_batch(
    batch_id: int,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Handler for rollback_migration_batch tool (Tier 2 - Propose/Confirm)."""
    tenant_id = _get_active_tenant_id()
    res = _migration_svc.rollback(
        request=batch_id,
        reason=reason,
        business_id=tenant_id,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _list_migration_batches(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Resource handler for nova://migration/batches."""
    tenant_id = _get_active_tenant_id()
    return _migration_svc.list_batches(limit=limit, offset=offset, business_id=tenant_id)


def _list_supported_connectors() -> List[Dict[str, Any]]:
    """Resource handler for nova://migration/connectors."""
    return _migration_svc.list_supported_connectors()


def main() -> None:
    """Run migration MCP server in stdio mode."""
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio

    server = McpServer(name="migration-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
