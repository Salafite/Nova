from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_users_repo = CrudRepository('T0021', business_columns=['id', 'username', 'full_name', 'email', 'role', 'permissions', 'status', 'last_login'])
_users_svc = CrudService(_users_repo)

_audit_repo = CrudRepository('T0023', business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at'])
_audit_svc = CrudService(_audit_repo)

_settings_repo = CrudRepository('T0025', business_columns=['id', 'setting_key', 'setting_value', 'description', 'setting_group', 'is_active'])
_settings_svc = CrudService(_settings_repo)

_notif_repo = CrudRepository('T0098', business_columns=['id', 'user_id', 'title', 'message', 'notification_type', 'reference_type', 'reference_id', 'is_read'])
_notif_svc = CrudService(_notif_repo)

_tasks_repo = CrudRepository('T0099', business_columns=['id', 'task_name', 'task_type', 'cron_expression', 'description', 'config', 'is_active', 'last_run_at', 'next_run_at', 'status'])
_tasks_svc = CrudService(_tasks_repo)

_modules_repo = CrudRepository('T0100', business_columns=['id', 'module_key', 'name', 'version', 'author', 'category', 'is_core', 'is_active', 'installed_at'])
_modules_svc = CrudService(_modules_repo)


def register_tools():
    register_tool(Tool(name="list_users", description="List system users", input_schema={
        "type": "object", "properties": {"role": {"type": "string"}, "limit": {"type": "integer"}},
    }), _list_users)
    register_tool(Tool(name="get_audit_log", description="Query the audit log", input_schema={
        "type": "object", "properties": {
            "table_name": {"type": "string"}, "action": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_audit)
    register_tool(Tool(name="list_settings", description="List system settings", input_schema={
        "type": "object", "properties": {"group": {"type": "string"}},
    }), _list_settings)
    register_tool(Tool(name="get_setting", description="Get a single setting by key", input_schema={
        "type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"],
    }), _get_setting)
    register_tool(Tool(name="list_notifications", description="List notifications for a user", input_schema={
        "type": "object", "properties": {
            "user_id": {"type": "integer"}, "unread_only": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
        "required": ["user_id"],
    }), _list_notifications)
    register_tool(Tool(name="list_scheduled_tasks", description="List scheduled tasks", input_schema={
        "type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}},
    }), _list_tasks)
    register_tool(Tool(name="list_modules", description="List registered modules", input_schema={
        "type": "object", "properties": {"is_active": {"type": "boolean"}},
    }), _list_modules)


def _list_users(role: str = None, limit: int = 50):
    filters = {}
    if role: filters["role"] = role
    return _users_svc.list(filters=filters or None, limit=limit)

def _list_audit(table_name: str = None, action: str = None, limit: int = 50):
    filters = {}
    if table_name: filters["table_name"] = table_name
    if action: filters["action"] = action
    return _audit_svc.list(filters=filters or None, limit=limit)

def _list_settings(group: str = None):
    filters = {}
    if group: filters["setting_group"] = group
    return _settings_svc.list(filters=filters or None)

def _get_setting(key: str):
    rows = _settings_svc.list(filters={"setting_key": key})
    return rows[0] if rows else None

def _list_notifications(user_id: int, unread_only: bool = False, limit: int = 50):
    filters = {"user_id": user_id}
    if unread_only: filters["is_read"] = False
    return _notif_svc.list(filters=filters, limit=limit)

def _list_tasks(status: str = None, limit: int = 50):
    filters = {}
    if status: filters["status"] = status
    return _tasks_svc.list(filters=filters or None, limit=limit)

def _list_modules(is_active: bool = None):
    filters = {}
    if is_active is not None: filters["is_active"] = is_active
    return _modules_svc.list(filters=filters or None)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="admin-mcp", version="1.0"))

if __name__ == "__main__":
    main()
