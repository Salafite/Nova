import pytest
from unittest.mock import patch, MagicMock
from packages.mcp import registry
from packages.mcp.servers import sales_mcp
from packages.mcp.servers.sales_mcp import register_tools


MOCK_ORDER = {"id": 1, "order_number": "SO-00001", "customer_id": 1, "status": "Draft", "grand_total": 100.0}
MOCK_CUSTOMER = {"id": 1, "name": "Acme Corp", "balance": 0, "credit_limit": 10000}
MOCK_QUOTE = {"id": 1, "quote_number": "QT-00001", "customer_id": 1, "status": "Pending"}


@pytest.fixture
def clear_registry():
    from packages.mcp import registry
    registry._tools.clear()
    registry._resources.clear()
    yield


@pytest.fixture
def mock_svc():
    with patch.multiple(sales_mcp,
                        _orders_svc=MagicMock(),
                        _customers_svc=MagicMock(),
                        _credit_svc=MagicMock(),
                        _quotations_svc=MagicMock(),
                        _deliveries_svc=MagicMock(),
                        _price_lists_svc=MagicMock(),
                        _tax_rates_svc=MagicMock(),
                        _lines_svc=MagicMock(),
                        _lines_repo=MagicMock(),
                        _aging_svc=MagicMock()):
        yield


class TestListOrders:
    def test_no_filters(self, mock_svc):
        sales_mcp._orders_svc.list.return_value = [MOCK_ORDER]
        result = sales_mcp._list_orders()
        assert result == [MOCK_ORDER]
        sales_mcp._orders_svc.list.assert_called_with(filters=None, limit=50)

    def test_with_status_filter(self, mock_svc):
        sales_mcp._orders_svc.list.return_value = [MOCK_ORDER]
        sales_mcp._list_orders(status="Confirmed")
        sales_mcp._orders_svc.list.assert_called_with(filters={"status": "Confirmed"}, limit=50)

    def test_with_catch_weight_filter(self, mock_svc):
        sales_mcp._orders_svc.list.return_value = [MOCK_ORDER]
        sales_mcp._list_orders(is_catch_weight=True)
        sales_mcp._orders_svc.list.assert_called_with(filters={"is_catch_weight": True}, limit=50)


class TestGetOrder:
    def test_found_with_lines(self, mock_svc):
        order_data = dict(MOCK_ORDER)
        mock_lines = [{
            "id": 1,
            "product_name": "Cheddar Cheese Block",
            "qty": 5,
            "unit_price": 100.0,
            "is_catch_weight": True,
            "nominal_weight": 25.0,
            "catch_weight_actual": 26.2,
            "unit_price_pricing_uom": 20.0,
            "recalculated_total": 524.0,
        }]
        sales_mcp._orders_svc.get.return_value = order_data
        sales_mcp._lines_repo.list.return_value = mock_lines
        result = sales_mcp._get_order(1)
        assert result["id"] == 1
        assert result["lines"] == mock_lines
        sales_mcp._lines_repo.list.assert_called_with(filters={"sales_order_id": 1})

    def test_not_found(self, mock_svc):
        sales_mcp._orders_svc.get.return_value = None
        assert sales_mcp._get_order(999) is None


class TestCreateOrder:
    def test_minimal(self, mock_svc):
        sales_mcp._orders_svc.create.return_value = MOCK_ORDER
        result = sales_mcp._create_order(customer_id=1)
        sales_mcp._orders_svc.create.assert_called_once()
        args = sales_mcp._orders_svc.create.call_args[0][0]
        assert args["customer_id"] == 1
        assert args["status"] == "Draft"
        assert result == MOCK_ORDER

    def test_with_grand_total(self, mock_svc):
        sales_mcp._orders_svc.create.return_value = MOCK_ORDER
        sales_mcp._create_order(customer_id=1, grand_total=200.0)
        args = sales_mcp._orders_svc.create.call_args[0][0]
        assert args["grand_total"] == 200.0


