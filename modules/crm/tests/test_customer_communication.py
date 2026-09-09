"""
Unit and integration tests for CustomerCommunicationService.
Tests communication logging, timeline queries, status updates, delivery receipts,
failure tracking, retries, and customer reminder preferences.
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, List

from modules.crm.models.customer_communication import (
    CustomerCommunicationCreate,
    CustomerCommunicationUpdate,
    CommunicationStatusUpdate,
    CustomerCommunicationTimelineQuery,
    CustomerReminderPreferencesUpdate,
)
from modules.crm.services.customer_communication_service import (
    CustomerCommunicationService,
    parse_datetime_safe,
)


class MockRepository:
    """In-memory mock repository for tests."""

    def __init__(self, items: List[Dict[str, Any]] = None):
        self._items: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1
        if items:
            for item in items:
                self.create(item)

    def get(self, id_val: int) -> Dict[str, Any]:
        return self._items.get(id_val)

    def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        res = list(self._items.values())
        if filters:
            for k, v in filters.items():
                res = [i for i in res if i.get(k) == v]
        return res[offset: offset + limit]

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(data)
        if 'id' not in item or not item['id']:
            item['id'] = self._next_id
            self._next_id += 1
        else:
            if item['id'] >= self._next_id:
                self._next_id = item['id'] + 1
        self._items[item['id']] = item
        return item

    def update(self, id_val: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if id_val not in self._items:
            raise KeyError(f"Item #{id_val} not found")
        self._items[id_val].update(data)
        return self._items[id_val]

    def delete(self, id_val: int) -> bool:
        if id_val in self._items:
            del self._items[id_val]
            return True
        return False


class MockDispatchService:
    """Mock dispatch adapter service for testing retries."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.email_calls = []
        self.whatsapp_calls = []

    def send_email(self, to_email: str, subject: str, html_body: str, **kwargs) -> Dict[str, Any]:
        self.email_calls.append({'to': to_email, 'subject': subject, 'kwargs': kwargs})
        if self.should_succeed:
            return {
                'success': True,
                'channel': 'EMAIL',
                'status': 'SENT',
                'external_message_id': 'mock-resend-retry-id-123',
            }
        return {
            'success': False,
            'channel': 'EMAIL',
            'status': 'FAILED',
            'error_message': 'SMTP connection timeout',
        }

    def send_whatsapp(self, to_phone: str, message_text: str = None, **kwargs) -> Dict[str, Any]:
        self.whatsapp_calls.append({'to': to_phone, 'text': message_text, 'kwargs': kwargs})
        if self.should_succeed:
            return {
                'success': True,
                'channel': 'WHATSAPP',
                'status': 'SENT',
                'external_message_id': 'wamid.HBgLMOCKRETRY123=',
            }
        return {
            'success': False,
            'channel': 'WHATSAPP',
            'status': 'FAILED',
            'error_message': 'Meta Graph API Error 131026: Message undeliverable',
        }


@pytest.fixture
def mock_customer_repo():
    return MockRepository([
        {
            'id': 101,
            'name': 'Bistro Roma Italian Restaurant',
            'email': 'accounts@bistroroma.com',
            'phone': '+15551234567',
            'reminder_email': 'cfo@bistroroma.com',
            'reminder_phone': '+15559876543',
            'is_vip': False,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'EMAIL',
            'balance': 4500.00,
            'is_active': True,
            'business_id': 1,
        },
        {
            'id': 102,
            'name': 'Trattoria Bella',
            'email': 'billing@trattoriabella.com',
            'phone': '+15552345678',
            'is_vip': True,
            'exclude_from_reminders': False,
            'preferred_reminder_channel': 'WHATSAPP',
            'balance': 8900.00,
            'is_active': True,
            'business_id': 1,
        },
    ])


@pytest.fixture
def mock_rule_repo():
    return MockRepository([
        {
            'id': 1,
            'rule_code': 'RULE-30D',
            'rule_name': '30-Day Overdue Notice',
            'trigger_type': 'AGING_THRESHOLD',
            'threshold_days': 30,
            'is_active': True,
        },
    ])


