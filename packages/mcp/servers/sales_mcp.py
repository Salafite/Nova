from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.sales.services.sales_service import SalesOrderService, ORDER_REPO, LINE_REPO
from modules.crm.services.aging_service import AgingService
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


_orders_repo = ORDER_REPO
_orders_svc = SalesOrderService(_orders_repo, line_repo=LINE_REPO)

_customers_repo = CrudRepository('T0010', business_columns=['id', 'name', 'phone', 'email', 'credit_limit', 'balance', 'payment_term_id', 'is_active'])
_customers_svc = CrudService(_customers_repo)
_aging_svc = AgingService(customer_repo=_customers_repo)

_quotations_repo = CrudRepository('T0067', business_columns=['id', 'quote_number', 'customer_id', 'quote_date', 'valid_until', 'subtotal', 'tax', 'grand_total', 'status', 'notes', 'converted_order_id'])
_quotations_svc = CrudService(_quotations_repo)

_deliveries_repo = CrudRepository('T0016', business_columns=['id', 'delivery_number', 'sales_order_id', 'customer_id', 'delivery_date', 'status', 'notes'])
_deliveries_svc = CrudService(_deliveries_repo)

_price_lists_repo = CrudRepository('T0083', business_columns=['id', 'name', 'is_active'])
_price_lists_svc = CrudService(_price_lists_repo)

_tax_rates_repo = CrudRepository('T0085', business_columns=['id', 'name', 'rate', 'is_active'])
_tax_rates_svc = CrudService(_tax_rates_repo)

_lines_repo = LINE_REPO
_lines_svc = CrudService(_lines_repo)


def register_tools():
    register_tool(
        Tool(name="list_orders", description="List sales orders with optional filters", input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (Draft, Pending, Confirmed, Shipped, Delivered, Invoiced, Paid, Cancelled)"},
                "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                "is_catch_weight": {"type": "boolean", "description": "Filter orders containing catch-weight products"},
                "limit": {"type": "integer", "description": "Max results (default 50)"},
            },
        }),
        _list_orders,
    )
    register_tool(
        Tool(name="get_order", description="Get a single sales order by ID with line items and dual UOM details", input_schema={
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
        Tool(name="create_order_line", description="Add a line item to a sales order with optional dual UOM and catch-weight pricing configuration", input_schema={
            "type": "object",
            "properties": {
                "sales_order_id": {"type": "integer", "description": "Sales order ID"},
                "product_name": {"type": "string", "description": "Product name"},
                "qty": {"type": "number", "description": "Ordered quantity in stocking UOM"},
                "unit_price": {"type": "number", "description": "Unit price per stocking unit"},
                "product_id": {"type": "integer", "description": "Product ID"},
                "uom_id": {"type": "integer", "description": "Stocking unit of measure ID"},
                "line_total": {"type": "number", "description": "Line total"},
                "line_number": {"type": "integer", "description": "Line number"},
                "is_catch_weight": {"type": "boolean", "description": "Whether line uses catch-weight pricing"},
                "pricing_uom_id": {"type": "integer", "description": "Pricing unit of measure ID (e.g. kg)"},
                "unit_price_pricing_uom": {"type": "number", "description": "Unit price per pricing UOM unit"},
                "nominal_weight": {"type": "number", "description": "Expected nominal weight for ordered quantity"},
                "catch_weight_actual": {"type": "number", "description": "Actual physical weighed weight"},
                "recalculated_total": {"type": "number", "description": "Recalculated line total based on actual weight"},
            },
            "required": ["sales_order_id", "product_name", "qty", "unit_price"],
        }),
        _create_order_line,
    )
    register_tool(
        Tool(name="list_order_lines", description="List sales order line items with dual UOM pricing attributes", input_schema={
            "type": "object",
            "properties": {
                "sales_order_id": {"type": "integer", "description": "Sales order ID"},
            },
            "required": ["sales_order_id"],
        }),
        _list_order_lines,
    )
    register_tool(
        Tool(name="recalculate_order_catch_weight", description="Recalculate sales order line totals and order grand total based on actual catch-weight measurements from warehouse picking", input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Sales order ID"},
            },
            "required": ["id"],
        }),
        _recalculate_order_catch_weight,
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
        Tool(name="get_customer_aging", description="Get customer accounts receivable aging report with overdue breakdown", input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Customer ID"},
                "as_of_date": {"type": "string", "description": "Optional as-of date (YYYY-MM-DD)"},
            },
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
    register_resource(
        Resource(uri="nova://sales/orders", name="All Orders", description="List of all sales orders"),
        _list_orders,
    )


def _list_orders(status: str = None, customer_id: int = None, is_catch_weight: bool = None, limit: int = 50):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    if is_catch_weight is not None:
        filters["is_catch_weight"] = is_catch_weight
    return _orders_svc.list(filters=filters or None, limit=limit)


def _get_order(id: int):
    order = _orders_svc.get(id)
    if order:
        try:
            lines = _lines_repo.list(filters={"sales_order_id": id})
            order["lines"] = lines
        except Exception:
            pass
    return order


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


def _create_order_line(
    sales_order_id: int,
    product_name: str,
    qty: float,
    unit_price: float,
    product_id: int = None,
    uom_id: int = None,
    line_total: float = None,
    line_number: int = 1,
    is_catch_weight: bool = False,
    pricing_uom_id: int = None,
    unit_price_pricing_uom: float = None,
    nominal_weight: float = None,
    catch_weight_actual: float = None,
    recalculated_total: float = None,
):
    payload = {
        "sales_order_id": sales_order_id,
        "product_name": product_name,
        "qty": qty,
        "unit_price": unit_price,
        "line_total": line_total if line_total is not None else round(qty * unit_price, 2),
        "line_number": line_number,
        "is_catch_weight": is_catch_weight,
    }
    if product_id is not None:
        payload["product_id"] = product_id
    if uom_id is not None:
        payload["uom_id"] = uom_id
    if pricing_uom_id is not None:
        payload["pricing_uom_id"] = pricing_uom_id
    if unit_price_pricing_uom is not None:
        payload["unit_price_pricing_uom"] = unit_price_pricing_uom
    if nominal_weight is not None:
        payload["nominal_weight"] = nominal_weight
    if catch_weight_actual is not None:
        payload["catch_weight_actual"] = catch_weight_actual
    if recalculated_total is not None:
        payload["recalculated_total"] = recalculated_total
    return _lines_svc.create(payload)


def _list_order_lines(sales_order_id: int):
    return _lines_repo.list(filters={"sales_order_id": sales_order_id})


def _recalculate_order_catch_weight(id: int):
    return _orders_svc.recalculate_order_catch_weight(id)


def _update_order_status(id: int, status: str):
    return _orders_svc.update(id, {"status": status})


def _confirm_order(id: int):
    return _orders_svc.update(id, {"status": "Confirmed"})


def _cancel_order(id: int):
    return _orders_svc.update(id, {"status": "Cancelled"})


def _list_customers(limit: int = 50):
    return _customers_svc.list(limit=limit)


def _get_customer_aging(id: int, as_of_date: str = None):
    return _aging_svc.get_customer_aging(id, as_of_date=as_of_date)


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


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="sales-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
