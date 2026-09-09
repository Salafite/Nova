import pytest
from datetime import datetime, date, timezone
from modules.accounting.models import (
    ARReminderTemplateCreate,
    ARReminderTemplateUpdate,
    ARReminderTemplateResponse,
    ARReminderRuleCreate,
    ARReminderRuleUpdate,
    ARReminderRuleResponse,
    ReminderDispatchPayload,
    StatementDispatchPayload,
    BatchReminderRunRequest,
    BatchReminderResult,
    AR_REMINDER_RULE_REPO,
    AR_REMINDER_TEMPLATE_REPO,
)
from modules.crm.models import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerCommunicationCreate,
    CustomerCommunicationUpdate,
    CustomerCommunicationResponse,
    CommunicationStatusUpdate,
    CustomerCommunicationTimelineQuery,
    CustomerReminderPreferencesUpdate,
    CustomerReminderPreferencesResponse,
    CUSTOMER_COMMUNICATION_REPO,
)


class TestARReminderTemplateModels:
    """Test suite for AR reminder template Pydantic models."""

    def test_create_email_template(self):
        tmpl = ARReminderTemplateCreate(
            template_code='TMPL-OVERDUE-30D',
            template_name='30-Day Overdue Email Reminder',
            channel='EMAIL',
            subject_template='Payment Reminder: Account {{customer_name}} Overdue Balance',
            body_template='Dear {{customer_name}}, you have {{invoice_count}} overdue invoice(s) totaling {{overdue_amount}}.',
            language='en',
            is_default=True,
            business_id=1,
        )
        assert tmpl.template_code == 'TMPL-OVERDUE-30D'
        assert tmpl.channel == 'EMAIL'
        assert tmpl.is_default is True
        assert tmpl.business_id == 1

    def test_create_whatsapp_template(self):
        tmpl = ARReminderTemplateCreate(
            template_code='TMPL-WA-60D',
            template_name='60-Day Overdue WhatsApp Alert',
            channel='WHATSAPP',
            body_template='Hello {{1}}, your balance of {{2}} is 60 days overdue.',
            whatsapp_template_name='ar_overdue_notice_60d',
            whatsapp_namespace='nova_erp_notifications',
            language='en',
            business_id=2,
        )
        assert tmpl.channel == 'WHATSAPP'
        assert tmpl.whatsapp_template_name == 'ar_overdue_notice_60d'
        assert tmpl.whatsapp_namespace == 'nova_erp_notifications'
        assert tmpl.business_id == 2

    def test_update_template(self):
        update_data = ARReminderTemplateUpdate(
            template_name='Updated Template Title',
            is_active=False,
        )
        assert update_data.template_name == 'Updated Template Title'
        assert update_data.is_active is False
        assert update_data.channel is None

    def test_response_template_serialization(self):
        resp = ARReminderTemplateResponse(
            id=10,
            template_code='TMPL-WEEKLY-STMT',
            template_name='Weekly Account Statement',
            channel='EMAIL',
            subject_template='Weekly Statement - {{customer_name}}',
            body_template='Please find attached your weekly account statement.',
            language='en',
            is_default=False,
            is_active=True,
            business_id=1,
            created_at=datetime.now(timezone.utc),
            update_number=1,
        )
        assert resp.id == 10
        assert resp.template_code == 'TMPL-WEEKLY-STMT'
        dump = resp.model_dump()
        assert dump['id'] == 10
        assert dump['business_id'] == 1


