import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.auth.jwt import create_access_token
from modules.portal.models.portal import (
    PortalCatalogResponse,
    PortalCatalogItem,
    PortalCatalogCategory,
    PortalAccountSummary,
    PortalOrderResponse,
    PortalOrderLineResponse,
    CutoffValidationResponse,
    OrderValidationResponse,
)


@pytest.fixture
def portal_user():
    return {
        'id': 100,
        'username': 'bistro_buyer',
        'full_name': 'Bistro Buyer',
        'email': 'buyer@bistro.com',
        'role': 'Customer',
        'permissions': None,
        'business_id': 1,
        'customer_id': 50,
    }


@pytest.fixture
def portal_headers(portal_user):
    token = create_access_token(portal_user['id'])
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def non_portal_user():
    return {
        'id': 101,
        'username': 'regular_viewer',
        'full_name': 'Regular Viewer',
        'email': 'viewer@example.com',
        'role': 'Viewer',
        'permissions': ['CRM_VIEW'],
        'business_id': 1,
        'customer_id': None,
    }


@pytest.fixture
def non_portal_headers(non_portal_user):
    token = create_access_token(non_portal_user['id'])
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client():
    return TestClient(app)


class TestPortalCatalogEndpoints:
    def test_get_catalog_authenticated(self, client, portal_headers, portal_user):
        mock_response = PortalCatalogResponse(
            items=[
                PortalCatalogItem(
                    id=1,
                    product_code='FLOUR-01',
                    product_name='Bread Flour',
                    category_name='Grains',
                    base_price=30.0,
                    contracted_price=25.0,
                    is_contracted=True,
                    discount_percent=16.67,
                    stock_qty=50.0,
                    is_in_stock=True,
                )
            ],
            total=1,
            page=1,
            limit=50,
            categories=[
                PortalCatalogCategory(id=1, category_name='Grains', item_count=1)
            ],
            min_order_amount=150.0,
            order_cutoff_time='22:00',
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalPricingService.get_catalog', return_value=mock_response):
            resp = client.get('/api/portal/catalog?search=Flour', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['total'] == 1
            assert len(data['items']) == 1
            assert data['items'][0]['product_name'] == 'Bread Flour'
            assert data['items'][0]['contracted_price'] == 25.0
            assert data['min_order_amount'] == 150.0
            assert data['order_cutoff_time'] == '22:00'

    def test_get_catalog_unauthorized(self, client):
        resp = client.get('/api/portal/catalog')
        assert resp.status_code in (401, 403)

    def test_get_catalog_forbidden_for_user_without_customer(self, client, non_portal_headers, non_portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=non_portal_user):
            resp = client.get('/api/portal/catalog', headers=non_portal_headers)
            assert resp.status_code == 403


class TestPortalAccountSummaryEndpoint:
    def test_get_account_summary(self, client, portal_headers, portal_user):
        mock_summary = PortalAccountSummary(
            customer_id=50,
            customer_name='Bistro Bella',
            group_name='Restaurant Wholesale',
            email='buyer@bistro.com',
            phone='555-9000',
            credit_limit=10000.0,
            current_balance=2500.0,
            available_credit=7500.0,
            min_order_amount=200.0,
            order_cutoff_time='22:00',
            allow_reorders=True,
            open_invoices_count=2,
            total_unpaid_amount=2500.0,
            recent_orders_count=8,
            default_price_list_name='VIP Restaurant Tier',
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalPricingService.get_account_summary', return_value=mock_summary):
            resp = client.get('/api/portal/account/summary', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['customer_id'] == 50
            assert data['customer_name'] == 'Bistro Bella'
            assert data['current_balance'] == 2500.0
            assert data['available_credit'] == 7500.0
            assert data['open_invoices_count'] == 2
            assert data['default_price_list_name'] == 'VIP Restaurant Tier'


class TestPortalCutoffAndValidateEndpoints:
    def test_get_cutoff_status(self, client, portal_headers, portal_user):
        mock_cutoff = CutoffValidationResponse(
            is_past_cutoff=False,
            cutoff_time='22:00',
            current_time='19:30',
            current_timezone='UTC',
            next_delivery_date=date(2026, 8, 24),
            message='Order placed before 22:00 cutoff. Scheduled for next-day delivery on 2026-08-24.',
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.validate_cutoff_time', return_value=mock_cutoff):
            resp = client.get('/api/portal/cutoff-status', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['is_past_cutoff'] is False
            assert data['cutoff_time'] == '22:00'
            assert data['next_delivery_date'] == '2026-08-24'

    def test_validate_order_cart(self, client, portal_headers, portal_user):
        mock_validation = OrderValidationResponse(
            is_valid=True,
            subtotal=250.0,
            min_order_amount=200.0,
            meets_minimum=True,
            cutoff_status=CutoffValidationResponse(
                is_past_cutoff=False,
                cutoff_time='22:00',
                current_time='18:00',
                current_timezone='UTC',
                next_delivery_date=date(2026, 8, 24),
                message='On schedule',
            ),
            errors=[],
            warnings=[],
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.validate_order', return_value=mock_validation):
            payload = [{'product_id': 1, 'qty': 10}]
            resp = client.post('/api/portal/orders/validate', json=payload, headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['is_valid'] is True
            assert data['subtotal'] == 250.0
            assert data['meets_minimum'] is True


class TestPortalOrdersEndpoints:
    def test_create_order_success(self, client, portal_headers, portal_user):
        mock_order = PortalOrderResponse(
            id=501,
            order_number='SO-20260823-00501',
            customer_id=50,
            customer_name='Bistro Bella',
            subtotal=300.0,
            tax=30.0,
            grand_total=330.0,
            status='Confirmed',
            order_date=date(2026, 8, 23),
            requested_delivery_date=date(2026, 8, 24),
            notes='Delivery before 9 AM',
            lines=[
                PortalOrderLineResponse(
                    id=10,
                    sales_order_id=501,
                    product_id=1,
                    product_code='FLOUR-01',
                    product_name='Bread Flour',
                    qty=10.0,
                    unit_price=30.0,
                    line_total=300.0,
                    line_number=1,
                )
            ],
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.create_order', return_value=mock_order):
            payload = {
                'items': [{'product_id': 1, 'qty': 10}],
                'notes': 'Delivery before 9 AM',
                'status': 'Confirmed',
            }
            resp = client.post('/api/portal/orders', json=payload, headers=portal_headers)

            assert resp.status_code == 201
            data = resp.json()
            assert data['id'] == 501
            assert data['order_number'] == 'SO-20260823-00501'
            assert data['status'] == 'Confirmed'
            assert data['grand_total'] == 330.0
            assert len(data['lines']) == 1

    def test_create_order_below_minimum_returns_400(self, client, portal_headers, portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.create_order', side_effect=ValueError("Order subtotal $50.00 is below the minimum required order amount of $200.00.")):
            payload = {
                'items': [{'product_id': 1, 'qty': 1}],
            }
            resp = client.post('/api/portal/orders', json=payload, headers=portal_headers)

            assert resp.status_code == 400
            assert "below the minimum required order amount" in resp.json()['detail']

    def test_list_orders(self, client, portal_headers, portal_user):
        mock_orders = [
            PortalOrderResponse(
                id=501,
                order_number='SO-00501',
                customer_id=50,
                customer_name='Bistro Bella',
                subtotal=300.0,
                tax=0.0,
                grand_total=300.0,
                status='Confirmed',
                order_date=date(2026, 8, 20),
                lines=[],
            )
        ]

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.get_orders', return_value=(mock_orders, 1)):
            resp = client.get('/api/portal/orders?page=1&limit=20', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['total'] == 1
            assert len(data['items']) == 1
            assert data['items'][0]['id'] == 501

    def test_get_order_detail_found(self, client, portal_headers, portal_user):
        mock_order = PortalOrderResponse(
            id=501,
            order_number='SO-00501',
            customer_id=50,
            customer_name='Bistro Bella',
            subtotal=300.0,
            tax=0.0,
            grand_total=300.0,
            status='Confirmed',
            order_date=date(2026, 8, 20),
            lines=[
                PortalOrderLineResponse(
                    id=1,
                    product_id=5,
                    product_name='Sugar 50lb',
                    qty=5.0,
                    unit_price=60.0,
                    line_total=300.0,
                    line_number=1,
                )
            ],
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.get_order_by_id', return_value=mock_order):
            resp = client.get('/api/portal/orders/501', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['id'] == 501
            assert data['order_number'] == 'SO-00501'
            assert len(data['lines']) == 1

    def test_get_order_detail_not_found(self, client, portal_headers, portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.get_order_by_id', return_value=None):
            resp = client.get('/api/portal/orders/999', headers=portal_headers)

            assert resp.status_code == 404
            assert "Order #999 not found" in resp.json()['detail']

    def test_reorder_endpoint(self, client, portal_headers, portal_user):
        mock_new_order = PortalOrderResponse(
            id=502,
            order_number='SO-00502',
            customer_id=50,
            customer_name='Bistro Bella',
            subtotal=300.0,
            tax=0.0,
            grand_total=300.0,
            status='Confirmed',
            order_date=date(2026, 8, 23),
            lines=[],
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.reorder', return_value=mock_new_order):
            resp = client.post('/api/portal/orders/501/reorder', json={}, headers=portal_headers)

            assert resp.status_code == 201
            data = resp.json()
            assert data['id'] == 502
            assert data['order_number'] == 'SO-00502'

    def test_cancel_endpoint(self, client, portal_headers, portal_user):
        mock_cancelled_order = PortalOrderResponse(
            id=501,
            order_number='SO-00501',
            customer_id=50,
            customer_name='Bistro Bella',
            subtotal=300.0,
            tax=0.0,
            grand_total=300.0,
            status='Cancelled',
            order_date=date(2026, 8, 20),
            notes='Cancelled by buyer',
            lines=[],
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_orders_controller.PortalOrderService.cancel_order', return_value=mock_cancelled_order):
            payload = {'reason': 'Changed menu'}
            resp = client.post('/api/portal/orders/501/cancel', json=payload, headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['id'] == 501
            assert data['status'] == 'Cancelled'
