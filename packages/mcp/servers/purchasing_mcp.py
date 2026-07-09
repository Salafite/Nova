from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_po_repo = CrudRepository('T0014', business_columns=['id', 'order_number', 'supplier_id', 'total', 'status', 'order_date', 'expected_date', 'notes'])
_po_svc = CrudService(_po_repo)

_pr_repo = CrudRepository('T0081', business_columns=['id', 'return_number', 'purchase_order_id', 'supplier_id', 'return_date', 'status', 'reason', 'notes'])
_pr_svc = CrudService(_pr_repo)

_rfq_repo = CrudRepository('T0071', business_columns=['id', 'rfq_number', 'title', 'description', 'status', 'due_date', 'notes'])
_rfq_svc = CrudService(_rfq_repo)


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


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="purchasing-mcp", version="1.0"))

if __name__ == "__main__":
    main()
