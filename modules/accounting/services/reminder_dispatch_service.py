"""
Reminder Dispatch Adapter Service for Nova ERP.

Handles multi-channel dispatch of AR collection reminders and PDF account statements:
- Transactional Email dispatch with PDF statement attachments (via Resend or SMTP/mock)
- WhatsApp Business API integration (direct messaging & Cloud API template messages)
- Template variable interpolation for customer balance, overdue amount, invoice count, and payment links
- Simulator / Mock support for local development, automated testing, and offline staging
- Webhook status callback processing for real-time delivery and read receipts (t0122_customer_communications)
"""

import os
import re
import json
import base64
import uuid
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date, timezone

import httpx

from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant
from modules.accounting.services.statement_pdf_service import StatementPdfService

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: Optional[str]) -> str:
    """Normalize phone number to international E.164 format (e.g., +15551234567).

    Strips out formatting characters (spaces, dashes, parentheses, dots).
    Ensures leading '+' if a country code is detected, or defaults to standard prefix.
    """
    if not phone:
        return ''
    cleaned = re.sub(r'[^\d+]', '', str(phone).strip())
    if not cleaned:
        return ''
    if cleaned.startswith('+'):
        return cleaned
    if len(cleaned) == 10:
        # Default US/Canada 10-digit number
        return f'+1{cleaned}'
    if len(cleaned) == 11 and cleaned.startswith('1'):
        return f'+{cleaned}'
    return f'+{cleaned}'


