from typing import Any, Dict, List, Optional
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.sales.models.field_sales import (
    FieldSalesBatchSyncRequest,
    FieldSalesBatchSyncResponse,
    FieldSalesOrderLine,
    FieldSalesOrderSubmission,
    FieldSalesValidationRequest,
    FieldSalesValidationResponse,
)
from modules.sales.services.field_sales_catalog_service import (
    FieldSalesCatalogService,
    field_sales_catalog_service as default_catalog_service,
)
from modules.sales.services.field_sales_sync_service import (
    FieldSalesSyncService,
    field_sales_sync_service as default_sync_service,
)
from packages.mcp.registry import register_tool, register_resource, get_current_user
from packages.mcp.types import Tool, Resource


_orders_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal', 'tax', 'grand_total', 'status', 'order_date', 'notes'])
_orders_svc = CrudService(_orders_repo)

_customers_repo = CrudRepository('T0010', business_columns=['id', 'name', 'phone', 'email', 'credit_limit', 'balance', 'is_active'])
_customers_svc = CrudService(_customers_repo)

_quotations_repo = CrudRepository('T0067', business_columns=['id', 'quote_number', 'customer_id', 'quote_date', 'valid_until', 'subtotal', 'tax', 'grand_total', 'status', 'notes', 'converted_order_id'])
_quotations_svc = CrudService(_quotations_repo)

_deliveries_repo = CrudRepository('T0016', business_columns=['id', 'delivery_number', 'sales_order_id', 'customer_id', 'delivery_date', 'status', 'notes'])
_deliveries_svc = CrudService(_deliveries_repo)

_price_lists_repo = CrudRepository('T0083', business_columns=['id', 'name', 'is_active'])
_price_lists_svc = CrudService(_price_lists_repo)

_tax_rates_repo = CrudRepository('T0085', business_columns=['id', 'name', 'rate', 'is_active'])
_tax_rates_svc = CrudService(_tax_rates_repo)

_lines_repo = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total'])

_field_sales_catalog_svc: FieldSalesCatalogService = default_catalog_service
_field_sales_sync_svc: FieldSalesSyncService = default_sync_service


