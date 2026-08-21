import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from packages.auth.deps import require_permission, get_current_user
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.purchasing.services.demand_forecast_service import DemandForecastService
from modules.purchasing.services.restock_agent import RestockAgentService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/purchasing/restock",
    tags=["Purchasing - Proactive Demand Restock"],
    dependencies=[Depends(require_permission("PURCHASING_VIEW"))],
)

_forecast_svc = DemandForecastService()
_restock_agent = RestockAgentService(forecast_service=_forecast_svc)

_po_repo = CrudRepository(
    "T0014",
    business_columns=[
        "id",
        "order_number",
        "supplier_id",
        "total",
        "status",
        "order_date",
        "expected_date",
        "notes",
        "converted_rfq_id",
    ],
)
_po_svc = CrudService(_po_repo)

_po_line_repo = CrudRepository(
    "T0015",
    business_columns=[
        "id",
        "purchase_order_id",
        "product_id",
        "product_name",
        "uom_id",
        "qty",
        "unit_price",
        "line_total",
        "line_number",
    ],
)

_product_repo = CrudRepository(
    "T0003",
    business_columns=[
        "id",
        "name",
        "sku",
        "price",
        "cost_price",
        "category",
        "brand",
        "tax_rate",
        "is_active",
    ],
)


class RestockEditRequest(BaseModel):
    qty: Optional[float] = Field(None, description="Adjusted order quantity")
    supplier_id: Optional[int] = Field(None, description="Adjusted supplier ID")
    warehouse_id: Optional[int] = Field(None, description="Destination warehouse ID")
    expected_date: Optional[str] = Field(None, description="Expected delivery date in YYYY-MM-DD format")
    notes: Optional[str] = Field(None, description="Custom PO notes or rationale")
    unit_price: Optional[float] = Field(None, description="Custom unit price")


class RestockRejectRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for rejecting or dismissing suggestion")


class RestockRunForecastRequest(BaseModel):
    warehouse_id: Optional[int] = None
    days: int = 30
    safety_margin_days: int = 7
    target_coverage_days: int = 30
    send_notification: bool = False


@router.get("/suggestions")
def list_restock_suggestions(
    warehouse_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    safety_margin_days: int = Query(7, ge=0, le=90),
    target_coverage_days: int = Query(30, ge=1, le=365),
    only_at_risk: bool = Query(True),
):
    """Retrieve demand forecasting and restock recommendations with velocity,
    projected stockouts, supplier terms, MOQs, and decision rationale.
    """
    all_forecasts = _forecast_svc.calculate_all_forecasts(
        warehouse_id=warehouse_id,
        days=days,
        safety_margin_days=safety_margin_days,
        target_coverage_days=target_coverage_days,
        only_at_risk=False,
    )

    suggestions = [f for f in all_forecasts if (not only_at_risk or f.get("needs_restock"))]

    total_evaluated = len(all_forecasts)
    at_risk_count = len([f for f in all_forecasts if f.get("needs_restock")])
    critical_count = sum(1 for s in suggestions if s.get("urgency") == "CRITICAL")
    high_count = sum(1 for s in suggestions if s.get("urgency") == "HIGH")
    medium_count = sum(1 for s in suggestions if s.get("urgency") == "MEDIUM")

    total_suggested_qty = round(
        sum(float(s.get("suggested_order_qty", 0.0) or 0.0) for s in suggestions), 2
    )
    total_estimated_spend = round(
        sum(float(s.get("estimated_cost", 0.0) or 0.0) for s in suggestions), 2
    )

    return {
        "summary": {
            "total_evaluated": total_evaluated,
            "at_risk_count": at_risk_count,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "total_suggested_qty": total_suggested_qty,
            "total_estimated_spend": total_estimated_spend,
        },
        "suggestions": suggestions,
    }


