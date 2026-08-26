"""
Nova ERP — Inter-Branch Replenishment REST Controller
Provides endpoints for evaluating warehouse inventory deficits against reorder points,
matching deficit items with surplus central distribution hubs, and one-click transfer order generation.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from packages.auth.deps import require_permission, get_current_user
from modules.core.context import set_current_tenant
from modules.inventory.services.replenishment_service import ReplenishmentService
from modules.warehouse.models.stock_transfer import (
    ReplenishmentSuggestionResponse,
    ReplenishmentGenerateRequest,
    ReplenishmentGenerateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/inventory/replenishment",
    tags=["Inventory - Inter-Branch Replenishment"],
    dependencies=[Depends(require_permission("INVENTORY_VIEW"))],
)

service = ReplenishmentService()


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get("business_id") if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.get("/suggestions", response_model=ReplenishmentSuggestionResponse)
def get_replenishment_suggestions(
    warehouse_id: Optional[int] = Query(None, description="Destination branch warehouse ID"),
    source_warehouse_id: Optional[int] = Query(None, description="Preferred source hub warehouse ID"),
    product_id: Optional[int] = Query(None, description="Filter to specific product SKU"),
    category: Optional[str] = Query(None, description="Filter products by category"),
    priority: Optional[str] = Query(None, description="Filter by priority (Critical, High, Normal, Low)"),
    min_deficit: float = Query(0.0, ge=0.0, description="Minimum quantity deficit"),
    safety_stock_ratio: float = Query(0.5, ge=0.0, le=1.0, description="Ratio of reorder level used as safety threshold"),
    target_coverage_multiplier: float = Query(1.5, ge=1.0, description="Multiplier on reorder level for target order size"),
    user: dict = Depends(get_current_user),
):
    """
    Evaluates branch warehouse inventory levels vs reorder points and safety thresholds,
    matches deficit items with surplus central distribution hubs, and returns ranked
    replenishment recommendations.
    """
    _set_tenant_from_user(user)
    try:
        return service.get_replenishment_suggestions(
            warehouse_id=warehouse_id,
            source_warehouse_id=source_warehouse_id,
            product_id=product_id,
            category=category,
            priority=priority,
            min_deficit=min_deficit,
            safety_stock_ratio=safety_stock_ratio,
            target_coverage_multiplier=target_coverage_multiplier,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Failed to calculate replenishment suggestions: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Replenishment evaluation failed: {str(e)}")


@router.post("/generate-transfers", response_model=ReplenishmentGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_replenishment_transfers(
    body: Optional[ReplenishmentGenerateRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    One-click draft Stock Transfer order generation from replenishment recommendations.
    Groups items by (source_warehouse, destination_warehouse) into unified transfer orders.
    """
    _set_tenant_from_user(user)
    try:
        payload = body or ReplenishmentGenerateRequest()
        user_id = user.get("id") if isinstance(user, dict) else None
        return service.generate_transfers(payload=payload, user_id=user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Failed to generate replenishment transfers: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Transfer generation failed: {str(e)}")


@router.get("/summary")
def get_replenishment_summary(
    user: dict = Depends(get_current_user),
):
    """
    Returns network-wide inventory health summary KPIs:
    total products monitored, active warehouses, total deficits,
    critical stockouts, and in-transit transfers.
    """
    _set_tenant_from_user(user)
    try:
        return service.get_stock_health_summary()
    except Exception as e:
        logger.error(f"Failed to fetch replenishment health summary: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to fetch health summary: {str(e)}")