class TestOrderLines:
    def test_create_order_line(self, mock_svc):
        mock_line = {
            "id": 1,
            "sales_order_id": 1,
            "product_name": "Parmesan Cheese",
            "qty": 2,
            "unit_price": 50.0,
            "line_total": 100.0,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "unit_price_pricing_uom": 10.0,
            "nominal_weight": 10.0,
        }
        sales_mcp._lines_svc.create.return_value = mock_line
        result = sales_mcp._create_order_line(
            sales_order_id=1,
            product_name="Parmesan Cheese",
            qty=2,
            unit_price=50.0,
            is_catch_weight=True,
            pricing_uom_id=2,
            unit_price_pricing_uom=10.0,
            nominal_weight=10.0,
        )
        assert result == mock_line
        sales_mcp._lines_svc.create.assert_called_once_with({
            "sales_order_id": 1,
            "product_name": "Parmesan Cheese",
            "qty": 2,
            "unit_price": 50.0,
            "line_total": 100.0,
            "line_number": 1,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "unit_price_pricing_uom": 10.0,
            "nominal_weight": 10.0,
        })

    def test_create_order_line_full_dual_uom(self, mock_svc):
        mock_line = {
            "id": 2,
            "sales_order_id": 1,
            "product_id": 10,
            "product_name": "Cheddar Wheel",
            "uom_id": 1,
            "qty": 3,
            "unit_price": 60.0,
            "line_total": 180.0,
            "line_number": 2,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "unit_price_pricing_uom": 12.0,
            "nominal_weight": 15.0,
            "catch_weight_actual": 15.8,
            "recalculated_total": 189.6,
        }
        sales_mcp._lines_svc.create.return_value = mock_line
        result = sales_mcp._create_order_line(
            sales_order_id=1,
            product_id=10,
            product_name="Cheddar Wheel",
            uom_id=1,
            qty=3,
            unit_price=60.0,
            line_total=180.0,
            line_number=2,
            is_catch_weight=True,
            pricing_uom_id=2,
            unit_price_pricing_uom=12.0,
            nominal_weight=15.0,
            catch_weight_actual=15.8,
            recalculated_total=189.6,
        )
        assert result == mock_line
        sales_mcp._lines_svc.create.assert_called_once_with({
            "sales_order_id": 1,
            "product_name": "Cheddar Wheel",
            "product_id": 10,
            "uom_id": 1,
            "qty": 3,
            "unit_price": 60.0,
            "line_total": 180.0,
            "line_number": 2,
            "is_catch_weight": True,
            "pricing_uom_id": 2,
            "unit_price_pricing_uom": 12.0,
            "nominal_weight": 15.0,
            "catch_weight_actual": 15.8,
            "recalculated_total": 189.6,
        })

    def test_list_order_lines(self, mock_svc):
        mock_lines = [{"id": 1, "product_name": "Gouda"}]
        sales_mcp._lines_repo.list.return_value = mock_lines
        result = sales_mcp._list_order_lines(sales_order_id=1)
        assert result == mock_lines
        sales_mcp._lines_repo.list.assert_called_with(filters={"sales_order_id": 1})


class TestRecalculateCatchWeight:
    def test_recalculate(self, mock_svc):
        recalc_result = {
            "order_id": 1,
            "is_catch_weight": True,
            "original_subtotal": 500.0,
            "recalculated_subtotal": 524.0,
            "weight_adjustment_amount": 24.0,
            "nominal_total_weight": 25.0,
            "actual_total_weight": 26.2,
            "grand_total": 550.2,
        }
        sales_mcp._orders_svc.recalculate_order_catch_weight.return_value = recalc_result
        result = sales_mcp._recalculate_order_catch_weight(id=1)
        assert result == recalc_result
        sales_mcp._orders_svc.recalculate_order_catch_weight.assert_called_once_with(1)


class TestUpdateOrderStatus:
    def test_updates(self, mock_svc):
        sales_mcp._orders_svc.update.return_value = {**MOCK_ORDER, "status": "Confirmed"}
        result = sales_mcp._update_order_status(id=1, status="Confirmed")
        assert result["status"] == "Confirmed"


