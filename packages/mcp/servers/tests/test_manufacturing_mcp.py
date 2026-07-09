from unittest.mock import patch, MagicMock
from packages.mcp.servers import manufacturing_mcp
from packages.mcp.servers.manufacturing_mcp import register_tools


def _patch(name):
    return patch.object(manufacturing_mcp, name, MagicMock())


class TestManufacturingMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_mfg(self):
        with _patch("_mfg_svc"):
            manufacturing_mcp._mfg_svc.list.return_value = [{"order_number": "MFG-001"}]
            assert manufacturing_mcp._list_mfg()[0]["order_number"] == "MFG-001"

    def test_list_boms(self):
        with _patch("_bom_svc"):
            manufacturing_mcp._bom_svc.list.return_value = [{"bom_name": "BOM-001"}]
            assert manufacturing_mcp._list_boms()[0]["bom_name"] == "BOM-001"

    def test_list_qc(self):
        with _patch("_qc_svc"):
            manufacturing_mcp._qc_svc.list.return_value = [{"inspection_no": "QC-001"}]
            assert manufacturing_mcp._list_qc()[0]["inspection_no"] == "QC-001"

    def test_list_shop(self):
        with _patch("_shop_svc"):
            manufacturing_mcp._shop_svc.list.return_value = [{"job_number": "JOB-001"}]
            assert manufacturing_mcp._list_shop()[0]["job_number"] == "JOB-001"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_manufacturing_orders" in names
        assert "list_boms" in names
        assert "list_qc_inspections" in names
        assert "list_shop_jobs" in names