def register_tools():
    register_tool(
        Tool(name="list_orders", description="List sales orders with optional filters", input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (Draft, Pending, Confirmed, Shipped, Delivered, Invoiced, Paid, Cancelled)"},
                "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
        }),
        _list_orders,
    )
    register_tool(
        Tool(name="get_order", description="Get a single sales order by ID", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Order ID"}},
            "required": ["id"],
        }),
        _get_order,
    )
    register_tool(
        Tool(name="create_order", description="Create a new sales order", input_schema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Customer ID"},
                "warehouse_id": {"type": "integer", "description": "Warehouse ID"},
                "order_date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                "subtotal": {"type": "number", "description": "Subtotal amount"},
                "tax": {"type": "number", "description": "Tax amount"},
                "grand_total": {"type": "number", "description": "Grand total"},
                "notes": {"type": "string", "description": "Order notes"},
                "order_number": {"type": "string", "description": "Order number (auto-generated if omitted)"},
            },
            "required": ["customer_id"],
        }),
        _create_order,
    )
    register_tool(
        Tool(name="update_order_status", description="Update a sales order status with validation", input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Order ID"},
                "status": {"type": "string", "description": "New status (Confirmed, Shipped, Delivered, Cancelled)"},
            },
            "required": ["id", "status"],
        }),
        _update_order_status,
    )
    register_tool(
        Tool(name="confirm_order", description="Confirm a sales order (reserves stock)", tier="tier2", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Order ID to confirm"}},
            "required": ["id"],
        }),
        _confirm_order,
    )
    register_tool(
        Tool(name="cancel_order", description="Cancel a sales order (releases stock)", tier="tier2", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Order ID to cancel"}},
            "required": ["id"],
        }),
        _cancel_order,
    )
    register_tool(
        Tool(name="list_customers", description="List customers with optional search", input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
        }),
        _list_customers,
    )
    register_tool(
        Tool(name="get_customer_aging", description="Get customer aging report with outstanding balances", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Customer ID"}},
            "required": ["id"],
        }),
        _get_customer_aging,
    )
    register_tool(
        Tool(name="list_quotations", description="List sales quotations", input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status"},
                "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                "limit": {"type": "integer"},
            },
        }),
        _list_quotations,
    )
    register_tool(
        Tool(name="convert_quotation_to_order", description="Convert a quotation to a sales order", tier="tier2", input_schema={
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Quotation ID"}},
            "required": ["id"],
        }),
        _convert_quotation,
    )
    register_tool(
        Tool(name="list_deliveries", description="List deliveries", input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
        }),
        _list_deliveries,
    )
    register_tool(
        Tool(name="list_price_lists", description="List price lists", input_schema={
            "type": "object", "properties": {},
        }),
        _list_price_lists,
    )
    register_tool(
        Tool(name="list_tax_rates", description="List tax rates", input_schema={
            "type": "object", "properties": {},
        }),
        _list_tax_rates,
    )
    register_tool(
        Tool(
            name="get_field_sales_catalog",
            description="Get mobile catalog bundle (products with stock levels, customer financial profiles, price list rules, metadata) for offline field sales",
            input_schema={
                "type": "object",
                "properties": {
                    "delta_timestamp": {
                        "type": "string",
                        "description": "Optional ISO timestamp of last sync for delta export (e.g. 2026-08-20T10:00:00Z)",
                    },
                    "warehouse_id": {
                        "type": "integer",
                        "description": "Optional warehouse ID to filter stock levels",
                    },
                    "sales_rep_id": {
                        "type": "integer",
                        "description": "Optional sales representative user ID to filter customer assignments",
                    },
                },
            },
        ),
        _get_field_sales_catalog,
    )
    register_tool(
        Tool(
            name="sync_offline_orders",
            description="Process a batch of offline field sales orders with idempotency checks and stock conflict detection",
            input_schema={
                "type": "object",
                "properties": {
                    "orders": {
                        "type": "array",
                        "description": "List of offline order submissions to synchronize",
                        "items": {
                            "type": "object",
                            "properties": {
                                "client_order_uuid": {"type": "string", "description": "Unique client UUID for idempotency"},
                                "customer_id": {"type": "integer", "description": "Customer ID"},
                                "warehouse_id": {"type": "integer", "description": "Source warehouse ID"},
                                "sales_rep_id": {"type": "integer", "description": "Sales rep user ID"},
                                "order_date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                                "offline_created_at": {"type": "string", "description": "ISO timestamp when order was drafted offline"},
                                "notes": {"type": "string", "description": "Order notes"},
                                "lines": {
                                    "type": "array",
                                    "description": "Order line items",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "product_id": {"type": "integer", "description": "Product ID"},
                                            "product_name": {"type": "string", "description": "Product name"},
                                            "qty": {"type": "number", "description": "Quantity ordered"},
                                            "unit_price": {"type": "number", "description": "Unit selling price"},
                                            "discount_pct": {"type": "number", "description": "Line discount percentage"},
                                            "line_number": {"type": "integer", "description": "Line number"},
                                            "notes": {"type": "string", "description": "Line notes"},
                                        },
                                        "required": ["product_id", "product_name", "qty", "unit_price"],
                                    },
                                },
                            },
                            "required": ["client_order_uuid", "customer_id"],
                        },
                    },
                    "device_id": {"type": "string", "description": "Optional device identifier"},
                    "client_timestamp": {"type": "string", "description": "Optional client ISO timestamp"},
                },
                "required": ["orders"],
            },
        ),
        _sync_offline_orders,
    )
    register_tool(
        Tool(
            name="check_offline_order_conflicts",
            description="Validate queued offline field sales orders for stock shortages, price mismatches, and credit limit issues without modifying database",
            input_schema={
                "type": "object",
                "properties": {
                    "orders": {
                        "type": "array",
                        "description": "List of offline order submissions to validate",
                        "items": {
                            "type": "object",
                            "properties": {
                                "client_order_uuid": {"type": "string", "description": "Unique client UUID"},
                                "customer_id": {"type": "integer", "description": "Customer ID"},
                                "warehouse_id": {"type": "integer", "description": "Source warehouse ID"},
                                "sales_rep_id": {"type": "integer", "description": "Sales rep user ID"},
                                "order_date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                                "offline_created_at": {"type": "string", "description": "ISO timestamp when order was drafted offline"},
                                "notes": {"type": "string", "description": "Order notes"},
                                "lines": {
                                    "type": "array",
                                    "description": "Order line items",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "product_id": {"type": "integer", "description": "Product ID"},
                                            "product_name": {"type": "string", "description": "Product name"},
                                            "qty": {"type": "number", "description": "Quantity ordered"},
                                            "unit_price": {"type": "number", "description": "Unit selling price"},
                                            "discount_pct": {"type": "number", "description": "Line discount percentage"},
                                            "line_number": {"type": "integer", "description": "Line number"},
                                            "notes": {"type": "string", "description": "Line notes"},
                                        },
                                        "required": ["product_id", "product_name", "qty", "unit_price"],
                                    },
                                },
                            },
                            "required": ["client_order_uuid", "customer_id"],
                        },
                    },
                },
                "required": ["orders"],
            },
        ),
        _check_offline_order_conflicts,
    )
    register_resource(
        Resource(uri="nova://sales/orders", name="All Orders", description="List of all sales orders"),
        _list_orders,
    )


