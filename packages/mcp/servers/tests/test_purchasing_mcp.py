from unittest.mock import patch, MagicMock
from packages.mcp.servers import purchasing_mcp
from packages.mcp.servers.purchasing_mcp import register_tools
from packages.mcp import registry


MOCK_PO = {"id": 1, "order_number": "PO-001", "supplier_id": 1, "status": "Pending", "total": 500}
MOCK_FORECAST = {
    "product_id": 101,
    "product_name": "Organic Milk",
    "sku": "MILK-001",
    "needs_restock": True,
    "urgency": "CRITICAL",
    "suggested_order_qty": 50.0,
    "min_order_qty": 20.0,
    "unit_cost": 3.0,
    "supplier_id": 2,
    "lead_time_days": 5,
    "days_of_inventory": 2.0,
    "projected_stockout_date": "2026-08-25",
    "rationale": "[CRITICAL RESTOCK] MILK-001: 2 days supply remaining.",
}


def _patch(name):
    return patch.object(purchasing_mcp, name, MagicMock())


class TestPurchasingMcp:
    def setup_method(self):
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
        names = [t.name for t in registry.get_tools()]
        assert "list_purchase_orders" in names
        assert "get_purchase_order" in names
        assert "list_purchase_returns" in names
        assert "list_rfqs" in names
        assert "calculate_restock_forecast" in names
        assert "propose_draft_purchase_order" in names

        tools_map = {t.name: t for t in registry.get_tools()}
        assert tools_map["calculate_restock_forecast"].tier == "tier1"
        assert tools_map["propose_draft_purchase_order"].tier == "tier2"

    def test_calculate_restock_forecast_sku(self):
        with _patch("_forecast_svc"):
            purchasing_mcp._forecast_svc.calculate_sku_forecast.return_value = MOCK_FORECAST
            result = purchasing_mcp._calculate_restock_forecast(product_id=101, days=30)
            assert result["product_id"] == 101
            assert result["urgency"] == "CRITICAL"
            purchasing_mcp._forecast_svc.calculate_sku_forecast.assert_called_once()

    def test_calculate_restock_forecast_all(self):
        with _patch("_forecast_svc"):
            purchasing_mcp._forecast_svc.calculate_all_forecasts.return_value = [MOCK_FORECAST]
            result = purchasing_mcp._calculate_restock_forecast(product_id=None, only_at_risk=True)
            assert len(result) == 1
            assert result[0]["sku"] == "MILK-001"
            purchasing_mcp._forecast_svc.calculate_all_forecasts.assert_called_once()

    def test_propose_draft_purchase_order_single_product(self):
        with _patch("_forecast_svc"), _patch("_po_svc"), _patch("_po_repo"), _patch("_po_line_repo"):
            purchasing_mcp._forecast_svc.calculate_sku_forecast.return_value = MOCK_FORECAST
            purchasing_mcp._po_repo.list.return_value = []
            purchasing_mcp._po_svc.create.return_value = {
                "id": 10,
                "order_number": "PO-001",
                "supplier_id": 2,
                "total": 150.0,
                "status": "Pending",
            }
            purchasing_mcp._po_line_repo.create.return_value = {
                "id": 1,
                "purchase_order_id": 10,
                "product_id": 101,
                "qty": 50.0,
                "unit_price": 3.0,
                "line_total": 150.0,
            }

            result = purchasing_mcp._propose_draft_purchase_order(product_id=101)

            assert result["purchase_order"]["order_number"] == "PO-001"
            assert result["purchase_order"]["status"] == "Pending"
            assert len(result["lines"]) == 1
            assert result["lines"][0]["qty"] == 50.0
            assert "Pending" in result["message"]

    def test_propose_draft_purchase_order_multiple_items(self):
        with _patch("_po_svc"), _patch("_po_repo"), _patch("_po_line_repo"), _patch("_forecast_svc"), _patch("_product_repo"):
            purchasing_mcp._po_repo.list.return_value = []
            purchasing_mcp._forecast_svc.get_preferred_supplier.return_value = {"supplier_id": 4}
            purchasing_mcp._po_svc.create.return_value = {
                "id": 20,
                "order_number": "PO-002",
                "supplier_id": 4,
                "total": 300.0,
                "status": "Pending",
            }
            purchasing_mcp._po_line_repo.create.side_effect = lambda line: {"id": 1, **line}

            items = [
                {"product_id": 101, "product_name": "Product A", "qty": 10, "unit_price": 10.0},
                {"product_id": 102, "product_name": "Product B", "qty": 20, "unit_price": 10.0},
            ]
            result = purchasing_mcp._propose_draft_purchase_order(items=items)

            assert result["purchase_order"]["order_number"] == "PO-002"
            assert len(result["lines"]) == 2
            assert result["lines"][0]["line_total"] == 100.0
            assert result["lines"][1]["line_total"] == 200.0

    def test_tier2_propose_and_confirm_workflow(self):
        register_tools()
        with _patch("_forecast_svc"), _patch("_po_svc"), _patch("_po_repo"), _patch("_po_line_repo"):
            purchasing_mcp._forecast_svc.calculate_sku_forecast.return_value = MOCK_FORECAST
            purchasing_mcp._po_repo.list.return_value = []
            purchasing_mcp._po_svc.create.return_value = {
                "id": 30,
                "order_number": "PO-003",
                "supplier_id": 2,
                "total": 150.0,
                "status": "Pending",
            }
            purchasing_mcp._po_line_repo.create.return_value = {
                "id": 1,
                "purchase_order_id": 30,
                "product_id": 101,
                "qty": 50.0,
                "unit_price": 3.0,
            }

            # Step 1: Propose action
            proposed = registry.propose_action("propose_draft_purchase_order", {"product_id": 101})
            assert "action_id" in proposed
            assert proposed["tool"] == "propose_draft_purchase_order"
            action_id = proposed["action_id"]

            # Step 2: Confirm action executes the underlying handler
            confirmed = registry.confirm_action(action_id)
            assert confirmed["purchase_order"]["order_number"] == "PO-003"
            assert confirmed["purchase_order"]["status"] == "Pending"