class TestConfirmCancel:
    def test_confirm(self, mock_svc):
        sales_mcp._orders_svc.update.return_value = {**MOCK_ORDER, "status": "Confirmed"}
        result = sales_mcp._confirm_order(id=1)
        sales_mcp._orders_svc.update.assert_called_with(1, {"status": "Confirmed"})
        assert result["status"] == "Confirmed"

    def test_cancel(self, mock_svc):
        sales_mcp._orders_svc.update.return_value = {**MOCK_ORDER, "status": "Cancelled"}
        sales_mcp._cancel_order(id=1)
        sales_mcp._orders_svc.update.assert_called_with(1, {"status": "Cancelled"})


class TestCustomers:
    def test_list(self, mock_svc):
        sales_mcp._customers_svc.list.return_value = [MOCK_CUSTOMER]
        result = sales_mcp._list_customers()
        assert result == [MOCK_CUSTOMER]

    def test_aging(self, mock_svc):
        mock_aging = {
            "customer_id": 1,
            "customer_name": "Acme Corp",
            "balance": 1500.0,
            "as_of_date": "2026-08-25",
            "aging": {
                "current": 500.0,
                "1_30": 1000.0,
                "31_60": 0.0,
                "61_90": 0.0,
                "90_plus": 0.0,
                "30": 1000.0,
                "60": 0.0,
                "90": 0.0,
                "total_outstanding": 1500.0,
                "total_paid": 0.0,
            },
            "invoices_count": 2,
            "open_invoices_count": 2,
            "paid_invoices_count": 0,
        }
        sales_mcp._aging_svc.get_customer_aging.return_value = mock_aging
        result = sales_mcp._get_customer_aging(id=1, as_of_date="2026-08-25")
        assert result == mock_aging
        sales_mcp._aging_svc.get_customer_aging.assert_called_with(1, as_of_date="2026-08-25")

    def test_aging_default_as_of_date(self, mock_svc):
        mock_aging = {
            "customer_id": 1,
            "customer_name": "Acme Corp",
            "balance": 0.0,
            "aging": {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0},
        }
        sales_mcp._aging_svc.get_customer_aging.return_value = mock_aging
        result = sales_mcp._get_customer_aging(id=1)
        assert result == mock_aging
        sales_mcp._aging_svc.get_customer_aging.assert_called_with(1, as_of_date=None)


class TestQuotations:
    def test_list(self, mock_svc):
        sales_mcp._quotations_svc.list.return_value = [MOCK_QUOTE]
        result = sales_mcp._list_quotations()
        assert result == [MOCK_QUOTE]

    def test_convert(self, mock_svc):
        sales_mcp._quotations_svc.update.return_value = {**MOCK_QUOTE, "status": "Converted"}
        sales_mcp._convert_quotation(id=1)
        sales_mcp._quotations_svc.update.assert_called_with(1, {"status": "Converted"})


class TestDeliveries:
    def test_list(self, mock_svc):
        sales_mcp._deliveries_svc.list.return_value = [{"id": 1, "delivery_number": "DEL-001"}]
        result = sales_mcp._list_deliveries()
        assert result == [{"id": 1, "delivery_number": "DEL-001"}]


class TestPriceListsTaxRates:
    def test_price_lists(self, mock_svc):
        sales_mcp._price_lists_svc.list.return_value = [{"id": 1, "name": "Standard"}]
        assert sales_mcp._list_price_lists() == [{"id": 1, "name": "Standard"}]

    def test_tax_rates(self, mock_svc):
        sales_mcp._tax_rates_svc.list.return_value = [{"id": 1, "name": "VAT", "rate": 0.15}]
        assert sales_mcp._list_tax_rates() == [{"id": 1, "name": "VAT", "rate": 0.15}]


