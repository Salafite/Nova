"""T0104I Controller: REST API endpoints for Legacy ERP Database Connector & Migration Bridge.

Exposes endpoints for:
- Connection testing & metadata discovery (SQL Server, CSV dumps, SQL scripts)
- Table preview sampling
- Dry-run simulation and isolated staging
- Reconciliation reporting (customer balances, inventory quantities, valuation)
- One-click commit and instant zero-downtime rollback
- Batch history and tracking management
- Legacy single-file CSV upload
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel

from modules.core.context import get_current_tenant
from modules.migration.models.migration import (
    CommitMigrationRequest,
    CommitMigrationResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    DryRunRequest,
    DryRunResult,
    MigrationBatchListResponse,
    MigrationBatchResponse,
    ReconciliationReport,
    RollbackMigrationRequest,
    RollbackMigrationResponse,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    TablePreviewRequest,
    TablePreviewResponse,
)
from modules.migration.services import migration_service
from packages.auth.deps import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/migration",
    tags=["Migration"],
    dependencies=[Depends(require_permission("ADMIN_MIGRATION"))],
)


# ==============================================================================
# 1. Connector Testing, Discovery & Previews
# ==============================================================================

@router.get("/connectors")
def list_supported_connectors():
    """List all supported legacy database connectors and extractor modules."""
    return migration_service.list_supported_connectors()


@router.post("/connectors/test", response_model=ConnectionTestResponse)
def test_connection(payload: ConnectionTestRequest):
    """Test connectivity and introspect metadata from a legacy database or file dump."""
    try:
        return migration_service.test_connection(payload)
    except Exception as e:
        logger.error(f"Error testing connection: {e}", exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            error=str(e),
        )


@router.post("/connectors/discover", response_model=SchemaDiscoveryResponse)
def discover_schema(payload: SchemaDiscoveryRequest):
    """Introspect tables, columns, primary/foreign keys, and row count estimates."""
    try:
        return migration_service.discover_schema(payload)
    except Exception as e:
        logger.error(f"Error discovering schema: {e}", exc_info=True)
        return SchemaDiscoveryResponse(
            success=False,
            tables_count=0,
            tables=[],
            schemas={},
            error=str(e),
        )


@router.post("/connectors/preview", response_model=TablePreviewResponse)
def preview_table(payload: TablePreviewRequest):
    """Fetch a sampled preview slice from a legacy table or CSV dataset."""
    try:
        return migration_service.preview_table(payload)
    except Exception as e:
        logger.error(f"Error previewing table {payload.table_name}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to preview table: {str(e)}")


# ==============================================================================
# 2. Dry-Run Simulation & Staging
# ==============================================================================

@router.post("/dry-run", response_model=DryRunResult)
def run_dry_run(payload: DryRunRequest):
    """Execute complete dry-run simulation pipeline with safe batch staging."""
    try:
        tenant_id = get_current_tenant()
        return migration_service.run_dry_run(payload, tenant_id=tenant_id)
    except Exception as e:
        logger.error(f"Error executing migration dry run: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Dry run failed: {str(e)}")


# ==============================================================================
# 3. One-Click Commit & Instant Rollback
# ==============================================================================

class CommitPayload(BaseModel):
    batch_id: int
    force: bool = False


class RollbackPayload(BaseModel):
    batch_id: int
    reason: Optional[str] = None


@router.post("/commit")
def commit_batch(
    payload: Optional[CommitPayload] = None,
    batch_id: Optional[int] = Query(None),
    force: bool = Query(False),
):
    """Commit validated records from staged storage into target Nova ERP tables."""
    effective_batch_id = payload.batch_id if payload else batch_id
    effective_force = payload.force if payload else force

    if effective_batch_id is None:
        raise HTTPException(status_code=400, detail="batch_id is required")

    try:
        tenant_id = get_current_tenant()
        return migration_service.commit(
            request=effective_batch_id,
            business_id=tenant_id,
            force=effective_force,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error committing batch #{effective_batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")


@router.post("/rollback")
def rollback_batch(
    payload: Optional[RollbackPayload] = None,
    batch_id: Optional[int] = Query(None),
    reason: Optional[str] = Query(None),
):
    """Instantly roll back a committed or preview migration batch with zero downtime."""
    effective_batch_id = payload.batch_id if payload else batch_id
    effective_reason = payload.reason if payload else reason

    if effective_batch_id is None:
        raise HTTPException(status_code=400, detail="batch_id is required")

    try:
        tenant_id = get_current_tenant()
        return migration_service.rollback(
            request=effective_batch_id,
            business_id=tenant_id,
            reason=effective_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back batch #{effective_batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


# ==============================================================================
# 4. Batch History, Details & Reconciliation
# ==============================================================================

@router.get("/batches")
def list_batches(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
):
    """Retrieve paginated list of migration batches."""
    filters = {}
    if status:
        filters["status"] = status
    if source_type:
        filters["source_type"] = source_type

    tenant_id = get_current_tenant()
    return migration_service.list_batches(
        filters=filters or None,
        limit=limit,
        offset=offset,
        business_id=tenant_id,
    )


@router.get("/batches/{batch_id}")
@router.get("/batch/{batch_id}")
def get_batch(batch_id: int):
    """Fetch details of a single migration batch."""
    tenant_id = get_current_tenant()
    batch = migration_service.get_batch(batch_id, business_id=tenant_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Migration batch #{batch_id} not found")
    return batch


@router.get("/batches/{batch_id}/reconciliation")
def get_batch_reconciliation(
    batch_id: int,
    tolerance: float = Query(0.01, ge=0.0),
):
    """Retrieve opening balance and inventory reconciliation report for a batch."""
    tenant_id = get_current_tenant()
    report = migration_service.get_reconciliation_report(batch_id_or_key=batch_id, business_id=tenant_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reconciliation report for batch #{batch_id} not found")
    if hasattr(report, "model_dump"):
        return report.model_dump()
    return report


@router.get("/batches/{batch_id}/items")
def get_batch_items(
    batch_id: int,
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Retrieve individual record tracking items for a batch."""
    tenant_id = get_current_tenant()
    return migration_service.get_committed_items(
        batch_id=batch_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
        business_id=tenant_id,
    )


# ==============================================================================
# 5. Legacy CSV Upload & Staging (Backward Compatibility)
# ==============================================================================

@router.post("/upload")
def upload_csv(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    column_mapping: str = Form("{}"),
):
    """Upload and stage a legacy single-entity CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    try:
        mapping = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")

    content = file.file.read().decode("utf-8-sig")
    tenant_id = get_current_tenant()
    try:
        preview = migration_service.upload_csv(
            entity_type=entity_type,
            csv_content=content,
            column_mapping=mapping,
            business_id=tenant_id,
        )
        return preview
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
