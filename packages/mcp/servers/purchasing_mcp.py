from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.purchasing.services.demand_forecast_service import DemandForecastService
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_po_repo = CrudRepository('T0014', business_columns=['id', 'order_number', 'supplier_id', 'total', 'status', 'order_date', 'expected_date', 'notes', 'converted_rfq_id'])
_po_svc = CrudService(_po_repo)

_po_line_repo = CrudRepository('T0015', business_columns=['id', 'purchase_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total', 'line_number'])
_po_line_svc = CrudService(_po_line_repo)

_pr_repo = CrudRepository('T0081', business_columns=['id', 'return_number', 'purchase_order_id', 'supplier_id', 'return_date', 'status', 'reason', 'notes'])
_pr_svc = CrudService(_pr_repo)

_rfq_repo = CrudRepository('T0071', business_columns=['id', 'rfq_number', 'title', 'description', 'status', 'due_date', 'notes'])
_rfq_svc = CrudService(_rfq_repo)

_product_repo = CrudRepository('T0003', business_columns=['id', 'name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'is_active'])
_supplier_repo = CrudRepository('T0011', business_columns=['id', 'name', 'category', 'phone', 'email', 'payment_terms', 'rating', 'is_active'])

_forecast_svc = DemandForecastService()


def register_tools():
    register_tool(Tool(name="list_purchase_orders", description="List purchase orders", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "supplier_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_po)
    register_tool(Tool(name="get_purchase_order", description="Get a purchase order by ID", input_schema={
        "type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"],
    }), _get_po)
    register_tool(Tool(name="list_purchase_returns", description="List purchase returns", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "supplier_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_pr)
    register_tool(Tool(name="list_rfqs", description="List requests for quotation", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "limit": {"type": "integer"},
        },
    }), _list_rfq)
    register_tool(
        Tool(
            name="calculate_restock_forecast",
            description="Calculate demand forecasting, 30-day sales velocity, projected stockout dates, supplier lead times, and restock suggestions",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Optional product ID to calculate forecast for a single SKU. If omitted, returns forecasts across all active products.",
                    },
                    "warehouse_id": {
                        "type": "integer",
                        "description": "Optional warehouse ID filter.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Lookback window in days for sales velocity (default 30).",
                    },
                    "safety_margin_days": {
                        "type": "integer",
                        "description": "Safety margin buffer in days (default 7).",
                    },
                    "target_coverage_days": {
                        "type": "integer",
                        "description": "Target days of inventory coverage (default 30).",
                    },
                    "only_at_risk": {
                        "type": "boolean",
                        "description": "If true, only return products that currently need restock (default false).",
                    },
                },
            },
        ),
        _calculate_restock_forecast,
    )
    register_tool(
        Tool(
            name="propose_draft_purchase_order",
            description="Propose and generate a draft purchase order for restock based on demand forecasting, supplier lead time, and MOQ",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID to restock (optional if items list is provided)",
                    },
                    "supplier_id": {
                        "type": "integer",
                        "description": "Supplier ID (optional; auto-resolved from preferred supplier mapping if omitted)",
                    },
                    "qty": {
                        "type": "number",
                        "description": "Order quantity (optional; auto-calculated from demand forecast & MOQ if omitted)",
                    },
                    "warehouse_id": {
                        "type": "integer",
                        "description": "Destination warehouse ID (optional, default 1)",
                    },
                    "expected_date": {
                        "type": "string",
                        "description": "Expected delivery date in YYYY-MM-DD format (optional; auto-calculated from supplier lead time)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional custom notes or reason for order",
                    },
                    "items": {
                        "type": "array",
                        "description": "Optional list of multiple items for draft PO: [{'product_id': int, 'qty': float, 'unit_price': float, 'product_name': str}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "integer"},
                                "qty": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "product_name": {"type": "string"},
                            },
                            "required": ["product_id", "qty"],
                        },
                    },
                },
            },
        ),
        _propose_draft_purchase_order,
    )


