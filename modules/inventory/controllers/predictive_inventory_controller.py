"""
Nova ERP — Predictive Inventory & Spoilage Prevention REST Controller
Provides REST API endpoints for statistical demand forecasting with confidence intervals
and perishable batch spoilage risk evaluation with promotional discount markdown proposals.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from packages.auth.deps import require_permission, get_current_user
from modules.core.context import set_current_tenant
from modules.inventory.services.predictive_demand_service import PredictiveDemandService
from modules.inventory.services.spoilage_prevention_service import SpoilagePreventionService
from modules.inventory.models.predictive_forecast import SKUForecastParameters
from modules.inventory.models.spoilage_prevention import (
    SpoilageRiskSummaryResponse,
    BatchDiscountPromotionProposal,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory - Predictive Demand & Spoilage"],
    dependencies=[Depends(require_permission("INVENTORY_VIEW"))],
)

demand_service = PredictiveDemandService()
spoilage_service = SpoilagePreventionService(demand_service=demand_service)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get("business_id") if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


@router.get("/predictive-demand", response_model=List[SKUForecastParameters])
def get_predictive_demand_forecast(
    product_id: Optional[int] = Query(None, description="Filter by product SKU ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    lookback_days: int = Query(90, ge=7, le=365, description="Historical sales lookback window in days"),
    forecast_weeks: int = Query(4, ge=1, le=52, description="Number of weeks to project forecast"),
    user: dict = Depends(get_current_user),
):
    """
    Project weekly demand forecasts per SKU with statistical confidence intervals (80% & 95% bounds).
    """
    _set_tenant_from_user(user)
    try:
        if product_id:
            forecast = demand_service.generate_demand_forecast(
                product_id=product_id,
                warehouse_id=warehouse_id,
                lookback_days=lookback_days,
                forecast_weeks=forecast_weeks,
            )
            return [forecast]
        else:
            return demand_service.list_demand_forecasts(
                product_ids=None,
                warehouse_id=warehouse_id,
                lookback_days=lookback_days,
                forecast_weeks=forecast_weeks,
            )
    except Exception as e:
        logger.error(f"Error fetching predictive demand forecast: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate predictive demand forecast: {str(e)}",
        )


@router.get("/spoilage-risk", response_model=SpoilageRiskSummaryResponse)
def get_spoilage_risk_alerts(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    product_id: Optional[int] = Query(None, description="Filter by product SKU ID"),
    min_severity: Optional[str] = Query(None, description="Filter by minimum risk severity ('low', 'medium', 'high', 'critical')"),
    days_to_expiry_threshold: int = Query(60, ge=1, le=365, description="Days to expiry horizon threshold"),
    user: dict = Depends(get_current_user),
):
    """
    Evaluate active perishable inventory batches against demand velocity to detect spoilage risk.
    """
    _set_tenant_from_user(user)
    try:
        return spoilage_service.evaluate_spoilage_risks(
            warehouse_id=warehouse_id,
            product_id=product_id,
            min_severity=min_severity,
            days_to_expiry_threshold=days_to_expiry_threshold,
        )
    except Exception as e:
        logger.error(f"Error evaluating spoilage risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate batch spoilage risks: {str(e)}",
        )


@router.post("/spoilage-risk/propose-discount", response_model=BatchDiscountPromotionProposal)
def propose_batch_discount_promotion(
    batch_id: int = Query(..., description="ID of the batch to apply markdown discount"),
    discount_percentage: Optional[float] = Query(None, ge=0.0, le=90.0, description="Optional override discount percentage"),
    user: dict = Depends(get_current_user),
):
    """
    Generate a promotional discount markdown proposal for a perishable batch to prevent spoilage.
    """
    _set_tenant_from_user(user)
    try:
        return spoilage_service.propose_batch_discount_promotion(
            batch_id=batch_id,
            override_discount_pct=discount_percentage,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error proposing batch discount promotion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch discount promotion proposal: {str(e)}",
        )