@pytest.fixture
def comm_service(mock_customer_repo, mock_rule_repo):
    comm_repo = MockRepository()
    dispatch_mock = MockDispatchService(should_succeed=True)
    return CustomerCommunicationService(
        communication_repo=comm_repo,
        customer_repo=mock_customer_repo,
        rule_repo=mock_rule_repo,
        dispatch_service=dispatch_mock,
    )


class TestCustomerCommunicationRecording:
    """Tests recording new communication events."""

    def test_record_communication_success(self, comm_service):
        payload = CustomerCommunicationCreate(
            customer_id=101,
            rule_id=1,
            channel='EMAIL',
            communication_type='REMINDER',
            recipient_address='cfo@bistroroma.com',
            recipient_name='Bistro Roma Italian Restaurant',
            subject='Urgent: Outstanding Balance Reminder',
            message_body='Your account balance is $4,500.00.',
            status='SENT',
            invoice_count=3,
            total_balance=4500.00,
            overdue_amount=4500.00,
            payment_link='https://app.novaerp.com/pay/101',
        )

        record = comm_service.record_communication(payload)
        assert record['id'] is not None
        assert record['customer_id'] == 101
        assert record['customer_name'] == 'Bistro Roma Italian Restaurant'
        assert record['rule_name'] == '30-Day Overdue Notice'
        assert record['tracking_number'].startswith('TRK-')
        assert record['status'] == 'SENT'
        assert record['total_balance'] == 4500.00
        assert record['metadata']['retries'] == 0

    def test_record_communication_with_dict(self, comm_service):
        record = comm_service.record_communication({
            'customer_id': 101,
            'channel': 'WHATSAPP',
            'message_body': 'Hello Bistro Roma, please check your weekly statement.',
        })
        assert record['id'] is not None
        assert record['channel'] == 'WHATSAPP'
        assert record['recipient_address'] == '+15559876543'  # customer reminder_phone
        assert record['recipient_name'] == 'Bistro Roma Italian Restaurant'
        assert record['total_balance'] == 4500.00

    def test_record_communication_nonexistent_customer(self, comm_service):
        with pytest.raises(ValueError, match="Customer #999 does not exist"):
            comm_service.record_communication({'customer_id': 999, 'message_body': 'Test'})


class TestDeliveryStatusTracking:
    """Tests delivery, read receipt, and error status updates."""

    def test_update_status_by_id_delivered_and_read(self, comm_service):
        rec = comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'message_body': 'Test notice',
            'status': 'SENT',
        })
        comm_id = rec['id']

        # Update to DELIVERED
        now_dt = datetime.now(timezone.utc)
        upd1 = comm_service.update_status(comm_id, {'status': 'DELIVERED', 'delivery_timestamp': now_dt})
        assert upd1['status'] == 'DELIVERED'
        assert upd1['delivery_timestamp'] is not None

        # Update to READ
        upd2 = comm_service.update_status(comm_id, {'status': 'READ', 'read_timestamp': now_dt + timedelta(minutes=5)})
        assert upd2['status'] == 'READ'
        assert upd2['read_timestamp'] is not None

    def test_update_status_by_tracking_number(self, comm_service):
        rec = comm_service.record_communication({
            'customer_id': 101,
            'tracking_number': 'TRK-EMA-20260908-101-CUSTOM01',
            'channel': 'EMAIL',
            'message_body': 'Test',
        })
        upd = comm_service.update_status('TRK-EMA-20260908-101-CUSTOM01', {'status': 'DELIVERED'})
        assert upd['status'] == 'DELIVERED'
        assert upd['tracking_number'] == 'TRK-EMA-20260908-101-CUSTOM01'

    def test_update_status_by_external_id(self, comm_service):
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'WHATSAPP',
            'external_message_id': 'wamid.HBgLTESTMESSAGE123=',
            'message_body': 'WhatsApp reminder',
            'status': 'SENT',
        })

        upd = comm_service.update_status_by_external_id(
            external_message_id='wamid.HBgLTESTMESSAGE123=',
            status='READ',
            timestamp=datetime.now(timezone.utc),
        )
        assert upd is not None
        assert upd['status'] == 'READ'
        assert upd['external_message_id'] == 'wamid.HBgLTESTMESSAGE123='

    def test_update_status_not_found(self, comm_service):
        with pytest.raises(ValueError, match="not found"):
            comm_service.update_status(9999, {'status': 'DELIVERED'})


