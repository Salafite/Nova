from unittest.mock import patch, MagicMock
from packages.mcp.servers import crm_mcp
from packages.mcp.servers.crm_mcp import register_tools


def _patch(name):
    return patch.object(crm_mcp, name, MagicMock())


class TestCrmMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_leads(self):
        with _patch("_leads_svc"):
            crm_mcp._leads_svc.list.return_value = [{"first_name": "John"}]
            assert crm_mcp._list_leads()[0]["first_name"] == "John"

    def test_list_opps(self):
        with _patch("_opps_svc"):
            crm_mcp._opps_svc.list.return_value = [{"opportunity_name": "Big Deal"}]
            assert crm_mcp._list_opps()[0]["opportunity_name"] == "Big Deal"

    def test_list_suppliers(self):
        with _patch("_suppliers_svc"):
            crm_mcp._suppliers_svc.list.return_value = [{"name": "Acme"}]
            assert crm_mcp._list_suppliers()[0]["name"] == "Acme"

    def test_list_groups(self):
        with _patch("_groups_svc"):
            crm_mcp._groups_svc.list.return_value = [{"name": "Retail"}]
            assert crm_mcp._list_groups()[0]["name"] == "Retail"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_leads" in names
        assert "list_opportunities" in names
        assert "list_suppliers" in names
        assert "list_customer_groups" in names