@router.post("/suggestions/{id}/approve")
def approve_restock_suggestion(
    id: int,
    warehouse_id: Optional[int] = Query(None),
):
    """One-click approve a restock recommendation and generate a draft Purchase Order
    in status 'Pending' with computed MOQ, velocity, and rationale.
    """
    product = _product_repo.get(id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{id} not found")

    forecast = _forecast_svc.calculate_sku_forecast(
        product=product,
        warehouse_id=warehouse_id,
    )

    order_qty = float(forecast.get("suggested_order_qty") or 0.0)
    if order_qty <= 0:
        order_qty = max(1.0, float(forecast.get("min_order_qty") or 1.0))

    supplier_id = forecast.get("supplier_id") or 1
    unit_cost = float(forecast.get("unit_cost") or 0.0)
    lead_time = int(forecast.get("lead_time_days") or 7)
    expected_date = (date.today() + timedelta(days=lead_time)).isoformat()
    total_amount = round(order_qty * unit_cost, 2)
    product_name = forecast.get("product_name", product.get("name", f"Product #{id}"))

    # Generate unique PO order number
    existing_pos = _po_repo.list()
    count = len(existing_pos) + 1
    existing_numbers = {p.get("order_number") for p in existing_pos if isinstance(p, dict)}
    order_number = f"PO-{str(count).zfill(3)}"
    while order_number in existing_numbers:
        count += 1
        order_number = f"PO-{str(count).zfill(3)}"

    rationale = forecast.get("rationale", "")
    po_payload = {
        "order_number": order_number,
        "supplier_id": supplier_id,
        "total": total_amount,
        "status": "Pending",
        "order_date": date.today().isoformat(),
        "expected_date": expected_date,
        "notes": rationale or f"AI restock order for {product_name} ({order_qty} units)",
    }

    created_po = _po_svc.create(po_payload)
    po_id = created_po.get("id")

    line_data = {
        "purchase_order_id": po_id,
        "product_id": id,
        "product_name": product_name,
        "qty": order_qty,
        "unit_price": unit_cost,
        "line_total": total_amount,
        "line_number": 1,
    }
    created_line = _po_line_repo.create(line_data)

    return {
        "ok": True,
        "purchase_order": created_po,
        "lines": [created_line],
        "message": f"Draft Purchase Order {order_number} created successfully",
    }


@router.post("/suggestions/{id}/edit")
def edit_and_create_restock_po(
    id: int,
    payload: RestockEditRequest,
):
    """Modify restock quantity, supplier, expected date, or notes before creating draft PO."""
    product = _product_repo.get(id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{id} not found")

    forecast = _forecast_svc.calculate_sku_forecast(
        product=product,
        warehouse_id=payload.warehouse_id,
    )

    order_qty = float(payload.qty) if payload.qty is not None else float(forecast.get("suggested_order_qty") or 1.0)
    if order_qty <= 0:
        order_qty = 1.0

    supplier_id = payload.supplier_id if payload.supplier_id is not None else (forecast.get("supplier_id") or 1)
    unit_cost = float(payload.unit_price) if payload.unit_price is not None else float(forecast.get("unit_cost") or 0.0)

    lead_time = int(forecast.get("lead_time_days") or 7)
    expected_date = payload.expected_date or (date.today() + timedelta(days=lead_time)).isoformat()
    total_amount = round(order_qty * unit_cost, 2)
    product_name = forecast.get("product_name", product.get("name", f"Product #{id}"))

    existing_pos = _po_repo.list()
    count = len(existing_pos) + 1
    existing_numbers = {p.get("order_number") for p in existing_pos if isinstance(p, dict)}
    order_number = f"PO-{str(count).zfill(3)}"
    while order_number in existing_numbers:
        count += 1
        order_number = f"PO-{str(count).zfill(3)}"

    notes = payload.notes or forecast.get("rationale") or f"Customized AI restock order for {product_name}"
    po_payload = {
        "order_number": order_number,
        "supplier_id": supplier_id,
        "total": total_amount,
        "status": "Pending",
        "order_date": date.today().isoformat(),
        "expected_date": expected_date,
        "notes": notes,
    }

    created_po = _po_svc.create(po_payload)
    po_id = created_po.get("id")

    line_data = {
        "purchase_order_id": po_id,
        "product_id": id,
        "product_name": product_name,
        "qty": order_qty,
        "unit_price": unit_cost,
        "line_total": total_amount,
        "line_number": 1,
    }
    created_line = _po_line_repo.create(line_data)

    return {
        "ok": True,
        "purchase_order": created_po,
        "lines": [created_line],
        "message": f"Draft Purchase Order {order_number} created successfully",
    }


@router.post("/suggestions/{id}/reject")
def reject_restock_suggestion(
    id: int,
    payload: Optional[RestockRejectRequest] = None,
):
    """Dismiss or reject a restock suggestion."""
    product = _product_repo.get(id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product #{id} not found")

    reason = payload.reason if payload else None
    logger.info(f"Restock suggestion for product #{id} ({product.get('sku')}) dismissed. Reason: {reason}")

    return {
        "ok": True,
        "product_id": id,
        "status": "Dismissed",
        "reason": reason,
        "message": f"Restock suggestion for {product.get('sku', f'Product #{id}')} dismissed",
    }


@router.post("/run-forecast")
def trigger_demand_forecast(
    payload: Optional[RestockRunForecastRequest] = None,
):
    """Trigger an on-demand background demand forecasting evaluation."""
    req = payload or RestockRunForecastRequest()
    result = _restock_agent.run_evaluation(
        warehouse_id=req.warehouse_id,
        days=req.days,
        safety_margin_days=req.safety_margin_days,
        target_coverage_days=req.target_coverage_days,
        send_notification=req.send_notification,
    )
    return result