def _list_orders(status: str = None, customer_id: int = None, limit: int = 50):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    return _orders_svc.list(filters=filters or None, limit=limit)


def _get_order(id: int):
    return _orders_svc.get(id)


def _create_order(customer_id: int, warehouse_id: int = None, order_date: str = None, subtotal: float = 0, tax: float = 0, grand_total: float = None, notes: str = None, order_number: str = None):
    payload = {
        "customer_id": customer_id,
        "subtotal": subtotal,
        "tax": tax,
        "grand_total": grand_total if grand_total else subtotal + tax,
        "status": "Draft",
    }
    if warehouse_id:
        payload["warehouse_id"] = warehouse_id
    if order_date:
        payload["order_date"] = order_date
    if notes:
        payload["notes"] = notes
    if order_number:
        payload["order_number"] = order_number
    return _orders_svc.create(payload)


def _update_order_status(id: int, status: str):
    return _orders_svc.update(id, {"status": status})


def _confirm_order(id: int):
    return _orders_svc.update(id, {"status": "Confirmed"})


def _cancel_order(id: int):
    return _orders_svc.update(id, {"status": "Cancelled"})


def _list_customers(limit: int = 50):
    return _customers_svc.list(limit=limit)


def _get_customer_aging(id: int):
    return _customers_svc.get(id)


def _list_quotations(status: str = None, customer_id: int = None, limit: int = 50):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    return _quotations_svc.list(filters=filters or None, limit=limit)


def _convert_quotation(id: int):
    return _quotations_svc.update(id, {"status": "Converted"})


def _list_deliveries(status: str = None, limit: int = 50):
    filters = {}
    if status:
        filters["status"] = status
    return _deliveries_svc.list(filters=filters or None, limit=limit)


def _list_price_lists():
    return _price_lists_svc.list()


def _list_tax_rates():
    return _tax_rates_svc.list()


def _normalize_order_submissions(orders: List[Any]) -> List[FieldSalesOrderSubmission]:
    normalized: List[FieldSalesOrderSubmission] = []
    current_user = get_current_user()
    current_user_id = current_user.get("id") if isinstance(current_user, dict) else None

    for ord_data in orders:
        if isinstance(ord_data, FieldSalesOrderSubmission):
            if not ord_data.sales_rep_id and current_user_id:
                ord_data.sales_rep_id = current_user_id
            normalized.append(ord_data)
            continue

        if not isinstance(ord_data, dict):
            continue

        data = dict(ord_data)
        if not data.get("sales_rep_id") and current_user_id:
            data["sales_rep_id"] = current_user_id

        lines_raw = data.get("lines") or data.get("items") or []
        normalized_lines: List[FieldSalesOrderLine] = []
        for idx, line in enumerate(lines_raw, start=1):
            if isinstance(line, FieldSalesOrderLine):
                normalized_lines.append(line)
            elif isinstance(line, dict):
                l_dict = dict(line)
                if "line_number" not in l_dict or l_dict["line_number"] is None:
                    l_dict["line_number"] = idx
                if "discount_pct" not in l_dict and "discount_percentage" in l_dict:
                    l_dict["discount_pct"] = l_dict.pop("discount_percentage")
                normalized_lines.append(FieldSalesOrderLine(**l_dict))
        data["lines"] = normalized_lines
        normalized.append(FieldSalesOrderSubmission(**data))
    return normalized


def _get_field_sales_catalog(
    delta_timestamp: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    sales_rep_id: Optional[int] = None,
) -> Dict[str, Any]:
    if sales_rep_id is None:
        current_user = get_current_user()
        if isinstance(current_user, dict) and current_user.get("id"):
            sales_rep_id = current_user.get("id")

    bundle = _field_sales_catalog_svc.get_mobile_catalog(
        delta_timestamp=delta_timestamp,
        warehouse_id=warehouse_id,
        sales_rep_id=sales_rep_id,
    )
    if hasattr(bundle, "model_dump"):
        return bundle.model_dump()
    return bundle


def _sync_offline_orders(
    orders: List[Any],
    device_id: Optional[str] = None,
    client_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    order_objects = _normalize_order_submissions(orders)
    req = FieldSalesBatchSyncRequest(
        orders=order_objects,
        device_id=device_id,
        client_timestamp=client_timestamp,
    )
    res = _field_sales_sync_svc.sync_batch(req)
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res


def _check_offline_order_conflicts(
    orders: List[Any],
) -> Dict[str, Any]:
    order_objects = _normalize_order_submissions(orders)
    req = FieldSalesValidationRequest(orders=order_objects)
    res = _field_sales_sync_svc.validate_batch(req)
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="sales-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