def _list_po(status: str = None, supplier_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if supplier_id: filters["supplier_id"] = supplier_id
    return _po_svc.list(filters=filters or None, limit=limit)

def _get_po(id: int):
    return _po_svc.get(id)

def _list_pr(status: str = None, supplier_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if supplier_id: filters["supplier_id"] = supplier_id
    return _pr_svc.list(filters=filters or None, limit=limit)

def _list_rfq(status: str = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    return _rfq_svc.list(filters=filters or None, limit=limit)


def _calculate_restock_forecast(
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    days: int = 30,
    safety_margin_days: int = 7,
    target_coverage_days: int = 30,
    only_at_risk: bool = False,
):
    if product_id is not None:
        return _forecast_svc.calculate_sku_forecast(
            product=product_id,
            warehouse_id=warehouse_id,
            days=days or 30,
            safety_margin_days=safety_margin_days or 7,
            target_coverage_days=target_coverage_days or 30,
        )
    return _forecast_svc.calculate_all_forecasts(
        warehouse_id=warehouse_id,
        days=days or 30,
        safety_margin_days=safety_margin_days or 7,
        target_coverage_days=target_coverage_days or 30,
        only_at_risk=bool(only_at_risk),
    )


def _propose_draft_purchase_order(
    product_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    qty: Optional[float] = None,
    warehouse_id: Optional[int] = None,
    expected_date: Optional[str] = None,
    notes: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
):
    line_items = []
    final_supplier_id = supplier_id
    forecast_rationale = notes or ""

    if items and len(items) > 0:
        for idx, item in enumerate(items, start=1):
            p_id = item.get("product_id")
            p_qty = float(item.get("qty", 1.0))
            p_name = item.get("product_name")
            p_price = item.get("unit_price")

            if not p_name or p_price is None:
                p_data = _product_repo.get(p_id) if p_id else None
                if p_data:
                    p_name = p_name or p_data.get("name", f"Product #{p_id}")
                    if p_price is None:
                        p_price = float(p_data.get("cost_price", 0.0) or 0.0)
                else:
                    p_name = p_name or f"Product #{p_id}"
                    p_price = float(p_price or 0.0)

            line_items.append({
                "product_id": p_id,
                "product_name": p_name,
                "qty": p_qty,
                "unit_price": float(p_price),
                "line_total": round(p_qty * float(p_price), 2),
                "line_number": idx,
            })

            if final_supplier_id is None and p_id:
                sup_mapping = _forecast_svc.get_preferred_supplier(p_id)
                if sup_mapping:
                    final_supplier_id = sup_mapping.get("supplier_id")
    elif product_id is not None:
        forecast = _forecast_svc.calculate_sku_forecast(
            product=product_id,
            warehouse_id=warehouse_id,
        )
        if final_supplier_id is None:
            final_supplier_id = forecast.get("supplier_id") or 1

        order_qty = float(qty) if (qty is not None and qty > 0) else float(forecast.get("suggested_order_qty") or 0.0)
        if order_qty <= 0:
            order_qty = max(1.0, float(forecast.get("min_order_qty") or 1.0))

        unit_cost = float(forecast.get("unit_cost") or 0.0)
        lead_time = int(forecast.get("lead_time_days") or 7)
        if not expected_date:
            expected_date = (date.today() + timedelta(days=lead_time)).isoformat()

        if not forecast_rationale:
            forecast_rationale = forecast.get("rationale", "")

        product_name = forecast.get("product_name", f"Product #{product_id}")

        line_items.append({
            "product_id": product_id,
            "product_name": product_name,
            "qty": order_qty,
            "unit_price": unit_cost,
            "line_total": round(order_qty * unit_cost, 2),
            "line_number": 1,
        })
    else:
        raise ValueError("Either product_id or items must be provided to propose a draft purchase order.")

    if final_supplier_id is None:
        final_supplier_id = 1

    total_amount = round(sum(l["line_total"] for l in line_items), 2)

    # Generate unique PO order number
    existing_pos = _po_repo.list()
    count = len(existing_pos) + 1
    existing_numbers = {p.get("order_number") for p in existing_pos if isinstance(p, dict)}
    order_number = f"PO-{str(count).zfill(3)}"
    while order_number in existing_numbers:
        count += 1
        order_number = f"PO-{str(count).zfill(3)}"

    if not expected_date:
        expected_date = (date.today() + timedelta(days=7)).isoformat()

    po_payload = {
        "order_number": order_number,
        "supplier_id": final_supplier_id,
        "total": total_amount,
        "status": "Pending",
        "order_date": date.today().isoformat(),
        "expected_date": expected_date,
        "notes": forecast_rationale or f"Restock PO generated by AI Agent for supplier #{final_supplier_id}",
    }

    created_po = _po_svc.create(po_payload)
    po_id = created_po.get("id")

    created_lines = []
    for line in line_items:
        line_data = {
            "purchase_order_id": po_id,
            "product_id": line["product_id"],
            "product_name": line["product_name"],
            "qty": line["qty"],
            "unit_price": line["unit_price"],
            "line_total": line["line_total"],
            "line_number": line["line_number"],
        }
        created_line = _po_line_repo.create(line_data)
        created_lines.append(created_line)

    return {
        "purchase_order": created_po,
        "lines": created_lines,
        "forecast_rationale": forecast_rationale,
        "message": f"Draft purchase order {created_po.get('order_number')} created successfully with status 'Pending'.",
    }


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="purchasing-mcp", version="1.0"))

if __name__ == "__main__":
    main()