class TestARReminderRuleModels:
    """Test suite for AR reminder rule Pydantic models."""

    def test_create_aging_threshold_rule(self):
        rule = ARReminderRuleCreate(
            rule_name='30-Day Overdue Reminder Rule',
            rule_code='RULE-OVERDUE-30D',
            trigger_type='AGING_THRESHOLD',
            threshold_days=30,
            frequency='ONCE',
            channel='ALL',
            template_id=1,
            attach_statement_pdf=True,
            include_payment_link=True,
            min_overdue_balance=100.0,
            exclude_vip=True,
            exclude_credit_hold=False,
            business_id=1,
        )
        assert rule.rule_name == '30-Day Overdue Reminder Rule'
        assert rule.threshold_days == 30
        assert rule.exclude_vip is True
        assert rule.attach_statement_pdf is True
        assert rule.min_overdue_balance == 100.0

    def test_create_weekly_statement_rule(self):
        rule = ARReminderRuleCreate(
            rule_name='Friday Weekly Statement Schedule',
            rule_code='RULE-STMT-WEEKLY-FRI',
            trigger_type='STATEMENT_SCHEDULE',
            threshold_days=0,
            frequency='WEEKLY',
            schedule_day='FRIDAY',
            schedule_time='09:00:00',
            channel='EMAIL',
            attach_statement_pdf=True,
            business_id=1,
        )
        assert rule.frequency == 'WEEKLY'
        assert rule.schedule_day == 'FRIDAY'
        assert rule.schedule_time == '09:00:00'

    def test_update_rule(self):
        update = ARReminderRuleUpdate(
            threshold_days=60,
            min_overdue_balance=250.0,
            exclude_vip=False,
        )
        assert update.threshold_days == 60
        assert update.min_overdue_balance == 250.0
        assert update.exclude_vip is False
        assert update.rule_name is None

    def test_response_rule_serialization(self):
        resp = ARReminderRuleResponse(
            id=5,
            rule_name='90-Day Critical Overdue',
            rule_code='RULE-OVERDUE-90D',
            trigger_type='AGING_THRESHOLD',
            threshold_days=90,
            frequency='DAILY',
            channel='WHATSAPP',
            attach_statement_pdf=True,
            include_payment_link=True,
            min_overdue_balance=500.0,
            exclude_vip=True,
            exclude_credit_hold=True,
            is_active=True,
            business_id=1,
            template_name='Critical Overdue Template',
            created_at=datetime.now(timezone.utc),
            update_number=1,
        )
        assert resp.id == 5
        assert resp.threshold_days == 90
        assert resp.template_name == 'Critical Overdue Template'
        dump = resp.model_dump()
        assert dump['id'] == 5
        assert dump['threshold_days'] == 90


class TestCustomerCommunicationModels:
    """Test suite for customer communication audit log models."""

    def test_create_communication_log(self):
        comm = CustomerCommunicationCreate(
            tracking_number='COMM-2026-0001',
            customer_id=101,
            rule_id=5,
            template_id=2,
            channel='EMAIL',
            communication_type='REMINDER',
            recipient_address='ap@restaurant.com',
            recipient_name='Chef Mario',
            subject='Overdue Balance Notice',
            message_body='Your account has overdue invoices.',
            status='SENT',
            statement_pdf_path='/storage/statements/stmt_101.pdf',
            statement_pdf_size=45210,
            invoice_count=3,
            total_balance=4500.0,
            overdue_amount=3200.0,
            payment_link='https://pay.novaerp.com/checkout/c101',
            is_automated=True,
            business_id=1,
        )
        assert comm.tracking_number == 'COMM-2026-0001'
        assert comm.customer_id == 101
        assert comm.total_balance == 4500.0
        assert comm.overdue_amount == 3200.0
        assert comm.is_automated is True

    def test_update_communication_log_delivery_status(self):
        update = CustomerCommunicationUpdate(
            status='DELIVERED',
            delivery_timestamp=datetime.now(timezone.utc),
            external_message_id='msg_sendgrid_987654321',
        )
        assert update.status == 'DELIVERED'
        assert update.delivery_timestamp is not None
        assert update.external_message_id == 'msg_sendgrid_987654321'

    def test_communication_status_update_webhook_model(self):
        status_update = CommunicationStatusUpdate(
            status='READ',
            read_timestamp=datetime.now(timezone.utc),
            external_message_id='wa_msg_12345',
            metadata={'raw_event': 'read_receipt', 'provider': 'twilio'},
        )
        assert status_update.status == 'READ'
        assert status_update.metadata['provider'] == 'twilio'

    def test_timeline_query_model(self):
        query = CustomerCommunicationTimelineQuery(
            customer_id=101,
            channel='WHATSAPP',
            status='DELIVERED',
            limit=25,
            offset=0,
        )
        assert query.customer_id == 101
        assert query.channel == 'WHATSAPP'
        assert query.limit == 25