class TestCheckCustomerCredit:
    def test_check_customer_credit_status_without_order_amount(self, mock_svc):
        mock_status = {
            "customer_id": 1,
            "customer_name": "Acme Corp",
            "credit_limit": 10000.0,
            "balance": 2500.0,
            "available_credit": 7500.0,
            "overdue_invoices": [],
            "overdue_total": 0.0,
            "has_overdue_30_days": False,
            "requires_hold": False,
        }
        sales_mcp._credit_svc.get_customer_credit_status.return_value = mock_status

        result = sales_mcp._check_customer_credit(customer_id=1)

        assert result == mock_status
        sales_mcp._credit_svc.get_customer_credit_status.assert_called_once_with(1, as_of_date=None)
        sales_mcp._credit_svc.evaluate_order_credit.assert_not_called()

    def test_check_customer_credit_with_order_amount_and_as_of_date(self, mock_svc):
        mock_eval = {
            "customer_id": 1,
            "credit_limit": 5000.0,
            "current_balance": 4000.0,
            "order_amount": 2000.0,
            "projected_balance": 6000.0,
            "available_credit": 1000.0,
            "exceeds_credit_limit": True,
            "has_overdue_30_days": False,
            "requires_hold": True,
            "approved": False,
            "hold_reasons": ["Order total $2,000.00 exceeds available credit limit of $1,000.00 (projected balance $6,000.00 > credit limit $5,000.00)"],
        }
        sales_mcp._credit_svc.evaluate_order_credit.return_value = mock_eval

        result = sales_mcp._check_customer_credit(customer_id=1, order_amount=2000.0, as_of_date="2026-08-25")

        assert result == mock_eval
        assert result["requires_hold"] is True
        assert result["approved"] is False
        sales_mcp._credit_svc.evaluate_order_credit.assert_called_once_with(1, order_amount=2000.0, as_of_date="2026-08-25")
        sales_mcp._credit_svc.get_customer_credit_status.assert_not_called()

    def test_check_customer_credit_zero_order_amount_delegates_to_status(self, mock_svc):
        mock_status = {"customer_id": 2, "balance": 0.0, "available_credit": 5000.0}
        sales_mcp._credit_svc.get_customer_credit_status.return_value = mock_status

        result = sales_mcp._check_customer_credit(customer_id=2, order_amount=0.0)

        assert result == mock_status
        sales_mcp._credit_svc.get_customer_credit_status.assert_called_once_with(2, as_of_date=None)
        sales_mcp._credit_svc.evaluate_order_credit.assert_not_called()

    def test_check_customer_credit_overdue_delinquent_evaluation(self, mock_svc):
        mock_eval = {
            "customer_id": 3,
            "credit_limit": 10000.0,
            "current_balance": 2000.0,
            "order_amount": 500.0,
            "projected_balance": 2500.0,
            "available_credit": 8000.0,
            "exceeds_credit_limit": False,
            "has_overdue_30_days": True,
            "requires_hold": True,
            "approved": False,
            "hold_reasons": ["Customer has 1 invoice(s) overdue by > 30 days totaling $1,200.00"],
        }
        sales_mcp._credit_svc.evaluate_order_credit.return_value = mock_eval

        result = sales_mcp._check_customer_credit(customer_id=3, order_amount=500.0)

        assert result["approved"] is False
        assert result["has_overdue_30_days"] is True
        assert result["requires_hold"] is True

    def test_call_tool_check_customer_credit_via_registry(self, clear_registry, mock_svc):
        register_tools()
        mock_eval = {
            "customer_id": 3,
            "approved": True,
            "requires_hold": False,
            "hold_reasons": [],
        }
        sales_mcp._credit_svc.evaluate_order_credit.return_value = mock_eval

        result = registry.call_tool("check_customer_credit", {"customer_id": 3, "order_amount": 150.0})

        assert result == mock_eval
        sales_mcp._credit_svc.evaluate_order_credit.assert_called_once_with(3, order_amount=150.0, as_of_date=None)