def is_valid_email(email: Optional[str]) -> bool:
    """Basic RFC 5322-compliant email format validation."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


class ReminderDispatchService:
    """Multi-channel dispatch adapter for AR payment reminders and account statements."""

    def __init__(
        self,
        communication_repo: Optional[CrudRepository] = None,
        statement_pdf_service: Optional[StatementPdfService] = None,
        resend_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        whatsapp_api_key: Optional[str] = None,
        whatsapp_phone_number_id: Optional[str] = None,
        whatsapp_business_account_id: Optional[str] = None,
        whatsapp_api_version: str = 'v18.0',
        simulator_mode: Optional[bool] = None,
        default_company_name: str = 'Nova ERP',
        portal_base_url: Optional[str] = None,
    ):
        self.communication_repo = communication_repo or CrudRepository(
            't0122_customer_communications',
            business_columns=[
                'id',
                'tracking_number',
                'customer_id',
                'rule_id',
                'template_id',
                'channel',
                'communication_type',
                'recipient_address',
                'recipient_name',
                'subject',
                'message_body',
                'status',
                'delivery_timestamp',
                'read_timestamp',
                'error_message',
                'external_message_id',
                'statement_pdf_path',
                'statement_pdf_size',
                'invoice_count',
                'total_balance',
                'overdue_amount',
                'payment_link',
                'dispatched_by',
                'is_automated',
                'metadata',
                'is_active',
            ],
        )
        self.statement_pdf_service = statement_pdf_service or StatementPdfService()

        # Email Configuration
        self.resend_api_key = resend_api_key or os.environ.get('RESEND_API_KEY', '')
        self.from_email = from_email or os.environ.get('RESEND_FROM_EMAIL', 'billing@novaerp.com')

        # WhatsApp Configuration
        self.whatsapp_api_key = whatsapp_api_key or os.environ.get('WHATSAPP_API_KEY', '')
        self.whatsapp_phone_number_id = whatsapp_phone_number_id or os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
        self.whatsapp_business_account_id = whatsapp_business_account_id or os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
        self.whatsapp_api_version = whatsapp_api_version

        # Simulator Mode: Enabled if explicitly set or if no real API keys are present
        env_sim = os.environ.get('NOVA_DISPATCH_SIMULATOR_MODE', '').lower() in ('1', 'true', 'yes')
        if simulator_mode is not None:
            self.simulator_mode = simulator_mode
        else:
            self.simulator_mode = env_sim or (not self.resend_api_key and not self.whatsapp_api_key)

        self.default_company_name = default_company_name
        self.portal_base_url = portal_base_url or os.environ.get('APP_URL', 'https://app.novaerp.com')

        # In-memory dispatch simulator audit log for testing/inspection
        self.simulated_dispatches: List[Dict[str, Any]] = []

    # ----------------------------------------------------------------------
    # 1. Template Variable Interpolation
    # ----------------------------------------------------------------------
    def interpolate_template(self, template_str: Optional[str], context: Optional[Dict[str, Any]]) -> str:
        """Interpolate template placeholders with context variables.

        Supports both double-bracket `{{key}}` and single-bracket `{key}` syntaxes.
        Handles numeric currency formatting for balance and overdue metrics.

        Available variables:
        - customer_name / name
        - customer_id / account_number
        - total_balance / balance
        - overdue_amount / overdue_balance
        - current_amount / current_balance
        - invoice_count / open_invoices_count
        - payment_link / pay_link
        - due_date / earliest_due_date
        - as_of_date / statement_date
        - company_name
        - currency
        """
        if not template_str:
            return ''
        if not context:
            return template_str

        # Build normalized lookup dictionary
        norm_ctx: Dict[str, Any] = {}
        for k, v in context.items():
            norm_ctx[k] = v
            # Normalise common variations
            norm_ctx[k.lower()] = v
            norm_ctx[k.replace('_', '')] = v

        # Format numeric variables
        def _fmt_money(val: Any) -> str:
            try:
                num = float(val)
                return f'${num:,.2f}'
            except (ValueError, TypeError):
                return str(val or '$0.00')

        # Aliases mapping
        val_customer_name = str(norm_ctx.get('customer_name') or norm_ctx.get('name') or norm_ctx.get('customer') or 'Valued Customer')
        val_customer_id = str(norm_ctx.get('customer_id') or norm_ctx.get('id') or norm_ctx.get('account_number') or '')
        val_balance_num = norm_ctx.get('total_balance') or norm_ctx.get('balance') or 0.0
        val_overdue_num = norm_ctx.get('overdue_amount') or norm_ctx.get('overdue') or 0.0
        val_current_num = norm_ctx.get('current_amount') or norm_ctx.get('current') or 0.0
        val_invoice_count = str(norm_ctx.get('invoice_count') or norm_ctx.get('open_invoices_count') or 0)
        val_payment_link = str(norm_ctx.get('payment_link') or norm_ctx.get('pay_link') or '')
        val_due_date = str(norm_ctx.get('due_date') or norm_ctx.get('earliest_due_date') or '')
        val_as_of_date = str(norm_ctx.get('as_of_date') or norm_ctx.get('statement_date') or date.today().isoformat())
        val_company_name = str(norm_ctx.get('company_name') or self.default_company_name)
        val_currency = str(norm_ctx.get('currency') or 'USD')

        replacements = {
            'customer_name': val_customer_name,
            'name': val_customer_name,
            'customer': val_customer_name,
            'customer_id': val_customer_id,
            'account_number': val_customer_id,
            'total_balance': _fmt_money(val_balance_num),
            'balance': _fmt_money(val_balance_num),
            'total_balance_raw': f"{float(val_balance_num or 0):.2f}",
            'balance_raw': f"{float(val_balance_num or 0):.2f}",
            'overdue_amount': _fmt_money(val_overdue_num),
            'overdue_balance': _fmt_money(val_overdue_num),
            'overdue': _fmt_money(val_overdue_num),
            'overdue_amount_raw': f"{float(val_overdue_num or 0):.2f}",
            'current_amount': _fmt_money(val_current_num),
            'current_balance': _fmt_money(val_current_num),
            'invoice_count': val_invoice_count,
            'open_invoices_count': val_invoice_count,
            'payment_link': val_payment_link,
            'pay_link': val_payment_link,
            'due_date': val_due_date,
            'earliest_due_date': val_due_date,
            'as_of_date': val_as_of_date,
            'statement_date': val_as_of_date,
            'company_name': val_company_name,
            'currency': val_currency,
        }

        # Include custom extra context
        for k, v in context.items():
            if k not in replacements:
                replacements[k] = str(v)

        result = template_str

        # Replace double braces {{var}}
        for key, val in replacements.items():
            pattern_double = re.compile(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', re.IGNORECASE)
            result = pattern_double.sub(val, result)

        # Replace single braces {var}
        for key, val in replacements.items():
            pattern_single = re.compile(r'\{\s*' + re.escape(key) + r'\s*\}', re.IGNORECASE)
            result = pattern_single.sub(val, result)

        return result

    # ----------------------------------------------------------------------
    # 2. Tracking Number & Payment Link Helpers
    # ----------------------------------------------------------------------
    def generate_tracking_number(self, customer_id: Optional[int] = None, channel: str = 'REM') -> str:
        """Generate a unique audit tracking identifier for dispatch events."""
        today_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:8].upper()
        cid = customer_id or 0
        ch = channel.upper()[:3]
        return f'TRK-{ch}-{today_str}-{cid}-{unique_suffix}'

    def generate_payment_link(self, customer_id: int, invoice_id: Optional[int] = None) -> str:
        """Generate a direct payment link for a customer account or specific invoice."""
        base = self.portal_base_url.rstrip('/')
        if invoice_id:
            return f'{base}/portal/pay/invoice/{invoice_id}'
        return f'{base}/portal/pay/customer/{customer_id}'

    # ----------------------------------------------------------------------
    # 3. Transactional Email Dispatch
    # ----------------------------------------------------------------------
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        recipient_name: Optional[str] = None,
        text_body: Optional[str] = None,
        pdf_attachment_bytes: Optional[bytes] = None,
        pdf_filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a transactional email with optional PDF attachment.

        Uses Resend API if configured, or falls back to simulator mode.
        """
        sender = from_email or self.from_email
        clean_to = to_email.strip()

        if not is_valid_email(clean_to):
            logger.warning('Invalid email address format: %s', clean_to)
            return {
                'success': False,
                'channel': 'EMAIL',
                'status': 'FAILED',
                'recipient': clean_to,
                'error_message': f'Invalid email address: {clean_to}',
                'external_message_id': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

        # Simulated Mode
        if self.simulator_mode or not self.resend_api_key:
            mock_id = f'msg_mock_email_{uuid.uuid4().hex[:16]}'
            logger.info('[SIMULATOR] Sent email to %s (subject: "%s", mock_id: %s)', clean_to, subject, mock_id)
            result = {
                'success': True,
                'channel': 'EMAIL',
                'status': 'SENT',
                'recipient': clean_to,
                'recipient_name': recipient_name,
                'subject': subject,
                'external_message_id': mock_id,
                'attachment_size': len(pdf_attachment_bytes) if pdf_attachment_bytes else 0,
                'attachment_name': pdf_filename,
                'is_simulated': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
            }
            self.simulated_dispatches.append(result)
            return result

        # Real Resend API Dispatch
        try:
            import resend
            resend.api_key = self.resend_api_key

            email_payload: Dict[str, Any] = {
                'from': sender,
                'to': clean_to,
                'subject': subject,
                'html': html_body,
            }
            if text_body:
                email_payload['text'] = text_body

            if pdf_attachment_bytes:
                att_name = pdf_filename or 'Account_Statement.pdf'
                # Resend accepts attachments as list of int bytes or base64
                email_payload['attachments'] = [
                    {
                        'filename': att_name,
                        'content': list(pdf_attachment_bytes),
                    }
                ]

            response = resend.Emails.send(email_payload)
            external_id = response.get('id') if isinstance(response, dict) else getattr(response, 'id', str(response))

            return {
                'success': True,
                'channel': 'EMAIL',
                'status': 'SENT',
                'recipient': clean_to,
                'recipient_name': recipient_name,
                'subject': subject,
                'external_message_id': external_id,
                'attachment_size': len(pdf_attachment_bytes) if pdf_attachment_bytes else 0,
                'attachment_name': pdf_filename,
                'is_simulated': False,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
            }

        except Exception as e:
            logger.error('Failed to send email via Resend to %s: %s', clean_to, str(e), exc_info=True)
            return {
                'success': False,
                'channel': 'EMAIL',
                'status': 'FAILED',
                'recipient': clean_to,
                'recipient_name': recipient_name,
                'subject': subject,
                'error_message': str(e),
                'external_message_id': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

    # ----------------------------------------------------------------------
    # 4. WhatsApp Business API Dispatch
    # ----------------------------------------------------------------------
    def send_whatsapp(
        self,
        to_phone: str,
        message_text: Optional[str] = None,
        template_name: Optional[str] = None,
        template_namespace: Optional[str] = None,
        language_code: str = 'en',
        template_parameters: Optional[List[Dict[str, Any]]] = None,
        media_attachment_url: Optional[str] = None,
        media_filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a WhatsApp message via Meta WhatsApp Business Cloud API or Simulator.

        Supports free-form text messages (for active customer service windows)
        and official HSM template messages with variable parameters.
        """
        normalized_phone = normalize_phone_number(to_phone)
        if not normalized_phone or len(normalized_phone) < 8:
            logger.warning('Invalid WhatsApp phone number: %s', to_phone)
            return {
                'success': False,
                'channel': 'WHATSAPP',
                'status': 'FAILED',
                'recipient': to_phone,
                'error_message': f'Invalid WhatsApp phone number: {to_phone}',
                'external_message_id': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

        # Simulated Mode
        if self.simulator_mode or not self.whatsapp_api_key or not self.whatsapp_phone_number_id:
            mock_wamid = f'wamid.HBgL{uuid.uuid4().hex[:20]}MOCK='
            logger.info(
                '[SIMULATOR] Sent WhatsApp message to %s (template: %s, mock_id: %s)',
                normalized_phone,
                template_name or 'FREE_FORM',
                mock_wamid,
            )
            result = {
                'success': True,
                'channel': 'WHATSAPP',
                'status': 'SENT',
                'recipient': normalized_phone,
                'template_name': template_name,
                'message_body': message_text,
                'external_message_id': mock_wamid,
                'media_attachment_url': media_attachment_url,
                'is_simulated': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
            }
            self.simulated_dispatches.append(result)
            return result

        # Real Meta WhatsApp Cloud API Dispatch
        try:
            url = f'https://graph.facebook.com/{self.whatsapp_api_version}/{self.whatsapp_phone_number_id}/messages'
            headers = {
                'Authorization': f'Bearer {self.whatsapp_api_key}',
                'Content-Type': 'application/json',
            }

            # WhatsApp recipient phone without leading '+' in Cloud API payload
            recipient_digits = normalized_phone.lstrip('+')

            if template_name:
                # HSM Template Dispatch
                payload: Dict[str, Any] = {
                    'messaging_product': 'whatsapp',
                    'to': recipient_digits,
                    'type': 'template',
                    'template': {
                        'name': template_name,
                        'language': {'code': language_code or 'en'},
                    },
                }
                if template_namespace:
                    payload['template']['namespace'] = template_namespace

                components = []
                if template_parameters:
                    components.append({
                        'type': 'body',
                        'parameters': template_parameters,
                    })
                if media_attachment_url:
                    components.append({
                        'type': 'header',
                        'parameters': [
                            {
                                'type': 'document',
                                'document': {
                                    'link': media_attachment_url,
                                    'filename': media_filename or 'Account_Statement.pdf',
                                },
                            }
                        ],
                    })
                if components:
                    payload['template']['components'] = components
            else:
                # Free-form Text Message Dispatch
                payload = {
                    'messaging_product': 'whatsapp',
                    'recipient_type': 'individual',
                    'to': recipient_digits,
                    'type': 'text',
                    'text': {'preview_url': True, 'body': message_text or ''},
                }

            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            external_id = None
            if 'messages' in data and len(data['messages']) > 0:
                external_id = data['messages'][0].get('id')

            return {
                'success': True,
                'channel': 'WHATSAPP',
                'status': 'SENT',
                'recipient': normalized_phone,
                'template_name': template_name,
                'message_body': message_text,
                'external_message_id': external_id,
                'is_simulated': False,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
            }

        except Exception as e:
            logger.error('Failed to send WhatsApp message to %s: %s', normalized_phone, str(e), exc_info=True)
            return {
                'success': False,
                'channel': 'WHATSAPP',
                'status': 'FAILED',
                'recipient': normalized_phone,
                'template_name': template_name,
                'error_message': str(e),
                'external_message_id': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

    # ----------------------------------------------------------------------
    # 5. Unified Reminder & Statement Dispatch
    # ----------------------------------------------------------------------
    def dispatch_reminder(
        self,
        customer: Dict[str, Any],
        rule: Optional[Dict[str, Any]] = None,
        template: Optional[Dict[str, Any]] = None,
        channel: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        pdf_bytes: Optional[bytes] = None,
        custom_message: Optional[str] = None,
        payment_link: Optional[str] = None,
        as_of_date: Optional[Union[date, str]] = None,
        communication_type: str = 'REMINDER',
        dispatched_by: Optional[int] = None,
        is_automated: bool = True,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Unified dispatch method for reminders and statements.

        Resolves preferred channel, renders subject and body templates,
        generates PDF account statement (if requested), dispatches across chosen
        channel(s), and logs audit events to t0122_customer_communications.
        """
        cust_id = customer.get('id') or 0
        cust_name = customer.get('name') or 'Valued Customer'
        active_tenant = business_id or customer.get('business_id') or get_current_tenant()

        # 1. Determine Target Channel
        # Hierarchy: explicit argument -> customer preferred channel -> rule channel -> default 'EMAIL'
        selected_channel = 'EMAIL'
        if channel:
            selected_channel = channel.upper()
        elif customer.get('preferred_reminder_channel'):
            selected_channel = customer.get('preferred_reminder_channel', 'EMAIL').upper()
        elif rule and rule.get('channel'):
            selected_channel = rule.get('channel', 'EMAIL').upper()

        if selected_channel in ('ALL', 'BOTH'):
            target_channels = ['EMAIL', 'WHATSAPP']
        elif selected_channel == 'WHATSAPP':
            target_channels = ['WHATSAPP']
        else:
            target_channels = ['EMAIL']

        # 2. Build Context for Interpolation
        merged_context: Dict[str, Any] = {
            'customer_id': cust_id,
            'customer_name': cust_name,
            'company_name': self.default_company_name,
            'as_of_date': str(as_of_date or date.today().isoformat()),
        }
        if context:
            merged_context.update(context)

        # Ensure payment link
        p_link = payment_link or merged_context.get('payment_link')
        if not p_link and (not rule or rule.get('include_payment_link', True)):
            p_link = self.generate_payment_link(customer_id=cust_id)
        merged_context['payment_link'] = p_link

        # Ensure balance metrics
        total_balance = float(merged_context.get('total_balance', customer.get('balance', 0.0) or 0.0))
        overdue_amount = float(merged_context.get('overdue_amount', total_balance))
        invoice_count = int(merged_context.get('invoice_count', 1))

        # 3. Handle PDF Statement Generation
        attach_pdf = True
        if rule is not None:
            attach_pdf = rule.get('attach_statement_pdf', True)

        statement_pdf_data = pdf_bytes
        if attach_pdf and statement_pdf_data is None:
            try:
                statement_pdf_data = self.statement_pdf_service.generate_statement_pdf_for_customer(
                    customer_id=cust_id,
                    as_of_date=as_of_date,
                    payment_link=p_link,
                    custom_message=custom_message,
                )
            except Exception as e:
                logger.warning('Failed to generate PDF statement for customer #%s: %s', cust_id, e)
                statement_pdf_data = None

        # 4. Resolve Templates
        subject_tpl = None
        body_tpl = None
        wa_template_name = None
        wa_namespace = None

        if template:
            subject_tpl = template.get('subject_template')
            body_tpl = template.get('body_template')
            wa_template_name = template.get('whatsapp_template_name')
            wa_namespace = template.get('whatsapp_namespace')

        # Fallback default templates if none provided
        if not subject_tpl:
            subject_tpl = f'Payment Reminder: Outstanding Balance for {cust_name}'
        if not body_tpl:
            body_tpl = (
                f'Dear {{{{customer_name}}}},\n\n'
                f'This is a friendly reminder from {{{{company_name}}}} that your account has an overdue '
                f'balance of {{{{overdue_amount}}}} (Total Balance: {{{{total_balance}}}} across {{{{invoice_count}}}} invoice(s)).\n\n'
                f'Please review your attached account statement and arrange payment at your earliest convenience.\n'
                f'Direct Payment Link: {{{{payment_link}}}}\n\n'
                f'Thank you for your business,\n{{{{company_name}}}} AR Department'
            )

        # Render Subject & Body
        rendered_subject = self.interpolate_template(subject_tpl, merged_context)
        rendered_body = self.interpolate_template(body_tpl, merged_context)

        # 5. Dispatch across Target Channels
        dispatch_results: List[Dict[str, Any]] = []

        recip_email = customer.get('reminder_email') or customer.get('email')
        recip_phone = customer.get('reminder_phone') or customer.get('phone')

        for ch in target_channels:
            tracking_num = self.generate_tracking_number(customer_id=cust_id, channel=ch)
            channel_result: Dict[str, Any] = {}

            if ch == 'EMAIL':
                if not recip_email:
                    channel_result = {
                        'success': False,
                        'channel': 'EMAIL',
                        'status': 'FAILED',
                        'recipient': 'N/A',
                        'error_message': f'Customer #{cust_id} has no email address configured',
                        'tracking_number': tracking_num,
                    }
                else:
                    email_html = (
                        f"<div style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;'>"
                        f"{rendered_body.replace(chr(10), '<br/>')}"
                        f"</div>"
                    )
                    send_res = self.send_email(
                        to_email=recip_email,
                        subject=rendered_subject,
                        html_body=email_html,
                        recipient_name=cust_name,
                        pdf_attachment_bytes=statement_pdf_data,
                        pdf_filename=f"Statement_{cust_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        metadata={'tracking_number': tracking_num, 'customer_id': cust_id},
                    )
                    channel_result = {**send_res, 'tracking_number': tracking_num}

            elif ch == 'WHATSAPP':
                if not recip_phone:
                    channel_result = {
                        'success': False,
                        'channel': 'WHATSAPP',
                        'status': 'FAILED',
                        'recipient': 'N/A',
                        'error_message': f'Customer #{cust_id} has no phone number configured',
                        'tracking_number': tracking_num,
                    }
                else:
                    # Prepare parameters if using WhatsApp template
                    wa_params = None
                    if wa_template_name:
                        wa_params = [
                            {'type': 'text', 'text': cust_name},
                            {'type': 'text', 'text': f'${overdue_amount:,.2f}'},
                            {'type': 'text', 'text': f'${total_balance:,.2f}'},
                            {'type': 'text', 'text': p_link or ''},
                        ]

                    send_res = self.send_whatsapp(
                        to_phone=recip_phone,
                        message_text=rendered_body,
                        template_name=wa_template_name,
                        template_namespace=wa_namespace,
                        template_parameters=wa_params,
                        metadata={'tracking_number': tracking_num, 'customer_id': cust_id},
                    )
                    channel_result = {**send_res, 'tracking_number': tracking_num}

            # 6. Log Communication Event to Database (t0122_customer_communications)
            comm_log_record = {
                'tracking_number': tracking_num,
                'customer_id': cust_id,
                'rule_id': rule.get('id') if rule else None,
                'template_id': template.get('id') if template else None,
                'channel': ch,
                'communication_type': communication_type,
                'recipient_address': recip_email if ch == 'EMAIL' else (recip_phone or 'N/A'),
                'recipient_name': cust_name,
                'subject': rendered_subject if ch == 'EMAIL' else None,
                'message_body': rendered_body,
                'status': channel_result.get('status', 'PENDING'),
                'delivery_timestamp': datetime.now(timezone.utc) if channel_result.get('success') else None,
                'error_message': channel_result.get('error_message'),
                'external_message_id': channel_result.get('external_message_id'),
                'statement_pdf_path': f'statements/{cust_id}/statement_{datetime.now().strftime("%Y%m%d")}.pdf' if statement_pdf_data else None,
                'statement_pdf_size': len(statement_pdf_data) if statement_pdf_data else None,
                'invoice_count': invoice_count,
                'total_balance': total_balance,
                'overdue_amount': overdue_amount,
                'payment_link': p_link,
                'dispatched_by': dispatched_by,
                'is_automated': is_automated,
                'metadata': {
                    'is_simulated': channel_result.get('is_simulated', self.simulator_mode),
                    'customer_group': customer.get('group_name'),
                },
                'is_active': True,
            }

            if self.communication_repo:
                try:
                    created_comm = self.communication_repo.create(comm_log_record)
                    channel_result['communication_id'] = created_comm.get('id') if isinstance(created_comm, dict) else getattr(created_comm, 'id', None)
                except Exception as ex:
                    logger.warning('Failed to insert communication audit record: %s', ex)
                    # Non-blocking for mock/simulated environments

            dispatch_results.append(channel_result)

        # 7. Summary response
        overall_success = all(r.get('success', False) for r in dispatch_results) if dispatch_results else False
        return {
            'success': overall_success,
            'customer_id': cust_id,
            'channels': target_channels,
            'results': dispatch_results,
            'rendered_subject': rendered_subject,
            'rendered_body': rendered_body,
            'payment_link': p_link,
            'pdf_generated': statement_pdf_data is not None,
            'pdf_size': len(statement_pdf_data) if statement_pdf_data else 0,
        }

    # ----------------------------------------------------------------------
    # 6. Webhook Status Callback Processing
    # ----------------------------------------------------------------------
    def process_whatsapp_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Meta WhatsApp Cloud API status webhook and update delivery receipts.

        Handles events: 'sent', 'delivered', 'read', 'failed'.
        """
        results: List[Dict[str, Any]] = []
        if not payload or not isinstance(payload, dict):
            return results

        # Meta Webhook payload format: entry[0].changes[0].value.statuses[0]
        entries = payload.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                val = change.get('value', {})
                statuses = val.get('statuses', [])
                for st in statuses:
                    wamid = st.get('id')
                    raw_status = str(st.get('status', '')).lower()
                    recip_id = st.get('recipient_id')
                    ts_unix = st.get('timestamp')
                    errors = st.get('errors')

                    status_map = {
                        'sent': 'SENT',
                        'delivered': 'DELIVERED',
                        'read': 'READ',
                        'failed': 'FAILED',
                    }
                    normalized_status = status_map.get(raw_status, 'PENDING')

                    event_dt = datetime.fromtimestamp(int(ts_unix), tz=timezone.utc) if ts_unix else datetime.now(timezone.utc)

                    update_info = {
                        'external_message_id': wamid,
                        'recipient_id': recip_id,
                        'status': normalized_status,
                        'raw_status': raw_status,
                        'timestamp': event_dt.isoformat(),
                        'error': errors[0] if errors and len(errors) > 0 else None,
                    }

                    # Update communication log if repo present
                    if self.communication_repo and wamid:
                        try:
                            # Find record by external_message_id
                            existing = self.communication_repo.list(filters={'external_message_id': wamid}, limit=1)
                            if existing and len(existing) > 0:
                                record_id = existing[0]['id']
                                update_fields: Dict[str, Any] = {'status': normalized_status}
                                if normalized_status == 'DELIVERED':
                                    update_fields['delivery_timestamp'] = event_dt
                                elif normalized_status == 'READ':
                                    update_fields['read_timestamp'] = event_dt
                                elif normalized_status == 'FAILED' and errors:
                                    update_fields['error_message'] = json.dumps(errors)
                                self.communication_repo.update(record_id, update_fields)
                                update_info['communication_id'] = record_id
                        except Exception as e:
                            logger.error('Error updating communication log from WhatsApp webhook: %s', e)

                    results.append(update_info)

        return results

    def process_email_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transactional email webhook (e.g. Resend, SendGrid) and update delivery receipts.

        Handles events: 'email.sent', 'email.delivered', 'email.opened', 'email.bounced', 'email.complained'.
        """
        if not payload or not isinstance(payload, dict):
            return {'status': 'IGNORED', 'reason': 'Invalid payload'}

        event_type = payload.get('type', '').lower()
        data = payload.get('data', {})
        email_id = data.get('email_id') or payload.get('id') or data.get('id')

        status_map = {
            'email.sent': 'SENT',
            'sent': 'SENT',
            'email.delivered': 'DELIVERED',
            'delivered': 'DELIVERED',
            'email.opened': 'READ',
            'email.clicked': 'READ',
            'opened': 'READ',
            'email.bounced': 'FAILED',
            'bounced': 'FAILED',
            'failed': 'FAILED',
        }
        normalized_status = status_map.get(event_type, 'PENDING')
        event_dt = datetime.now(timezone.utc)

        update_info = {
            'external_message_id': email_id,
            'event_type': event_type,
            'status': normalized_status,
            'timestamp': event_dt.isoformat(),
        }

        if self.communication_repo and email_id:
            try:
                existing = self.communication_repo.list(filters={'external_message_id': email_id}, limit=1)
                if existing and len(existing) > 0:
                    record_id = existing[0]['id']
                    update_fields: Dict[str, Any] = {'status': normalized_status}
                    if normalized_status == 'DELIVERED':
                        update_fields['delivery_timestamp'] = event_dt
                    elif normalized_status == 'READ':
                        update_fields['read_timestamp'] = event_dt
                    elif normalized_status == 'FAILED':
                        update_fields['error_message'] = str(data.get('error') or event_type)
                    self.communication_repo.update(record_id, update_fields)
                    update_info['communication_id'] = record_id
            except Exception as e:
                logger.error('Error updating communication log from Email webhook: %s', e)

        return update_info

    def process_webhook_status(self, provider: str, payload: Dict[str, Any]) -> Any:
        """Route webhook callback to appropriate provider handler."""
        provider_norm = str(provider).lower().strip()
        if provider_norm in ('whatsapp', 'meta', 'wa'):
            return self.process_whatsapp_webhook(payload)
        elif provider_norm in ('email', 'resend', 'sendgrid'):
            return self.process_email_webhook(payload)
        else:
            return {'error': f'Unsupported webhook provider: {provider}'}


# Singleton instance helper
reminder_dispatch_service = ReminderDispatchService()