class TestCustomerTimelineQueries:
    """Tests timeline queries, filtering, and summary statistics."""

    @pytest.fixture(autouse=True)
    def seed_timeline_data(self, comm_service):
        # Seed 4 communication records for customer 101
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'communication_type': 'REMINDER',
            'message_body': 'Reminder 1',
            'status': 'READ',
            'created_at': datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        })
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'WHATSAPP',
            'communication_type': 'REMINDER',
            'message_body': 'Reminder 2',
            'status': 'DELIVERED',
            'created_at': datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
        })
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'communication_type': 'STATEMENT',
            'message_body': 'Statement 1',
            'status': 'SENT',
            'created_at': datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        })
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'communication_type': 'REMINDER',
            'message_body': 'Reminder 3',
            'status': 'FAILED',
            'error_message': 'Mailbox full',
            'created_at': datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        })
        # Seed 1 record for customer 102
        comm_service.record_communication({
            'customer_id': 102,
            'channel': 'WHATSAPP',
            'communication_type': 'REMINDER',
            'message_body': 'Customer 102 message',
            'status': 'DELIVERED',
        })

    def test_get_customer_timeline_all_items_and_stats(self, comm_service):
        timeline = comm_service.get_customer_timeline(customer_id=101)
        assert timeline['customer_id'] == 101
        assert timeline['total'] == 4
        assert len(timeline['items']) == 4

        summary = timeline['summary']
        assert summary['total_communications'] == 4
        assert summary['total_sent'] == 3  # READ + DELIVERED + SENT
        assert summary['total_delivered'] == 2  # READ + DELIVERED
        assert summary['total_read'] == 1  # READ
        assert summary['total_failed'] == 1  # FAILED
        assert summary['delivery_rate_percent'] == round(2 / 3 * 100.0, 1)

    def test_get_customer_timeline_channel_filter(self, comm_service):
        timeline = comm_service.get_customer_timeline(customer_id=101, channel='WHATSAPP')
        assert timeline['total'] == 1
        assert timeline['items'][0]['channel'] == 'WHATSAPP'

    def test_get_customer_timeline_status_filter(self, comm_service):
        timeline = comm_service.get_customer_timeline(customer_id=101, status='FAILED')
        assert timeline['total'] == 1
        assert timeline['items'][0]['status'] == 'FAILED'

    def test_get_customer_timeline_date_range_filter(self, comm_service):
        timeline = comm_service.get_customer_timeline(
            customer_id=101,
            start_date='2026-08-10',
            end_date='2026-08-22',
        )
        assert timeline['total'] == 2
        types = [i['communication_type'] for i in timeline['items']]
        assert 'REMINDER' in types
        assert 'STATEMENT' in types

    def test_list_timeline_query_pagination(self, comm_service):
        query = CustomerCommunicationTimelineQuery(customer_id=101, limit=2, offset=0)
        res = comm_service.list_timeline(query=query)
        assert res['total'] == 4
        assert len(res['items']) == 2
        assert res['limit'] == 2
        assert res['offset'] == 0


