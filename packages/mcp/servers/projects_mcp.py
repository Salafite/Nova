from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_proj_repo = CrudRepository('T0044', business_columns=['id', 'project_code', 'project_name', 'description', 'department_id', 'manager_id', 'start_date', 'end_date', 'budget', 'status', 'is_active'])
_proj_svc = CrudService(_proj_repo)

_task_repo = CrudRepository('T0045', business_columns=['id', 'project_id', 'task_code', 'task_name', 'description', 'assigned_to', 'start_date', 'end_date', 'priority', 'status', 'estimated_hours', 'actual_hours', 'parent_task_id', 'is_active'])
_task_svc = CrudService(_task_repo)

_milestone_repo = CrudRepository('T0047', business_columns=['id', 'employee_id', 'project_id', 'task_id', 'date', 'hours', 'description', 'status', 'approved_by', 'is_active'])
_milestone_svc = CrudService(_milestone_repo)

_expense_repo = CrudRepository('T0049', business_columns=['id', 'contract_code', 'contract_name', 'customer_id', 'contract_type', 'start_date', 'end_date', 'value', 'status', 'notes', 'is_active'])
_expense_svc = CrudService(_expense_repo)


def register_tools():
    register_tool(Tool(name="list_projects", description="List projects", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "department_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_projects)
    register_tool(Tool(name="get_project", description="Get project by ID", input_schema={
        "type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"],
    }), _get_project)
    register_tool(Tool(name="list_tasks", description="List project tasks", input_schema={
        "type": "object", "properties": {
            "project_id": {"type": "integer"}, "status": {"type": "string"},
            "assigned_to": {"type": "integer"}, "limit": {"type": "integer"},
        },
    }), _list_tasks)
    register_tool(Tool(name="list_milestones", description="List project milestones/timesheets", input_schema={
        "type": "object", "properties": {
            "project_id": {"type": "integer"}, "task_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }), _list_milestones)


def _list_projects(status: str = None, department_id: int = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    if department_id: filters["department_id"] = department_id
    return _proj_svc.list(filters=filters or None, limit=limit)

def _get_project(id: int):
    return _proj_svc.get(id)

def _list_tasks(project_id: int = None, status: str = None, assigned_to: int = None, limit: int = 50):
    filters = {}
    if project_id: filters["project_id"] = project_id
    if status: filters["status"] = status
    if assigned_to: filters["assigned_to"] = assigned_to
    return _task_svc.list(filters=filters or None, limit=limit)

def _list_milestones(project_id: int = None, task_id: int = None, limit: int = 50):
    filters = {}
    if project_id: filters["project_id"] = project_id
    if task_id: filters["task_id"] = task_id
    return _milestone_svc.list(filters=filters or None, limit=limit)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="projects-mcp", version="1.0"))

if __name__ == "__main__":
    main()
