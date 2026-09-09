"""
AR Collection Reminder Evaluation and Scheduled Batch Engine Service for Nova ERP.

Provides end-to-end automated AR collections and statement dispatch orchestration:
- Evaluates customer aging data against configured 30/60/90-day thresholds and weekly schedules
- Enforces customer-level VIP exclusions, credit hold checks, and reminder preferences
- Renders personalized email and WhatsApp templates with dynamic financial merge tags
- Dispatches transactional reminders and branded PDF account statements
- Executes dry-run and live batch reminder evaluations across active customer accounts
- Updates customer audit tracking timestamps (last_reminder_sent_at, last_statement_sent_at)
- Calculates aggregate AR overdue collection metrics and portfolio health statistics
"""

import logging
import uuid
from typing import Optional, Dict, Any, List, Union
from datetime import date, datetime, timezone

from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant
from modules.accounting.models.reminder import (
    AR_REMINDER_RULE_REPO,
    AR_REMINDER_TEMPLATE_REPO,
    BatchReminderResult,
    ARReminderRuleCreate,
    ARReminderRuleUpdate,
    ARReminderTemplateCreate,
    ARReminderTemplateUpdate,
)
from modules.crm.models.customer_communication import CUSTOMER_COMMUNICATION_REPO
from modules.accounting.services.aging_service import (
    AgingService,
    aging_service,
    parse_date,
    classify_overdue_days,
)
from modules.accounting.services.statement_pdf_service import StatementPdfService
from modules.accounting.services.reminder_dispatch_service import (
    ReminderDispatchService,
    reminder_dispatch_service,
    is_valid_email,
    normalize_phone_number,
)

logger = logging.getLogger(__name__)