class TestOverrideCreditHold:
    def test_override_credit_hold_with_default_arguments(self, mock_svc):
        mock_released_order = {
            "id": 10,
            "order_number": "SO-00010",
            "status": "Confirmed",
            "hold_release_reason": "",
            "hold_released_by": 1,
        }
        sales_mcp._orders_svc.override_credit_hold.return_value = mock_released_order

        result = sales_mcp._override_credit_hold(id=10)

        assert result == mock_released_order
        sales_mcp._orders_svc.override_credit_hold.assert_called_once_with(
            order_id=10,
            user_id=1,
            user_name="Financial Manager",
            reason="",
            target_status="Confirmed",
        )

    def test_override_credit_hold_with_explicit_reason_and_target_status(self, mock_svc):
        mock_released_order = {
            "id": 12,
            "order_number": "SO-00012",
            "status": "Pending",
            "hold_release_reason": "Customer wire transfer in transit",
            "hold_released_by": 1,
        }
        sales_mcp._orders_svc.override_credit_hold.return_value = mock_released_order

        result = sales_mcp._override_credit_hold(
            id=12,
            reason="Customer wire transfer in transit",
            target_status="Pending",
        )

        assert result == mock_released_order
        sales_mcp._orders_svc.override_credit_hold.assert_called_once_with(
            order_id=12,
            user_id=1,
            user_name="Financial Manager",
            reason="Customer wire transfer in transit",
            target_status="Pending",
        )

    def test_override_credit_hold_with_authenticated_user_context(self, clear_registry, mock_svc):
        register_tools()
        mock_released_order = {
            "id": 15,
            "order_number": "SO-00015",
            "status": "Confirmed",
            "hold_release_reason": "Executive CFO exception approval",
            "hold_released_by": 42,
        }
        sales_mcp._orders_svc.override_credit_hold.return_value = mock_released_order

        user_context = {"id": 42, "username": "sarah_cfo", "role": "financial_manager"}
        result = registry.call_tool(
            "override_credit_hold",
            {"id": 15, "reason": "Executive CFO exception approval", "target_status": "Confirmed"},
            user=user_context,
        )

        assert result == mock_released_order
        sales_mcp._orders_svc.override_credit_hold.assert_called_once_with(
            order_id=15,
            user_id=42,
            user_name="sarah_cfo",
            reason="Executive CFO exception approval",
            target_status="Confirmed",
        )


class TestTier2OverrideCreditHold:
    def test_override_credit_hold_is_tier2_tool(self, clear_registry):
        register_tools()
        tools = {t.name: t for t in registry.get_tools()}
        assert "override_credit_hold" in tools
        assert tools["override_credit_hold"].tier == "tier2"

    def test_check_customer_credit_is_tier1_tool(self, clear_registry):
        register_tools()
        tools = {t.name: t for t in registry.get_tools()}
        assert "check_customer_credit" in tools
        assert tools["check_customer_credit"].tier == "tier1"

    def test_propose_and_confirm_override_credit_hold_workflow(self, clear_registry, mock_svc):
        register_tools()
        mock_released_order = {
            "id": 20,
            "order_number": "SO-00020",
            "status": "Confirmed",
            "hold_release_reason": "Board-level customer account authorization",
            "hold_released_by": 7,
        }
        sales_mcp._orders_svc.override_credit_hold.return_value = mock_released_order

        user_context = {"id": 7, "username": "fin_director"}

        # Step 1: Propose action
        proposed = registry.propose_action(
            "override_credit_hold",
            {"id": 20, "reason": "Board-level customer account authorization", "target_status": "Confirmed"},
            user=user_context,
        )

        assert "action_id" in proposed
        assert proposed["tool"] == "override_credit_hold"
        assert "Action: override_credit_hold" in proposed["preview"]
        action_id = proposed["action_id"]

        # Step 2: Confirm action
        confirmed = registry.confirm_action(action_id)

        assert confirmed == mock_released_order
        sales_mcp._orders_svc.override_credit_hold.assert_called_once_with(
            order_id=20,
            user_id=7,
            user_name="fin_director",
            reason="Board-level customer account authorization",
            target_status="Confirmed",
        )


class TestRegisterTools:
    def test_registers_all_tools(self, clear_registry):
        register_tools()
        from packages.mcp.registry import get_tools, list_resources
        tool_names = [t.name for t in get_tools()]
        expected = ["list_orders", "get_order", "create_order", "create_order_line",
                    "list_order_lines", "recalculate_order_catch_weight",
                    "update_order_status", "confirm_order", "cancel_order", "list_customers",
                    "get_customer_aging", "list_quotations", "convert_quotation_to_order",
                    "list_deliveries", "list_price_lists", "list_tax_rates",
                    "check_customer_credit", "override_credit_hold"]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"
        resource_uris = [r.uri for r in list_resources()]
        assert "nova://sales/orders" in resource_uris

