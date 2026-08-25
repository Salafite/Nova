"""Unified Orchestrator and Facade Service for Legacy ERP Migration Bridge.

Provides a single, cohesive facade for:
1. Legacy database connection testing and introspection (SQL Server, CSV dumps, SQL scripts).
2. Automated schema discovery, T-code entity mapping, and field translation rules.
3. Multi-layer data cleansing (phantom products, deduplication, contact sanitization, numeric bounds).
4. Dry-run simulation and isolated staging pipeline.
5. Opening customer balance, inventory stock, valuation, and entity count reconciliation reporting.
6. Atomic one-click commit and instant zero-downtime rollback with multi-tenant context propagation.
7. Batch history, tracking, staging inspection, and audit management.
"""

import csv
from datetime import date, datetime
import io
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.migration.connectors.base import BaseConnector
from modules.migration.connectors.factory import (
    get_connector,
    list_supported_connectors,
    validate_connection_params,
)
from modules.migration.models.migration import (
    CleansingSummary,
    CommitMigrationRequest,
    CommitMigrationResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    CustomerBalanceReconciliation,
    DataCleansingConfig,
    DryRunRequest,
    DryRunResult,
    EntityCountReconciliation,
    InventoryReconciliation,
    MigrationBatchItemResponse,
    MigrationBatchListResponse,
    MigrationBatchResponse,
    MigrationMappingConfig,
    ReconciliationReport,
    RollbackMigrationRequest,
    RollbackMigrationResponse,
    RowValidationError,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    TableMetadata,
    TablePreviewRequest,
    TablePreviewResponse,
)
from modules.migration.services.cleansing_service import (
    CleansingService,
    cleansing_service,
)
from modules.migration.services.commit_service import (
    BATCH_ITEMS_REPO,
    BATCH_REPO,
    CommitService,
    commit_service,
)
from modules.migration.services.dry_run_service import (
    DryRunService,
    dry_run_service,
)
from modules.migration.services.mapping_engine import (
    ENTITY_TARGET_SCHEMAS,
    MappingEngine,
    mapping_engine,
)
from modules.migration.services.reconciliation_service import (
    ReconciliationService,
    reconciliation_service,
)
from modules.migration.services.rollback_service import (
    RollbackService,
    rollback_service,
)

logger = logging.getLogger(__name__)

# Backward-compatible entity maps for legacy single-table migration endpoints
ENTITY_MAP = {
    "products": ("T0003", "name", ["name", "sku", "price", "cost_price", "category", "brand", "tax_rate", "image_url"]),
    "customers": ("T0010", "name", ["name", "group_name", "phone", "email", "credit_limit"]),
    "suppliers": ("T0011", "name", ["name", "category", "phone", "email", "payment_terms", "rating"]),
}

FIELD_MAP = {
    "products": {
        "name": "name", "sku": "sku", "price": "price", "cost": "cost_price",
        "category": "category", "brand": "brand", "tax": "tax_rate",
    },
    "customers": {
        "name": "name", "group": "group_name", "phone": "phone",
        "email": "email", "credit": "credit_limit",
    },
    "suppliers": {
        "name": "name", "category": "category", "phone": "phone",
        "email": "email", "terms": "payment_terms", "rating": "rating",
    },
}