class TestFailureLoggingAndRetryEngine:
    """Tests delivery failure recording and retry mechanism."""

    def test_log_delivery_failure(self, comm_service):
        rec = comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'message_body': 'Failed message test',
            'status': 'PENDING',
        })
        comm_id = rec['id']

        res = comm_service.log_delivery_failure(
            communication_id=comm_id,
            error_message='550 User unknown',
            error_code='ERR_550',
        )
        assert res['status'] == 'FAILED'
        assert res['error_message'] == '550 User unknown'
        assert len(res['metadata']['failure_history']) == 1
        assert res['metadata']['failure_history'][0]['error_code'] == 'ERR_550'

    def test_retry_communication_success(self, comm_service):
        rec = comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'subject': 'Retry Subject',
            'message_body': 'Retry message body',
            'status': 'FAILED',
            'error_message': 'Previous failure',
        })
        comm_id = rec['id']

        retry_res = comm_service.retry_communication(comm_id)
        assert retry_res['success'] is True
        assert retry_res['retry_count'] == 1
        assert retry_res['status'] == 'SENT'
        assert retry_res['external_message_id'] == 'mock-resend-retry-id-123'

        updated = comm_service.get_communication(comm_id)
        assert updated['status'] == 'SENT'
        assert updated['metadata']['retries'] == 1
        assert len(updated['metadata']['retry_history']) == 1

    def test_retry_communication_max_retries_exceeded(self, comm_service):
        rec = comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'message_body': 'Test',
            'status': 'FAILED',
            'metadata': {'retries': 3, 'retry_history': []},
        })
        comm_id = rec['id']

        retry_res = comm_service.retry_communication(comm_id, max_retries=3)
        assert retry_res['success'] is False
        assert "Max retry limit" in retry_res['reason']

        # Overriding with force=True should attempt retry
        forced_res = comm_service.retry_communication(comm_id, max_retries=3, force=True)
        assert forced_res['success'] is True
        assert forced_res['retry_count'] == 4

    def test_get_failed_and_retry_all(self, comm_service):
        # Create 2 failed communications
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'EMAIL',
            'message_body': 'Fail 1',
            'status': 'FAILED',
        })
        comm_service.record_communication({
            'customer_id': 101,
            'channel': 'WHATSAPP',
            'message_body': 'Fail 2',
            'status': 'FAILED',
        })

        failed = comm_service.get_failed_communications(customer_id=101)
        assert len(failed) == 2

        batch_retry = comm_service.retry_all_failed(customer_id=101)
        assert batch_retry['attempted'] == 2
        assert batch_retry['succeeded'] == 2
        assert batch_retry['failed'] == 0


class TestCustomerReminderPreferences:
    """Tests fetching and updating customer reminder and VIP preferences."""

    def test_get_customer_preferences(self, comm_service):
        prefs = comm_service.get_customer_preferences(101)
        assert prefs['customer_id'] == 101
        assert prefs['customer_name'] == 'Bistro Roma Italian Restaurant'
        assert prefs['is_vip'] is False
        assert prefs['exclude_from_reminders'] is False
        assert prefs['preferred_reminder_channel'] == 'EMAIL'
        assert prefs['reminder_email'] == 'cfo@bistroroma.com'
        assert prefs['reminder_phone'] == '+15559876543'

    def test_update_customer_preferences(self, comm_service):
        update_data = CustomerReminderPreferencesUpdate(
            is_vip=True,
            exclude_from_reminders=True,
            preferred_reminder_channel='WHATSAPP',
            reminder_phone='+15550001111',
            reminder_email='vip@bistroroma.com',
        )

        updated_prefs = comm_service.update_customer_preferences(101, update_data)
        assert updated_prefs['is_vip'] is True
        assert updated_prefs['exclude_from_reminders'] is True
        assert updated_prefs['preferred_reminder_channel'] == 'WHATSAPP'
        assert updated_prefs['reminder_phone'] == '+15550001111'
        assert updated_prefs['reminder_email'] == 'vip@bistroroma.com'

    def test_preferences_customer_not_found(self, comm_service):
        with pytest.raises(ValueError, match="does not exist"):
            comm_service.get_customer_preferences(9999)
