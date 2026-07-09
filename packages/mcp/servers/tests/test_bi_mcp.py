from unittest.mock import patch, MagicMock
from packages.mcp.servers import bi_mcp
from packages.mcp.servers.bi_mcp import register_tools


def _patch(name):
    return patch.object(bi_mcp, name, MagicMock())


class TestBiMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_kpis(self):
        with _patch("_kpi_def_svc"):
            bi_mcp._kpi_def_svc.list.return_value = [{"kpi_name": "Revenue"}]
            assert bi_mcp._list_kpis()[0]["kpi_name"] == "Revenue"

    def test_get_kpi_values(self):
        with _patch("_kpi_val_svc"):
            bi_mcp._kpi_val_svc.list.return_value = [{"actual_value": 100}]
            assert bi_mcp._get_kpi_values(kpi_id=1)[0]["actual_value"] == 100

    def test_list_dashboards(self):
        with _patch("_dash_svc"):
            bi_mcp._dash_svc.list.return_value = [{"dashboard_name": "Sales"}]
            assert bi_mcp._list_dashboards()[0]["dashboard_name"] == "Sales"

    def test_get_widgets(self):
        with _patch("_widget_svc"):
            bi_mcp._widget_svc.list.return_value = [{"title": "Chart"}]
            assert bi_mcp._get_widgets(dashboard_id=1)[0]["title"] == "Chart"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_kpis" in names
        assert "get_kpi_values" in names
        assert "list_dashboards" in names
        assert "get_dashboard_widgets" in names
