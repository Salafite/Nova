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


class SupplierPOItemOverride(BaseModel):
    product_id: int
    qty: Optional[float] = Field(None, description="Adjusted order quantity")
    unit_price: Optional[float] = Field(None, description="Custom unit price")
    product_name: Optional[str] = Field(None, description="Custom product name")


class SupplierPOBatchApproveRequest(BaseModel):
    supplier_id: Optional[int] = Field(None, description="Supplier ID")
    warehouse_id: Optional[int] = Field(None, description="Destination warehouse ID")
    expected_date: Optional[str] = Field(None, description="Expected delivery date in YYYY-MM-DD format")
    notes: Optional[str] = Field(None, description="Custom PO notes or rationale")
    items: Optional[List[SupplierPOItemOverride]] = Field(None, description="Optional override list of line items")


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


@router.get("/supplier-queue")
@router.get("/draft-po-queue")
def list_supplier_draft_po_queue(
    warehouse_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    safety_margin_days: int = Query(7, ge=0, le=90),
    target_coverage_days: int = Query(30, ge=1, le=365),
    only_at_risk: bool = Query(True),
):
    """Retrieve consolidated draft PO recommendations grouped by primary supplier,
    including supplier lead times, MOQs, expected delivery dates, and total line items.
    """
    queue = _forecast_svc.get_aggregated_supplier_draft_pos(
        warehouse_id=warehouse_id,
        days=days,
        safety_margin_days=safety_margin_days,
        target_coverage_days=target_coverage_days,
        only_at_risk=only_at_risk,
    )

    total_suppliers = len(queue)
    total_items = sum(g.get("total_items", 0) for g in queue)
    total_suggested_qty = round(sum(float(g.get("total_qty", 0.0) or 0.0) for g in queue), 2)
    total_estimated_spend = round(sum(float(g.get("total_estimated_cost", 0.0) or 0.0) for g in queue), 2)

    return {
        "summary": {
            "total_suppliers": total_suppliers,
            "total_items": total_items,
            "total_suggested_qty": total_suggested_qty,
            "total_estimated_spend": total_estimated_spend,
        },
        "supplier_queue": queue,
    }


@router.post("/supplier-queue/{supplier_id}/approve")
@router.post("/supplier-queue/approve")
def approve_supplier_draft_po(
    supplier_id: Optional[int] = None,
    payload: Optional[SupplierPOBatchApproveRequest] = None,
):
    """Approve or customize a consolidated multi-item draft Purchase Order for a specific supplier."""
    req_payload = payload or SupplierPOBatchApproveRequest()
    target_supplier_id = supplier_id if supplier_id is not None else req_payload.supplier_id

    # Gather supplier group from forecast if items not explicitly provided
    supplier_group = None
    if req_payload.items is None:
        queue = _forecast_svc.get_aggregated_supplier_draft_pos(
            warehouse_id=req_payload.warehouse_id,
            only_at_risk=True,
        )
        for g in queue:
            if g.get("supplier_id") == target_supplier_id:
                supplier_group = g
                break

        if not supplier_group and target_supplier_id is not None:
            all_queue = _forecast_svc.get_aggregated_supplier_draft_pos(
                warehouse_id=req_payload.warehouse_id,
                only_at_risk=False,
            )
            for g in all_queue:
                if g.get("supplier_id") == target_supplier_id:
                    supplier_group = g
                    break

        if not supplier_group:
            raise HTTPException(
                status_code=404,
                detail=f"No restock items found for supplier #{target_supplier_id}",
            )

    lines_data = []
    if req_payload.items is not None:
        for item in req_payload.items:
            product = _product_repo.get(item.product_id)
            p_name = item.product_name or (product.get("name") if product else f"Product #{item.product_id}")
            unit_price = item.unit_price
            if unit_price is None:
                sup_map = _forecast_svc.get_preferred_supplier(item.product_id)
                unit_price = float(sup_map.get("unit_cost") if sup_map else (product.get("cost_price", 0.0) if product else 0.0))

            qty = float(item.qty) if item.qty is not None else 1.0
            if qty <= 0:
                qty = 1.0

            line_total = round(qty * unit_price, 2)
            lines_data.append({
                "product_id": item.product_id,
                "product_name": p_name,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            })
    elif supplier_group:
        for item in supplier_group.get("items", []):
            qty = float(item.get("suggested_order_qty") or 1.0)
            if qty <= 0:
                qty = float(item.get("min_order_qty") or 1.0)
            unit_price = float(item.get("unit_cost") or 0.0)
            line_total = round(qty * unit_price, 2)
            lines_data.append({
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name", f"Product #{item.get('product_id')}"),
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            })

    if not lines_data:
        raise HTTPException(status_code=400, detail="Cannot create purchase order with zero line items")

    lead_time = supplier_group.get("lead_time_days", 7) if supplier_group else 7
    expected_date = req_payload.expected_date or (date.today() + timedelta(days=lead_time)).isoformat()
    total_amount = round(sum(l["line_total"] for l in lines_data), 2)

    sup_name = supplier_group.get("supplier_name") if supplier_group else f"Supplier #{target_supplier_id}"

    existing_pos = _po_repo.list()
    count = len(existing_pos) + 1
    existing_numbers = {p.get("order_number") for p in existing_pos if isinstance(p, dict)}
    order_number = f"PO-{str(count).zfill(3)}"
    while order_number in existing_numbers:
        count += 1
        order_number = f"PO-{str(count).zfill(3)}"

    notes = req_payload.notes or (supplier_group.get("po_notes") if supplier_group else f"Consolidated draft PO for {sup_name}")

    po_payload = {
        "order_number": order_number,
        "supplier_id": target_supplier_id or 1,
        "total": total_amount,
        "status": "Pending",
        "order_date": date.today().isoformat(),
        "expected_date": expected_date,
        "notes": notes,
    }

    created_po = _po_svc.create(po_payload)
    po_id = created_po.get("id")

    created_lines = []
    for idx, l in enumerate(lines_data, start=1):
        line_data = {
            "purchase_order_id": po_id,
            "product_id": l["product_id"],
            "product_name": l["product_name"],
            "qty": l["qty"],
            "unit_price": l["unit_price"],
            "line_total": l["line_total"],
            "line_number": idx,
        }
        created_line = _po_line_repo.create(line_data)
        created_lines.append(created_line)

    return {
        "ok": True,
        "purchase_order": created_po,
        "lines": created_lines,
        "total_items": len(created_lines),
        "total_amount": total_amount,
        "message": f"Consolidated Draft Purchase Order {order_number} created successfully with {len(created_lines)} items",
    }


