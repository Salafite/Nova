"""
Unit and Integration Tests for ReminderDispatchService.

Covers:
- Template variable interpolation (double & single braces, monetary formatting)
- Transactional email dispatch with PDF attachments (Simulator & Resend API)
- WhatsApp Business API dispatch (Simulator & Meta Cloud API)
- Multi-channel dispatch evaluation and customer preferences
- Database communication audit logging (t0122_customer_communications)
- Webhook status callback processing for delivery & read receipts
"""

import json
import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from modules.accounting.services.reminder_dispatch_service import (
    ReminderDispatchService,
    normalize_phone_number,
    is_valid_email,
)


@pytest.fixture
def sample_customer():
    return {
        'id': 101,
        'name': 'Bistro Gourmet LLC',
        'email': 'ap@bistrogourmet.com',
        'phone': '+1 (555) 234-5678',
        'group_name': 'Premium Restaurants',
        'credit_limit': 50000.0,
        'balance': 12500.0,
        'is_vip': False,
        'exclude_from_reminders': False,
        'preferred_reminder_channel': 'EMAIL',
        'reminder_phone': '+1 (555) 234-5678',
        'reminder_email': 'billing@bistrogourmet.com',
    }


@pytest.fixture
def mock_statement_pdf_service():
    service = MagicMock()
    service.generate_statement_pdf_for_customer.return_value = b'%PDF-1.4 Mock PDF Content %%EOF'
    return service


@pytest.fixture
def mock_comm_repo():
    repo = MagicMock()
    repo.create.return_value = {'id': 501, 'tracking_number': 'TRK-EMA-20260908-101-ABC123'}
    repo.list.return_value = [{'id': 501, 'external_message_id': 'msg_mock_123'}]
    repo.update.return_value = {'id': 501, 'status': 'DELIVERED'}
    return repo


class TestPhoneAndEmailValidation:
    """Test phone normalisation and email validation utilities."""

    def test_normalize_phone_number(self):
        assert normalize_phone_number('+1 (555) 234-5678') == '+15552345678'
        assert normalize_phone_number('5552345678') == '+15552345678'
        assert normalize_phone_number('15552345678') == '+15552345678'
        assert normalize_phone_number('+44 20 7946 0958') == '+442079460958'
        assert normalize_phone_number('') == ''
        assert normalize_phone_number(None) == ''

    def test_is_valid_email(self):
        assert is_valid_email('billing@bistrogourmet.com') is True
        assert is_valid_email('john.doe+test@sub.example.co.uk') is True
        assert is_valid_email('invalid-email') is False
        assert is_valid_email('user@') is False
        assert is_valid_email('@domain.com') is False
        assert is_valid_email(None) is False


class TestTemplateInterpolation:
    """Test variable placeholder interpolation across email and WhatsApp message bodies."""

    def test_interpolate_double_brackets(self):
        service = ReminderDispatchService(simulator_mode=True)
        template = (
            'Hello {{customer_name}}, your overdue balance is {{overdue_amount}} '
            '(Total: {{total_balance}}) for account #{{customer_id}}. Pay at {{payment_link}}.'
        )
        context = {
            'customer_name': 'Acme Cafe',
            'customer_id': 42,
            'overdue_amount': 3450.50,
            'total_balance': 5200.00,
            'payment_link': 'https://pay.novaerp.com/c/42',
        }

        result = service.interpolate_template(template, context)

        assert 'Hello Acme Cafe' in result
        assert '$3,450.50' in result
        assert '$5,200.00' in result
        assert 'account #42' in result
        assert 'https://pay.novaerp.com/c/42' in result

    def test_interpolate_single_brackets(self):
        service = ReminderDispatchService(simulator_mode=True)
        template = 'Reminder for {customer_name}: Balance {balance} is due.'
        context = {
            'customer_name': 'Green Grocers',
            'balance': 1200.0,
        }

        result = service.interpolate_template(template, context)
        assert 'Reminder for Green Grocers: Balance $1,200.00 is due.' == result

    def test_interpolate_with_missing_and_empty_template(self):
        service = ReminderDispatchService(simulator_mode=True)
        assert service.interpolate_template('', {}) == ''
        assert service.interpolate_template(None, {}) == ''

        # Preserves unmatched placeholders
        rendered = service.interpolate_template('Custom {{unmatched_key}} note', {'customer_name': 'Test'})
        assert 'Custom {{unmatched_key}} note' in rendered


