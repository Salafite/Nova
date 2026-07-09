from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_mfg_repo = CrudRepository('T0018', business_columns=['id', 'order_number', 'product_id', 'product_name', 'quantity', 'status', 'due_date', 'priority'])
_mfg_svc = CrudService(_mfg_repo)

_bom_repo = CrudRepository('T0065', business_columns=['id', 'bom_code', 'bom_name', 'product_id', 'quantity', 'version', 'is_active'])
_bom_svc = CrudService(_bom_repo)

_qc_repo = CrudRepository('T0019', business_columns=['id', 'inspection_no', 'product_id', 'product_name', 'batch_no', 'result', 'inspector', 'inspection_date', 'notes'])
_qc_svc = CrudService(_qc_repo)

_shop_repo = CrudRepository('T0020', business_columns=['id', 'job_number', 'product_id', 'product_name', 'quantity', 'workstation', 'status'])
_shop_svc = CrudService(_shop_repo)


def register_tools():
    register_tool(Tool(name="list_manufacturing_orders", description="List manufacturing orders", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "product_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_mfg)
    register_tool(Tool(name="list_boms", description="List bills of materials", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "is_active": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    }), _list_boms)
    register_tool(Tool(name="list_qc_inspections", description="List QC inspections", input_schema={
        "type": "object", "properties": {
            "product_id": {"type": "integer"}, "result": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_qc)
    register_tool(Tool(name="list_shop_jobs", description="List shop floor jobs", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "workstation": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_shop)


def _list_mfg(status: str = None, product_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if product_id: filters["product_id"] = product_id
    return _mfg_svc.list(filters=filters or None, limit=limit)

def _list_boms(product_id: int = None, is_active: bool = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if is_active is not None: filters["is_active"] = is_active
    return _bom_svc.list(filters=filters or None, limit=limit)

def _list_qc(product_id: int = None, result: str = None, limit: int = 50):
    filters = {}
    if product_id: filters["product_id"] = product_id
    if result: filters["result"] = result
    return _qc_svc.list(filters=filters or None, limit=limit)

def _list_shop(status: str = None, workstation: str = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if workstation: filters["workstation"] = workstation
    return _shop_svc.list(filters=filters or None, limit=limit)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="manufacturing-mcp", version="1.0"))

if __name__ == "__main__":
    main()
