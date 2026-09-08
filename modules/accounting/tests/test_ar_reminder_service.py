"""
Unit and Integration Tests for ARReminderService.

Covers:
- Rule and template management CRUD operations
- Customer eligibility evaluation across aging thresholds (30/60/90 days), weekly statement schedules
- VIP customer exclusion and customer-level reminder opt-out flags
- Channel availability and contact address checks
- On-demand single customer reminder dispatch with statement PDF attachment
- On-demand single customer account statement generation and delivery
- Batch reminder evaluation engine (dry-run mode and live execution)
- Deduplication and tracking timestamp updates (last_reminder_sent_at, last_statement_sent_at)
- Aggregate AR portfolio overdue summary calculations
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from modules.accounting.services.ar_reminder_service import ARReminderService
from modules.accounting.models.reminder import (
    ARReminderRuleCreate,
    ARReminderRuleUpdate,
    ARReminderTemplateCreate,
    ARReminderTemplateUpdate,
    BatchReminderResult,
)


@pytest.fixture
def sample_customer_normal():
    return {
        'id': 101,
        'name': 'Gourmet Bistro LLC',
        'group_name': 'Restaurants',
        'phone': '+15552345678',
        'email': 'ap@gourmetbistro.com',
        'credit_limit': 20000.0,
        'balance': 5400.0,
        'is_vip': False,
        'exclude_from_reminders': False,
        'preferred_reminder_channel': 'EMAIL',
        'reminder_phone': '+15552345678',
        'reminder_email': 'billing@gourmetbistro.com',
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_customer_vip():
    return {
        'id': 102,
        'name': 'Grand Hotel & Resort',
        'group_name': 'Hospitality',
        'phone': '+15558889999',
        'email': 'ap@grandhotel.com',
        'credit_limit': 100000.0,
        'balance': 15000.0,
        'is_vip': True,
        'exclude_from_reminders': False,
        'preferred_reminder_channel': 'BOTH',
        'reminder_phone': '+15558889999',
        'reminder_email': 'ap@grandhotel.com',
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_customer_excluded():
    return {
        'id': 103,
        'name': 'Government Cafeteria',
        'group_name': 'Institutional',
        'phone': '+15551112222',
        'email': 'finance@govcafe.org',
        'credit_limit': 50000.0,
        'balance': 8000.0,
        'is_vip': False,
        'exclude_from_reminders': True,
        'preferred_reminder_channel': 'EMAIL',
        'reminder_phone': None,
        'reminder_email': 'finance@govcafe.org',
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_rule_30d():
    return {
        'id': 1,
        'rule_name': '30-Day Overdue Collection Reminder',
        'rule_code': 'RULE-OVERDUE-30D',
        'trigger_type': 'AGING_THRESHOLD',
        'threshold_days': 30,
        'frequency': 'ONCE',
        'channel': 'EMAIL',
        'template_id': 1,
        'attach_statement_pdf': True,
        'include_payment_link': True,
        'min_overdue_balance': 100.0,
        'exclude_vip': True,
        'exclude_credit_hold': False,
        'customer_group': None,
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_rule_60d():
    return {
        'id': 2,
        'rule_name': '60-Day Critical Overdue Reminder',
        'rule_code': 'RULE-OVERDUE-60D',
        'trigger_type': 'AGING_THRESHOLD',
        'threshold_days': 60,
        'frequency': 'DAILY',
        'channel': 'WHATSAPP',
        'template_id': 2,
        'attach_statement_pdf': True,
        'include_payment_link': True,
        'min_overdue_balance': 500.0,
        'exclude_vip': True,
        'exclude_credit_hold': False,
        'customer_group': None,
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_rule_weekly_stmt():
    return {
        'id': 3,
        'rule_name': 'Friday Account Statement Dispatch',
        'rule_code': 'RULE-STMT-WEEKLY-FRI',
        'trigger_type': 'STATEMENT_SCHEDULE',
        'threshold_days': 0,
        'frequency': 'WEEKLY',
        'schedule_day': 'FRIDAY',
        'channel': 'EMAIL',
        'template_id': 3,
        'attach_statement_pdf': True,
        'include_payment_link': True,
        'min_overdue_balance': 0.0,
        'exclude_vip': False,
        'is_active': True,
        'business_id': 1,
    }


@pytest.fixture
def sample_template_email():
    return {
        'id': 1,
        'template_code': 'TMPL-EMA-30D',
        'template_name': '30-Day Email Template',
        'channel': 'EMAIL',
        'subject_template': 'Payment Reminder: Account {{customer_name}}',
        'body_template': 'Hello {{customer_name}}, your overdue balance is {{overdue_amount}}.',
        'is_default': True,
        'is_active': True,
    }


@pytest.fixture
def sample_invoices_35d_overdue():
    # As of 2026-09-08, an invoice with due date 2026-08-04 is 35 days overdue
    return [
        {
            'id': 1001,
            'invoice_number': 'INV-2026-001',
            'partner_id': 101,
            'issue_date': '2026-07-04',
            'due_date': '2026-08-04',
            'total_amount': 3000.0,
            'paid_amount': 0.0,
            'status': 'Unpaid',
        },
        {
            'id': 1002,
            'invoice_number': 'INV-2026-002',
            'partner_id': 101,
            'issue_date': '2026-08-15',
            'due_date': '2026-09-15',
            'total_amount': 2400.0,
            'paid_amount': 0.0,
            'status': 'Unpaid',
        },
    ]


@pytest.fixture
def mock_service_components(sample_customer_normal, sample_rule_30d, sample_template_email, sample_invoices_35d_overdue):
    rule_repo = MagicMock()
    rule_repo.get.side_effect = lambda rid: sample_rule_30d if rid == 1 else None
    rule_repo.list.return_value = [sample_rule_30d]
    rule_repo.create.side_effect = lambda data: {'id': 99, **data}
    rule_repo.update.side_effect = lambda rid, data: {'id': rid, **data}
    rule_repo.delete.return_value = True

    template_repo = MagicMock()
    template_repo.get.side_effect = lambda tid: sample_template_email if tid == 1 else None
    template_repo.list.return_value = [sample_template_email]
    template_repo.create.side_effect = lambda data: {'id': 88, **data}
    template_repo.update.side_effect = lambda tid, data: {'id': tid, **data}
    template_repo.delete.return_value = True

    customer_repo = MagicMock()
    customer_repo.get.side_effect = lambda cid: sample_customer_normal if cid == 101 else None
    customer_repo.list.return_value = [sample_customer_normal]
    customer_repo.update.return_value = sample_customer_normal

    invoice_repo = MagicMock()
    invoice_repo.list.return_value = sample_invoices_35d_overdue

    comm_repo = MagicMock()
    comm_repo.create.return_value = {'id': 555, 'tracking_number': 'TRK-EMA-101'}

    dispatch_service = MagicMock()
    dispatch_service.dispatch_reminder.return_value = {
        'success': True,
        'customer_id': 101,
        'channels': ['EMAIL'],
        'results': [{'channel': 'EMAIL', 'status': 'SENT'}],
        'rendered_subject': 'Payment Reminder: Account Gourmet Bistro LLC',
        'rendered_body': 'Hello Gourmet Bistro LLC, your overdue balance is $3,000.00.',
        'payment_link': 'https://pay.novaerp.com/portal/pay/customer/101',
        'pdf_generated': True,
        'pdf_size': 12040,
    }

    statement_pdf_service = MagicMock()
    statement_pdf_service.generate_statement_pdf_for_customer.return_value = b'%PDF-1.4 Mock PDF Content %%EOF'

    service = ARReminderService(
        rule_repo=rule_repo,
        template_repo=template_repo,
        customer_repo=customer_repo,
        invoice_repo=invoice_repo,
        communication_repo=comm_repo,
        dispatch_service=dispatch_service,
        statement_pdf_service=statement_pdf_service,
    )

    return {
        'service': service,
        'rule_repo': rule_repo,
        'template_repo': template_repo,
        'customer_repo': customer_repo,
        'invoice_repo': invoice_repo,
        'comm_repo': comm_repo,
        'dispatch_service': dispatch_service,
        'statement_pdf_service': statement_pdf_service,
    }


class TestARReminderRuleAndTemplateManagement:
    """Test suite for CRUD operations on rules and templates."""

    def test_list_and_get_rule(self, mock_service_components, sample_rule_30d):
        svc = mock_service_components['service']
        rules = svc.list_rules(is_active=True)
        assert len(rules) == 1
        assert rules[0]['rule_code'] == 'RULE-OVERDUE-30D'
        assert rules[0]['template_name'] == '30-Day Email Template'

        rule = svc.get_rule(1)
        assert rule is not None
        assert rule['threshold_days'] == 30

    def test_create_and_update_rule(self, mock_service_components):
        svc = mock_service_components['service']
        create_data = ARReminderRuleCreate(
            rule_name='90-Day Legal Escalation',
            trigger_type='AGING_THRESHOLD',
            threshold_days=90,
            channel='ALL',
            min_overdue_balance=1000.0,
        )
        res = svc.create_rule(create_data)
        assert res['id'] == 99
        assert res['rule_name'] == '90-Day Legal Escalation'
        assert res['rule_code'].startswith('RULE-AR-')

        update_res = svc.update_rule(99, ARReminderRuleUpdate(min_overdue_balance=1500.0))
        assert update_res['min_overdue_balance'] == 1500.0

    def test_create_and_list_templates(self, mock_service_components):
        svc = mock_service_components['service']
        tmpl_data = ARReminderTemplateCreate(
            template_name='WhatsApp 30D Alert',
            channel='WHATSAPP',
            body_template='Hello {{customer_name}}, payment is overdue.',
        )
        res = svc.create_template(tmpl_data)
        assert res['id'] == 88
        assert res['template_code'].startswith('TMPL-WH-')

        default_tmpl = svc.get_default_template(channel='EMAIL')
        assert default_tmpl is not None
        assert default_tmpl['channel'] == 'EMAIL'


class TestCustomerEligibilityEvaluation:
    """Test suite for evaluating customer accounts against aging rules."""

    def test_eligible_customer_passing_30d_threshold(self, mock_service_components, sample_customer_normal, sample_rule_30d):
        svc = mock_service_components['service']
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_normal,
            rule=sample_rule_30d,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is True
        assert eval_res['reason'] == 'ELIGIBLE'
        assert eval_res['overdue_amount'] == 3000.0
        assert eval_res['total_balance'] == 5400.0
        assert eval_res['max_days_overdue'] >= 30
        assert eval_res['target_channel'] == 'EMAIL'

    def test_skip_vip_customer_when_rule_excludes_vip(self, mock_service_components, sample_customer_vip, sample_rule_30d):
        svc = mock_service_components['service']
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_vip,
            rule=sample_rule_30d,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is False
        assert eval_res['reason'] == 'VIP_EXCLUDED'

    def test_allow_vip_customer_when_rule_does_not_exclude_vip(self, mock_service_components, sample_customer_vip, sample_rule_30d):
        svc = mock_service_components['service']
        rule_vip_allowed = dict(sample_rule_30d, exclude_vip=False)
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_vip,
            rule=rule_vip_allowed,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is True
        assert eval_res['reason'] == 'ELIGIBLE'

    def test_skip_customer_with_reminder_opt_out(self, mock_service_components, sample_customer_excluded, sample_rule_30d):
        svc = mock_service_components['service']
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_excluded,
            rule=sample_rule_30d,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is False
        assert eval_res['reason'] == 'EXCLUDED_FROM_REMINDERS'

    def test_skip_customer_below_min_balance(self, mock_service_components, sample_customer_normal, sample_rule_30d):
        svc = mock_service_components['service']
        rule_high_min = dict(sample_rule_30d, min_overdue_balance=10000.0)
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_normal,
            rule=rule_high_min,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is False
        assert eval_res['reason'] == 'BELOW_MIN_BALANCE'

    def test_skip_customer_threshold_not_met(self, mock_service_components, sample_customer_normal, sample_rule_60d):
        svc = mock_service_components['service']
        # Invoices are 35 days overdue, but rule threshold is 60 days
        eval_res = svc.evaluate_customer_eligibility(
            customer=sample_customer_normal,
            rule=sample_rule_60d,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is False
        assert eval_res['reason'] == 'THRESHOLD_NOT_MET'

    def test_weekly_statement_schedule_day_matching(self, mock_service_components, sample_customer_normal, sample_rule_weekly_stmt):
        svc = mock_service_components['service']
        # 2026-09-08 is a Tuesday -> schedule_day is FRIDAY -> should skip
        eval_tuesday = svc.evaluate_customer_eligibility(
            customer=sample_customer_normal,
            rule=sample_rule_weekly_stmt,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_tuesday['eligible'] is False
        assert eval_tuesday['reason'] == 'SCHEDULE_NOT_MATCHED'

        # 2026-09-11 is a Friday -> should be eligible
        eval_friday = svc.evaluate_customer_eligibility(
            customer=sample_customer_normal,
            rule=sample_rule_weekly_stmt,
            as_of_date=date(2026, 9, 11),
        )
        assert eval_friday['eligible'] is True
        assert eval_friday['reason'] == 'ELIGIBLE'

    def test_skip_customer_with_no_channel(self, mock_service_components, sample_customer_normal, sample_rule_30d):
        svc = mock_service_components['service']
        cust_no_channel = dict(sample_customer_normal, preferred_reminder_channel='NONE')
        eval_res = svc.evaluate_customer_eligibility(
            customer=cust_no_channel,
            rule=sample_rule_30d,
            as_of_date=date(2026, 9, 8),
        )
        assert eval_res['eligible'] is False
        assert eval_res['reason'] == 'NO_CHANNEL_CONFIGURED'


class TestSingleCustomerReminderAndStatementDispatch:
    """Test suite for on-demand reminder and statement dispatch operations."""

    def test_send_customer_reminder_success(self, mock_service_components):
        svc = mock_service_components['service']
        customer_repo = mock_service_components['customer_repo']
        dispatch_service = mock_service_components['dispatch_service']

        res = svc.send_customer_reminder(
            customer_id=101,
            rule_id=1,
            custom_message='Urgent payment requested before end of month.',
            as_of_date=date(2026, 9, 8),
        )

        assert res['success'] is True
        assert res['customer_id'] == 101
        dispatch_service.dispatch_reminder.assert_called_once()
        customer_repo.update.assert_called_once()
        update_args = customer_repo.update.call_args[0]
        assert update_args[0] == 101
        assert 'last_reminder_sent_at' in update_args[1]

    def test_send_customer_reminder_not_found(self, mock_service_components):
        svc = mock_service_components['service']
        with pytest.raises(ValueError, match="Customer #999 was not found"):
            svc.send_customer_reminder(customer_id=999)

    def test_dispatch_customer_statement_success(self, mock_service_components):
        svc = mock_service_components['service']
        customer_repo = mock_service_components['customer_repo']
        pdf_service = mock_service_components['statement_pdf_service']
        dispatch_service = mock_service_components['dispatch_service']

        res = svc.dispatch_customer_statement(
            customer_id=101,
            channel='EMAIL',
            as_of_date=date(2026, 9, 8),
        )

        assert res['success'] is True
        pdf_service.generate_statement_pdf_for_customer.assert_called_once()
        dispatch_service.dispatch_reminder.assert_called_once()
        customer_repo.update.assert_called_once()
        update_args = customer_repo.update.call_args[0]
        assert update_args[0] == 101
        assert 'last_statement_sent_at' in update_args[1]


class TestBatchReminderEngine:
    """Test suite for scheduled and batch reminder evaluation runs."""

    def test_run_batch_reminders_dry_run(self, mock_service_components):
        svc = mock_service_components['service']
        dispatch_service = mock_service_components['dispatch_service']

        batch_res = svc.run_batch_reminders(
            rule_id=1,
            as_of_date=date(2026, 9, 8),
            dry_run=True,
        )

        assert isinstance(batch_res, BatchReminderResult)
        assert batch_res.total_evaluated == 1
        assert batch_res.total_eligible == 1
        assert batch_res.total_dispatched == 1
        assert len(batch_res.dispatched_communications) == 1
        assert batch_res.dispatched_communications[0]['dry_run'] is True
        assert batch_res.dispatched_communications[0]['status'] == 'PREVIEW'
        # In dry run mode, dispatch_reminder is NOT called
        dispatch_service.dispatch_reminder.assert_not_called()

    def test_run_batch_reminders_live_execution(self, mock_service_components):
        svc = mock_service_components['service']
        dispatch_service = mock_service_components['dispatch_service']
        customer_repo = mock_service_components['customer_repo']

        batch_res = svc.run_batch_reminders(
            rule_id=1,
            as_of_date=date(2026, 9, 8),
            dry_run=False,
        )

        assert batch_res.total_evaluated == 1
        assert batch_res.total_eligible == 1
        assert batch_res.total_dispatched == 1
        assert len(batch_res.dispatched_communications) == 1
        assert batch_res.dispatched_communications[0]['status'] == 'SENT'
        dispatch_service.dispatch_reminder.assert_called_once()
        customer_repo.update.assert_called_once()

    def test_run_batch_reminders_skips_already_sent_today(self, mock_service_components, sample_customer_normal):
        svc = mock_service_components['service']
        dispatch_service = mock_service_components['dispatch_service']

        # Set customer's last reminder sent at today
        sample_customer_normal['last_reminder_sent_at'] = datetime(2026, 9, 8, 8, 30, tzinfo=timezone.utc)

        batch_res = svc.run_batch_reminders(
            rule_id=1,
            as_of_date=date(2026, 9, 8),
            dry_run=False,
            force=False,
        )

        assert batch_res.total_evaluated == 1
        assert batch_res.total_eligible == 1
        assert batch_res.total_dispatched == 0
        dispatch_service.dispatch_reminder.assert_not_called()


class TestAROverdueSummaryMetrics:
    """Test suite for calculating portfolio-wide AR collection metrics."""

    def test_get_ar_overdue_summary(self, mock_service_components):
        svc = mock_service_components['service']

        summary = svc.get_ar_overdue_summary(as_of_date=date(2026, 9, 8))

        assert summary['total_customers'] == 1
        assert summary['overdue_customers_count'] == 1
        assert summary['total_balance'] == 5400.0
        assert summary['total_overdue'] == 3000.0
        assert summary['current_balance'] == 2400.0
        assert '31_60' in summary['aging_breakdown']
        assert summary['aging_breakdown']['31_60'] == 3000.0
