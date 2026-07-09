from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_notif_repo = CrudRepository('T0098', business_columns=['id', 'user_id', 'title', 'message', 'notification_type', 'reference_type', 'reference_id', 'is_read'])
_notif_svc = CrudService(_notif_repo)


def register_tools():
    register_tool(Tool(name="list_user_notifications", description="List notifications for a user", input_schema={
        "type": "object", "properties": {
            "user_id": {"type": "integer"}, "unread_only": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
        "required": ["user_id"],
    }), _list_notifications)
    register_tool(Tool(name="mark_notification_read", description="Mark a notification as read", input_schema={
        "type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"],
    }), _mark_read)
    register_tool(Tool(name="mark_all_notifications_read", description="Mark all notifications as read for a user", tier="tier2", input_schema={
        "type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"],
    }), _mark_all_read)


def _list_notifications(user_id: int, unread_only: bool = False, limit: int = 50):
    filters = {"user_id": user_id}
    if unread_only: filters["is_read"] = False
    return _notif_svc.list(filters=filters, limit=limit)

def _mark_read(id: int):
    return _notif_svc.update(id, {"is_read": True})

def _mark_all_read(user_id: int):
    rows = _notif_svc.list(filters={"user_id": user_id, "is_read": False})
    count = 0
    for row in rows:
        _notif_svc.update(row["id"], {"is_read": True})
        count += 1
    return {"updated": count}


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="notifications-mcp", version="1.0"))

if __name__ == "__main__":
    main()