class TestEmailDispatch:
    """Test email dispatch with simulated and real mock Resend client."""

    def test_send_email_simulator_mode(self):
        service = ReminderDispatchService(simulator_mode=True)
        pdf_content = b'%PDF-1.4 Mock PDF Statement %%EOF'

        res = service.send_email(
            to_email='ap@bistrogourmet.com',
            subject='Account Statement September 2026',
            html_body='<p>Your statement is attached.</p>',
            recipient_name='Bistro Gourmet',
            pdf_attachment_bytes=pdf_content,
            pdf_filename='Statement_101.pdf',
        )

        assert res['success'] is True
        assert res['channel'] == 'EMAIL'
        assert res['status'] == 'SENT'
        assert res['recipient'] == 'ap@bistrogourmet.com'
        assert res['external_message_id'].startswith('msg_mock_email_')
        assert res['attachment_size'] == len(pdf_content)
        assert res['is_simulated'] is True

    def test_send_email_invalid_address(self):
        service = ReminderDispatchService(simulator_mode=True)
        res = service.send_email(
            to_email='invalid-email-address',
            subject='Payment Reminder',
            html_body='<p>Test</p>',
        )

        assert res['success'] is False
        assert res['status'] == 'FAILED'
        assert 'Invalid email' in res['error_message']

    @patch('modules.accounting.services.reminder_dispatch_service.is_valid_email', return_value=True)
    def test_send_email_resend_integration(self, mock_val):
        with patch('resend.Emails.send') as mock_resend_send:
            mock_resend_send.return_value = {'id': 're_123456789'}

            service = ReminderDispatchService(
                resend_api_key='re_test_key_123',
                from_email='billing@novaerp.com',
                simulator_mode=False,
            )

            res = service.send_email(
                to_email='ap@bistrogourmet.com',
                subject='Urgent Payment Reminder',
                html_body='<p>Please settle balance.</p>',
                pdf_attachment_bytes=b'PDF_BYTES',
                pdf_filename='Statement.pdf',
            )

            assert res['success'] is True
            assert res['external_message_id'] == 're_123456789'
            assert res['is_simulated'] is False
            mock_resend_send.assert_called_once()


class TestWhatsAppDispatch:
    """Test WhatsApp messaging with simulated and mock Meta Cloud API."""

    def test_send_whatsapp_simulator_mode(self):
        service = ReminderDispatchService(simulator_mode=True)

        res = service.send_whatsapp(
            to_phone='+1 (555) 234-5678',
            message_text='Dear Customer, your invoice is overdue. Pay at https://pay.novaerp.com',
        )

        assert res['success'] is True
        assert res['channel'] == 'WHATSAPP'
        assert res['status'] == 'SENT'
        assert res['recipient'] == '+15552345678'
        assert res['external_message_id'].startswith('wamid.')
        assert res['is_simulated'] is True

    def test_send_whatsapp_invalid_phone(self):
        service = ReminderDispatchService(simulator_mode=True)
        res = service.send_whatsapp(to_phone='123', message_text='Hello')

        assert res['success'] is False
        assert res['status'] == 'FAILED'
        assert 'Invalid WhatsApp phone' in res['error_message']

    def test_send_whatsapp_meta_cloud_api_template(self):
        service = ReminderDispatchService(
            whatsapp_api_key='mock_meta_wa_token',
            whatsapp_phone_number_id='1000998877',
            simulator_mode=False,
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            'messaging_product': 'whatsapp',
            'contacts': [{'input': '15552345678', 'wa_id': '15552345678'}],
            'messages': [{'id': 'wamid.HBgLMockMetaMsg123'}],
        }

        with patch('httpx.Client.post', return_value=mock_resp) as mock_post:
            res = service.send_whatsapp(
                to_phone='+15552345678',
                template_name='payment_reminder_v1',
                template_namespace='nova_erp_ar',
                language_code='en_US',
                template_parameters=[
                    {'type': 'text', 'text': 'Bistro Gourmet'},
                    {'type': 'text', 'text': '$3,400.00'},
                ],
            )

            assert res['success'] is True
            assert res['external_message_id'] == 'wamid.HBgLMockMetaMsg123'
            assert res['is_simulated'] is False
            mock_post.assert_called_once()
            called_url = mock_post.call_args[0][0]
            assert '1000998877/messages' in called_url


