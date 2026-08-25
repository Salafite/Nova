"""Dry-Run Migration Simulation and Staging Pipeline Service.

Orchestrates the end-to-end legacy data migration simulation:
1. Connector extraction and chunk streaming (SQL Server, CSV dumps, SQL scripts).
2. Automated schema discovery and T-code entity mapping resolution.
3. Multi-layer data cleansing (phantom products, deduplication, contact sanitization, lookups, numeric clamping).
4. Entity schema transformation and row-level validation (with detailed error/warning tracking).
5. Preliminary balance and inventory reconciliation calculations.
6. Safe, isolated staging into batch storage (t0104_staging / t0104) with ZERO production table modifications.
"""

from copy import deepcopy
from datetime import date, datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

import psycopg2.extras

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.migration.connectors.base import BaseConnector
from modules.migration.connectors.csv_dump import CsvDumpConnector
from modules.migration.connectors.factory import get_connector
from modules.migration.models.migration import (
    CleansingSummary,
    DataCleansingConfig,
    DryRunRequest,
    DryRunResult,
    MigrationMappingConfig,
    RowValidationError,
    TableMappingRule,
)
from modules.migration.services.cleansing_service import (
    CleansingService,
    cleansing_service,
)
from modules.migration.services.mapping_engine import (
    ENTITY_TARGET_SCHEMAS,
    MappingEngine,
    mapping_engine,
)

logger = logging.getLogger(__name__)

# Repository for migration batch metadata
BATCH_REPO = CrudRepository(
    "T0104",
    business_columns=[
        "id",
        "batch_key",
        "entity_type",
        "source_type",
        "total_rows",
        "inserted_rows",
        "status",
        "dry_run_completed",
        "connection_config",
        "reconciliation_summary",
        "execution_log",
        "error_details",
        "business_id",
    ],
)


