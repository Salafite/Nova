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
        assert "create_purchase_return_rma" in names
        assert "get_purchase_return_details" in names
        assert "approve_purchase_return" in names

        tools_map = {t.name: t for t in registry.get_tools()}
        assert tools_map["calculate_restock_forecast"].tier == "tier1"
        assert tools_map["propose_draft_purchase_order"].tier == "tier2"
        assert tools_map["create_purchase_return_rma"].tier == "tier1"
        assert tools_map["get_purchase_return_details"].tier == "tier1"
        assert tools_map["approve_purchase_return"].tier == "tier2"

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
            user = {"id": 1, "role": "Purchasing Manager"}
            proposed = registry.propose_action("propose_draft_purchase_order", {"product_id": 101}, user=user)
            assert "action_id" in proposed
            assert proposed["tool"] == "propose_draft_purchase_order"
            action_id = proposed["action_id"]

            # Step 2: Confirm action executes the underlying handler
            confirmed = registry.confirm_action(action_id, user=user)
            assert confirmed["purchase_order"]["order_number"] == "PO-003"
            assert confirmed["purchase_order"]["status"] == "Pending"

    def test_calculate_restock_forecast_grouped_by_supplier(self):
        mock_group = [{
            "supplier_id": 2,
            "supplier_name": "Supplier 2",
            "total_items": 2,
            "total_qty": 70.0,
            "total_estimated_cost": 210.0,
            "items": [MOCK_FORECAST],
        }]
        with _patch("_forecast_svc"):
            purchasing_mcp._forecast_svc.get_aggregated_supplier_draft_pos.return_value = mock_group
            result = purchasing_mcp._calculate_restock_forecast(group_by_supplier=True)
            assert len(result) == 1
            assert result[0]["supplier_id"] == 2
            purchasing_mcp._forecast_svc.get_aggregated_supplier_draft_pos.assert_called_once()

    def test_propose_draft_purchase_order_by_supplier_id(self):
        mock_group = [{
            "supplier_id": 5,
            "supplier_name": "Supplier 5",
            "lead_time_days": 7,
            "expected_date": "2026-09-10",
            "po_notes": "Consolidated draft PO",
            "items": [
                {
                    "product_id": 101,
                    "product_name": "Product A",
                    "suggested_order_qty": 50.0,
                    "unit_cost": 4.0,
                }
            ]
        }]
        with _patch("_forecast_svc"), _patch("_po_svc"), _patch("_po_repo"), _patch("_po_line_repo"):
            purchasing_mcp._forecast_svc.get_aggregated_supplier_draft_pos.return_value = mock_group
            purchasing_mcp._po_repo.list.return_value = []
            purchasing_mcp._po_svc.create.return_value = {
                "id": 40,
                "order_number": "PO-004",
                "supplier_id": 5,
                "total": 200.0,
                "status": "Pending",
            }
            purchasing_mcp._po_line_repo.create.side_effect = lambda line: {"id": 1, **line}

            result = purchasing_mcp._propose_draft_purchase_order(supplier_id=5)

            assert result["purchase_order"]["order_number"] == "PO-004"
            assert result["purchase_order"]["supplier_id"] == 5
            assert len(result["lines"]) == 1
            assert result["lines"][0]["line_total"] == 200.0

    def test_create_purchase_return_rma_with_lines(self):
        with _patch("_pr_service"), _patch("_pr_line_repo"), _patch("_product_repo"):
            purchasing_mcp._pr_service.create.return_value = {
                "id": 101,
                "return_number": "RMA-00001",
                "supplier_id": 2,
                "purchase_order_id": 10,
                "status": "Draft",
                "total_amount": 150.0,
            }
            purchasing_mcp._pr_line_repo.create.side_effect = lambda line: {"id": 1, **line}

            lines = [
                {
                    "product_id": 5,
                    "product_name": "Organic Apples",
                    "qty": 10.0,
                    "unit_price": 15.0,
                    "batch_id": 12,
                    "batch_number": "BAT-001",
                    "reason_code": "damaged",
                }
            ]

            result = purchasing_mcp._create_purchase_return_rma(
                supplier_id=2,
                purchase_order_id=10,
                reason="Damaged upon receiving",
                lines=lines,
            )

            assert result["id"] == 101
            assert result["return_number"] == "RMA-00001"
            assert len(result["lines"]) == 1
            assert result["lines"][0]["line_total"] == 150.0
            assert result["lines"][0]["reason_code"] == "damaged"
            purchasing_mcp._pr_service.create.assert_called_once()
            purchasing_mcp._pr_line_repo.create.assert_called_once()

    def test_create_purchase_return_rma_from_goods_receipt(self):
        with _patch("_pr_service"):
            purchasing_mcp._pr_service.create_from_goods_receipt.return_value = {
                "id": 102,
                "return_number": "RMA-00002",
                "goods_receipt_id": 25,
                "supplier_id": 3,
                "status": "Draft",
            }

            result = purchasing_mcp._create_purchase_return_rma(
                supplier_id=3,
                goods_receipt_id=25,
                reason="Dock rejection",
            )

            assert result["id"] == 102
            assert result["return_number"] == "RMA-00002"
            purchasing_mcp._pr_service.create_from_goods_receipt.assert_called_once()

    def test_get_purchase_return_details(self):
        with _patch("_pr_service"):
            purchasing_mcp._pr_service.get_return_details.return_value = {
                "id": 101,
                "return_number": "RMA-00001",
                "supplier_id": 2,
                "supplier_name": "Fresh Farms",
                "lines": [{"id": 1, "product_name": "Apples", "qty": 10}],
                "debit_memo_number": "DM-001",
            }

            result = purchasing_mcp._get_purchase_return_details(101)

            assert result["id"] == 101
            assert result["supplier_name"] == "Fresh Farms"
            assert result["debit_memo_number"] == "DM-001"
            purchasing_mcp._pr_service.get_return_details.assert_called_once_with(101)

    def test_approve_purchase_return_handler(self):
        with _patch("_pr_service"):
            purchasing_mcp._pr_service.approve_return.return_value = {
                "id": 101,
                "return_number": "RMA-00001",
                "status": "Approved",
                "debit_memo_id": 55,
                "approved_at": "2026-09-08T00:00:00Z",
            }

            result = purchasing_mcp._approve_purchase_return(
                id=101,
                approved_by=1,
                notes="Verified damaged goods",
            )

            assert result["status"] == "Approved"
            assert result["debit_memo_id"] == 55
            assert "approved successfully" in result["message"]
            purchasing_mcp._pr_service.approve_return.assert_called_once_with(
                id_val=101,
                approved_by=1,
                notes="Verified damaged goods",
                create_debit_memo=True,
                quarantine_inventory=True,
            )

    def test_tier2_approve_purchase_return_workflow(self):
        register_tools()
        with _patch("_pr_service"):
            purchasing_mcp._pr_service.approve_return.return_value = {
                "id": 105,
                "return_number": "RMA-00005",
                "status": "Approved",
                "debit_memo_id": 88,
            }

            # Step 1: Propose action
            proposed = registry.propose_action("approve_purchase_return", {"id": 105, "notes": "Approved by AP"})
            assert "action_id" in proposed
            assert proposed["tool"] == "approve_purchase_return"
            action_id = proposed["action_id"]

            # Step 2: Confirm action executes the underlying handler
            confirmed = registry.confirm_action(action_id)
            assert confirmed["status"] == "Approved"
            assert confirmed["debit_memo_id"] == 88
            assert "RMA-00005" in confirmed["message"]



