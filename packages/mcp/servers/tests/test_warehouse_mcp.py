from unittest.mock import patch, MagicMock
from packages.mcp.servers import warehouse_mcp
from packages.mcp.servers.warehouse_mcp import register_tools


class TestWarehouseMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def _test(self, fn_name, svc_name, expected):
        mod = warehouse_mcp
        with patch.object(mod, svc_name, MagicMock()) as mock:
            mock.list.return_value = [expected]
            fn = getattr(mod, fn_name)
            result = fn()
            assert result == [expected]

    def test_list_gr(self):
        self._test("_list_gr", "_gr_svc", {"id": 1, "receipt_number": "GR-001"})

    def test_list_serial(self):
        self._test("_list_serial", "_serial_svc", {"id": 1, "serial_number": "SN-001"})

    def test_list_batch(self):
        self._test("_list_batch", "_batch_svc", {"id": 1, "batch_number": "BT-001"})

    def test_list_pick(self):
        self._test("_list_pick", "_pick_svc", {"id": 1, "pick_list_number": "PL-001"})

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_goods_receipts" in names
        assert "list_serial_numbers" in names
        assert "list_batch_numbers" in names
        assert "list_pick_lists" in names
