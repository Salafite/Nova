"""
Nova ERP — Warehouse Bins & Staging Areas Controller (T0125I)
Manages storage bin locations, staging docks, thermal profile constraints,
and cold-chain putaway compatibility checks.
"""
import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, status

from modules.warehouse.models.temperature_zone import (
    WarehouseBinCreate,
    WarehouseBinUpdate,
    WarehouseBinResponse,
    TemperatureCheckRequest,
    TemperatureCheckResponse,
)
from modules.warehouse.services.cold_chain_service import ColdChainService, BIN_REPO
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

bin_crud_service = CrudService(BIN_REPO)
cold_chain_service = ColdChainService()

router = create_crud_router(
    '/api/T0133I',
    'T0133 - Warehouse Bins & Staging Areas',
    bin_crud_service,
    WarehouseBinCreate,
    WarehouseBinUpdate,
    WarehouseBinResponse,
)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.post('/check-compatibility', response_model=TemperatureCheckResponse)
def check_storage_compatibility(
    body: TemperatureCheckRequest,
    user: dict = Depends(get_current_user),
):
    """
    Validate product temperature constraints against target warehouse bin, zone, or compartment.
    Detects critical HACCP violations, inappropriate storage zones, and excursion risks.
    """
    _set_tenant_from_user(user)
    try:
        return cold_chain_service.check_temperature_compatibility(
            product_id=body.product_id,
            target_zone_id=body.target_zone_id,
            target_bin_id=body.target_bin_id,
            target_compartment_id=body.target_compartment_id,
            warehouse_id=body.warehouse_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking temperature compatibility: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


router.routes.sort(key=lambda r: 1 if "{" in getattr(r, "path", "") else 0)
