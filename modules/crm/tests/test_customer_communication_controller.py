"""
Unit and integration tests for Customer Controller (T0010I) Communication Timeline,
Reminder Preferences, and On-Demand Dispatch Endpoints.

Tests endpoints:
- GET /api/T0010I/{id}/communications
- GET /api/T0010I/{id}/reminder-preferences
- PUT /api/T0010I/{id}/reminder-preferences
- PATCH /api/T0010I/{id}/reminder-preferences
- POST /api/T0010I/{id}/reminders/dispatch (and /api/T0010I/{id}/dispatch-reminder)
- POST /api/T0010I/{id}/statements/dispatch (and /api/T0010I/{id}/dispatch-statement)
- POST /api/T0010I/{id}/communications/{comm_id}/retry
- POST /api/T0010I/{id}/communications/retry-failed
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.crm.controllers import T0010I
from modules.crm.controllers.T0010I import router
from modules.crm.services.customer_communication_service import CustomerCommunicationService
from modules.accounting.services.ar_reminder_service import ARReminderService
from packages.auth.deps import get_current_user


class InMemoryRepo:
    """In-memory repository mock for T0010 customer testing."""

    def __init__(self, items=None):
        self.items = {item['id']: dict(item) for item in (items or [])}
        self._next_id = max(self.items.keys(), default=0) + 1

    def get(self, id_val, **kwargs):
        item = self.items.get(id_val)
        return dict(item) if item else None

    def get_unscoped(self, id_val, **kwargs):
        item = self.items.get(id_val)
        return dict(item) if item else None

    def list(self, filters=None, limit=1000, order_by=None, offset=0, **kwargs):
        results = list(self.items.values())
        if filters:
            for k, v in filters.items():
                results = [r for r in results if r.get(k) == v]
        return [dict(r) for r in results[offset:offset + limit]]

    def create(self, payload, **kwargs):
        new_id = payload.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        record = dict(payload, id=new_id)
        self.items[new_id] = record
        return dict(record)

    def update(self, id_val, payload, **kwargs):
        if id_val not in self.items:
            return None
        self.items[id_val].update(payload)
        return dict(self.items[id_val])

    def delete(self, id_val, **kwargs):
        return self.items.pop(id_val, None) is not None


@pytest.fixture
def test_data():
    customers = [
        {
            'id': 1,
            'name': 'Bistro 42',
            'phone': '+15551234567',
            'email': 'billing@bistro42.com',
            'credit_limit': 10000.0,
            'balance': 3500.0,
            'is_vip': False,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'EMAIL',
            'reminder_phone': '+15551234567',
            'reminder_email': 'billing@bistro42.com',
            'business_id': 1,
            'is_active': True,
        },
        {
            'id': 2,
            'name': 'Grand Hotel and Spa',
            'phone': '+15559876543',
            'email': 'finance@grandhotel.com',
            'credit_limit': 50000.0,
            'balance': 12000.0,
            'is_vip': True,
            'exclude_from_reminders': True,
            'preferred_reminder_channel': 'WHATSAPP',
            'reminder_phone': '+15559876543',
            'reminder_email': 'vip@grandhotel.com',
            'business_id': 1,
            'is_active': True,
        },
    ]
    return {'customers': customers}


@pytest.fixture
def mock_comm_service():
    svc = MagicMock(spec=CustomerCommunicationService)
    return svc


@pytest.fixture
def mock_ar_service():
    svc = MagicMock(spec=ARReminderService)
    return svc


@pytest.fixture
def app_client(test_data, mock_comm_service, mock_ar_service):
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_current_user] = lambda: {
        'id': 99,
        'username': 'testaccountant',
        'role': 'Admin',
        'permissions': ['*'],
        'business_id': 1,
    }

    mock_repo = InMemoryRepo(test_data['customers'])
    orig_repo = T0010I.repo
    orig_comm = T0010I.customer_comm_service
    orig_ar = T0010I.ar_rem_service

    T0010I.repo = mock_repo
    T0010I.customer_comm_service = mock_comm_service
    T0010I.ar_rem_service = mock_ar_service

    yield TestClient(app)

    T0010I.repo = orig_repo
    T0010I.customer_comm_service = orig_comm
    T0010I.ar_rem_service = orig_ar
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# 1. Timeline Endpoints Tests
# ----------------------------------------------------------------------
class TestCustomerCommunicationsTimelineEndpoints:
    def test_get_customer_communications_success(self, app_client, mock_comm_service):
        mock_comm_service.get_customer_timeline.return_value = {
            'customer_id': 1,
            'customer_name': 'Bistro 42',
            'total': 2,
            'limit': 50,
            'offset': 0,
            'items': [
                {
                    'id': 101,
                    'tracking_number': 'TRK-EMA-20260908-1-ABC1',
                    'customer_id': 1,
                    'channel': 'EMAIL',
                    'communication_type': 'REMINDER',
                    'recipient_address': 'billing@bistro42.com',
                    'subject': 'Payment Reminder - 30 Days Overdue',
                    'status': 'DELIVERED',
                    'delivery_timestamp': '2026-09-08T08:30:00Z',
                    'total_balance': 3500.0,
                    'overdue_amount': 2000.0,
                },
                {
                    'id': 100,
                    'tracking_number': 'TRK-WHA-20260901-1-DEF2',
                    'customer_id': 1,
                    'channel': 'WHATSAPP',
                    'communication_type': 'STATEMENT',
                    'recipient_address': '+15551234567',
                    'status': 'READ',
                    'delivery_timestamp': '2026-09-01T09:00:00Z',
                    'read_timestamp': '2026-09-01T09:05:00Z',
                    'total_balance': 3500.0,
                    'overdue_amount': 0.0,
                },
            ],
            'summary': {
                'total_communications': 2,
                'total_sent': 2,
                'total_delivered': 2,
                'total_read': 1,
                'total_failed': 0,
                'delivery_rate_percent': 100.0,
                'read_rate_percent': 50.0,
            },
        }

        response = app_client.get('/api/T0010I/1/communications?channel=EMAIL&limit=10')
        assert response.status_code == 200
        data = response.json()
        assert data['customer_id'] == 1
        assert data['total'] == 2
        assert len(data['items']) == 2
        assert data['items'][0]['channel'] == 'EMAIL'
        assert data['summary']['delivery_rate_percent'] == 100.0

        mock_comm_service.get_customer_timeline.assert_called_once_with(
            customer_id=1,
            channel='EMAIL',
            status=None,
            communication_type=None,
            start_date=None,
            end_date=None,
            limit=10,
            offset=0,
        )

    def test_get_customer_communications_nonexistent_customer(self, app_client):
        response = app_client.get('/api/T0010I/999/communications')
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()


# ----------------------------------------------------------------------
# 2. Customer Reminder Preferences Tests
# ----------------------------------------------------------------------
class TestCustomerReminderPreferencesEndpoints:
    def test_get_customer_reminder_preferences_success(self, app_client, mock_comm_service):
        mock_comm_service.get_customer_preferences.return_value = {
            'customer_id': 1,
            'customer_name': 'Bistro 42',
            'is_vip': False,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'EMAIL',
            'reminder_phone': '+15551234567',
            'reminder_email': 'billing@bistro42.com',
            'last_reminder_sent_at': None,
            'last_statement_sent_at': None,
            'business_id': 1,
        }

        response = app_client.get('/api/T0010I/1/reminder-preferences')
        assert response.status_code == 200
        data = response.json()
        assert data['customer_id'] == 1
        assert data['is_vip'] is False
        assert data['preferred_reminder_channel'] == 'EMAIL'
        mock_comm_service.get_customer_preferences.assert_called_once_with(1)

    def test_get_reminder_preferences_nonexistent_customer(self, app_client):
        response = app_client.get('/api/T0010I/999/reminder-preferences')
        assert response.status_code == 404

    def test_update_customer_reminder_preferences_put(self, app_client, mock_comm_service):
        mock_comm_service.update_customer_preferences.return_value = {
            'customer_id': 1,
            'customer_name': 'Bistro 42',
            'is_vip': True,
            'exclude_from_reminders': True,
            'preferred_reminder_channel': 'WHATSAPP',
            'reminder_phone': '+15559998888',
            'reminder_email': 'newbilling@bistro42.com',
            'business_id': 1,
        }

        update_payload = {
            'is_vip': True,
            'exclude_from_reminders': True,
            'preferred_reminder_channel': 'WHATSAPP',
            'reminder_phone': '+15559998888',
            'reminder_email': 'newbilling@bistro42.com',
        }

        response = app_client.put('/api/T0010I/1/reminder-preferences', json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data['is_vip'] is True
        assert data['exclude_from_reminders'] is True
        assert data['preferred_reminder_channel'] == 'WHATSAPP'
        assert data['reminder_phone'] == '+15559998888'

    def test_update_customer_reminder_preferences_patch(self, app_client, mock_comm_service):
        mock_comm_service.update_customer_preferences.return_value = {
            'customer_id': 2,
            'customer_name': 'Grand Hotel and Spa',
            'is_vip': False,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'BOTH',
            'reminder_phone': '+15559876543',
            'reminder_email': 'finance@grandhotel.com',
            'business_id': 1,
        }

        response = app_client.patch('/api/T0010I/2/reminder-preferences', json={
            'is_vip': False,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'BOTH',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['is_vip'] is False
        assert data['preferred_reminder_channel'] == 'BOTH'

    def test_update_reminder_preferences_nonexistent_customer(self, app_client):
        response = app_client.put('/api/T0010I/999/reminder-preferences', json={'is_vip': True})
        assert response.status_code == 404


# ----------------------------------------------------------------------
# 3. Manual On-Demand Reminder & Statement Dispatch Tests
# ----------------------------------------------------------------------
class TestCustomerManualDispatchEndpoints:
    def test_dispatch_customer_reminder_success(self, app_client, mock_ar_service):
        mock_ar_service.send_customer_reminder.return_value = {
            'success': True,
            'customer_id': 1,
            'customer_name': 'Bistro 42',
            'tracking_number': 'TRK-EMA-20260908-1-XYZ9',
            'channel': 'EMAIL',
            'recipient': 'billing@bistro42.com',
            'status': 'SENT',
            'total_balance': 3500.0,
            'overdue_amount': 2000.0,
        }

        payload = {
            'channel': 'EMAIL',
            'custom_message': 'Please remit overdue payment as soon as possible.',
            'attach_statement_pdf': True,
            'include_payment_link': True,
        }

        response = app_client.post('/api/T0010I/1/reminders/dispatch', json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['customer_id'] == 1
        assert data['tracking_number'] == 'TRK-EMA-20260908-1-XYZ9'

        mock_ar_service.send_customer_reminder.assert_called_once()
        call_kwargs = mock_ar_service.send_customer_reminder.call_args.kwargs
        assert call_kwargs['customer_id'] == 1
        assert call_kwargs['channel'] == 'EMAIL'
        assert call_kwargs['attach_statement_pdf'] is True

    def test_dispatch_customer_reminder_alias(self, app_client, mock_ar_service):
        mock_ar_service.send_customer_reminder.return_value = {
            'success': True,
            'customer_id': 1,
            'status': 'SENT',
        }

        response = app_client.post('/api/T0010I/1/dispatch-reminder', json={})
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_dispatch_customer_reminder_nonexistent_customer(self, app_client):
        response = app_client.post('/api/T0010I/999/reminders/dispatch', json={})
        assert response.status_code == 404

    def test_dispatch_customer_statement_success(self, app_client, mock_ar_service):
        mock_ar_service.dispatch_customer_statement.return_value = {
            'success': True,
            'customer_id': 1,
            'tracking_number': 'TRK-EMA-20260908-1-STMT1',
            'channel': 'EMAIL',
            'recipient': 'billing@bistro42.com',
            'status': 'SENT',
        }

        payload = {
            'channel': 'EMAIL',
            'custom_message': 'Monthly account statement for August.',
        }

        response = app_client.post('/api/T0010I/1/statements/dispatch', json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['tracking_number'] == 'TRK-EMA-20260908-1-STMT1'

        mock_ar_service.dispatch_customer_statement.assert_called_once()

    def test_dispatch_customer_statement_alias(self, app_client, mock_ar_service):
        mock_ar_service.dispatch_customer_statement.return_value = {
            'success': True,
            'customer_id': 1,
            'status': 'SENT',
        }

        response = app_client.post('/api/T0010I/1/dispatch-statement', json={})
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_dispatch_customer_statement_nonexistent_customer(self, app_client):
        response = app_client.post('/api/T0010I/999/statements/dispatch', json={})
        assert response.status_code == 404


# ----------------------------------------------------------------------
# 4. Retry Endpoints Tests
# ----------------------------------------------------------------------
class TestCustomerCommunicationRetryEndpoints:
    def test_retry_customer_communication_success(self, app_client, mock_comm_service):
        mock_comm_service.get_communication.return_value = {
            'id': 55,
            'customer_id': 1,
            'status': 'FAILED',
            'channel': 'EMAIL',
            'recipient_address': 'billing@bistro42.com',
        }
        mock_comm_service.retry_communication.return_value = {
            'success': True,
            'communication_id': 55,
            'retry_count': 1,
            'status': 'SENT',
        }

        response = app_client.post('/api/T0010I/1/communications/55/retry')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['communication_id'] == 55
        assert data['status'] == 'SENT'
        mock_comm_service.retry_communication.assert_called_once_with(55, custom_recipient=None)

    def test_retry_customer_communication_mismatched_customer(self, app_client, mock_comm_service):
        mock_comm_service.get_communication.return_value = {
            'id': 55,
            'customer_id': 2,
            'status': 'FAILED',
        }

        response = app_client.post('/api/T0010I/1/communications/55/retry')
        assert response.status_code == 404

    def test_retry_all_failed_communications(self, app_client, mock_comm_service):
        mock_comm_service.retry_all_failed.return_value = {
            'attempted': 2,
            'succeeded': 2,
            'failed': 0,
            'results': [
                {'success': True, 'communication_id': 55},
                {'success': True, 'communication_id': 56},
            ],
        }

        response = app_client.post('/api/T0010I/1/communications/retry-failed?max_retries=3')
        assert response.status_code == 200
        data = response.json()
        assert data['attempted'] == 2
        assert data['succeeded'] == 2
        mock_comm_service.retry_all_failed.assert_called_once_with(customer_id=1, max_retries=3)