class TestUnifiedReminderDispatch:
    """Test unified dispatch_reminder flow across channels, PDF generation, and DB audit logging."""

    def test_dispatch_email_reminder(self, sample_customer, mock_statement_pdf_service, mock_comm_repo):
        service = ReminderDispatchService(
            communication_repo=mock_comm_repo,
            statement_pdf_service=mock_statement_pdf_service,
            simulator_mode=True,
        )

        template = {
            'id': 1,
            'subject_template': 'Payment Reminder for {{customer_name}}',
            'body_template': 'Overdue amount: {{overdue_amount}}. Click {{payment_link}}.',
        }
        rule = {
            'id': 10,
            'attach_statement_pdf': True,
            'include_payment_link': True,
            'channel': 'EMAIL',
        }

        result = service.dispatch_reminder(
            customer=sample_customer,
            rule=rule,
            template=template,
            context={'overdue_amount': 4500.0, 'total_balance': 12500.0, 'invoice_count': 3},
        )

        assert result['success'] is True
        assert result['customer_id'] == 101
        assert 'EMAIL' in result['channels']
        assert len(result['results']) == 1
        assert result['results'][0]['status'] == 'SENT'
        assert result['pdf_generated'] is True
        assert result['payment_link'].startswith('https://')

        # Verify audit repo create call
        mock_comm_repo.create.assert_called_once()
        saved_payload = mock_comm_repo.create.call_args[0][0]
        assert saved_payload['customer_id'] == 101
        assert saved_payload['channel'] == 'EMAIL'
        assert saved_payload['overdue_amount'] == 4500.0

    def test_dispatch_both_channels(self, sample_customer, mock_statement_pdf_service, mock_comm_repo):
        service = ReminderDispatchService(
            communication_repo=mock_comm_repo,
            statement_pdf_service=mock_statement_pdf_service,
            simulator_mode=True,
        )

        result = service.dispatch_reminder(
            customer=sample_customer,
            channel='BOTH',
            custom_message='Please wire the balance before Friday.',
        )

        assert result['success'] is True
        assert set(result['channels']) == {'EMAIL', 'WHATSAPP'}
        assert len(result['results']) == 2
        assert all(r['status'] == 'SENT' for r in result['results'])
        assert mock_comm_repo.create.call_count == 2


class TestWebhookProcessing:
    """Test webhook status callback parsing for WhatsApp and Transactional Email."""

    def test_process_whatsapp_status_webhook(self, mock_comm_repo):
        service = ReminderDispatchService(communication_repo=mock_comm_repo, simulator_mode=True)

        payload = {
            'object': 'whatsapp_business_account',
            'entry': [
                {
                    'id': 'WHATSAPP_BUSINESS_ACCOUNT_ID',
                    'changes': [
                        {
                            'value': {
                                'messaging_product': 'whatsapp',
                                'metadata': {'display_phone_number': '15550001111', 'phone_number_id': '1000998877'},
                                'statuses': [
                                    {
                                        'id': 'wamid.HBgLMockMetaMsg123',
                                        'status': 'delivered',
                                        'timestamp': '1788853083',
                                        'recipient_id': '15552345678',
                                    }
                                ],
                            },
                            'field': 'messages',
                        }
                    ],
                }
            ],
        }

        results = service.process_whatsapp_webhook(payload)
        assert len(results) == 1
        assert results[0]['status'] == 'DELIVERED'
        assert results[0]['external_message_id'] == 'wamid.HBgLMockMetaMsg123'

        mock_comm_repo.update.assert_called_once()
        update_args = mock_comm_repo.update.call_args[0]
        assert update_args[0] == 501
        assert update_args[1]['status'] == 'DELIVERED'
        assert 'delivery_timestamp' in update_args[1]

    def test_process_email_webhook_delivered(self, mock_comm_repo):
        service = ReminderDispatchService(communication_repo=mock_comm_repo, simulator_mode=True)

        payload = {
            'type': 'email.delivered',
            'created_at': '2026-09-08T10:30:00.000Z',
            'data': {
                'email_id': 'msg_mock_123',
                'from': 'billing@novaerp.com',
                'to': ['ap@bistrogourmet.com'],
                'subject': 'Payment Reminder',
            },
        }

        res = service.process_email_webhook(payload)
        assert res['status'] == 'DELIVERED'
        assert res['external_message_id'] == 'msg_mock_123'
        assert res['communication_id'] == 501

        mock_comm_repo.update.assert_called()

    def test_process_generic_webhook_router(self, mock_comm_repo):
        service = ReminderDispatchService(communication_repo=mock_comm_repo, simulator_mode=True)

        email_payload = {
            'type': 'email.opened',
            'data': {'email_id': 'msg_mock_123'},
        }
        res = service.process_webhook_status('resend', email_payload)
        assert res['status'] == 'READ'
