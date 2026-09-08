"""
Nova ERP — HACCP Checkpoint Logs & Compliance Reports Controller (T0128I)
Exposes endpoints for logging supply chain checkpoint temperatures and
compiling end-to-end HACCP compliance audit reports & certificates.
"""
import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, Query, status

from modules.quality.models.haccp_audit import (
    HACCPCheckpointLogCreate,
    HACCPCheckpointLogUpdate,
    HACCPCheckpointLogResponse,
    HACCPComplianceReportResponse,
)
from modules.quality.services.haccp_audit_service import HaccpAuditService, LOG_REPO
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

log_crud_service = CrudService(LOG_REPO)
haccp_service = HaccpAuditService()

router = create_crud_router(
    '/api/T0128I',
    'T0128 - HACCP Checkpoint Logs',
    log_crud_service,
    HACCPCheckpointLogCreate,
    HACCPCheckpointLogUpdate,
    HACCPCheckpointLogResponse,
)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.post('/checkpoint', response_model=HACCPCheckpointLogResponse, status_code=status.HTTP_201_CREATED)
def log_haccp_checkpoint(
    body: HACCPCheckpointLogCreate,
    user: dict = Depends(get_current_user),
):
    """
    Log a temperature checkpoint reading across any supply chain stage
    (GoodsReceipt, WarehouseStorage, StagingDock, VehicleDeparture, TransitCheckpoint, DestinationDelivery).
    Automatically checks against HACCP critical limits and generates excursion alerts if violated.
    """
    _set_tenant_from_user(user)
    try:
        if not body.logged_by_id and isinstance(user, dict) and user.get('id'):
            body.logged_by_id = user.get('id')
        return haccp_service.log_checkpoint(body)
    except Exception as e:
        logger.error(f"Failed to log HACCP checkpoint: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get('/compliance-report', response_model=HACCPComplianceReportResponse)
def get_haccp_compliance_report(
    product_id: Optional[int] = Query(None, description="Product ID filter"),
    batch_number: Optional[str] = Query(None, description="Batch / Lot number filter"),
    delivery_run_id: Optional[int] = Query(None, description="Delivery run ID filter"),
    user: dict = Depends(get_current_user),
):
    """
    Generate an end-to-end HACCP compliance audit report showing all thermal checkpoint readings,
    excursion statistics, and certification status from inbound receipt to customer delivery.
    """
    _set_tenant_from_user(user)
    try:
        return haccp_service.compile_compliance_report(
            product_id=product_id,
            batch_number=batch_number,
            delivery_run_id=delivery_run_id,
        )
    except Exception as e:
        logger.error(f"Failed to compile HACCP compliance report: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


router.routes.sort(key=lambda r: 1 if "{" in getattr(r, "path", "") else 0)
