from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool, register_resource
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


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="sales-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
