import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from modules.sales.controllers import T0012I
from modules.sales.services.sales_service import SalesOrderService
from packages.auth.deps import get_current_user, require_permission


class TestCreditHoldServiceMethods:
    @pytest.fixture
    def mock_service_setup(self):
        order_repo = MagicMock()
        line_repo = MagicMock()
        customer_repo = MagicMock()
        notification_service = MagicMock()
        orders = {}

        def mock_get(id_val, conn=None):
            return dict(orders[id_val]) if id_val in orders else None

        def mock_update(id_val, payload, conn=None):
            if id_val in orders:
                orders[id_val].update(payload)
                return dict(orders[id_val])
            return None

        order_repo.get.side_effect = mock_get
        order_repo.update.side_effect = mock_update

        svc = SalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=customer_repo,
            notification_service=notification_service,
        )
        svc._reserve_order_stock = MagicMock()
        svc._release_order_stock = MagicMock()
        svc._validate_delivery_tolerance_approvals = MagicMock()
        svc._create_invoice_from_order = MagicMock()
        svc._dispatch_ws_broadcast = MagicMock()

        return svc, orders, notification_service

    def test_override_credit_hold_success(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[101] = {
            'id': 101,
            'order_number': 'SO-101',
            'customer_id': 5,
            'sales_rep_id': 12,
            'status': 'Credit Hold',
            'hold_reason': 'Customer credit limit exceeded',
            'grand_total': 5000.0,
        }

        result = svc.override_credit_hold(
            order_id=101,
            user_id=7,
            user_name='fin_mgr',
            reason='Customer pledged wire transfer by Friday',
            target_status='Confirmed',
        )

        assert result['status'] == 'Confirmed'
        assert result['hold_released_by'] == 7
        assert result['hold_release_reason'] == 'Customer pledged wire transfer by Friday'
        assert result.get('hold_released_at') is not None
        svc._reserve_order_stock.assert_called_once()
        assert svc._reserve_order_stock.call_args[0][0] == 101
        # Sales rep notification was created
        notif_svc.create_notification.assert_called_once()
        call_kwargs = notif_svc.create_notification.call_args[1]
        assert call_kwargs['user_id'] == 12
        assert 'Credit Hold Approved' in call_kwargs['title']
        assert 'Customer pledged wire transfer by Friday' in call_kwargs['message']

    def test_override_credit_hold_custom_target_pending(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[102] = {
            'id': 102,
            'order_number': 'SO-102',
            'customer_id': 5,
            'status': 'Credit Hold',
            'hold_reason': 'Overdue invoices',
        }

        result = svc.override_credit_hold(
            order_id=102,
            user_id=7,
            user_name='fin_mgr',
            reason='Allow order review in pending state',
            target_status='Pending',
        )

        assert result['status'] == 'Pending'
        assert result['hold_released_by'] == 7
        assert result['hold_release_reason'] == 'Allow order review in pending state'

    def test_override_credit_hold_not_on_hold_raises_400(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[103] = {
            'id': 103,
            'order_number': 'SO-103',
            'status': 'Draft',
        }

        with pytest.raises(HTTPException) as exc_info:
            svc.override_credit_hold(order_id=103, user_id=1, reason='Override')

        assert exc_info.value.status_code == 400
        assert "expected 'Credit Hold'" in exc_info.value.detail

    def test_override_credit_hold_not_found_raises_value_error(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup

        with pytest.raises(ValueError) as exc_info:
            svc.override_credit_hold(order_id=999, user_id=1, reason='Override')

        assert "Sales order 999 not found" in str(exc_info.value)

    def test_override_credit_hold_invalid_target_status_raises_400(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[104] = {
            'id': 104,
            'order_number': 'SO-104',
            'status': 'Credit Hold',
        }

        with pytest.raises(HTTPException) as exc_info:
            svc.override_credit_hold(order_id=104, target_status='Shipped')

        assert exc_info.value.status_code == 400
        assert "Invalid target status 'Shipped'" in exc_info.value.detail

    def test_reject_credit_hold_success(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[105] = {
            'id': 105,
            'order_number': 'SO-105',
            'customer_id': 8,
            'sales_rep_id': 15,
            'status': 'Credit Hold',
            'hold_reason': 'Delinquent account > 90 days',
        }

        result = svc.reject_credit_hold(
            order_id=105,
            user_id=9,
            user_name='credit_mgr',
            reason='Customer refusal to settle past overdue invoices',
        )

        assert result['status'] == 'Cancelled'
        assert result['hold_released_by'] == 9
        assert 'Rejected: Customer refusal' in result['hold_release_reason']
        assert result.get('hold_released_at') is not None
        # Sales rep notification
        notif_svc.create_notification.assert_called_once()
        call_kwargs = notif_svc.create_notification.call_args[1]
        assert call_kwargs['user_id'] == 15
        assert 'Credit Hold Rejected' in call_kwargs['title']

    def test_reject_credit_hold_not_on_hold_raises_400(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup
        orders[106] = {
            'id': 106,
            'order_number': 'SO-106',
            'status': 'Pending',
        }

        with pytest.raises(HTTPException) as exc_info:
            svc.reject_credit_hold(order_id=106, user_id=1, reason='Reject')

        assert exc_info.value.status_code == 400
        assert "expected 'Credit Hold'" in exc_info.value.detail

    def test_reject_credit_hold_not_found_raises_value_error(self, mock_service_setup):
        svc, orders, notif_svc = mock_service_setup

        with pytest.raises(ValueError) as exc_info:
            svc.reject_credit_hold(order_id=888, user_id=1, reason='Reject')

        assert "Sales order 888 not found" in str(exc_info.value)


class TestCreditHoldControllerEndpoints:
    @pytest.fixture
    def test_app_client(self):
        app = FastAPI()
        current_user = {
            'id': 1,
            'username': 'admin_user',
            'role': 'Admin',
            'permissions': ['*'],
            'business_id': 1,
        }

        app.dependency_overrides[get_current_user] = lambda: current_user
        app.dependency_overrides[require_permission('SALES_VIEW')] = lambda: current_user
        app.include_router(T0012I.router)
        client = TestClient(app)
        return client, current_user

    def test_override_endpoint_authorized_financial_manager(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({
            'id': 50,
            'username': 'fin_controller',
            'role': 'Financial Manager',
            'permissions': ['FINANCE_VIEW', 'SALES_VIEW'],
        })

        mock_order = {
            'id': 201,
            'order_number': 'SO-201',
            'status': 'Credit Hold',
            'hold_reason': 'Credit limit exceeded',
        }
        mock_updated = dict(mock_order, status='Confirmed', hold_released_by=50, hold_release_reason='Approved by CFO')

        with patch.object(T0012I.service, 'get', return_value=mock_order), \
             patch.object(T0012I.service, 'override_credit_hold', return_value=mock_updated) as mock_override, \
             patch('modules.core.repositories.base.CrudRepository.create') as mock_audit:

            resp = client.post(
                '/api/T0012I/201/override-credit-hold',
                json={'reason': 'Approved by CFO', 'target_status': 'Confirmed'}
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data['status'] == 'Confirmed'
            mock_override.assert_called_once_with(
                order_id=201,
                user_id=50,
                user_name='fin_controller',
                reason='Approved by CFO',
                target_status='Confirmed',
            )

    def test_override_endpoint_unauthorized_sales_rep_returns_403(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({
            'id': 30,
            'username': 'salesrep',
            'role': 'Sales Rep',
            'permissions': ['SALES_VIEW'],
        })

        mock_order = {
            'id': 202,
            'order_number': 'SO-202',
            'status': 'Credit Hold',
        }

        with patch.object(T0012I.service, 'get', return_value=mock_order), \
             patch.object(T0012I, 'record_security_event') as mock_sec_event:

            resp = client.post(
                '/api/T0012I/202/override-credit-hold',
                json={'reason': 'Please approve'}
            )

            assert resp.status_code == 403
            assert 'Financial manager authorization required' in resp.json()['detail']
            mock_sec_event.assert_called_once()
            call_kwargs = mock_sec_event.call_args[1]
            assert call_kwargs['action'] == 'UNAUTHORIZED_CREDIT_OVERRIDE'

    def test_override_endpoint_order_not_on_credit_hold_returns_400(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({'role': 'Admin', 'permissions': ['*']})

        mock_order = {
            'id': 203,
            'order_number': 'SO-203',
            'status': 'Draft',
        }

        with patch.object(T0012I.service, 'get', return_value=mock_order):
            resp = client.post(
                '/api/T0012I/203/override-credit-hold',
                json={'reason': 'Approved'}
            )

            assert resp.status_code == 400
            assert "Only orders in 'Credit Hold' status can be overridden" in resp.json()['detail']

    def test_override_endpoint_order_not_found_returns_404(self, test_app_client):
        client, _ = test_app_client

        with patch.object(T0012I.service, 'get', return_value=None):
            resp = client.post(
                '/api/T0012I/999/override-credit-hold',
                json={'reason': 'Approved'}
            )

            assert resp.status_code == 404
            assert resp.json()['detail'] == 'Order not found'

    def test_reject_endpoint_authorized_credit_controller(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({
            'id': 60,
            'username': 'credit_officer',
            'role': 'Credit Controller',
            'permissions': ['SALES_VIEW', 'FINANCE_VIEW'],
        })

        mock_order = {
            'id': 204,
            'order_number': 'SO-204',
            'status': 'Credit Hold',
            'hold_reason': 'High default risk',
        }
        mock_updated = dict(mock_order, status='Cancelled', hold_released_by=60, hold_release_reason='Rejected: High risk')

        with patch.object(T0012I.service, 'get', return_value=mock_order), \
             patch.object(T0012I.service, 'reject_credit_hold', return_value=mock_updated) as mock_reject, \
             patch('modules.core.repositories.base.CrudRepository.create') as mock_audit:

            resp = client.post(
                '/api/T0012I/204/reject-credit-hold',
                json={'reason': 'High credit default risk'}
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data['status'] == 'Cancelled'
            mock_reject.assert_called_once_with(
                order_id=204,
                user_id=60,
                user_name='credit_officer',
                reason='High credit default risk',
            )

    def test_reject_endpoint_unauthorized_sales_rep_returns_403(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({
            'id': 31,
            'username': 'salesrep2',
            'role': 'Sales Rep',
            'permissions': ['SALES_VIEW'],
        })

        mock_order = {
            'id': 205,
            'order_number': 'SO-205',
            'status': 'Credit Hold',
        }

        with patch.object(T0012I.service, 'get', return_value=mock_order), \
             patch.object(T0012I, 'record_security_event') as mock_sec_event:

            resp = client.post(
                '/api/T0012I/205/reject-credit-hold',
                json={'reason': 'Rejecting order'}
            )

            assert resp.status_code == 403
            assert 'Financial manager authorization required' in resp.json()['detail']
            mock_sec_event.assert_called_once()
            call_kwargs = mock_sec_event.call_args[1]
            assert call_kwargs['action'] == 'UNAUTHORIZED_CREDIT_REJECT'

    def test_reject_endpoint_order_not_on_credit_hold_returns_400(self, test_app_client):
        client, current_user = test_app_client
        current_user.update({'role': 'Admin', 'permissions': ['*']})

        mock_order = {
            'id': 206,
            'order_number': 'SO-206',
            'status': 'Pending',
        }

        with patch.object(T0012I.service, 'get', return_value=mock_order):
            resp = client.post(
                '/api/T0012I/206/reject-credit-hold',
                json={'reason': 'Rejecting'}
            )

            assert resp.status_code == 400
            assert "Only orders in 'Credit Hold' status can be rejected" in resp.json()['detail']

    def test_reject_endpoint_order_not_found_returns_404(self, test_app_client):
        client, _ = test_app_client

        with patch.object(T0012I.service, 'get', return_value=None):
            resp = client.post(
                '/api/T0012I/998/reject-credit-hold',
                json={'reason': 'Rejecting'}
            )

            assert resp.status_code == 404
            assert resp.json()['detail'] == 'Order not found'
