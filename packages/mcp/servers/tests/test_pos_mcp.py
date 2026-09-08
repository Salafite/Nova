import pytest
from unittest.mock import patch, MagicMock
from modules.core.context import tenant_context
from modules.pos.models.pos import PosCheckoutResponse
from packages.mcp.servers import pos_mcp
from packages.mcp.servers.pos_mcp import register_tools, _pos_checkout_handler, _pos_customer_lookup_handler


@pytest.fixture
def clear_registry():
    from packages.mcp import registry
    registry._tools.clear()
    registry._resources.clear()
    yield


class TestPosMcp:
    def test_register_tools(self, clear_registry):
        register_tools()
        from packages.mcp.registry import get_tools
        tool_names = [t.name for t in get_tools()]
        assert "pos_checkout" in tool_names
        assert "pos_customer_lookup" in tool_names

    def test_checkout_handler_delegates_to_process_pos_checkout(self):
        mock_response = PosCheckoutResponse(
            success=True,
            order_id=10,
            order_number="POS-20260822-0001",
            grand_total=105.0,
            message="POS order POS-20260822-0001 created successfully",
        )
        with patch("packages.mcp.servers.pos_mcp.process_pos_checkout", return_value=mock_response) as mock_checkout:
            cart_items = [
                {"product_id": 1, "product_name": "Test Item", "qty": 2, "unit_price": 50.0}
            ]
            payments = [
                {"payment_method": "Cash", "amount": 55.0},
                {"payment_method": "Card", "amount": 50.0}
            ]
            result = _pos_checkout_handler(
                cart_items=cart_items,
                customer_id=123,
                customer_name="John Doe",
                warehouse_id=1,
                payments=payments,
                amount_tendered=110.0,
                notes="MCP checkout test"
            )
            assert result["success"] is True
            assert result["order_id"] == 10
            assert result["order_number"] == "POS-20260822-0001"
            assert result["grand_total"] == 105.0
            
            mock_checkout.assert_called_once()
            req = mock_checkout.call_args[0][0]
            assert req.customer_id == 123
            assert req.customer_name == "John Doe"
            assert req.warehouse_id == 1
            assert req.amount_tendered == 110.0
            assert len(req.payments) == 2
            assert req.payments[0].payment_method == "Cash"
            assert req.payments[1].payment_method == "Card"
            assert len(req.cart_items) == 1
            assert req.cart_items[0].product_id == 1

    def test_checkout_handler_with_tenant_context(self):
        mock_response = PosCheckoutResponse(
            success=True,
            order_id=20,
            order_number="POS-20260822-0002",
            grand_total=52.5,
            message="POS order POS-20260822-0002 created successfully",
        )
        with tenant_context(42):
            with patch("packages.mcp.servers.pos_mcp.process_pos_checkout", return_value=mock_response) as mock_checkout:
                cart_items = [
                    {"product_id": 2, "product_name": "Item 2", "qty": 1, "unit_price": 50.0}
                ]
                result = _pos_checkout_handler(cart_items=cart_items)
                assert result["success"] is True
                assert result["order_id"] == 20
                mock_checkout.assert_called_once()

    def test_pos_customer_lookup_handler(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [
            {"id": 1, "name": "John Doe", "phone": "12345", "email": "j@doe.com", "customer_group": "Retail", "credit_limit": 0, "current_balance": 0}
        ]
        with patch("packages.mcp.servers.pos_mcp.get_connection", return_value=mock_conn):
            with patch("packages.mcp.servers.pos_mcp.release_connection") as mock_release:
                result = _pos_customer_lookup_handler(query="John", limit=5)
                assert len(result) == 1
                assert result[0]["name"] == "John Doe"
                mock_conn.cursor.assert_called_once()
                mock_cur.execute.assert_called_once()
                mock_release.assert_called_once_with(mock_conn)
