import pytest
from unittest.mock import patch, MagicMock
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
                        _quotations_svc=MagicMock(),
                        _deliveries_svc=MagicMock(),
                        _price_lists_svc=MagicMock(),
                        _tax_rates_svc=MagicMock()):
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


class TestGetOrder:
    def test_found(self, mock_svc):
        sales_mcp._orders_svc.get.return_value = MOCK_ORDER
        assert sales_mcp._get_order(1) == MOCK_ORDER

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
        sales_mcp._customers_svc.get.return_value = MOCK_CUSTOMER
        result = sales_mcp._get_customer_aging(id=1)
        assert result == MOCK_CUSTOMER


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


class TestRegisterTools:
    def test_registers_all_tools(self, clear_registry):
        register_tools()
        from packages.mcp.registry import get_tools, list_resources
        tool_names = [t.name for t in get_tools()]
        expected = ["list_orders", "get_order", "create_order", "update_order_status",
                     "confirm_order", "cancel_order", "list_customers", "get_customer_aging",
                     "list_quotations", "convert_quotation_to_order", "list_deliveries",
                     "list_price_lists", "list_tax_rates"]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"
        resource_uris = [r.uri for r in list_resources()]
        assert "nova://sales/orders" in resource_uris