class TestCustomerReminderPreferencesModels:
    """Test suite for VIP and reminder preference configuration."""

    def test_customer_reminder_preferences_update(self):
        pref = CustomerReminderPreferencesUpdate(
            is_vip=True,
            exclude_from_reminders=False,
            preferred_reminder_channel='WHATSAPP',
            reminder_phone='+15551234567',
            reminder_email='accounts@gourmet.com',
        )
        assert pref.is_vip is True
        assert pref.preferred_reminder_channel == 'WHATSAPP'
        assert pref.reminder_phone == '+15551234567'

    def test_customer_reminder_preferences_response(self):
        resp = CustomerReminderPreferencesResponse(
            customer_id=55,
            customer_name='Gourmet Bistro',
            is_vip=True,
            exclude_from_reminders=True,
            preferred_reminder_channel='BOTH',
            reminder_phone='+15559876543',
            reminder_email='billing@bistro.com',
            last_reminder_sent_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            business_id=1,
        )
        assert resp.customer_id == 55
        assert resp.is_vip is True
        assert resp.exclude_from_reminders is True
        assert resp.business_id == 1

    def test_extended_customer_crud_models(self):
        cust = CustomerCreate(
            name='Elite Restaurant',
            is_vip=True,
            exclude_from_reminders=False,
            preferred_reminder_channel='EMAIL',
            reminder_email='billing@elite.com',
            reminder_phone='+15559990000',
            business_id=1,
        )
        assert cust.is_vip is True
        assert cust.exclude_from_reminders is False
        assert cust.preferred_reminder_channel == 'EMAIL'
        assert cust.reminder_email == 'billing@elite.com'

        resp = CustomerResponse(
            id=12,
            name='Elite Restaurant',
            is_vip=True,
            exclude_from_reminders=False,
            preferred_reminder_channel='EMAIL',
            reminder_email='billing@elite.com',
            business_id=1,
            update_number=1,
        )
        assert resp.is_vip is True
        assert resp.id == 12


class TestDispatchPayloadsAndBatchModels:
    """Test suite for dispatch payloads and batch reminder engine models."""

    def test_reminder_dispatch_payload(self):
        payload = ReminderDispatchPayload(
            customer_id=42,
            rule_id=1,
            template_id=2,
            channel='WHATSAPP',
            custom_message='Special note on overdue invoice.',
            attach_statement_pdf=True,
            include_payment_link=True,
            recipient_phone='+15554443322',
            business_id=1,
        )
        assert payload.customer_id == 42
        assert payload.channel == 'WHATSAPP'
        assert payload.attach_statement_pdf is True
        assert payload.business_id == 1

    def test_statement_dispatch_payload(self):
        payload = StatementDispatchPayload(
            customer_id=42,
            channel='EMAIL',
            recipient_email='ap@distro.com',
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            business_id=1,
        )
        assert payload.customer_id == 42
        assert payload.start_date == date(2026, 8, 1)
        assert payload.end_date == date(2026, 8, 31)

    def test_batch_run_request_and_result(self):
        req = BatchReminderRunRequest(
            rule_id=1,
            customer_ids=[10, 20, 30],
            dry_run=True,
            force=False,
            business_id=1,
        )
        assert req.dry_run is True
        assert req.customer_ids == [10, 20, 30]

        result = BatchReminderResult(
            total_evaluated=10,
            total_eligible=8,
            total_dispatched=7,
            total_skipped_vip=1,
            total_skipped_excluded=1,
            total_failed=1,
            dispatched_communications=[{'customer_id': 10, 'channel': 'EMAIL'}],
            errors=[{'customer_id': 30, 'error': 'Invalid email address'}],
        )
        assert result.total_evaluated == 10
        assert result.total_dispatched == 7
        assert result.total_skipped_vip == 1
        assert len(result.errors) == 1


class TestReminderRepositories:
    """Test suite verifying CrudRepositories for reminder rules, templates, and communications."""

    def test_ar_reminder_rule_repo_columns(self):
        assert 'rule_name' in AR_REMINDER_RULE_REPO.business_columns
        assert 'rule_code' in AR_REMINDER_RULE_REPO.business_columns
        assert 'trigger_type' in AR_REMINDER_RULE_REPO.business_columns
        assert 'threshold_days' in AR_REMINDER_RULE_REPO.business_columns
        assert 'exclude_vip' in AR_REMINDER_RULE_REPO.business_columns
        assert 'attach_statement_pdf' in AR_REMINDER_RULE_REPO.business_columns

    def test_ar_reminder_template_repo_columns(self):
        assert 'template_code' in AR_REMINDER_TEMPLATE_REPO.business_columns
        assert 'template_name' in AR_REMINDER_TEMPLATE_REPO.business_columns
        assert 'channel' in AR_REMINDER_TEMPLATE_REPO.business_columns
        assert 'body_template' in AR_REMINDER_TEMPLATE_REPO.business_columns
        assert 'whatsapp_template_name' in AR_REMINDER_TEMPLATE_REPO.business_columns

    def test_customer_communication_repo_columns(self):
        assert 'tracking_number' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'customer_id' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'status' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'channel' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'statement_pdf_path' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'total_balance' in CUSTOMER_COMMUNICATION_REPO.business_columns
        assert 'overdue_amount' in CUSTOMER_COMMUNICATION_REPO.business_columns