@router.post("/supplier-queue/approve-all")
def batch_approve_all_supplier_pos(
    warehouse_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    safety_margin_days: int = Query(7, ge=0, le=90),
    target_coverage_days: int = Query(30, ge=1, le=365),
):
    """Batch approve and generate consolidated draft purchase orders for all suppliers with at-risk items."""
    queue = _forecast_svc.get_aggregated_supplier_draft_pos(
        warehouse_id=warehouse_id,
        days=days,
        safety_margin_days=safety_margin_days,
        target_coverage_days=target_coverage_days,
        only_at_risk=True,
    )

    if not queue:
        return {
            "ok": True,
            "created_pos": [],
            "total_pos": 0,
            "total_spend": 0.0,
            "message": "No at-risk supplier queues found to approve",
        }

    created_pos = []
    total_spend = 0.0

    for group in queue:
        sup_id = group.get("supplier_id")
        res = approve_supplier_draft_po(
            supplier_id=sup_id,
            payload=SupplierPOBatchApproveRequest(
                supplier_id=sup_id,
                warehouse_id=warehouse_id,
            ),
        )
        created_pos.append(res["purchase_order"])
        total_spend += res["total_amount"]

    return {
        "ok": True,
        "created_pos": created_pos,
        "total_pos": len(created_pos),
        "total_spend": round(total_spend, 2),
        "message": f"Successfully generated {len(created_pos)} consolidated draft purchase orders totaling ${total_spend:,.2f}",
    }


@router.get("/supplier-lead-times")
def list_supplier_lead_times():
    """Retrieve primary supplier lead times, MOQs, and unit cost mappings across products."""
    products = _product_repo.list()
    lead_time_records = []

    for p in products:
        if not p.get("is_active", True):
            continue
        p_id = p.get("id")
        sup_mapping = _forecast_svc.get_preferred_supplier(p_id)
        if sup_mapping:
            lead_time_records.append({
                "product_id": p_id,
                "product_name": p.get("name"),
                "sku": p.get("sku"),
                "supplier_id": sup_mapping.get("supplier_id"),
                "supplier_name": sup_mapping.get("supplier_name") or "Unassigned Supplier",
                "supplier_sku": sup_mapping.get("supplier_sku"),
                "unit_cost": sup_mapping.get("unit_cost"),
                "lead_time_days": sup_mapping.get("lead_time_days"),
                "min_order_qty": sup_mapping.get("min_order_qty"),
                "is_preferred": sup_mapping.get("is_preferred"),
            })

    return {
        "total_mappings": len(lead_time_records),
        "supplier_lead_times": lead_time_records,
    }
