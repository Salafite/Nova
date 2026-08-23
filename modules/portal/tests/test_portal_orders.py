import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date, time
from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.services.portal_pricing_service import PortalPricingService
from modules.portal.services.portal_order_service import PortalOrderService
from modules.portal.models.portal import (
    PortalOrderCreate,
    PortalOrderLineCreate,
    PortalOrderResponse,
    PortalReorderRequest,
    PortalOrderCancelRequest,
    CutoffValidationResponse,
    OrderValidationResponse,
)


@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=PortalRepository)
    return repo


@pytest.fixture
def mock_pricing_service(mock_repo):
    svc = MagicMock(spec=PortalPricingService)
    svc.portal_repo = mock_repo
    return svc


@pytest.fixture
def order_service(mock_repo, mock_pricing_service):
    return PortalOrderService(portal_repo=mock_repo, pricing_service=mock_pricing_service)


class TestCutoffValidation:
    def test_before_cutoff_time(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 200.0,
            'is_active': True
        }

        # Current time 20:30 on 2026-08-23 (before 22:00 cutoff)
        test_dt = datetime(2026, 8, 23, 20, 30, 0)
        res = order_service.validate_cutoff_time(101, current_dt=test_dt)

        assert isinstance(res, CutoffValidationResponse)
        assert res.is_past_cutoff is False
        assert res.cutoff_time == '22:00'
        assert res.current_time == '20:30'
        assert res.next_delivery_date == date(2026, 8, 24)
        assert "next-day delivery" in res.message

    def test_after_cutoff_time(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 200.0,
            'is_active': True
        }

        # Current time 22:45 on 2026-08-23 (after 22:00 cutoff)
        test_dt = datetime(2026, 8, 23, 22, 45, 0)
        res = order_service.validate_cutoff_time(101, current_dt=test_dt)

        assert isinstance(res, CutoffValidationResponse)
        assert res.is_past_cutoff is True
        assert res.cutoff_time == '22:00'
        assert res.current_time == '22:45'
        assert res.next_delivery_date == date(2026, 8, 25)
        assert "passed" in res.message

    def test_no_cutoff_configured(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = {
            'id': 102,
            'name': 'Corner Cafe',
            'order_cutoff_time': None,
            'min_order_amount': 0.0,
            'is_active': True
        }

        test_dt = datetime(2026, 8, 23, 23, 15, 0)
        res = order_service.validate_cutoff_time(102, current_dt=test_dt)

        assert res.is_past_cutoff is False
        assert res.cutoff_time is None
        assert res.next_delivery_date == date(2026, 8, 24)

    def test_customer_not_found(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = None
        with pytest.raises(ValueError, match="does not exist"):
            order_service.validate_cutoff_time(9999)


class TestOrderValidation:
    def test_order_validation_success(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 150.0,
            'is_active': True
        }
        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {'product_id': 1, 'qty': 10.0, 'unit_price': 20.0, 'line_total': 200.0}
        ]

        items = [PortalOrderLineCreate(product_id=1, qty=10.0)]
        test_dt = datetime(2026, 8, 23, 19, 0, 0)
        res = order_service.validate_order(101, items=items, current_dt=test_dt)

        assert isinstance(res, OrderValidationResponse)
        assert res.is_valid is True
        assert res.subtotal == 200.0
        assert res.min_order_amount == 150.0
        assert res.meets_minimum is True
        assert len(res.errors) == 0

    def test_order_validation_below_minimum(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 250.0,
            'is_active': True
        }
        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {'product_id': 1, 'qty': 2.0, 'unit_price': 50.0, 'line_total': 100.0}
        ]

        items = [PortalOrderLineCreate(product_id=1, qty=2.0)]
        res = order_service.validate_order(101, items=items)

        assert res.is_valid is False
        assert res.subtotal == 100.0
        assert res.min_order_amount == 250.0
        assert res.meets_minimum is False
        assert len(res.errors) == 1
        assert "below the minimum required order amount" in res.errors[0]

    def test_order_validation_past_cutoff_warning(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '21:00',
            'min_order_amount': 100.0,
            'is_active': True
        }
        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {'product_id': 1, 'qty': 5.0, 'unit_price': 30.0, 'line_total': 150.0}
        ]

        items = [PortalOrderLineCreate(product_id=1, qty=5.0)]
        test_dt = datetime(2026, 8, 23, 21, 30, 0)
        res = order_service.validate_order(101, items=items, current_dt=test_dt)

        assert res.is_valid is True
        assert res.meets_minimum is True
        assert res.cutoff_status.is_past_cutoff is True
        assert len(res.warnings) == 1
        assert "cutoff deadline" in res.warnings[0]


