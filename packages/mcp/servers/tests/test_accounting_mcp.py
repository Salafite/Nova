from unittest.mock import patch, MagicMock
from packages.mcp.servers import accounting_mcp
from packages.mcp.servers.accounting_mcp import register_tools


class TestAccountingMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_coa(self):
        with patch.multiple(accounting_mcp, _coa_svc=MagicMock()):
            accounting_mcp._coa_svc.list.return_value = [{"id": 1, "account_code": "1000"}]
            result = accounting_mcp._list_coa()
            assert result == [{"id": 1, "account_code": "1000"}]

    def test_list_invoices(self):
        with patch.multiple(accounting_mcp, _inv_svc=MagicMock()):
            accounting_mcp._inv_svc.list.return_value = [{"id": 1, "invoice_number": "INV-001"}]
            result = accounting_mcp._list_invoices()
            assert result[0]["invoice_number"] == "INV-001"

    def test_get_invoice(self):
        with patch.multiple(accounting_mcp, _inv_svc=MagicMock()):
            accounting_mcp._inv_svc.get.return_value = {"id": 1, "total_amount": 100}
            assert accounting_mcp._get_invoice(1)["total_amount"] == 100

    def test_list_payments(self):
        with patch.multiple(accounting_mcp, _pay_svc=MagicMock()):
            accounting_mcp._pay_svc.list.return_value = [{"id": 1, "amount": 50}]
            result = accounting_mcp._list_payments()
            assert len(result) == 1

    def test_list_terms(self):
        with patch.multiple(accounting_mcp, _terms_svc=MagicMock()):
            accounting_mcp._terms_svc.list.return_value = [{"name": "Net 30"}]
            assert accounting_mcp._list_terms()[0]["name"] == "Net 30"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_chart_of_accounts" in names
        assert "list_invoices" in names
        assert "get_invoice" in names
        assert "list_payments" in names
        assert "list_payment_terms" in names
