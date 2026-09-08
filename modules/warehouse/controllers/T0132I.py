"""
Nova ERP — Warehouse Temperature Zones Controller (T0124I)
Provides REST endpoints for defining thermal control zones (Ambient, Chilled, Frozen, Deep Freeze),
tracking real-time temperatures, and logging sensor telemetry readings.
"""
import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, status

from modules.warehouse.models.temperature_zone import (
    TemperatureZoneCreate,
    TemperatureZoneUpdate,
    TemperatureZoneResponse,
    ZoneReadingLogRequest,
    WarehouseBinResponse,
)
from modules.warehouse.services.cold_chain_service import ColdChainService, ZONE_REPO, BIN_REPO
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

service = ColdChainService(zone_repo=ZONE_REPO, bin_repo=BIN_REPO)

router = create_crud_router(
    '/api/T0132I',
    'T0132 - Warehouse Temperature Zones',
    service,
    TemperatureZoneCreate,
    TemperatureZoneUpdate,
    TemperatureZoneResponse,
)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.post('/{id}/reading', response_model=TemperatureZoneResponse)
def record_zone_temperature_reading(
    id: int,
    body: ZoneReadingLogRequest,
    user: dict = Depends(get_current_user),
):
    """
    Log an IoT sensor or manual temperature reading for a specific zone.
    Automatically evaluates threshold status (Normal, Warning, Excursion).
    """
    _set_tenant_from_user(user)
    zone = service.get_zone(id)
    if not zone:
        check_record_ownership(service, id, user, 'T0132', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Temperature zone #{id} not found")

    try:
        return service.record_zone_reading(
            zone_id=id,
            recorded_temperature=body.recorded_temperature,
            humidity_pct=body.humidity_pct,
            sensor_id=body.sensor_id,
            notes=body.notes,
        )
    except Exception as e:
        logger.error(f"Failed to record zone reading for zone #{id}: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get('/{id}/bins', response_model=List[WarehouseBinResponse])
def get_zone_bins(
    id: int,
    user: dict = Depends(get_current_user),
):
    """List all warehouse storage bins allocated to this temperature zone."""
    _set_tenant_from_user(user)
    zone = service.get_zone(id)
    if not zone:
        check_record_ownership(service, id, user, 'T0132', 'GET')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Temperature zone #{id} not found")

    return service.list_bins(filters={'zone_id': id})


router.routes.sort(key=lambda r: 1 if "{" in getattr(r, "path", "") else 0)