class TestOrderCreation:
    def test_create_order_success(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 200.0,
            'default_price_list_id': 3,
            'default_tax_rate_id': 1,
            'payment_term_id': 2,
            'is_active': True
        }
        mock_repo.get_active_warehouse.return_value = {'id': 1, 'name': 'Main Warehouse'}
        mock_repo.get_tax_rate.return_value = {'id': 1, 'name': 'Standard Tax', 'rate': 10.0}

        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {
                'line_number': 1,
                'product_id': 50,
                'product_code': 'FLOUR-50',
                'product_name': 'Bread Flour 50lb',
                'uom_name': 'Bag',
                'qty': 10.0,
                'unit_price': 25.0,
                'base_price': 30.0,
                'line_total': 250.0,
                'is_contracted': True
            }
        ]

        mock_repo.create_order.return_value = {
            'id': 501,
            'order_number': 'SO-20260823-00001',
            'customer_id': 101,
            'warehouse_id': 1,
            'subtotal': 250.0,
            'tax': 25.0,
            'grand_total': 275.0,
            'status': 'Confirmed',
            'order_date': date(2026, 8, 23),
            'notes': '[Delivery Date: 2026-08-24]\nPlease deliver before 10 AM',
            'price_list_id': 3,
            'tax_rate_id': 1,
            'payment_term_id': 2,
            'lines': [
                {
                    'id': 1001,
                    'sales_order_id': 501,
                    'product_id': 50,
                    'product_code': 'FLOUR-50',
                    'product_name': 'Bread Flour 50lb',
                    'uom_name': 'Bag',
                    'qty': 10.0,
                    'unit_price': 25.0,
                    'line_total': 250.0,
                    'line_number': 1
                }
            ]
        }

        order_in = PortalOrderCreate(
            items=[PortalOrderLineCreate(product_id=50, qty=10.0)],
            notes="Please deliver before 10 AM",
            status="Confirmed"
        )
        test_dt = datetime(2026, 8, 23, 18, 0, 0)
        res = order_service.create_order(101, order_in=order_in, user_id=42, current_dt=test_dt)

        assert isinstance(res, PortalOrderResponse)
        assert res.id == 501
        assert res.order_number == 'SO-20260823-00001'
        assert res.subtotal == 250.0
        assert res.tax == 25.0
        assert res.grand_total == 275.0
        assert res.status == 'Confirmed'
        assert len(res.lines) == 1
        assert res.lines[0].product_name == 'Bread Flour 50lb'
        assert res.lines[0].unit_price == 25.0

    def test_create_draft_order_success(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'order_cutoff_time': '22:00',
            'min_order_amount': 50.0,
            'default_price_list_id': 3,
            'default_tax_rate_id': None,
            'payment_term_id': None,
            'is_active': True
        }
        mock_repo.get_active_warehouse.return_value = {'id': 1, 'name': 'Main Warehouse'}
        mock_repo.get_tax_rate.return_value = None

        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {
                'line_number': 1,
                'product_id': 50,
                'product_code': 'FLOUR-50',
                'product_name': 'Bread Flour 50lb',
                'uom_name': 'Bag',
                'qty': 2.0,
                'unit_price': 30.0,
                'base_price': 30.0,
                'line_total': 60.0,
                'is_contracted': False
            }
        ]

        mock_repo.create_order.return_value = {
            'id': 502,
            'order_number': 'SO-20260823-00002',
            'customer_id': 101,
            'warehouse_id': 1,
            'subtotal': 60.0,
            'tax': 0.0,
            'grand_total': 60.0,
            'status': 'Draft',
            'order_date': date(2026, 8, 23),
            'notes': '[Delivery Date: 2026-08-25]\nDraft order for review',
            'price_list_id': 3,
            'tax_rate_id': None,
            'payment_term_id': None,
            'lines': [
                {
                    'id': 1002,
                    'sales_order_id': 502,
                    'product_id': 50,
                    'product_code': 'FLOUR-50',
                    'product_name': 'Bread Flour 50lb',
                    'uom_name': 'Bag',
                    'qty': 2.0,
                    'unit_price': 30.0,
                    'line_total': 60.0,
                    'line_number': 1
                }
            ]
        }

        order_in = PortalOrderCreate(
            items=[PortalOrderLineCreate(product_id=50, qty=2.0)],
            requested_delivery_date=date(2026, 8, 25),
            notes="Draft order for review",
            status="Draft"
        )
        res = order_service.create_order(101, order_in=order_in, user_id=42)

        assert isinstance(res, PortalOrderResponse)
        assert res.id == 502
        assert res.status == 'Draft'
        assert res.grand_total == 60.0

    def test_create_order_below_minimum_raises(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'min_order_amount': 300.0,
            'is_active': True
        }
        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {'product_id': 1, 'qty': 1.0, 'unit_price': 100.0, 'line_total': 100.0}
        ]

        order_in = PortalOrderCreate(
            items=[PortalOrderLineCreate(product_id=1, qty=1.0)],
            status="Confirmed"
        )

        with pytest.raises(ValueError, match="below the minimum required order amount"):
            order_service.create_order(101, order_in=order_in)

    def test_create_order_inactive_customer_raises(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Closed Bistro',
            'is_active': False
        }

        order_in = PortalOrderCreate(
            items=[PortalOrderLineCreate(product_id=1, qty=5.0)]
        )

        with pytest.raises(ValueError, match="inactive"):
            order_service.create_order(101, order_in=order_in)