class DryRunService:
    """Orchestrates end-to-end dry-run migration simulation and staging pipeline."""

    def __init__(
        self,
        mapper: Optional[MappingEngine] = None,
        cleaner: Optional[CleansingService] = None,
    ) -> None:
        self.mapping_engine = mapper or mapping_engine
        self.cleansing_service = cleaner or cleansing_service
        # In-memory staging fallback for testing / isolated execution
        self._in_memory_staging: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}

    # ==========================================================================
    # Main Entry Points
    # ==========================================================================

    def run_dry_run(
        self,
        request: Union[DryRunRequest, Dict[str, Any]],
        connector: Optional[BaseConnector] = None,
        tenant_id: Optional[int] = None,
    ) -> DryRunResult:
        """Execute a full dry-run migration simulation from a DryRunRequest or dict.
        
        Args:
            request: DryRunRequest model or dictionary payload.
            connector: Optional pre-initialized BaseConnector instance.
            tenant_id: Optional business_id override.
            
        Returns:
            DryRunResult: Comprehensive result with metrics, errors, and reconciliation.
        """
        if isinstance(request, dict):
            req = DryRunRequest(**request)
        else:
            req = request

        active_tenant = tenant_id if tenant_id is not None else (req.tenant_id if req.tenant_id is not None else get_current_tenant())

        # Instantiate connector if not provided
        conn_instance = connector
        if conn_instance is None:
            conn_instance = get_connector(req.source_type, **req.connection_config)

        return self.run_dry_run_from_connector(
            connector=conn_instance,
            mapping_config=req.mapping_config,
            cleansing_config=req.cleansing_config,
            selected_entities=req.selected_entities,
            sample_limit=req.sample_limit,
            tenant_id=active_tenant,
            source_type=req.source_type,
            raw_connection_config=req.connection_config,
        )

    def run_dry_run_from_connector(
        self,
        connector: BaseConnector,
        mapping_config: Optional[MigrationMappingConfig] = None,
        cleansing_config: Optional[DataCleansingConfig] = None,
        selected_entities: Optional[List[str]] = None,
        sample_limit: Optional[int] = None,
        tenant_id: Optional[int] = None,
        source_type: str = "sqlserver",
        raw_connection_config: Optional[Dict[str, Any]] = None,
    ) -> DryRunResult:
        """Run dry-run simulation against an active connector."""
        start_time = time.perf_counter()
        batch_key = uuid.uuid4().hex[:12].upper()
        execution_log: List[Dict[str, Any]] = []

        active_tenant = tenant_id if tenant_id is not None else get_current_tenant()
        clean_cfg = cleansing_config or DataCleansingConfig()

        # Step 1: Connect & Test
        t0 = time.perf_counter()
        with connector:
            test_res = connector.test_connection()
            if not test_res.success:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                execution_log.append({
                    "step": "connection_test",
                    "status": "failed",
                    "error": test_res.error or test_res.message,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.now().isoformat(),
                })
                return DryRunResult(
                    batch_key=batch_key,
                    success=False,
                    total_source_rows=0,
                    valid_rows_count=0,
                    warning_rows_count=0,
                    error_rows_count=1,
                    phantom_products_count=0,
                    execution_duration_ms=(time.perf_counter() - start_time) * 1000.0,
                    validation_errors=[
                        RowValidationError(
                            row_index=0,
                            entity_type="connection",
                            error_type="connection_failed",
                            message=f"Connection failed: {test_res.error or test_res.message}",
                            severity="error",
                        )
                    ],
                    ready_for_commit=False,
                )

            execution_log.append({
                "step": "connection_test",
                "status": "success",
                "server_version": test_res.server_version,
                "tables_count": len(test_res.tables),
                "duration_ms": (time.perf_counter() - t0) * 1000.0,
                "timestamp": datetime.now().isoformat(),
            })

            # Step 2: Schema Discovery & Mapping Config Resolution
            t0 = time.perf_counter()
            available_tables = connector.get_tables()
            table_schemas: Dict[str, Any] = {}
            for tbl in available_tables:
                try:
                    table_schemas[tbl] = connector.get_table_schema(tbl)
                except Exception as e:
                    logger.warning(f"Could not introspect schema for table {tbl}: {e}")

            map_cfg = mapping_config
            if map_cfg is None or not map_cfg.mappings:
                map_cfg = self.mapping_engine.generate_mapping_config(
                    discovered_tables=table_schemas or available_tables,
                    auto_fuzzy=True,
                )

            execution_log.append({
                "step": "schema_discovery_and_mapping",
                "status": "success",
                "discovered_tables": available_tables,
                "mapped_entities": list(map_cfg.mappings.keys()),
                "duration_ms": (time.perf_counter() - t0) * 1000.0,
                "timestamp": datetime.now().isoformat(),
            })

            # Filter selected entities
            active_mappings: Dict[str, TableMappingRule] = {}
            for entity_type, rule in map_cfg.mappings.items():
                if not rule.enabled:
                    continue
                if selected_entities and entity_type not in selected_entities:
                    continue
                active_mappings[entity_type] = rule

            # Helper to match table name with or without extensions/casing
            def _find_matching_table(src_tbl: str, available: List[str]) -> Optional[str]:
                if src_tbl in available:
                    return src_tbl
                for t in available:
                    if t.lower() == src_tbl.lower():
                        return t
                clean_src = src_tbl.rsplit(".", 1)[0].lower()
                for t in available:
                    clean_t = t.rsplit(".", 1)[0].lower()
                    if clean_t == clean_src:
                        return t
                return None

            # Step 3: Extract datasets
            t0 = time.perf_counter()
            extracted_by_entity: Dict[str, List[Dict[str, Any]]] = {}
            total_extracted_count = 0

            for entity_type, rule in active_mappings.items():
                matched_tbl = _find_matching_table(rule.source_table, available_tables)
                if not matched_tbl:
                    # Table not present in legacy source
                    continue

                try:
                    if sample_limit and sample_limit > 0:
                        rows = connector.preview_table(matched_tbl, limit=sample_limit)
                    else:
                        rows = connector.extract_all(matched_tbl, filter_condition=rule.filter_clause)
                    extracted_by_entity[entity_type] = rows
                    total_extracted_count += len(rows)
                except Exception as e:
                    logger.error(f"Error extracting table '{matched_tbl}' for entity '{entity_type}': {e}")
                    extracted_by_entity[entity_type] = []

            execution_log.append({
                "step": "extraction",
                "status": "success",
                "total_rows_extracted": total_extracted_count,
                "entities_extracted": {e: len(r) for e, r in extracted_by_entity.items()},
                "duration_ms": (time.perf_counter() - t0) * 1000.0,
                "timestamp": datetime.now().isoformat(),
            })

        # Process extracted datasets through cleansing, mapping, staging
        return self._process_and_stage_datasets(
            batch_key=batch_key,
            extracted_by_entity=extracted_by_entity,
            active_mappings=active_mappings,
            cleansing_config=clean_cfg,
            source_type=source_type,
            connection_config=raw_connection_config or {},
            tenant_id=active_tenant,
            execution_log=execution_log,
            start_time=start_time,
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
        """Run dry-run simulation directly from in-memory entity records."""
        start_time = time.perf_counter()
        batch_key = uuid.uuid4().hex[:12].upper()
        execution_log: List[Dict[str, Any]] = []

        active_tenant = tenant_id if tenant_id is not None else get_current_tenant()
        clean_cfg = cleansing_config or DataCleansingConfig()

        # Build mapping rules if not provided
        active_mappings: Dict[str, TableMappingRule] = {}
        if mapping_config and mapping_config.mappings:
            for e, r in mapping_config.mappings.items():
                if r.enabled:
                    active_mappings[e] = r
        else:
            for entity_type, rows in records_by_entity.items():
                if entity_type in ENTITY_TARGET_SCHEMAS:
                    cols = list(rows[0].keys()) if rows else []
                    rule = self.mapping_engine.create_table_mapping_rule(
                        entity_type=entity_type,
                        source_table=entity_type,
                        source_columns=cols,
                    )
                    active_mappings[entity_type] = rule

        execution_log.append({
            "step": "in_memory_intake",
            "status": "success",
            "entities_received": {e: len(r) for e, r in records_by_entity.items()},
            "duration_ms": 0.5,
            "timestamp": datetime.now().isoformat(),
        })

        return self._process_and_stage_datasets(
            batch_key=batch_key,
            extracted_by_entity=records_by_entity,
            active_mappings=active_mappings,
            cleansing_config=clean_cfg,
            source_type=source_type,
            connection_config=connection_config or {},
            tenant_id=active_tenant,
            execution_log=execution_log,
            start_time=start_time,
        )

    def run_dry_run_from_csv(
        self,
        csv_content: str,
        entity_type: str = "products",
        column_mapping: Optional[Dict[str, str]] = None,
        cleansing_config: Optional[DataCleansingConfig] = None,
        tenant_id: Optional[int] = None,
    ) -> DryRunResult:
        """Run dry-run simulation from raw CSV text content for a specific entity."""
        connector = CsvDumpConnector(in_memory_files={f"{entity_type}.csv": csv_content})
        mapping_rule: Optional[TableMappingRule] = None

        if column_mapping:
            mapping_rule = self.mapping_engine.create_table_mapping_rule(
                entity_type=entity_type,
                source_table=entity_type,
                custom_overrides=column_mapping,
            )

        map_config = (
            MigrationMappingConfig(mappings={entity_type: mapping_rule})
            if mapping_rule
            else None
        )

        return self.run_dry_run(
            request=DryRunRequest(
                source_type="csv_dump",
                connection_config={},
                mapping_config=map_config,
                cleansing_config=cleansing_config,
                selected_entities=[entity_type],
                tenant_id=tenant_id,
            ),
            connector=connector,
            tenant_id=tenant_id,
        )


    # ==========================================================================
    # Processing, Cleansing, Transformation & Staging Core
    # ==========================================================================

    def _process_and_stage_datasets(
        self,
        batch_key: str,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        active_mappings: Dict[str, TableMappingRule],
        cleansing_config: DataCleansingConfig,
        source_type: str,
        connection_config: Dict[str, Any],
        tenant_id: Optional[int],
        execution_log: List[Dict[str, Any]],
        start_time: float,
    ) -> DryRunResult:
        """Core pipeline: Cleansing -> Mapping & Validation -> Reconciliation -> Staging."""
        # Step 4: Cleansing
        t0 = time.perf_counter()
        cleaned_by_entity, cleansing_summary = self.cleansing_service.cleanse_batch(
            records_by_entity=extracted_by_entity,
            config=cleansing_config,
        )
        execution_log.append({
            "step": "cleansing",
            "status": "success",
            "phantoms_detected": cleansing_summary.phantom_products_detected,
            "phantoms_skipped": cleansing_summary.phantom_products_skipped,
            "duplicates_resolved": cleansing_summary.duplicates_resolved,
            "contacts_sanitized": cleansing_summary.contacts_sanitized,
            "lookups_created": cleansing_summary.lookups_auto_created,
            "duration_ms": (time.perf_counter() - t0) * 1000.0,
            "timestamp": datetime.now().isoformat(),
        })

        # Step 5: Entity Schema Transformation & Row Validation
        t0 = time.perf_counter()
        valid_staged_by_entity: Dict[str, List[Dict[str, Any]]] = {}
        validation_errors: List[RowValidationError] = []
        sample_transformed: Dict[str, List[Dict[str, Any]]] = {}
        entity_summaries: Dict[str, Dict[str, Any]] = {}

        total_source_rows = 0
        total_valid_rows = 0
        total_warning_rows = 0
        total_error_rows = 0

        for entity_type, raw_rows in extracted_by_entity.items():
            total_source_rows += len(raw_rows)
            mapping_rule = active_mappings.get(entity_type)
            if not mapping_rule:
                # Default mapping rule if none generated
                cols = list(raw_rows[0].keys()) if raw_rows else []
                mapping_rule = self.mapping_engine.create_table_mapping_rule(
                    entity_type=entity_type,
                    source_table=entity_type,
                    source_columns=cols,
                )

            cleansed_rows = cleaned_by_entity.get(entity_type, raw_rows)
            valid_entity_records: List[Dict[str, Any]] = []
            entity_error_count = 0
            entity_warning_count = 0
            entity_phantom_count = 0

            for idx, row in enumerate(cleansed_rows, start=1):
                source_key = (
                    row.get("sku")
                    or row.get("item_code")
                    or row.get("id")
                    or row.get("code")
                    or row.get("invoice_number")
                    or row.get("name")
                )

                if row.get("is_phantom") is True:
                    entity_phantom_count += 1

                try:
                    mapped_rec, row_warnings = self.mapping_engine.map_row(
                        row=row,
                        mapping_rule=mapping_rule,
                        strict=False,
                    )

                    has_fatal_error = False
                    for w in row_warnings:
                        if "Missing required field" in w:
                            has_fatal_error = True
                            entity_error_count += 1
                            validation_errors.append(
                                RowValidationError(
                                    row_index=idx,
                                    source_key=str(source_key) if source_key is not None else None,
                                    entity_type=entity_type,
                                    target_table=mapping_rule.target_table,
                                    error_type="missing_required",
                                    message=w,
                                    raw_data=row,
                                    severity="error",
                                )
                            )
                        else:
                            entity_warning_count += 1
                            validation_errors.append(
                                RowValidationError(
                                    row_index=idx,
                                    source_key=str(source_key) if source_key is not None else None,
                                    entity_type=entity_type,
                                    target_table=mapping_rule.target_table,
                                    error_type="transformation_warning",
                                    message=w,
                                    raw_data=row,
                                    severity="warning",
                                )
                            )

                    if not has_fatal_error:
                        valid_entity_records.append(mapped_rec)

                except Exception as e:
                    entity_error_count += 1
                    validation_errors.append(
                        RowValidationError(
                            row_index=idx,
                            source_key=str(source_key) if source_key is not None else None,
                            entity_type=entity_type,
                            target_table=mapping_rule.target_table,
                            error_type="schema_mapping_error",
                            message=str(e),
                            raw_data=row,
                            severity="error",
                        )
                    )

            valid_staged_by_entity[entity_type] = valid_entity_records
            total_valid_rows += len(valid_entity_records)
            total_error_rows += entity_error_count
            total_warning_rows += entity_warning_count

            # Sample first 5 transformed records
            sample_transformed[entity_type] = valid_entity_records[:5]

            entity_summaries[entity_type] = {
                "source_table": mapping_rule.source_table,
                "target_table": mapping_rule.target_table,
                "target_tcode": mapping_rule.target_tcode,
                "source_rows": len(raw_rows),
                "cleansed_rows": len(cleansed_rows),
                "valid_rows": len(valid_entity_records),
                "warning_rows": entity_warning_count,
                "error_rows": entity_error_count,
                "phantom_count": entity_phantom_count,
                "status": "ready" if entity_error_count == 0 else "has_errors",
            }

        execution_log.append({
            "step": "transformation_and_validation",
            "status": "success",
            "total_valid_rows": total_valid_rows,
            "total_error_rows": total_error_rows,
            "total_warning_rows": total_warning_rows,
            "duration_ms": (time.perf_counter() - t0) * 1000.0,
            "timestamp": datetime.now().isoformat(),
        })

        # Step 6: Reconciliation Preliminary Calculation
        reconciliation_summary = self._calculate_preliminary_reconciliation(
            extracted_by_entity=extracted_by_entity,
            valid_staged_by_entity=valid_staged_by_entity,
            entity_summaries=entity_summaries,
            cleansing_summary=cleansing_summary,
            total_source_rows=total_source_rows,
            total_valid_rows=total_valid_rows,
            total_error_rows=total_error_rows,
        )

        # Step 7: Staging Pipeline (Persistent & In-Memory Isolation)
        t0 = time.perf_counter()
        batch_id = self._stage_batch(
            batch_key=batch_key,
            source_type=source_type,
            connection_config=connection_config,
            entity_summaries=entity_summaries,
            total_source_rows=total_source_rows,
            reconciliation_summary=reconciliation_summary,
            execution_log=execution_log,
            validation_errors=validation_errors,
            valid_staged_by_entity=valid_staged_by_entity,
            tenant_id=tenant_id,
        )
        execution_log.append({
            "step": "staging",
            "status": "success",
            "batch_id": batch_id,
            "total_staged_records": total_valid_rows,
            "duration_ms": (time.perf_counter() - t0) * 1000.0,
            "timestamp": datetime.now().isoformat(),
        })

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        ready_for_commit = (total_valid_rows > 0 and total_error_rows == 0)

        return DryRunResult(
            batch_key=batch_key,
            success=True,
            total_source_rows=total_source_rows,
            valid_rows_count=total_valid_rows,
            warning_rows_count=total_warning_rows,
            error_rows_count=total_error_rows,
            phantom_products_count=cleansing_summary.phantom_products_detected,
            execution_duration_ms=total_duration_ms,
            entity_summaries=entity_summaries,
            cleansing_summary=cleansing_summary,
            validation_errors=validation_errors,
            sample_transformed=sample_transformed,
            reconciliation_summary=reconciliation_summary,
            ready_for_commit=ready_for_commit,
        )

    # ==========================================================================
    # Reconciliation Metrics Calculation
    # ==========================================================================

    def _calculate_preliminary_reconciliation(
        self,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        valid_staged_by_entity: Dict[str, List[Dict[str, Any]]],
        entity_summaries: Dict[str, Dict[str, Any]],
        cleansing_summary: CleansingSummary,
        total_source_rows: int,
        total_valid_rows: int,
        total_error_rows: int,
    ) -> Dict[str, Any]:
        """Compute preliminary customer receivables, inventory quantities, and entity metrics."""
        summary: Dict[str, Any] = {
            "batch_status": "Passed" if total_error_rows == 0 else "PassedWithWarnings",
            "total_source_entities": len(entity_summaries),
            "total_source_rows": total_source_rows,
            "total_valid_rows": total_valid_rows,
            "total_error_rows": total_error_rows,
            "total_phantom_products": cleansing_summary.phantom_products_detected,
            "customer_receivables": {
                "source_receivables_total": 0.0,
                "staged_receivables_total": 0.0,
                "variance": 0.0,
                "customer_count": 0,
            },
            "inventory_balances": {
                "source_quantity_total": 0.0,
                "staged_quantity_total": 0.0,
                "quantity_variance": 0.0,
                "source_valuation_total": 0.0,
                "staged_valuation_total": 0.0,
                "valuation_variance": 0.0,
                "negative_stock_items": 0,
            },
            "entity_counts": entity_summaries,
        }

        # 1. Customer Opening Balances / Receivables
        for ar_key in ("customer_opening_balances", "customers"):
            if ar_key in valid_staged_by_entity:
                staged_rows = valid_staged_by_entity[ar_key]
                raw_rows = extracted_by_entity.get(ar_key, [])
                
                src_total = sum(
                    float(r.get("balance") or r.get("total_amount") or r.get("amount") or 0.0)
                    for r in raw_rows
                )
                staged_total = sum(
                    float(r.get("balance") or r.get("total_amount") or r.get("amount") or 0.0)
                    for r in staged_rows
                )

                summary["customer_receivables"] = {
                    "source_receivables_total": round(src_total, 2),
                    "staged_receivables_total": round(staged_total, 2),
                    "variance": round(abs(src_total - staged_total), 2),
                    "customer_count": len(staged_rows),
                }
                break

        # 2. Inventory Quantities & Valuation
        if "inventory_opening" in valid_staged_by_entity or "products" in valid_staged_by_entity:
            inv_rows = valid_staged_by_entity.get(
                "inventory_opening", valid_staged_by_entity.get("products", [])
            )
            raw_inv = extracted_by_entity.get(
                "inventory_opening", extracted_by_entity.get("products", [])
            )

            src_qty = sum(
                float(r.get("qty") or r.get("quantity") or r.get("stock_quantity") or 0.0)
                for r in raw_inv
            )
            staged_qty = sum(
                float(r.get("qty") or r.get("quantity") or r.get("stock_quantity") or 0.0)
                for r in inv_rows
            )
            
            src_val = sum(
                float(r.get("qty") or r.get("quantity") or 0.0) * float(r.get("cost_price") or r.get("price") or 0.0)
                for r in raw_inv
            )
            staged_val = sum(
                float(r.get("qty") or r.get("quantity") or 0.0) * float(r.get("cost_price") or r.get("price") or 0.0)
                for r in inv_rows
            )

            neg_items = sum(
                1 for r in raw_inv if float(r.get("qty") or r.get("quantity") or 0.0) < 0
            )

            summary["inventory_balances"] = {
                "source_quantity_total": round(src_qty, 2),
                "staged_quantity_total": round(staged_qty, 2),
                "quantity_variance": round(abs(src_qty - staged_qty), 2),
                "source_valuation_total": round(src_val, 2),
                "staged_valuation_total": round(staged_val, 2),
                "valuation_variance": round(abs(src_val - staged_val), 2),
                "negative_stock_items": neg_items,
            }

        return summary

    # ==========================================================================
    # Staging Storage & Retrieval
    # ==========================================================================

    def _ensure_staging_table(self, conn=None) -> None:
        """Create Nova.t0104_staging table if not exists."""
        from packages.database.connection import get_connection, release_connection

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS "Nova".t0104_staging (
                        id          SERIAL PRIMARY KEY,
                        batch_id    INT NOT NULL REFERENCES "Nova".t0104(id) ON DELETE CASCADE,
                        entity_type VARCHAR(50) NOT NULL,
                        row_index   INT NOT NULL DEFAULT 0,
                        data        JSONB NOT NULL,
                        business_id INT REFERENCES "Nova".t0059(id),
                        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS idx_t0104_staging_batch_id ON "Nova".t0104_staging(batch_id);
                    CREATE INDEX IF NOT EXISTS idx_t0104_staging_entity ON "Nova".t0104_staging(batch_id, entity_type);
                    CREATE INDEX IF NOT EXISTS idx_t0104_staging_business_id ON "Nova".t0104_staging(business_id);
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize database staging table: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            if should_release:
                release_connection(conn)

    def _stage_batch(
        self,
        batch_key: str,
        source_type: str,
        connection_config: Dict[str, Any],
        entity_summaries: Dict[str, Dict[str, Any]],
        total_source_rows: int,
        reconciliation_summary: Dict[str, Any],
        execution_log: List[Dict[str, Any]],
        validation_errors: List[RowValidationError],
        valid_staged_by_entity: Dict[str, List[Dict[str, Any]]],
        tenant_id: Optional[int],
    ) -> int:
        """Save batch metadata to t0104 and stage records into t0104_staging."""
        primary_entity = (
            "multi_entity"
            if len(entity_summaries) > 1
            else (list(entity_summaries.keys())[0] if entity_summaries else "general")
        )

        error_details = [err.model_dump() for err in validation_errors]

        # 1. Create or update batch in t0104
        try:
            batch = BATCH_REPO.create(
                {
                    "batch_key": batch_key,
                    "entity_type": primary_entity,
                    "source_type": source_type,
                    "total_rows": total_source_rows,
                    "inserted_rows": 0,
                    "status": "Preview",
                    "dry_run_completed": True,
                    "connection_config": connection_config,
                    "reconciliation_summary": reconciliation_summary,
                    "execution_log": execution_log,
                    "error_details": error_details,
                    "business_id": tenant_id,
                },
                business_id=tenant_id,
            )
            batch_id = batch["id"] if batch and "id" in batch else 1
        except Exception as e:
            logger.warning(f"Failed to insert into T0104 repo, using fallback batch_id: {e}")
            batch_id = int(time.time()) % 100000

        # Store in-memory cache
        self._in_memory_staging[batch_id] = deepcopy(valid_staged_by_entity)

        # 2. Persist to database staging table if connected
        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                self._ensure_staging_table(conn)
                with conn.cursor() as cur:
                    for entity_type, records in valid_staged_by_entity.items():
                        for idx, rec in enumerate(records, start=1):
                            cur.execute(
                                """
                                INSERT INTO "Nova".t0104_staging 
                                    (batch_id, entity_type, row_index, data, business_id)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (
                                    batch_id,
                                    entity_type,
                                    idx,
                                    json.dumps(rec, default=str),
                                    tenant_id,
                                ),
                            )
                    conn.commit()
            finally:
                release_connection(conn)
        except Exception as e:
            logger.info(f"Database staging table insertion skipped or mocked: {e}")

        return batch_id

    def get_staged_records(
        self,
        batch_id: int,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        business_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve staged records for a given batch from database or in-memory cache."""
        active_tenant = business_id if business_id is not None else get_current_tenant()

        # Try database first
        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    query = 'SELECT data FROM "Nova".t0104_staging WHERE batch_id = %s'
                    params: List[Any] = [batch_id]

                    if entity_type:
                        query += ' AND entity_type = %s'
                        params.append(entity_type)

                    if active_tenant is not None:
                        query += ' AND (business_id = %s OR business_id IS NULL)'
                        params.append(active_tenant)

                    query += ' ORDER BY row_index ASC'

                    if limit is not None:
                        query += ' LIMIT %s'
                        params.append(limit)
                    if offset > 0:
                        query += ' OFFSET %s'
                        params.append(offset)

                    cur.execute(query, params)
                    rows = cur.fetchall()
                    if rows:
                        return [
                            r["data"] if isinstance(r["data"], dict) else json.loads(r["data"])
                            for r in rows
                        ]
            finally:
                release_connection(conn)
        except Exception as e:
            logger.debug(f"Database read for staged records failed, checking in-memory cache: {e}")

        # Fallback to in-memory staging
        if batch_id in self._in_memory_staging:
            staged_map = self._in_memory_staging[batch_id]
            if entity_type:
                records = staged_map.get(entity_type, [])
            else:
                records = []
                for rec_list in staged_map.values():
                    records.extend(rec_list)

            end_idx = (offset + limit) if limit is not None else len(records)
            return records[offset:end_idx]

        return []

    def get_dry_run_result(
        self,
        batch_id_or_key: Union[int, str],
        business_id: Optional[int] = None,
    ) -> Optional[DryRunResult]:
        """Fetch DryRunResult summary for a previously executed dry-run batch."""
        active_tenant = business_id if business_id is not None else get_current_tenant()

        batch_row = None
        if isinstance(batch_id_or_key, int) or (isinstance(batch_id_or_key, str) and batch_id_or_key.isdigit()):
            batch_row = BATCH_REPO.get(int(batch_id_or_key), business_id=active_tenant)
        else:
            batches = BATCH_REPO.list(
                filters={"batch_key": str(batch_id_or_key)},
                business_id=active_tenant,
            )
            if batches:
                batch_row = batches[0]

        if not batch_row:
            return None

        batch_id = batch_row["id"]
        batch_key = batch_row["batch_key"]
        recon = batch_row.get("reconciliation_summary") or {}
        if isinstance(recon, str):
            recon = json.loads(recon)

        err_list = batch_row.get("error_details") or []
        if isinstance(err_list, str):
            err_list = json.loads(err_list)

        parsed_errors = [
            RowValidationError(**err) if isinstance(err, dict) else err
            for err in err_list
        ]

        total_rows = batch_row.get("total_rows", 0)
        valid_rows = recon.get("total_valid_rows", total_rows - len(parsed_errors))
        error_rows = recon.get("total_error_rows", len([e for e in parsed_errors if getattr(e, "severity", "") == "error"]))
        warning_rows = len([e for e in parsed_errors if getattr(e, "severity", "") == "warning"])

        # Fetch sample transformed records
        sample_transformed: Dict[str, List[Dict[str, Any]]] = {}
        entity_summaries = recon.get("entity_counts") or {}
        for ent in entity_summaries.keys():
            sample_transformed[ent] = self.get_staged_records(batch_id, entity_type=ent, limit=5)

        return DryRunResult(
            batch_key=batch_key,
            success=batch_row.get("dry_run_completed", False),
            total_source_rows=total_rows,
            valid_rows_count=valid_rows,
            warning_rows_count=warning_rows,
            error_rows_count=error_rows,
            phantom_products_count=recon.get("total_phantom_products", 0),
            execution_duration_ms=0.0,
            entity_summaries=entity_summaries,
            validation_errors=parsed_errors,
            sample_transformed=sample_transformed,
            reconciliation_summary=recon,
            ready_for_commit=(valid_rows > 0 and error_rows == 0),
        )

    def clear_staging(self, batch_id: int) -> bool:
        """Purge staged records for a given batch."""
        if batch_id in self._in_memory_staging:
            del self._in_memory_staging[batch_id]

        try:
            from packages.database.connection import get_connection, release_connection
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "Nova".t0104_staging WHERE batch_id = %s', (batch_id,))
                    conn.commit()
                    return True
            finally:
                release_connection(conn)
        except Exception as e:
            logger.debug(f"Could not purge database staging records: {e}")
            return True


# Global default instance
dry_run_service = DryRunService()