class MigrationService:
    """Unified facade orchestrating connectors, mapping, cleansing, dry-runs, reconciliation, commit, and rollback."""

    def __init__(
        self,
        mapper: Optional[MappingEngine] = None,
        cleaner: Optional[CleansingService] = None,
        dry_runner: Optional[DryRunService] = None,
        reconciler: Optional[ReconciliationService] = None,
        committer: Optional[CommitService] = None,
        rollbacker: Optional[RollbackService] = None,
        batch_repo: Optional[CrudRepository] = None,
        items_repo: Optional[CrudRepository] = None,
    ) -> None:
        self.batch_repo = batch_repo or BATCH_REPO
        self.items_repo = items_repo or BATCH_ITEMS_REPO
        self.mapping_engine = mapper or mapping_engine
        self.cleansing_service = cleaner or cleansing_service
        self.dry_run_service = dry_runner or DryRunService(
            mapper=self.mapping_engine,
            cleaner=self.cleansing_service,
            batch_repo=self.batch_repo,
        )
        self.reconciliation_service = reconciler or reconciliation_service
        self.commit_service = committer or CommitService(
            batch_repo=self.batch_repo,
            items_repo=self.items_repo,
            dry_runner=self.dry_run_service,
        )
        self.rollback_service = rollbacker or RollbackService(
            batch_repo=self.batch_repo,
            items_repo=self.items_repo,
            dry_runner=self.dry_run_service,
        )

    # ==========================================================================
    # 1. Connectors, Testing & Schema Introspection
    # ==========================================================================

    def list_supported_connectors(self) -> List[Dict[str, Any]]:
        """List all supported legacy database connectors and extractor modules."""
        return list_supported_connectors()

    def list_connectors(self) -> List[Dict[str, Any]]:
        """Alias for list_supported_connectors."""
        return self.list_supported_connectors()

    def get_connector(self, source_type: str, **kwargs: Any) -> BaseConnector:
        """Instantiate a legacy connector for the specified source type."""
        return get_connector(source_type, **kwargs)

    def validate_connection_params(
        self,
        source_type: str,
        config: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Validate connection parameters for a given legacy source type."""
        res = validate_connection_params(source_type, config)
        valid = bool(res.get("valid", False))
        errors = res.get("errors", [])
        err_msg = "; ".join(errors) if errors else None
        return valid, err_msg

    def test_connection(
        self,
        source_type: Union[str, ConnectionTestRequest, Dict[str, Any]] = "sqlserver",
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ConnectionTestResponse:
        """Test connectivity and introspect metadata from a legacy database or file dump."""
        if isinstance(source_type, ConnectionTestRequest):
            src = source_type.source_type
            conn_params = dict(source_type.config)
        elif isinstance(source_type, dict):
            src = source_type.get("source_type", "sqlserver")
            conn_params = dict(source_type.get("config", source_type))
        else:
            src = source_type
            conn_params = dict(config or {})
        conn_params.update(kwargs)
        connector = self.get_connector(src, **conn_params)
        with connector:
            res = connector.test_connection()
            if isinstance(res, ConnectionTestResponse):
                return res
            return ConnectionTestResponse(
                success=res.success,
                message=res.message,
                latency_ms=res.latency_ms,
                server_version=res.server_version,
                database_name=res.database_name,
                tables_count=res.tables_count if res.tables_count is not None else len(res.tables),
                tables=res.tables,
                details=res.details,
                error=res.error,
            )

    def discover_schema(
        self,
        source_type: Union[str, SchemaDiscoveryRequest, Dict[str, Any]] = "sqlserver",
        config: Optional[Dict[str, Any]] = None,
        table_filter: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> SchemaDiscoveryResponse:
        """Introspect tables, columns, primary/foreign keys, and row count estimates."""
        if isinstance(source_type, SchemaDiscoveryRequest):
            src = source_type.source_type
            conn_params = dict(source_type.config)
            table_filter = table_filter or source_type.table_filter
        elif isinstance(source_type, dict):
            src = source_type.get("source_type", "sqlserver")
            conn_params = dict(source_type.get("config", source_type))
            table_filter = table_filter or source_type.get("table_filter")
        else:
            src = source_type
            conn_params = dict(config or {})
        conn_params.update(kwargs)
        connector = self.get_connector(src, **conn_params)
        with connector:
            raw_disc = connector.discover_schema(table_filter=table_filter)
            if isinstance(raw_disc, SchemaDiscoveryResponse):
                return raw_disc

            table_schemas: Dict[str, TableMetadata] = {}
            for tbl, schema_obj in raw_disc.get("schemas", {}).items():
                if isinstance(schema_obj, TableMetadata):
                    table_schemas[tbl] = schema_obj
                elif hasattr(schema_obj, "to_dict"):
                    s_dict = schema_obj.to_dict()
                    table_schemas[tbl] = TableMetadata(**s_dict)
                elif isinstance(schema_obj, dict):
                    table_schemas[tbl] = TableMetadata(**schema_obj)

            return SchemaDiscoveryResponse(
                success=raw_disc.get("success", True),
                database_name=raw_disc.get("database_name"),
                tables_count=raw_disc.get("tables_count", len(raw_disc.get("tables", []))),
                tables=raw_disc.get("tables", []),
                schemas=table_schemas,
                error=raw_disc.get("error"),
            )

    def preview_table(
        self,
        source_type: Union[str, TablePreviewRequest, Dict[str, Any]] = "sqlserver",
        config: Optional[Dict[str, Any]] = None,
        table_name: str = "",
        limit: int = 50,
        columns: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> TablePreviewResponse:
        """Fetch a sampled slice of records from a legacy table or file dataset."""
        if isinstance(source_type, TablePreviewRequest):
            src = source_type.source_type
            conn_params = dict(source_type.config)
            table_name = table_name or source_type.table_name
            limit = limit if limit != 50 else source_type.limit
            columns = columns or source_type.columns
        elif isinstance(source_type, dict):
            src = source_type.get("source_type", "sqlserver")
            conn_params = dict(source_type.get("config", source_type))
            table_name = table_name or source_type.get("table_name", "")
            limit = source_type.get("limit", limit)
            columns = columns or source_type.get("columns")
        else:
            src = source_type
            conn_params = dict(config or {})
        conn_params.update(kwargs)
        connector = self.get_connector(src, **conn_params)
        with connector:
            rows = connector.preview_table(table_name=table_name, limit=limit, columns=columns)
            cols = list(rows[0].keys()) if rows else (columns or [])
            return TablePreviewResponse(
                table_name=table_name,
                columns=cols,
                total_rows_estimate=len(rows),
                sample_rows=rows,
                row_count=len(rows),
            )

    # ==========================================================================
    # 2. Schema Mapping & Data Cleansing
    # ==========================================================================

    def generate_mapping_config(
        self,
        discovered_tables: Union[List[str], Dict[str, Any]],
        auto_fuzzy: bool = True,
        custom_overrides: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> MigrationMappingConfig:
        """Generate automated mapping configuration for legacy tables and T-code entities."""
        return self.mapping_engine.generate_mapping_config(
            discovered_tables=discovered_tables,
            auto_fuzzy=auto_fuzzy,
            custom_overrides=custom_overrides,
        )

    def cleanse_dataset(
        self,
        records_by_entity: Dict[str, List[Dict[str, Any]]],
        config: Optional[DataCleansingConfig] = None,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], CleansingSummary]:
        """Run automated cleansing rules: phantom product detection, contact sanitization, deduplication."""
        return self.cleansing_service.cleanse_batch(
            records_by_entity=records_by_entity,
            config=config or DataCleansingConfig(),
        )

    def scan_phantom_products(
        self,
        products: List[Dict[str, Any]],
        config: Optional[DataCleansingConfig] = None,
        reference_date: Optional[Union[date, datetime]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], CleansingSummary]:
        """Classify and partition products into active and phantom subsets."""
        return self.cleansing_service.scan_phantom_products(
            products=products,
            config=config or DataCleansingConfig(),
            reference_date=reference_date,
        )

    # ==========================================================================
    # 3. Dry-Run Simulation & Pipeline
    # ==========================================================================

    def run_dry_run(
        self,
        request: Union[DryRunRequest, Dict[str, Any]],
        connector: Optional[BaseConnector] = None,
        tenant_id: Optional[int] = None,
    ) -> DryRunResult:
        """Execute complete dry-run simulation pipeline with safe batch staging."""
        return self.dry_run_service.run_dry_run(
            request=request,
            connector=connector,
            tenant_id=tenant_id,
        )

    def run_dry_run_from_records(
        self,
        records_by_entity: Dict[str, List[Dict[str, Any]]],
        mapping_config: Optional[MigrationMappingConfig] = None,
        cleansing_config: Optional[DataCleansingConfig] = None,
        source_type: str = "csv_dump",
        connection_config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[int] = None,
    ) -> DryRunResult:
        """Run dry-run simulation directly from in-memory record datasets."""
        return self.dry_run_service.run_dry_run_from_records(
            records_by_entity=records_by_entity,
            mapping_config=mapping_config,
            cleansing_config=cleansing_config,
            source_type=source_type,
            connection_config=connection_config,
            tenant_id=tenant_id,
        )

    def run_dry_run_from_csv(
        self,
        csv_content: str,
        entity_type: str = "products",
        column_mapping: Optional[Dict[str, str]] = None,
        cleansing_config: Optional[DataCleansingConfig] = None,
        tenant_id: Optional[int] = None,
    ) -> DryRunResult:
        """Run dry-run simulation from raw CSV text content."""
        return self.dry_run_service.run_dry_run_from_csv(
            csv_content=csv_content,
            entity_type=entity_type,
            column_mapping=column_mapping,
            cleansing_config=cleansing_config,
            tenant_id=tenant_id,
        )

    def get_dry_run_result(
        self,
        batch_id_or_key: Union[int, str],
        business_id: Optional[int] = None,
    ) -> Optional[DryRunResult]:
        """Fetch DryRunResult summary for a previously executed dry-run batch."""
        return self.dry_run_service.get_dry_run_result(
            batch_id_or_key=batch_id_or_key,
            business_id=business_id,
        )

    # ==========================================================================
    # 4. Comprehensive Reconciliation Reporting
    # ==========================================================================

    def reconcile_customer_balances(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.01,
    ) -> CustomerBalanceReconciliation:
        """Compare legacy receivables against Nova opening balance records."""
        return self.reconciliation_service.reconcile_customer_balances(
            legacy_records=legacy_records,
            nova_records=nova_records,
            tolerance=tolerance,
        )

    def reconcile_inventory(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.001,
    ) -> InventoryReconciliation:
        """Compare legacy stock quantities and valuation against Nova opening stock."""
        return self.reconciliation_service.reconcile_inventory(
            legacy_records=legacy_records,
            nova_records=nova_records,
            tolerance=tolerance,
        )

    def reconcile_entity_counts(
        self,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        staged_by_entity: Dict[str, List[Dict[str, Any]]],
        cleansing_summary: Optional[CleansingSummary] = None,
        validation_errors: Optional[List[RowValidationError]] = None,
    ) -> Dict[str, EntityCountReconciliation]:
        """Audit entity row counts from extraction through cleansing and staging."""
        return self.reconciliation_service.reconcile_entity_counts(
            extracted_by_entity=extracted_by_entity,
            staged_by_entity=staged_by_entity,
            cleansing_summary=cleansing_summary,
            validation_errors=validation_errors,
        )

    def generate_reconciliation_report(
        self,
        batch_key: str,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        staged_by_entity: Dict[str, List[Dict[str, Any]]],
        cleansing_summary: Optional[CleansingSummary] = None,
        validation_errors: Optional[List[RowValidationError]] = None,
        tolerance: float = 0.01,
    ) -> ReconciliationReport:
        """Generate a complete end-to-end reconciliation report with actionable recommendations."""
        return self.reconciliation_service.generate_reconciliation_report(
            batch_key=batch_key,
            extracted_by_entity=extracted_by_entity,
            staged_by_entity=staged_by_entity,
            cleansing_summary=cleansing_summary,
            validation_errors=validation_errors,
            tolerance=tolerance,
        )

    def get_reconciliation_report(
        self,
        batch_id_or_key: Union[int, str],
        business_id: Optional[int] = None,
    ) -> Optional[ReconciliationReport]:
        """Retrieve or reconstruct reconciliation report for a given migration batch."""
        active_tenant = business_id if business_id is not None else get_current_tenant()

        batch = None
        if isinstance(batch_id_or_key, int) or (isinstance(batch_id_or_key, str) and batch_id_or_key.isdigit()):
            batch = self.batch_repo.get(int(batch_id_or_key), business_id=active_tenant)
        else:
            batches = self.batch_repo.list(filters={"batch_key": str(batch_id_or_key)}, business_id=active_tenant)
            if batches:
                batch = batches[0]

        if not batch:
            return None

        batch_id = batch["id"]
        batch_key = batch.get("batch_key", f"BATCH-{batch_id}")

        recon_raw = batch.get("reconciliation_summary")
        if isinstance(recon_raw, str):
            try:
                recon_raw = json.loads(recon_raw)
            except Exception:
                recon_raw = {}
        elif not isinstance(recon_raw, dict):
            recon_raw = {}

        # Fetch staged records for deep reconciliation if available
        staged_by_entity: Dict[str, List[Dict[str, Any]]] = {}
        entity_summaries = recon_raw.get("entity_counts") or {}
        for ent in entity_summaries.keys():
            staged_by_entity[ent] = self.dry_run_service.get_staged_records(batch_id, entity_type=ent)

        if not staged_by_entity and batch_id in self.dry_run_service._in_memory_staging:
            staged_by_entity = self.dry_run_service._in_memory_staging[batch_id]

        err_list = batch.get("error_details") or []
        if isinstance(err_list, str):
            try:
                err_list = json.loads(err_list)
            except Exception:
                err_list = []
        validation_errors = [
            RowValidationError(**err) if isinstance(err, dict) else err
            for err in err_list
        ]

        if staged_by_entity:
            return self.reconciliation_service.generate_reconciliation_report(
                batch_key=batch_key,
                extracted_by_entity=staged_by_entity,
                staged_by_entity=staged_by_entity,
                validation_errors=validation_errors,
            )

        # Fallback reconstruction from stored summary dict
        return ReconciliationReport(
            batch_key=batch_key,
            report_date=datetime.now(),
            overall_status=recon_raw.get("batch_status", "Passed" if not validation_errors else "PassedWithWarnings"),
            unresolved_errors_count=len([e for e in validation_errors if getattr(e, "severity", "") == "error"]),
            recommendations=[
                "Reconciliation report generated from stored batch metadata."
            ],
        )

    # ==========================================================================
    # 5. One-Click Commit & Instant Rollback
    # ==========================================================================

    def commit(
        self,
        request: Union[CommitMigrationRequest, Dict[str, Any], int],
        business_id: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Commit staged migration batch into active Nova tables.
        
        Returns a dictionary response with both modern attributes and backward-compatible fields.
        """
        res: CommitMigrationResponse = self.commit_service.commit(
            request=request,
            business_id=business_id,
            force=force,
        )
        return {
            "batch_id": res.batch_id,
            "batch_key": res.batch_key,
            "status": res.status,
            "inserted_rows": res.total_inserted,
            "total_inserted": res.total_inserted,
            "inserted_by_entity": res.inserted_by_entity,
            "execution_time_ms": res.execution_time_ms,
            "completed_at": res.completed_at.isoformat() if res.completed_at else None,
            "message": res.message,
        }

    def commit_batch(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
        force: bool = False,
    ) -> CommitMigrationResponse:
        """Typed commit method returning CommitMigrationResponse."""
        return self.commit_service.commit_batch(
            batch_id=batch_id,
            business_id=business_id,
            force=force,
        )

    def rollback(
        self,
        request: Union[RollbackMigrationRequest, Dict[str, Any], int],
        business_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Roll back a committed or preview migration batch, removing inserted records.
        
        Returns a dictionary response with both modern attributes and backward-compatible fields.
        """
        res: RollbackMigrationResponse = self.rollback_service.rollback(
            request=request,
            business_id=business_id,
            reason=reason,
        )
        return {
            "batch_id": res.batch_id,
            "batch_key": res.batch_key,
            "status": res.status,
            "deleted_rows": res.total_deleted,
            "total_deleted": res.total_deleted,
            "deleted_by_entity": res.deleted_by_entity,
            "execution_time_ms": res.execution_time_ms,
            "completed_at": res.completed_at.isoformat() if res.completed_at else None,
            "message": res.message,
        }

    def rollback_batch(
        self,
        batch_id: int,
        reason: Optional[str] = None,
        business_id: Optional[int] = None,
    ) -> RollbackMigrationResponse:
        """Typed rollback method returning RollbackMigrationResponse."""
        return self.rollback_service.rollback_batch(
            batch_id=batch_id,
            reason=reason,
            business_id=business_id,
        )

    def get_rollback_preview(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a preview of records that will be deleted during rollback."""
        return self.rollback_service.get_rollback_preview(
            batch_id=batch_id,
            business_id=business_id,
        )

    def verify_rollback(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Verify that all records in the batch have been removed and status is RolledBack."""
        return self.rollback_service.verify_rollback(
            batch_id=batch_id,
            business_id=business_id,
        )

    # ==========================================================================
    # 6. Batch History & Management
    # ==========================================================================

    def get_batch(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch batch record from table Nova.t0104 with multi-tenant scoping."""
        active_tenant = business_id if business_id is not None else get_current_tenant()
        return self.batch_repo.get(batch_id, business_id=active_tenant)

    def get_batch_by_key(
        self,
        batch_key: str,
        business_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch batch record by unique batch_key with multi-tenant scoping."""
        active_tenant = business_id if business_id is not None else get_current_tenant()
        batches = self.batch_repo.list(filters={"batch_key": batch_key}, business_id=active_tenant)
        return batches[0] if batches else None

    def list_batches(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "id DESC",
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve paginated list of migration batches with total count."""
        active_tenant = business_id if business_id is not None else get_current_tenant()
        items = self.batch_repo.list(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            business_id=active_tenant,
        )
        total = self.batch_repo.count(
            filters=filters,
            business_id=active_tenant,
        )
        return {
            "items": items,
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
        }

    def get_batch_summary(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch comprehensive summary of a batch including committed entity breakdowns."""
        return self.commit_service.get_batch_summary(batch_id=batch_id, business_id=business_id)

    def get_staged_records(
        self,
        batch_id: int,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        business_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch staged records for a dry-run batch from database or in-memory cache."""
        return self.dry_run_service.get_staged_records(
            batch_id=batch_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
            business_id=business_id,
        )

    def get_committed_items(
        self,
        batch_id: int,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        business_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch individual record tracking entries from Nova.t0104_items."""
        return self.commit_service.get_committed_items(
            batch_id=batch_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
            business_id=business_id,
        )

    def clear_staging(
        self,
        batch_id: int,
    ) -> bool:
        """Purge staged dry-run records for a given batch."""
        return self.dry_run_service.clear_staging(batch_id)

    def delete_batch(
        self,
        batch_id: int,
        business_id: Optional[int] = None,
    ) -> bool:
        """Delete a preview or rolled back batch and its tracking items."""
        active_tenant = business_id if business_id is not None else get_current_tenant()
        batch = self.batch_repo.get(batch_id, business_id=active_tenant)
        if not batch:
            return False

        # Clear staged records if any
        self.dry_run_service.clear_staging(batch_id)

        # Delete any tracking items
        try:
            items = self.items_repo.list(filters={"batch_id": batch_id}, business_id=active_tenant)
            for item in items:
                self.items_repo.delete(item["id"], business_id=active_tenant)
        except Exception as e:
            logger.debug(f"Error cleaning up batch tracking items on delete: {e}")

        # Delete batch record
        self.batch_repo.delete(batch_id, business_id=active_tenant)
        return True

    # ==========================================================================
    # 7. Legacy CSV Upload & Staging (Backward Compatibility)
    # ==========================================================================

    def upload_csv(
        self,
        entity_type: str,
        csv_content: str,
        column_mapping: Optional[Dict[str, str]] = None,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Upload and stage a legacy single-entity CSV file for preview/commit."""
        if entity_type not in ENTITY_MAP:
            raise ValueError(f"Unknown entity type {entity_type}")

        reader = csv.DictReader(io.StringIO(csv_content))
        raw_rows = list(reader)
        if not raw_rows:
            raise ValueError("CSV file is empty")

        active_tenant = business_id if business_id is not None else get_current_tenant()
        batch_key = str(uuid.uuid4())[:8]

        batch = self.batch_repo.create(
            {
                "batch_key": batch_key,
                "entity_type": entity_type,
                "total_rows": len(raw_rows),
                "inserted_rows": 0,
                "status": "Preview",
                "business_id": active_tenant,
            },
            business_id=active_tenant,
        )
        batch_id = batch["id"] if batch and "id" in batch else 1

        mapping = column_mapping or {}
        field_map = FIELD_MAP.get(entity_type, {})
        _, name_col, _ = ENTITY_MAP[entity_type]

        parsed_rows = []
        errors = []
        for i, row in enumerate(raw_rows):
            try:
                parsed = self._map_row(row, mapping, field_map, entity_type)
                if name_col not in parsed:
                    raise ValueError(f"Missing required field: {name_col}")
                parsed_rows.append(parsed)
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e), "data": dict(row)})

        # Store in dry run staging cache & legacy temp table storage
        self.dry_run_service._in_memory_staging[batch_id] = {entity_type: parsed_rows}
        self._store_parsed(batch_id, parsed_rows)

        return {
            "batch_key": batch_key,
            "batch_id": batch_id,
            "entity_type": entity_type,
            "total_rows": len(raw_rows),
            "valid_rows": len(parsed_rows),
            "error_rows": len(errors),
            "errors": errors,
            "sample": parsed_rows[:5],
            "columns": list(raw_rows[0].keys()) if raw_rows else [],
        }

    def _map_row(
        self,
        row: Dict[str, Any],
        mapping: Dict[str, str],
        field_map: Dict[str, str],
        entity_type: str,
    ) -> Dict[str, Any]:
        """Legacy helper to map CSV row fields."""
        result = {}
        for csv_col, value in row.items():
            val_str = str(value).strip() if value is not None else ""
            target = mapping.get(csv_col, "") or field_map.get(csv_col, "")
            if not target:
                continue
            if val_str == "":
                continue
            if target in ("price", "cost_price", "credit_limit", "rating", "tax_rate"):
                try:
                    val_str = float(val_str)
                except ValueError:
                    raise ValueError(f'Invalid number "{val_str}" in column {csv_col}')
            result[target] = val_str
        return result

    def _storage_table(self, batch_id: int) -> str:
        """Legacy storage table name helper."""
        return f"temp_mig_{batch_id}"

    def _store_parsed(self, batch_id: int, rows: List[Dict[str, Any]]) -> None:
        """Legacy helper to store parsed rows in temporary storage table."""
        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    tbl = self._storage_table(batch_id)
                    cur.execute(f"CREATE TEMP TABLE IF NOT EXISTS {tbl} (id SERIAL, data JSONB) ON COMMIT DROP")
                    for row in rows:
                        cur.execute(f"INSERT INTO {tbl} (data) VALUES (%s)", (json.dumps(row, default=str),))
                    conn.commit()
            finally:
                release_connection(conn)
        except Exception as e:
            logger.debug(f"Legacy temp table insert skipped or failed: {e}")

    def _load_stored(self, batch_id: int) -> List[Dict[str, Any]]:
        """Legacy helper to load parsed rows from temporary storage table."""
        if batch_id in self.dry_run_service._in_memory_staging:
            staged = self.dry_run_service._in_memory_staging[batch_id]
            res: List[Dict[str, Any]] = []
            for recs in staged.values():
                res.extend(recs)
            if res:
                return res

        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    tbl = self._storage_table(batch_id)
                    cur.execute(f"SELECT data FROM {tbl} ORDER BY id")
                    return [json.loads(r[0]) if isinstance(r[0], str) else r[0] for r in cur.fetchall()]
            finally:
                release_connection(conn)
        except Exception as e:
            logger.debug(f"Legacy temp table load skipped or failed: {e}")
            return []

    def _drop_storage(self, batch_id: int) -> None:
        """Legacy helper to drop temporary storage table."""
        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {self._storage_table(batch_id)}")
                    conn.commit()
            finally:
                release_connection(conn)
        except Exception as e:
            logger.debug(f"Legacy temp table drop skipped: {e}")


# Global default instance
migration_service = MigrationService()