class ARReminderService:
    """Automated AR Collection Reminder Evaluation and Batch Engine Service."""

    def __init__(
        self,
        rule_repo: Optional[CrudRepository] = None,
        template_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        communication_repo: Optional[CrudRepository] = None,
        aging_service_instance: Optional[AgingService] = None,
        dispatch_service: Optional[ReminderDispatchService] = None,
        statement_pdf_service: Optional[StatementPdfService] = None,
    ):
        self.rule_repo = rule_repo or AR_REMINDER_RULE_REPO
        self.template_repo = template_repo or AR_REMINDER_TEMPLATE_REPO
        self.communication_repo = communication_repo or CUSTOMER_COMMUNICATION_REPO
        self.customer_repo = customer_repo or CrudRepository(
            'T0010',
            business_columns=[
                'id',
                'name',
                'group_name',
                'phone',
                'email',
                'credit_limit',
                'balance',
                'is_vip',
                'exclude_from_reminders',
                'preferred_reminder_channel',
                'reminder_phone',
                'reminder_email',
                'last_reminder_sent_at',
                'last_statement_sent_at',
                'is_active',
                'business_id',
            ],
        )
        self.invoice_repo = invoice_repo or CrudRepository(
            'T0090',
            business_columns=[
                'id',
                'invoice_number',
                'invoice_type',
                'partner_id',
                'sales_order_id',
                'issue_date',
                'due_date',
                'discount_due_date',
                'discount_percentage',
                'discount_days',
                'early_discount_amount',
                'total_amount',
                'paid_amount',
                'status',
                'notes',
                'business_id',
            ],
        )
        self.aging_service = aging_service_instance or aging_service
        self.dispatch_service = dispatch_service or reminder_dispatch_service
        self.statement_pdf_service = statement_pdf_service or StatementPdfService(
            customer_repo=self.customer_repo,
            invoice_repo=self.invoice_repo,
            aging_service=self.aging_service,
        )

    # ----------------------------------------------------------------------
    # 1. Rule Management CRUD & Helpers
    # ----------------------------------------------------------------------
    def list_rules(
        self,
        is_active: Optional[bool] = None,
        trigger_type: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List AR reminder rules with optional filtering and linked template names."""
        filters: Dict[str, Any] = {}
        if is_active is not None:
            filters['is_active'] = is_active
        if trigger_type:
            filters['trigger_type'] = trigger_type
        if channel:
            filters['channel'] = channel

        rules = self.rule_repo.list(filters=filters, limit=limit, offset=offset)

        # Enhance with template names
        for rule in rules:
            if rule.get('template_id') and not rule.get('template_name'):
                try:
                    tmpl = self.template_repo.get(rule['template_id'])
                    if tmpl:
                        rule['template_name'] = tmpl.get('template_name')
                except Exception:
                    pass

        return rules

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single AR reminder rule by ID."""
        rule = self.rule_repo.get(rule_id)
        if rule and rule.get('template_id') and not rule.get('template_name'):
            try:
                tmpl = self.template_repo.get(rule['template_id'])
                if tmpl:
                    rule['template_name'] = tmpl.get('template_name')
            except Exception:
                pass
        return rule

    def create_rule(self, data: Union[ARReminderRuleCreate, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new AR reminder rule."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, ARReminderRuleCreate) else dict(data)

        if not payload.get('rule_code'):
            unique_code = f"RULE-AR-{uuid.uuid4().hex[:6].upper()}"
            payload['rule_code'] = unique_code

        return self.rule_repo.create(payload)

    def update_rule(self, rule_id: int, data: Union[ARReminderRuleUpdate, Dict[str, Any]]) -> Dict[str, Any]:
        """Update an existing AR reminder rule."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, ARReminderRuleUpdate) else dict(data)
        return self.rule_repo.update(rule_id, payload)

    def delete_rule(self, rule_id: int) -> bool:
        """Deactivate or delete an AR reminder rule."""
        return self.rule_repo.delete(rule_id)

    # ----------------------------------------------------------------------
    # 2. Template Management CRUD & Helpers
    # ----------------------------------------------------------------------
    def list_templates(
        self,
        channel: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List message templates."""
        filters: Dict[str, Any] = {}
        if channel:
            filters['channel'] = channel
        if is_active is not None:
            filters['is_active'] = is_active

        return self.template_repo.list(filters=filters, limit=limit, offset=offset)

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single template by ID."""
        return self.template_repo.get(template_id)

    def create_template(self, data: Union[ARReminderTemplateCreate, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new message template."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, ARReminderTemplateCreate) else dict(data)
        if not payload.get('template_code'):
            ch = payload.get('channel', 'EMAIL')[:2].upper()
            payload['template_code'] = f"TMPL-{ch}-{uuid.uuid4().hex[:6].upper()}"

        return self.template_repo.create(payload)

    def update_template(self, template_id: int, data: Union[ARReminderTemplateUpdate, Dict[str, Any]]) -> Dict[str, Any]:
        """Update an existing template."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, ARReminderTemplateUpdate) else dict(data)
        return self.template_repo.update(template_id, payload)

    def delete_template(self, template_id: int) -> bool:
        """Delete or deactivate template."""
        return self.template_repo.delete(template_id)

    def get_default_template(self, channel: str = 'EMAIL', trigger_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve default template for channel, or fallback to first active template."""
        templates = self.template_repo.list(filters={'channel': channel.upper(), 'is_active': True})
        if not templates:
            # Try finding any active template
            templates = self.template_repo.list(filters={'is_active': True})
        if not templates:
            return None

        # Look for is_default=True
        for tmpl in templates:
            if tmpl.get('is_default'):
                return tmpl
        return templates[0]

    # ----------------------------------------------------------------------
    # 3. Eligibility Evaluation Logic
    # ----------------------------------------------------------------------
    def evaluate_customer_eligibility(
        self,
        customer: Dict[str, Any],
        rule: Dict[str, Any],
        as_of_date: Optional[Union[date, str]] = None,
        customer_aging: Optional[Dict[str, Any]] = None,
        invoices: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a customer account against an AR reminder rule.

        Returns an evaluation verdict dictionary with eligibility status and reasons:
        - INACTIVE_CUSTOMER: Account marked inactive
        - EXCLUDED_FROM_REMINDERS: Customer opt-out flag set
        - VIP_EXCLUDED: Customer is VIP and rule excludes VIPs
        - CREDIT_HOLD_EXCLUDED: Customer is on credit hold and rule excludes credit holds
        - CUSTOMER_GROUP_MISMATCH: Customer group does not match rule filter
        - NO_OVERDUE_INVOICES: Account has zero overdue balance
        - BELOW_MIN_BALANCE: Overdue balance below rule minimum threshold
        - THRESHOLD_NOT_MET: Aging threshold (e.g. 30, 60, 90 days) not reached
        - SCHEDULE_NOT_MATCHED: Recurring day (e.g. Friday) does not match evaluation date
        - ZERO_BALANCE: Account has no outstanding balance
        - NO_CHANNEL_CONFIGURED: Preferred channel set to NONE or no contact info
        - MISSING_EMAIL_ADDRESS: Target channel requires email but none exists
        - MISSING_PHONE_NUMBER: Target channel requires phone but none exists
        - ELIGIBLE: Customer qualifies for automated reminder dispatch
        """
        eval_date = parse_date(as_of_date) or date.today()
        cust_id = customer.get('id', 0)
        cust_name = customer.get('name', 'Valued Customer')

        base_res: Dict[str, Any] = {
            'eligible': False,
            'reason': 'UNKNOWN',
            'customer_id': cust_id,
            'customer_name': cust_name,
            'rule_id': rule.get('id'),
            'rule_name': rule.get('rule_name'),
            'trigger_type': rule.get('trigger_type', 'AGING_THRESHOLD'),
            'total_balance': 0.0,
            'overdue_amount': 0.0,
            'max_days_overdue': 0,
            'open_invoices_count': 0,
            'aging': None,
            'target_channel': None,
        }

        # 1. Customer Account Status Checks
        if not customer.get('is_active', True):
            base_res['reason'] = 'INACTIVE_CUSTOMER'
            return base_res

        if customer.get('exclude_from_reminders', False):
            base_res['reason'] = 'EXCLUDED_FROM_REMINDERS'
            return base_res

        if rule.get('exclude_vip', True) and customer.get('is_vip', False):
            base_res['reason'] = 'VIP_EXCLUDED'
            return base_res

        if rule.get('exclude_credit_hold', False) and customer.get('credit_hold', False):
            base_res['reason'] = 'CREDIT_HOLD_EXCLUDED'
            return base_res

        if rule.get('customer_group') and rule.get('customer_group') != customer.get('group_name'):
            base_res['reason'] = 'CUSTOMER_GROUP_MISMATCH'
            return base_res

        # 2. Resolve Invoices & Aging Breakdown
        if customer_aging is None:
            if invoices is None:
                invoices = self.invoice_repo.list(filters={'partner_id': cust_id}, limit=500)
            customer_aging = self.aging_service.calculate_aging(invoices, as_of_date=eval_date)
        elif invoices is None:
            invoices = []

        total_balance = float(customer_aging.get('total_outstanding', customer.get('balance', 0.0) or 0.0))
        overdue_amount = sum(
            float(customer_aging.get(b, 0.0))
            for b in ('1_30', '31_60', '61_90', '90_plus')
        )

        # Calculate open invoice metrics
        open_invoices = [
            inv for inv in invoices
            if str(inv.get('status', '')).lower() not in ('paid', 'cancelled', 'void')
        ]
        open_invoices_count = len(open_invoices)

        max_days_overdue = 0
        for inv in open_invoices:
            due = parse_date(inv.get('due_date')) or parse_date(inv.get('issue_date')) or eval_date
            if due < eval_date:
                days_over = (eval_date - due).days
                if days_over > max_days_overdue:
                    max_days_overdue = days_over

        base_res['total_balance'] = round(total_balance, 2)
        base_res['overdue_amount'] = round(overdue_amount, 2)
        base_res['max_days_overdue'] = max_days_overdue
        base_res['open_invoices_count'] = open_invoices_count
        base_res['aging'] = customer_aging

        # 3. Trigger Type Evaluation
        trigger_type = str(rule.get('trigger_type', 'AGING_THRESHOLD')).upper()
        min_balance = float(rule.get('min_overdue_balance', 0.0) or 0.0)

        if trigger_type == 'AGING_THRESHOLD':
            threshold_days = int(rule.get('threshold_days', 30))

            if overdue_amount <= 0:
                base_res['reason'] = 'NO_OVERDUE_INVOICES'
                return base_res

            if overdue_amount < min_balance:
                base_res['reason'] = 'BELOW_MIN_BALANCE'
                return base_res

            # Check threshold qualification
            threshold_met = False
            if max_days_overdue > 0:
                threshold_met = (max_days_overdue >= threshold_days)
            else:
                if threshold_days >= 90:
                    threshold_met = float(customer_aging.get('90_plus', 0.0)) > 0
                elif threshold_days >= 60:
                    val_60_plus = float(customer_aging.get('61_90', 0.0)) + float(customer_aging.get('90_plus', 0.0))
                    threshold_met = val_60_plus > 0
                elif threshold_days >= 30:
                    val_30_plus = (
                        float(customer_aging.get('1_30', 0.0))
                        + float(customer_aging.get('31_60', 0.0))
                        + float(customer_aging.get('61_90', 0.0))
                        + float(customer_aging.get('90_plus', 0.0))
                    )
                    threshold_met = val_30_plus > 0
                else:
                    threshold_met = overdue_amount > 0

            if not threshold_met:
                base_res['reason'] = 'THRESHOLD_NOT_MET'
                return base_res

        elif trigger_type == 'STATEMENT_SCHEDULE':
            if total_balance <= 0:
                base_res['reason'] = 'ZERO_BALANCE'
                return base_res

            if total_balance < min_balance:
                base_res['reason'] = 'BELOW_MIN_BALANCE'
                return base_res

            schedule_day = rule.get('schedule_day')
            if schedule_day:
                current_day_name = eval_date.strftime('%A').upper()
                if current_day_name != schedule_day.upper():
                    base_res['reason'] = 'SCHEDULE_NOT_MATCHED'
                    return base_res

        elif trigger_type == 'DUE_DATE_OFFSET':
            threshold_days = int(rule.get('threshold_days', 0))
            offset_matched = False
            for inv in open_invoices:
                due = parse_date(inv.get('due_date')) or eval_date
                days_diff = (eval_date - due).days
                if days_diff >= threshold_days:
                    offset_matched = True
                    break

            if not offset_matched:
                base_res['reason'] = 'THRESHOLD_NOT_MET'
                return base_res

            if overdue_amount < min_balance and total_balance < min_balance:
                base_res['reason'] = 'BELOW_MIN_BALANCE'
                return base_res

        # 4. Channel & Recipient Contact Information Validation
        cust_pref_channel = str(customer.get('preferred_reminder_channel', 'EMAIL')).upper()
        if cust_pref_channel == 'NONE':
            base_res['reason'] = 'NO_CHANNEL_CONFIGURED'
            return base_res

        rule_channel = str(rule.get('channel', 'ALL')).upper()
        effective_channel = 'EMAIL'
        if rule_channel != 'ALL':
            effective_channel = rule_channel
        elif cust_pref_channel in ('EMAIL', 'WHATSAPP', 'BOTH', 'ALL'):
            effective_channel = cust_pref_channel

        base_res['target_channel'] = effective_channel

        email_addr = customer.get('reminder_email') or customer.get('email')
        phone_num = customer.get('reminder_phone') or customer.get('phone')

        if effective_channel in ('EMAIL', 'BOTH', 'ALL') and not email_addr:
            if effective_channel == 'EMAIL' or not phone_num:
                base_res['reason'] = 'MISSING_EMAIL_ADDRESS'
                return base_res

        if effective_channel == 'WHATSAPP' and not phone_num:
            base_res['reason'] = 'MISSING_PHONE_NUMBER'
            return base_res

        base_res['eligible'] = True
        base_res['reason'] = 'ELIGIBLE'
        return base_res

    # ----------------------------------------------------------------------
    # 4. Single Customer Reminder & Statement Dispatch
    # ----------------------------------------------------------------------
    def send_customer_reminder(
        self,
        customer_id: int,
        rule_id: Optional[int] = None,
        template_id: Optional[int] = None,
        channel: Optional[str] = None,
        custom_message: Optional[str] = None,
        as_of_date: Optional[Union[date, str]] = None,
        dispatched_by: Optional[int] = None,
        attach_statement_pdf: bool = True,
        include_payment_link: bool = True,
        recipient_email: Optional[str] = None,
        recipient_phone: Optional[str] = None,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Dispatch an on-demand AR payment reminder to a single customer."""
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} was not found.")

        eval_date = parse_date(as_of_date) or date.today()

        # Temporary contact overrides if provided
        cust_copy = dict(customer)
        if recipient_email:
            cust_copy['reminder_email'] = recipient_email
            cust_copy['email'] = recipient_email
        if recipient_phone:
            cust_copy['reminder_phone'] = recipient_phone
            cust_copy['phone'] = recipient_phone

        # Resolve Rule
        rule = None
        if rule_id:
            rule = self.get_rule(rule_id)
        if not rule:
            rule = {
                'id': None,
                'rule_name': 'Manual Collection Reminder',
                'channel': channel or cust_copy.get('preferred_reminder_channel', 'EMAIL'),
                'attach_statement_pdf': attach_statement_pdf,
                'include_payment_link': include_payment_link,
            }

        # Resolve Template
        template = None
        if template_id:
            template = self.get_template(template_id)
        elif rule.get('template_id'):
            template = self.get_template(rule['template_id'])
        if not template:
            target_ch = channel or cust_copy.get('preferred_reminder_channel', 'EMAIL')
            template = self.get_default_template(channel=target_ch)

        # Calculate Invoices and Aging for context
        invoices = self.invoice_repo.list(filters={'partner_id': customer_id}, limit=500)
        aging = self.aging_service.calculate_aging(invoices, as_of_date=eval_date)
        total_balance = float(aging.get('total_outstanding', cust_copy.get('balance', 0.0) or 0.0))
        overdue_amount = sum(
            float(aging.get(b, 0.0))
            for b in ('1_30', '31_60', '61_90', '90_plus')
        )
        open_invoices_count = sum(
            1 for inv in invoices
            if str(inv.get('status', '')).lower() not in ('paid', 'cancelled', 'void')
        )

        context = {
            'customer_id': customer_id,
            'customer_name': cust_copy.get('name'),
            'total_balance': total_balance,
            'overdue_amount': overdue_amount,
            'invoice_count': open_invoices_count,
            'as_of_date': eval_date.isoformat(),
        }

        # Execute dispatch
        result = self.dispatch_service.dispatch_reminder(
            customer=cust_copy,
            rule=rule,
            template=template,
            channel=channel,
            context=context,
            custom_message=custom_message,
            as_of_date=eval_date,
            communication_type='REMINDER',
            dispatched_by=dispatched_by,
            is_automated=False,
            business_id=business_id or customer.get('business_id'),
        )

        # Update customer last_reminder_sent_at timestamp
        if result.get('success'):
            try:
                now_dt = datetime.now(timezone.utc)
                self.customer_repo.update(customer_id, {'last_reminder_sent_at': now_dt})
            except Exception as e:
                logger.warning("Could not update last_reminder_sent_at for customer #%s: %s", customer_id, e)

        return result

    def dispatch_customer_statement(
        self,
        customer_id: int,
        channel: Optional[str] = 'EMAIL',
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        as_of_date: Optional[Union[date, str]] = None,
        custom_message: Optional[str] = None,
        recipient_email: Optional[str] = None,
        recipient_phone: Optional[str] = None,
        dispatched_by: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate and dispatch an account statement PDF to a single customer."""
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} was not found.")

        eval_date = parse_date(as_of_date) or date.today()
        period_start = parse_date(start_date)
        period_end = parse_date(end_date) or eval_date

        cust_copy = dict(customer)
        if recipient_email:
            cust_copy['reminder_email'] = recipient_email
            cust_copy['email'] = recipient_email
        if recipient_phone:
            cust_copy['reminder_phone'] = recipient_phone
            cust_copy['phone'] = recipient_phone

        # Generate statement PDF
        pdf_bytes = self.statement_pdf_service.generate_statement_pdf_for_customer(
            customer_id=customer_id,
            as_of_date=eval_date,
            start_date=period_start,
            end_date=period_end,
            custom_message=custom_message,
        )

        invoices = self.invoice_repo.list(filters={'partner_id': customer_id}, limit=500)
        aging = self.aging_service.calculate_aging(invoices, as_of_date=eval_date)
        total_balance = float(aging.get('total_outstanding', cust_copy.get('balance', 0.0) or 0.0))
        overdue_amount = sum(
            float(aging.get(b, 0.0))
            for b in ('1_30', '31_60', '61_90', '90_plus')
        )
        open_invoices_count = sum(
            1 for inv in invoices
            if str(inv.get('status', '')).lower() not in ('paid', 'cancelled', 'void')
        )

        statement_rule = {
            'id': None,
            'rule_name': 'Manual Statement Dispatch',
            'channel': channel or 'EMAIL',
            'attach_statement_pdf': True,
            'include_payment_link': True,
        }

        subject = f"Account Statement: {cust_copy.get('name')} (as of {eval_date.isoformat()})"
        body = (
            f"Dear {cust_copy.get('name')},\n\n"
            f"Please find attached your account statement as of {eval_date.isoformat()}.\n"
            f"Total Outstanding Balance: ${total_balance:,.2f}\n"
            f"Overdue Amount: ${overdue_amount:,.2f}\n\n"
            f"Thank you for your business."
        )
        if custom_message:
            body += f"\n\nSpecial Note: {custom_message}"

        template = {
            'id': None,
            'subject_template': subject,
            'body_template': body,
        }

        context = {
            'customer_id': customer_id,
            'customer_name': cust_copy.get('name'),
            'total_balance': total_balance,
            'overdue_amount': overdue_amount,
            'invoice_count': open_invoices_count,
            'as_of_date': eval_date.isoformat(),
        }

        result = self.dispatch_service.dispatch_reminder(
            customer=cust_copy,
            rule=statement_rule,
            template=template,
            channel=channel,
            context=context,
            pdf_bytes=pdf_bytes,
            custom_message=custom_message,
            as_of_date=eval_date,
            communication_type='STATEMENT',
            dispatched_by=dispatched_by,
            is_automated=False,
            business_id=business_id or customer.get('business_id'),
        )

        if result.get('success'):
            try:
                now_dt = datetime.now(timezone.utc)
                self.customer_repo.update(customer_id, {'last_statement_sent_at': now_dt})
            except Exception as e:
                logger.warning("Could not update last_statement_sent_at for customer #%s: %s", customer_id, e)

        return result

    # ----------------------------------------------------------------------
    # 5. Scheduled & Batch Reminder Evaluation Engine
    # ----------------------------------------------------------------------
    def run_batch_reminders(
        self,
        rule_id: Optional[int] = None,
        customer_ids: Optional[List[int]] = None,
        as_of_date: Optional[Union[date, str]] = None,
        dry_run: bool = False,
        force: bool = False,
        dispatched_by: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> BatchReminderResult:
        """Evaluate customer accounts against reminder rules and execute batch dispatches."""
        eval_date = parse_date(as_of_date) or date.today()
        today_str = eval_date.isoformat()

        # 1. Resolve Rules to Evaluate
        if rule_id:
            rule = self.get_rule(rule_id)
            if not rule:
                raise ValueError(f"Reminder Rule #{rule_id} was not found.")
            rules = [rule]
        else:
            rules = self.list_rules(is_active=True)

        if not rules:
            logger.info("No active AR reminder rules found for batch execution.")
            return BatchReminderResult()

        # 2. Resolve Customers
        if customer_ids:
            customers = []
            for cid in customer_ids:
                c = self.customer_repo.get(cid)
                if c:
                    customers.append(c)
        else:
            customers = self.customer_repo.list(limit=1000)

        # 3. Execution Counters & Tracking
        total_evaluated = 0
        total_eligible = 0
        total_dispatched = 0
        total_skipped_vip = 0
        total_skipped_excluded = 0
        total_skipped_balance = 0
        total_skipped_channel = 0
        total_failed = 0
        dispatched_comms: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        dispatched_customer_ids = set()

        for customer in customers:
            total_evaluated += 1
            cust_id = customer.get('id')
            cust_name = customer.get('name')

            if cust_id in dispatched_customer_ids and not force:
                continue

            invoices = self.invoice_repo.list(filters={'partner_id': cust_id}, limit=500)
            aging = self.aging_service.calculate_aging(invoices, as_of_date=eval_date)

            matched_rule = None
            eval_result = None

            sorted_rules = sorted(rules, key=lambda r: r.get('threshold_days', 0), reverse=True)
            for rule in sorted_rules:
                res = self.evaluate_customer_eligibility(
                    customer=customer,
                    rule=rule,
                    as_of_date=eval_date,
                    customer_aging=aging,
                    invoices=invoices,
                )
                if res['eligible']:
                    matched_rule = rule
                    eval_result = res
                    break
                else:
                    r_reason = res['reason']
                    if r_reason == 'VIP_EXCLUDED':
                        total_skipped_vip += 1
                    elif r_reason == 'EXCLUDED_FROM_REMINDERS':
                        total_skipped_excluded += 1
                    elif r_reason in ('BELOW_MIN_BALANCE', 'NO_OVERDUE_INVOICES', 'ZERO_BALANCE'):
                        total_skipped_balance += 1
                    elif r_reason in ('NO_CHANNEL_CONFIGURED', 'MISSING_EMAIL_ADDRESS', 'MISSING_PHONE_NUMBER'):
                        total_skipped_channel += 1

            if not matched_rule or not eval_result or not eval_result['eligible']:
                continue

            total_eligible += 1

            # Check if reminder already sent today unless force=True
            last_sent = customer.get('last_reminder_sent_at')
            if last_sent and not force:
                last_sent_date = parse_date(last_sent)
                if last_sent_date == eval_date:
                    logger.info("Skipping customer #%s: Reminder already dispatched today (%s)", cust_id, today_str)
                    continue

            template = None
            if matched_rule.get('template_id'):
                template = self.get_template(matched_rule['template_id'])
            if not template:
                template = self.get_default_template(channel=eval_result.get('target_channel', 'EMAIL'))

            context = {
                'customer_id': cust_id,
                'customer_name': cust_name,
                'total_balance': eval_result['total_balance'],
                'overdue_amount': eval_result['overdue_amount'],
                'invoice_count': eval_result['open_invoices_count'],
                'as_of_date': today_str,
            }

            if dry_run:
                sim_res = {
                    'customer_id': cust_id,
                    'customer_name': cust_name,
                    'rule_id': matched_rule.get('id'),
                    'rule_name': matched_rule.get('rule_name'),
                    'channel': eval_result.get('target_channel'),
                    'overdue_amount': eval_result['overdue_amount'],
                    'total_balance': eval_result['total_balance'],
                    'dry_run': True,
                    'status': 'PREVIEW',
                }
                dispatched_comms.append(sim_res)
                total_dispatched += 1
                dispatched_customer_ids.add(cust_id)
            else:
                try:
                    dispatch_res = self.dispatch_service.dispatch_reminder(
                        customer=customer,
                        rule=matched_rule,
                        template=template,
                        channel=eval_result.get('target_channel'),
                        context=context,
                        as_of_date=eval_date,
                        communication_type='REMINDER',
                        dispatched_by=dispatched_by,
                        is_automated=True,
                        business_id=business_id or customer.get('business_id'),
                    )

                    if dispatch_res.get('success'):
                        total_dispatched += 1
                        dispatched_customer_ids.add(cust_id)
                        dispatched_comms.append({
                            'customer_id': cust_id,
                            'customer_name': cust_name,
                            'rule_id': matched_rule.get('id'),
                            'rule_name': matched_rule.get('rule_name'),
                            'channel': eval_result.get('target_channel'),
                            'status': 'SENT',
                            'results': dispatch_res.get('results'),
                        })

                        try:
                            now_dt = datetime.now(timezone.utc)
                            self.customer_repo.update(cust_id, {'last_reminder_sent_at': now_dt})
                        except Exception as ex:
                            logger.warning("Failed to update last_reminder_sent_at for customer #%s: %s", cust_id, ex)
                    else:
                        total_failed += 1
                        errors.append({
                            'customer_id': cust_id,
                            'customer_name': cust_name,
                            'error': "Dispatch failed across channels",
                            'details': dispatch_res.get('results'),
                        })
                except Exception as e:
                    total_failed += 1
                    logger.error("Error dispatching batch reminder for customer #%s: %s", cust_id, e, exc_info=True)
                    errors.append({
                        'customer_id': cust_id,
                        'customer_name': cust_name,
                        'error': str(e),
                    })

        return BatchReminderResult(
            total_evaluated=total_evaluated,
            total_eligible=total_eligible,
            total_dispatched=total_dispatched,
            total_skipped_vip=total_skipped_vip,
            total_skipped_excluded=total_skipped_excluded,
            total_skipped_balance=total_skipped_balance,
            total_skipped_channel=total_skipped_channel,
            total_failed=total_failed,
            dispatched_communications=dispatched_comms,
            errors=errors,
        )

    # ----------------------------------------------------------------------
    # 6. Portfolio Metrics & Overdue Summaries
    # ----------------------------------------------------------------------
    def get_ar_overdue_summary(self, as_of_date: Optional[Union[date, str]] = None) -> Dict[str, Any]:
        """Compute portfolio-wide AR collection metrics and aging statistics."""
        eval_date = parse_date(as_of_date) or date.today()
        customers = self.customer_repo.list(limit=1000)

        total_customers = len(customers)
        total_balance = 0.0
        total_overdue = 0.0
        overdue_customers_count = 0
        vip_customers_count = 0
        excluded_customers_count = 0

        aging_totals = {
            'current': 0.0,
            '1_30': 0.0,
            '31_60': 0.0,
            '61_90': 0.0,
            '90_plus': 0.0,
        }

        for cust in customers:
            if cust.get('is_vip'):
                vip_customers_count += 1
            if cust.get('exclude_from_reminders'):
                excluded_customers_count += 1

            cid = cust.get('id')
            invoices = self.invoice_repo.list(filters={'partner_id': cid}, limit=500)
            aging = self.aging_service.calculate_aging(invoices, as_of_date=eval_date)

            cust_tot = float(aging.get('total_outstanding', 0.0))
            cust_overdue = sum(float(aging.get(b, 0.0)) for b in ('1_30', '31_60', '61_90', '90_plus'))

            total_balance += cust_tot
            total_overdue += cust_overdue

            if cust_overdue > 0:
                overdue_customers_count += 1

            for b in ('current', '1_30', '31_60', '61_90', '90_plus'):
                aging_totals[b] += float(aging.get(b, 0.0))

        for k in aging_totals:
            aging_totals[k] = round(aging_totals[k], 2)

        return {
            'as_of_date': eval_date.isoformat(),
            'total_customers': total_customers,
            'overdue_customers_count': overdue_customers_count,
            'vip_customers_count': vip_customers_count,
            'excluded_customers_count': excluded_customers_count,
            'total_balance': round(total_balance, 2),
            'total_overdue': round(total_overdue, 2),
            'current_balance': round(aging_totals['current'], 2),
            'aging_breakdown': aging_totals,
        }


# Singleton service instance
ar_reminder_service = ARReminderService()
