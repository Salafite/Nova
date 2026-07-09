from unittest.mock import patch, MagicMock
from packages.mcp.servers import purchasing_mcp
from packages.mcp.servers.purchasing_mcp import register_tools


MOCK_PO = {"id": 1, "order_number": "PO-001", "supplier_id": 1, "status": "Pending", "total": 500}


def _patch(name):
    return patch.object(purchasing_mcp, name, MagicMock())


class TestPurchasingMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_po(self):
        with _patch("_po_svc"):
            purchasing_mcp._po_svc.list.return_value = [MOCK_PO]
            assert purchasing_mcp._list_po() == [MOCK_PO]

    def test_get_po(self):
        with _patch("_po_svc"):
            purchasing_mcp._po_svc.get.return_value = MOCK_PO
            assert purchasing_mcp._get_po(1) == MOCK_PO

    def test_list_pr(self):
        with _patch("_pr_svc"):
            purchasing_mcp._pr_svc.list.return_value = [{"return_number": "PR-001"}]
            assert purchasing_mcp._list_pr()[0]["return_number"] == "PR-001"

    def test_list_rfq(self):
        with _patch("_rfq_svc"):
            purchasing_mcp._rfq_svc.list.return_value = [{"rfq_number": "RFQ-001"}]
            assert purchasing_mcp._list_rfq()[0]["rfq_number"] == "RFQ-001"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_purchase_orders" in names
        assert "get_purchase_order" in names
        assert "list_purchase_returns" in names
        assert "list_rfqs" in names
