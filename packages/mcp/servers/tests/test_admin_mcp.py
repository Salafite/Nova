from unittest.mock import patch, MagicMock
from packages.mcp.servers import admin_mcp
from packages.mcp.servers.admin_mcp import register_tools


class TestAdminMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def _patch_svc(self, svc_name):
        return patch.object(admin_mcp, svc_name, MagicMock())

    def test_list_users(self):
        with self._patch_svc("_users_svc"):
            admin_mcp._users_svc.list.return_value = [{"id": 1, "username": "admin"}]
            assert admin_mcp._list_users() == [{"id": 1, "username": "admin"}]

    def test_list_audit(self):
        with self._patch_svc("_audit_svc"):
            admin_mcp._audit_svc.list.return_value = [{"action": "INSERT"}]
            assert admin_mcp._list_audit()[0]["action"] == "INSERT"

    def test_list_settings(self):
        with self._patch_svc("_settings_svc"):
            admin_mcp._settings_svc.list.return_value = [{"setting_key": "site_name"}]
            assert admin_mcp._list_settings()[0]["setting_key"] == "site_name"

    def test_get_setting_found(self):
        with self._patch_svc("_settings_svc"):
            admin_mcp._settings_svc.list.return_value = [{"setting_key": "x", "setting_value": "y"}]
            assert admin_mcp._get_setting("x")["setting_value"] == "y"

    def test_get_setting_not_found(self):
        with self._patch_svc("_settings_svc"):
            admin_mcp._settings_svc.list.return_value = []
            assert admin_mcp._get_setting("x") is None

    def test_list_notifications(self):
        with self._patch_svc("_notif_svc"):
            admin_mcp._notif_svc.list.return_value = [{"title": "Test"}]
            assert admin_mcp._list_notifications(user_id=1)[0]["title"] == "Test"

    def test_list_tasks(self):
        with self._patch_svc("_tasks_svc"):
            admin_mcp._tasks_svc.list.return_value = [{"task_name": "Backup"}]
            assert admin_mcp._list_tasks()[0]["task_name"] == "Backup"

    def test_list_modules(self):
        with self._patch_svc("_modules_svc"):
            admin_mcp._modules_svc.list.return_value = [{"module_key": "inventory"}]
            assert admin_mcp._list_modules()[0]["module_key"] == "inventory"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_users" in names
        assert "get_audit_log" in names
        assert "list_settings" in names
        assert "get_setting" in names
        assert "list_notifications" in names
        assert "list_scheduled_tasks" in names
        assert "list_modules" in names
