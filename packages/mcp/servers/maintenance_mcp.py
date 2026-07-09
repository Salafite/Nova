from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_asset_repo = CrudRepository('T0041', business_columns=['id', 'asset_code', 'asset_name', 'asset_type', 'asset_model', 'serial_no', 'location', 'department_id', 'purchase_date', 'purchase_cost', 'useful_life', 'warranty_expiry', 'status', 'is_active'])
_asset_svc = CrudService(_asset_repo)

_sched_repo = CrudRepository('T0042', business_columns=['id', 'asset_id', 'schedule_code', 'schedule_name', 'frequency_type', 'frequency_value', 'last_maintenance', 'next_maintenance', 'assigned_to', 'notes', 'is_active'])
_sched_svc = CrudService(_sched_repo)

_wo_repo = CrudRepository('T0043', business_columns=['id', 'asset_id', 'schedule_id', 'work_order_code', 'description', 'priority', 'status', 'assigned_to', 'scheduled_date', 'completed_date', 'cost', 'notes', 'is_active'])
_wo_svc = CrudService(_wo_repo)


def register_tools():
    register_tool(Tool(name="list_assets", description="List maintenance assets", input_schema={
        "type": "object", "properties": {
            "asset_type": {"type": "string"}, "status": {"type": "string"},
            "department_id": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_assets)
    register_tool(Tool(name="list_maintenance_schedules", description="List maintenance schedules", input_schema={
        "type": "object", "properties": {
            "asset_id": {"type": "integer"}, "assigned_to": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_schedules)
    register_tool(Tool(name="list_work_orders", description="List maintenance work orders", input_schema={
        "type": "object", "properties": {
            "asset_id": {"type": "integer"}, "status": {"type": "string"},
            "priority": {"type": "string"}, "assigned_to": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_work_orders)


def _list_assets(asset_type: str = None, status: str = None, department_id: int = None, limit: int = 50):
    filters = {}
    if asset_type: filters["asset_type"] = asset_type
    if status: filters["status"] = status
    if department_id: filters["department_id"] = department_id
    return _asset_svc.list(filters=filters or None, limit=limit)

def _list_schedules(asset_id: int = None, assigned_to: int = None, limit: int = 50):
    filters = {}
    if asset_id: filters["asset_id"] = asset_id
    if assigned_to: filters["assigned_to"] = assigned_to
    return _sched_svc.list(filters=filters or None, limit=limit)

def _list_work_orders(asset_id: int = None, status: str = None, priority: str = None, assigned_to: int = None, limit: int = 50):
    filters = {}
    if asset_id: filters["asset_id"] = asset_id
    if status: filters["status"] = status
    if priority: filters["priority"] = priority
    if assigned_to: filters["assigned_to"] = assigned_to
    return _wo_svc.list(filters=filters or None, limit=limit)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="maintenance-mcp", version="1.0"))

if __name__ == "__main__":
    main()
