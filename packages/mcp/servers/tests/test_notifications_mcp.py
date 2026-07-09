from unittest.mock import patch, MagicMock
from packages.mcp.servers import notifications_mcp
from packages.mcp.servers.notifications_mcp import register_tools


class TestNotificationsMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_notifications(self):
        with patch.object(notifications_mcp, "_notif_svc", MagicMock()):
            notifications_mcp._notif_svc.list.return_value = [{"title": "Alert"}]
            result = notifications_mcp._list_notifications(user_id=1)
            assert result[0]["title"] == "Alert"

    def test_mark_read(self):
        with patch.object(notifications_mcp, "_notif_svc", MagicMock()):
            notifications_mcp._mark_read(id=5)
            notifications_mcp._notif_svc.update.assert_called_with(5, {"is_read": True})

    def test_mark_all_read(self):
        with patch.object(notifications_mcp, "_notif_svc", MagicMock()):
            notifications_mcp._notif_svc.list.return_value = [{"id": 1}, {"id": 2}]
            result = notifications_mcp._mark_all_read(user_id=1)
            assert result == {"updated": 2}
            assert notifications_mcp._notif_svc.update.call_count == 2

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_user_notifications" in names
        assert "mark_notification_read" in names
        assert "mark_all_notifications_read" in names