class TestOrderHistoryAndDetails:
    def test_get_orders_isolated_by_customer(self, order_service, mock_repo):
        mock_repo.get_orders.return_value = (
            [
                {
                    'id': 501,
                    'order_number': 'SO-00501',
                    'customer_id': 101,
                    'customer_name': 'Gourmet Bistro',
                    'warehouse_id': 1,
                    'subtotal': 250.0,
                    'tax': 25.0,
                    'grand_total': 275.0,
                    'status': 'Confirmed',
                    'order_date': date(2026, 8, 20),
                    'notes': None,
                    'lines': []
                }
            ],
            1
        )

        orders, total = order_service.get_orders(customer_id=101, page=1, limit=50)

        assert total == 1
        assert len(orders) == 1
        assert orders[0].id == 501
        assert orders[0].customer_id == 101
        mock_repo.get_orders.assert_called_once_with(
            customer_id=101,
            status=None,
            page=1,
            limit=50,
            conn=None
        )

    def test_get_order_by_id_found(self, order_service, mock_repo):
        mock_repo.get_order_by_id.return_value = {
            'id': 501,
            'order_number': 'SO-00501',
            'customer_id': 101,
            'customer_name': 'Gourmet Bistro',
            'warehouse_id': 1,
            'subtotal': 250.0,
            'tax': 25.0,
            'grand_total': 275.0,
            'status': 'Confirmed',
            'order_date': date(2026, 8, 20),
            'notes': '[Delivery Date: 2026-08-21]',
            'lines': [
                {
                    'id': 1001,
                    'sales_order_id': 501,
                    'product_id': 50,
                    'product_code': 'FLOUR-50',
                    'product_name': 'Bread Flour 50lb',
                    'uom_name': 'Bag',
                    'qty': 10.0,
                    'unit_price': 25.0,
                    'line_total': 250.0,
                    'line_number': 1
                }
            ]
        }

        order = order_service.get_order_by_id(customer_id=101, order_id=501)
        assert order is not None
        assert order.id == 501
        assert order.order_number == 'SO-00501'
        assert len(order.lines) == 1
        assert order.lines[0].product_name == 'Bread Flour 50lb'

    def test_get_order_by_id_different_customer_returns_none(self, order_service, mock_repo):
        # When querying for customer 102 but order belongs to 101, repo returns None
        mock_repo.get_order_by_id.return_value = None

        order = order_service.get_order_by_id(customer_id=102, order_id=501)
        assert order is None


