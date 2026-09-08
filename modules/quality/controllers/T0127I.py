"""
Nova ERP — Temperature Excursion Alerts Controller (T0127I)
Manages real-time cold-chain temperature excursion alerts, acknowledgment,
corrective action resolution, and lot quarantine workflows.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status

from modules.quality.models.haccp_audit import (
    ExcursionAlertCreate,
    ExcursionAlertUpdate,
    ExcursionAlertResponse,
    ExcursionAlertAcknowledgeRequest,
    ExcursionAlertResolveRequest,
    ExcursionAlertQuarantineRequest,
)
from modules.quality.services.haccp_audit_service import HaccpAuditService, ALERT_REPO
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

service = HaccpAuditService(alert_repo=ALERT_REPO)

router = create_crud_router(
    '/api/T0127I',
    'T0127 - Temperature Excursion Alerts',
    service,
    ExcursionAlertCreate,
    ExcursionAlertUpdate,
    ExcursionAlertResponse,
)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.post('/{id}/acknowledge', response_model=ExcursionAlertResponse)
def acknowledge_excursion_alert(
    id: int,
    body: Optional[ExcursionAlertAcknowledgeRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Acknowledge a temperature excursion alert by quality supervisor or warehouse operator.
    """
    _set_tenant_from_user(user)
    existing = service.get_alert(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0127', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{id} not found")

    user_id = (body.user_id if body and body.user_id else None) or (user.get('id') if isinstance(user, dict) else 1)
    notes = body.notes if body else None
    return service.acknowledge_alert(id, user_id=user_id, notes=notes)


@router.post('/{id}/resolve', response_model=ExcursionAlertResponse)
def resolve_excursion_alert(
    id: int,
    body: ExcursionAlertResolveRequest,
    user: dict = Depends(get_current_user),
):
    """
    Resolve a temperature excursion alert with documented corrective resolution action.
    """
    _set_tenant_from_user(user)
    existing = service.get_alert(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0127', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{id} not found")

    user_id = body.user_id or (user.get('id') if isinstance(user, dict) else 1)
    return service.resolve_alert(
        id,
        resolution_action=body.resolution_action,
        user_id=user_id,
        notes=body.notes,
    )


@router.post('/{id}/quarantine', response_model=ExcursionAlertResponse)
def quarantine_excursion_lot(
    id: int,
    body: ExcursionAlertQuarantineRequest,
    user: dict = Depends(get_current_user),
):
    """
    Quarantine affected inventory batch following a critical cold-chain breach.
    """
    _set_tenant_from_user(user)
    existing = service.get_alert(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0127', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{id} not found")

    user_id = body.user_id or (user.get('id') if isinstance(user, dict) else 1)
    return service.quarantine_lot(
        id,
        quarantine_notes=body.quarantine_notes,
        user_id=user_id,
    )


router.routes.sort(key=lambda r: 1 if "{" in getattr(r, "path", "") else 0)
