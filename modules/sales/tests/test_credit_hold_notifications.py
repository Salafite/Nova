"""
Unit and integration tests for manager notifications and WebSocket broadcasts
when sales orders are placed on Credit Hold.
"""

from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService


class DummyRepo:
    def __init__(self, items=None):
        self.items = items or []
        self._next_id = len(self.items) + 1

    def get(self, id_val, conn=None):
        for item in self.items:
            if item.get('id') == id_val:
                return dict(item)
        return None

    def list(self, filters=None, order_by=None, limit=None, offset=None, conn=None):
        result = []
        for item in self.items:
            match = True
            if filters:
                for k, v in filters.items():
                    if item.get(k) != v:
                        match = False
                        break
            if match:
                result.append(dict(item))
        return result

    def create(self, payload, conn=None):
        payload_copy = dict(payload)
        if 'id' not in payload_copy:
            payload_copy['id'] = self._next_id
            self._next_id += 1
        self.items.append(payload_copy)
        return dict(payload_copy)

    def update(self, id_val, payload, conn=None):
        for i, item in enumerate(self.items):
            if item.get('id') == id_val:
                updated = dict(item)
                updated.update(payload)
                self.items[i] = updated
                return dict(updated)
        return None


class TestCreditHoldNotifications:
    """Tests verifying NotificationService and WebSocket broadcasts on credit hold."""

    def test_sales_order_create_credit_hold_triggers_notification_and_broadcast(self):
        """When an order is created that exceeds credit limit, notification and broadcast must be triggered."""
        order_repo = DummyRepo()
        customer_repo = DummyRepo([{
            'id': 101,
            'name': 'Acme Corp',
            'credit_limit': 1000.0,
            'balance': 800.0,
        }])
        invoice_repo = DummyRepo()

        mock_notification_service = MagicMock()
        mock_notification_service.notify_roles.return_value = [{'id': 1}]

        service = SalesOrderService(
            repo=order_repo,
            customer_repo=customer_repo,
            inv_repo=invoice_repo,
            notification_service=mock_notification_service,
        )

        with patch.object(service, '_dispatch_ws_broadcast') as mock_ws:
            created = service.create({
                'order_number': 'SO-2026-001',
                'customer_id': 101,
                'subtotal': 500.0,
                'tax': 50.0,
                'grand_total': 550.0,
            })

            assert created['status'] == 'Credit Hold'
            assert 'Customer credit limit exceeded' in (created.get('hold_reason') or '')

            # Verify NotificationService.notify_roles called
            mock_notification_service.notify_roles.assert_called_once()
            call_kwargs = mock_notification_service.notify_roles.call_args.kwargs
            assert 'Credit Hold' in call_kwargs.get('title', '')
            assert 'SO-2026-001' in call_kwargs.get('title', '')
            assert 'Acme Corp' in call_kwargs.get('message', '')
            assert call_kwargs.get('notification_type') == 'Credit Hold'
            assert call_kwargs.get('reference_type') == 'SalesOrder'
            assert call_kwargs.get('reference_id') == created['id']
            assert 'admin' in call_kwargs.get('roles', [])

            # Verify WebSocket broadcast dispatched
            mock_ws.assert_called_once()
            ws_kwargs = mock_ws.call_args.kwargs
            assert ws_kwargs.get('order_id') == created['id']
            assert ws_kwargs.get('order_number') == 'SO-2026-001'
            assert ws_kwargs.get('status') == 'Credit Hold'
            assert ws_kwargs.get('customer_name') == 'Acme Corp'

    def test_sales_order_create_normal_does_not_trigger_hold_notification(self):
        """When an order does not exceed credit limit, no credit hold notification is sent."""
        order_repo = DummyRepo()
        customer_repo = DummyRepo([{
            'id': 102,
            'name': 'Good Standing Customer',
            'credit_limit': 5000.0,
            'balance': 200.0,
        }])
        invoice_repo = DummyRepo()

        mock_notification_service = MagicMock()
        service = SalesOrderService(
            repo=order_repo,
            customer_repo=customer_repo,
            inv_repo=invoice_repo,
            notification_service=mock_notification_service,
        )

        with patch.object(service, '_dispatch_ws_broadcast') as mock_ws:
            created = service.create({
                'order_number': 'SO-2026-002',
                'customer_id': 102,
                'grand_total': 300.0,
            })

            assert created['status'] == 'Pending'
            mock_notification_service.notify_roles.assert_not_called()
            mock_ws.assert_not_called()

    def test_sales_order_update_to_credit_hold_triggers_notification(self):
        """When an existing order is updated to 'Credit Hold', notifications are triggered."""
        order_repo = DummyRepo([{
            'id': 10,
            'order_number': 'SO-2026-010',
            'customer_id': 101,
            'status': 'Draft',
            'grand_total': 1200.0,
        }])
        customer_repo = DummyRepo([{
            'id': 101,
            'name': 'Acme Corp',
            'credit_limit': 1000.0,
            'balance': 800.0,
        }])
        invoice_repo = DummyRepo()

        mock_notification_service = MagicMock()
        service = SalesOrderService(
            repo=order_repo,
            customer_repo=customer_repo,
            inv_repo=invoice_repo,
            notification_service=mock_notification_service,
        )

        with patch.object(service, '_dispatch_ws_broadcast') as mock_ws:
            updated = service.update(10, {
                'status': 'Credit Hold',
                'hold_reason': 'Manager placed on hold pending payment',
            })

            assert updated['status'] == 'Credit Hold'
            mock_notification_service.notify_roles.assert_called_once()
            call_kwargs = mock_notification_service.notify_roles.call_args.kwargs
            assert 'Credit Hold' in call_kwargs.get('title', '')
            assert 'SO-2026-010' in call_kwargs.get('title', '')
            assert call_kwargs.get('reference_id') == 10
            mock_ws.assert_called_once()

    def test_enhanced_sales_order_create_with_lines_credit_hold(self):
        """EnhancedSalesOrderService.create_with_lines triggers credit hold notification when lines exceed limit."""
        order_repo = DummyRepo()
        line_repo = DummyRepo()
        customer_repo = DummyRepo([{
            'id': 105,
            'name': 'Overdue Debtor',
            'credit_limit': 2000.0,
            'balance': 1900.0,
        }])
        invoice_repo = DummyRepo()
        tax_rate_repo = DummyRepo([{'id': 1, 'rate': 10.0}])
        price_list_item_repo = DummyRepo([{'id': 1, 'price_list_id': 1, 'product_id': 1, 'unit_price': 100.0}])

        mock_notification_service = MagicMock()
        service = EnhancedSalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=customer_repo,
            inv_repo=invoice_repo,
            tax_rate_repo=tax_rate_repo,
            price_list_item_repo=price_list_item_repo,
            notification_service=mock_notification_service,
        )

        with patch.object(service, '_dispatch_ws_broadcast') as mock_ws:
            order_data = {
                'order_number': 'SO-2026-050',
                'customer_id': 105,
                'tax_rate_id': 1,
            }
            lines = [
                {'product_id': 1, 'qty': 5, 'unit_price': 100.0},  # subtotal 500 + 10% tax = 550; total exposure 1900+550=2450 > 2000
            ]

            result = service.create_with_lines(order_data, lines)

            assert result['status'] == 'Credit Hold'
            assert 'Customer credit limit exceeded' in (result.get('hold_reason') or '')

            mock_notification_service.notify_roles.assert_called_once()
            call_kwargs = mock_notification_service.notify_roles.call_args.kwargs
            assert 'Credit Hold' in call_kwargs.get('title', '')
            assert 'SO-2026-050' in call_kwargs.get('title', '')
            assert 'Overdue Debtor' in call_kwargs.get('message', '')
            assert call_kwargs.get('reference_id') == result['id']

            mock_ws.assert_called_once()
            ws_kwargs = mock_ws.call_args.kwargs
            assert ws_kwargs.get('status') == 'Credit Hold'
            assert ws_kwargs.get('customer_name') == 'Overdue Debtor'

    @pytest.mark.asyncio
    async def test_websocket_broadcast_helpers(self):
        """Test broadcast helper functions from packages.ws.broadcast."""
        from packages.ws.broadcast import order_status_changed, order_credit_hold_placed
        from packages.ws.manager import order_manager

        with patch.object(order_manager, 'broadcast', new_callable=AsyncMock) as mock_b:
            await order_status_changed(
                business_id=1,
                order_id=42,
                order_number='SO-42',
                status='Credit Hold',
                hold_reason='Over limit',
            )

            mock_b.assert_called_once_with(
                'orders:1',
                'order_status_changed',
                {'order_id': 42, 'order_number': 'SO-42', 'status': 'Credit Hold', 'hold_reason': 'Over limit'},
            )

        with patch.object(order_manager, 'broadcast', new_callable=AsyncMock) as mock_b:
            await order_credit_hold_placed(
                business_id=1,
                order_id=42,
                order_number='SO-42',
                customer_id=101,
                customer_name='Acme Corp',
                hold_reason='Limit exceeded',
                grand_total=1500.0,
            )

            mock_b.assert_called_once_with(
                'orders:1',
                'order_credit_hold',
                {
                    'order_id': 42,
                    'order_number': 'SO-42',
                    'customer_id': 101,
                    'customer_name': 'Acme Corp',
                    'hold_reason': 'Limit exceeded',
                    'grand_total': 1500.0,
                    'status': 'Credit Hold',
                },
            )