class TestReorderAndCancel:
    def test_reorder_success(self, order_service, mock_repo, mock_pricing_service):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'allow_reorders': True,
            'min_order_amount': 200.0,
            'order_cutoff_time': '22:00',
            'default_tax_rate_id': 1,
            'is_active': True
        }

        # Mock original order
        mock_repo.get_order_by_id.return_value = {
            'id': 400,
            'order_number': 'SO-00400',
            'customer_id': 101,
            'warehouse_id': 1,
            'lines': [
                {'product_id': 50, 'qty': 10.0, 'unit_price': 25.0},
                {'product_id': 51, 'qty': 2.0, 'unit_price': 15.0}
            ]
        }

        mock_pricing_service.resolve_line_items_pricing.return_value = [
            {'product_id': 50, 'product_name': 'Bread Flour 50lb', 'qty': 10.0, 'unit_price': 26.0, 'line_total': 260.0},
            {'product_id': 51, 'product_name': 'Yeast 1lb', 'qty': 2.0, 'unit_price': 15.0, 'line_total': 30.0}
        ]

        mock_repo.create_order.return_value = {
            'id': 600,
            'order_number': 'SO-00600',
            'customer_id': 101,
            'warehouse_id': 1,
            'subtotal': 290.0,
            'tax': 0.0,
            'grand_total': 290.0,
            'status': 'Confirmed',
            'order_date': date(2026, 8, 23),
            'notes': 'Replenishment reorder based on #SO-00400',
            'lines': [
                {'id': 1, 'sales_order_id': 600, 'product_id': 50, 'product_name': 'Bread Flour 50lb', 'qty': 10.0, 'unit_price': 26.0, 'line_total': 260.0, 'line_number': 1},
                {'id': 2, 'sales_order_id': 600, 'product_id': 51, 'product_name': 'Yeast 1lb', 'qty': 2.0, 'unit_price': 15.0, 'line_total': 30.0, 'line_number': 2}
            ]
        }

        reorder_req = PortalReorderRequest(order_id=400, status="Confirmed")
        new_order = order_service.reorder(101, reorder_in=reorder_req, user_id=42)

        assert isinstance(new_order, PortalOrderResponse)
        assert new_order.id == 600
        assert new_order.order_number == 'SO-00600'
        assert new_order.subtotal == 290.0
        assert len(new_order.lines) == 2

    def test_reorder_disabled_raises(self, order_service, mock_repo):
        mock_repo.get_customer_by_id.return_value = {
            'id': 101,
            'name': 'Gourmet Bistro',
            'allow_reorders': False,
            'is_active': True
        }

        reorder_req = PortalReorderRequest(order_id=400)
        with pytest.raises(ValueError, match="disabled"):
            order_service.reorder(101, reorder_in=reorder_req)

    def test_cancel_order_success(self, order_service, mock_repo):
        mock_repo.get_order_by_id.side_effect = [
            # First lookup before cancel
            {
                'id': 501,
                'order_number': 'SO-00501',
                'customer_id': 101,
                'status': 'Confirmed',
                'notes': 'Initial notes'
            },
            # Second lookup after update
            {
                'id': 501,
                'order_number': 'SO-00501',
                'customer_id': 101,
                'subtotal': 200.0,
                'tax': 0.0,
                'grand_total': 200.0,
                'status': 'Cancelled',
                'order_date': date(2026, 8, 23),
                'notes': 'Initial notes\n[Cancelled by customer: Overordered]',
                'lines': []
            }
        ]

        mock_repo.update_order_status.return_value = {'id': 501, 'status': 'Cancelled'}

        cancel_req = PortalOrderCancelRequest(reason="Overordered")
        res = order_service.cancel_order(101, order_id=501, cancel_in=cancel_req)

        assert res.status == 'Cancelled'
        assert "Overordered" in (res.notes or '')
        mock_repo.update_order_status.assert_called_once_with(
            order_id=501,
            status='Cancelled',
            notes='Initial notes\n[Cancelled by customer: Overordered]',
            customer_id=101,
            conn=None
        )

    def test_cancel_already_shipped_order_raises(self, order_service, mock_repo):
        mock_repo.get_order_by_id.return_value = {
            'id': 502,
            'order_number': 'SO-00502',
            'customer_id': 101,
            'status': 'Shipped'
        }

        cancel_req = PortalOrderCancelRequest(reason="Too late")
        with pytest.raises(ValueError, match="Cannot cancel order in 'Shipped' status"):
            order_service.cancel_order(101, order_id=502, cancel_in=cancel_req)
