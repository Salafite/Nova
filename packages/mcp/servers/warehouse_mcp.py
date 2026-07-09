from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_gr_repo = CrudRepository('T0075', business_columns=['id', 'receipt_number', 'purchase_order_id', 'receipt_date', 'warehouse_id', 'status', 'notes'])
_gr_svc = CrudService(_gr_repo)

_serial_repo = CrudRepository('T0087', business_columns=['id', 'product_id', 'serial_number', 'status', 'warehouse_id', 'notes'])
_serial_svc = CrudService(_serial_repo)

_batch_repo = CrudRepository('T0088', business_columns=['id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date', 'quantity', 'warehouse_id', 'status', 'notes'])
_batch_svc = CrudService(_batch_repo)

_pick_repo = CrudRepository('T0101', business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'])
_pick_svc = CrudService(_pick_repo)


def register_tools():
    register_tool(Tool(name="list_goods_receipts", description="List goods receipts", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "purchase_order_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_gr)
    register_tool(Tool(name="list_serial_numbers", description="List serial numbers for a product", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "status": {"type": "string"},
            "warehouse_id": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_serial)
    register_tool(Tool(name="list_batch_numbers", description="List batch numbers for a product", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "status": {"type": "string"},
            "warehouse_id": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_batch)
    register_tool(Tool(name="list_pick_lists", description="List pick lists", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "sales_order_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_pick)


def _list_gr(status: str = None, purchase_order_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if purchase_order_id: filters["purchase_order_id"] = purchase_order_id
    return _gr_svc.list(filters=filters or None, limit=limit)

def _list_serial(product_id: int = None, status: str = None, warehouse_id: int = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if status: filters["status"] = status
    if warehouse_id: filters["warehouse_id"] = warehouse_id
    return _serial_svc.list(filters=filters or None, limit=limit)

def _list_batch(product_id: int = None, status: str = None, warehouse_id: int = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if status: filters["status"] = status
    if warehouse_id: filters["warehouse_id"] = warehouse_id
    return _batch_svc.list(filters=filters or None, limit=limit)

def _list_pick(status: str = None, sales_order_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if sales_order_id: filters["sales_order_id"] = sales_order_id
    return _pick_svc.list(filters=filters or None, limit=limit)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="warehouse-mcp", version="1.0"))

if __name__ == "__main__":
    main()
