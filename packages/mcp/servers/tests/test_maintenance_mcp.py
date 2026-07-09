from unittest.mock import patch, MagicMock
from packages.mcp.servers import maintenance_mcp
from packages.mcp.servers.maintenance_mcp import register_tools


def _patch(name):
    return patch.object(maintenance_mcp, name, MagicMock())


class TestMaintenanceMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_assets(self):
        with _patch("_asset_svc"):
            maintenance_mcp._asset_svc.list.return_value = [{"asset_name": "Forklift"}]
            assert maintenance_mcp._list_assets()[0]["asset_name"] == "Forklift"

    def test_list_schedules(self):
        with _patch("_sched_svc"):
            maintenance_mcp._sched_svc.list.return_value = [{"schedule_name": "Monthly"}]
            assert maintenance_mcp._list_schedules()[0]["schedule_name"] == "Monthly"

    def test_list_work_orders(self):
        with _patch("_wo_svc"):
            maintenance_mcp._wo_svc.list.return_value = [{"work_order_code": "WO-001"}]
            assert maintenance_mcp._list_work_orders()[0]["work_order_code"] == "WO-001"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_assets" in names
        assert "list_maintenance_schedules" in names
        assert "list_work_orders" in names
