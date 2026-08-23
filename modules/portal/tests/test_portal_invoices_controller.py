import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.auth.jwt import create_access_token
from modules.portal.models.portal import (
    PortalCheckoutSessionResponse,
    PaymentSessionStatusResponse,
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


class TestPortalInvoicesEndpoints:
    def test_list_invoices_authenticated(self, client, portal_headers, portal_user):
        mock_invoices = [
            {
                "id": 101,
                "invoice_number": "INV-2026-00101",
                "invoice_type": "Sales",
                "partner_id": 50,
                "customer_name": "Bistro Bella",
                "sales_order_id": 501,
                "sales_order_number": "SO-00501",
                "issue_date": "2026-08-20",
                "due_date": "2026-09-20",
                "total_amount": 450.0,
                "paid_amount": 0.0,
                "balance_due": 450.0,
                "status": "Unpaid",
                "notes": "Net 30 terms",
                "stripe_payment_intent_id": None,
                "stripe_checkout_session_id": None,
                "payment_link": None,
                "created_at": "2026-08-20T10:00:00Z",
                "created_by": 1,
                "updated_at": "2026-08-20T10:00:00Z",
                "updated_by": 1,
                "update_number": 1,
            }
        ]

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.PortalRepository.get_invoices', return_value=(mock_invoices, 1)):
            resp = client.get('/api/portal/invoices?status=Unpaid&page=1&limit=20', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['total'] == 1
            assert len(data['items']) == 1
            assert data['items'][0]['invoice_number'] == 'INV-2026-00101'
            assert data['items'][0]['balance_due'] == 450.0

    def test_list_invoices_unauthorized(self, client):
        resp = client.get('/api/portal/invoices')
        assert resp.status_code in (401, 403)

    def test_list_invoices_forbidden_without_customer(self, client, non_portal_headers, non_portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=non_portal_user):
            resp = client.get('/api/portal/invoices', headers=non_portal_headers)
            assert resp.status_code == 403

    def test_get_invoice_detail_found(self, client, portal_headers, portal_user):
        mock_invoice = {
            "id": 101,
            "invoice_number": "INV-2026-00101",
            "invoice_type": "Sales",
            "partner_id": 50,
            "customer_name": "Bistro Bella",
            "sales_order_id": 501,
            "sales_order_number": "SO-00501",
            "issue_date": date(2026, 8, 20),
            "due_date": date(2026, 9, 20),
            "total_amount": 450.0,
            "paid_amount": 0.0,
            "balance_due": 450.0,
            "status": "Unpaid",
            "notes": "Net 30 terms",
            "stripe_payment_intent_id": None,
            "stripe_checkout_session_id": None,
            "payment_link": None,
        }

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.PortalRepository.get_invoice_by_id', return_value=mock_invoice):
            resp = client.get('/api/portal/invoices/101', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['id'] == 101
            assert data['invoice_number'] == 'INV-2026-00101'
            assert data['balance_due'] == 450.0

    def test_get_invoice_detail_not_found(self, client, portal_headers, portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.PortalRepository.get_invoice_by_id', return_value=None):
            resp = client.get('/api/portal/invoices/999', headers=portal_headers)

            assert resp.status_code == 404
            assert "Invoice #999 not found" in resp.json()['detail']

    def test_download_invoice_pdf(self, client, portal_headers, portal_user):
        fake_pdf = b"%PDF-1.4 Fake PDF Content for Invoice"

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.InvoicePdfService.generate_invoice_pdf', return_value=fake_pdf):
            resp = client.get('/api/portal/invoices/101/pdf', headers=portal_headers)

            assert resp.status_code == 200
            assert resp.headers['content-type'] == 'application/pdf'
            assert 'filename="invoice_101.pdf"' in resp.headers.get('content-disposition', '')
            assert resp.content == fake_pdf

    def test_download_invoice_pdf_not_found(self, client, portal_headers, portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.InvoicePdfService.generate_invoice_pdf', side_effect=ValueError("Invoice #999 was not found")):
            resp = client.get('/api/portal/invoices/999/pdf', headers=portal_headers)

            assert resp.status_code == 404
            assert "Invoice #999 was not found" in resp.json()['detail']


class TestPortalStripeCheckoutEndpoints:
    def test_create_invoice_checkout_session(self, client, portal_headers, portal_user):
        mock_checkout_resp = PortalCheckoutSessionResponse(
            session_id='cs_test_invoice_session_123',
            checkout_url='https://checkout.stripe.com/pay/cs_test_invoice_session_123',
            customer_id=50,
            amount=450.0,
            amount_cents=45000,
            currency='usd',
            settlement_type='invoice',
            invoice_id=101,
            payment_method_types=['card', 'us_bank_account'],
            status='open',
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.StripeSettlementService.create_invoice_checkout_session', return_value=mock_checkout_resp):
            payload = {
                'payment_method_types': ['card', 'us_bank_account'],
            }
            resp = client.post('/api/portal/invoices/101/checkout-session', json=payload, headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['session_id'] == 'cs_test_invoice_session_123'
            assert data['checkout_url'] == 'https://checkout.stripe.com/pay/cs_test_invoice_session_123'
            assert data['amount'] == 450.0
            assert data['invoice_id'] == 101

    def test_create_invoice_checkout_already_paid_error(self, client, portal_headers, portal_user):
        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.StripeSettlementService.create_invoice_checkout_session', side_effect=ValueError("Invoice #INV-101 is already fully settled.")):
            resp = client.post('/api/portal/invoices/101/checkout-session', json={}, headers=portal_headers)

            assert resp.status_code == 400
            assert "already fully settled" in resp.json()['detail']

    def test_create_balance_settlement_checkout_session(self, client, portal_headers, portal_user):
        mock_checkout_resp = PortalCheckoutSessionResponse(
            session_id='cs_test_balance_session_456',
            checkout_url='https://checkout.stripe.com/pay/cs_test_balance_session_456',
            customer_id=50,
            amount=1500.0,
            amount_cents=150000,
            currency='usd',
            settlement_type='balance',
            invoice_id=None,
            payment_method_types=['card', 'us_bank_account'],
            status='open',
        )

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.StripeSettlementService.create_balance_settlement_session', return_value=mock_checkout_resp):
            payload = {
                'amount': 1500.0,
                'payment_method_types': ['card', 'us_bank_account'],
            }
            resp = client.post('/api/portal/settlement/checkout-session', json=payload, headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['session_id'] == 'cs_test_balance_session_456'
            assert data['settlement_type'] == 'balance'
            assert data['amount'] == 1500.0

    def test_get_or_verify_settlement_session(self, client, portal_headers, portal_user):
        mock_reconciliation_result = {
            "reconciled": True,
            "already_processed": False,
            "payment_id": 99,
            "customer_id": 50,
            "amount": 450.0,
            "invoice_id": 101,
            "invoices_updated": [101],
            "new_customer_balance": 0.0,
            "journal_entry_id": 201,
            "journal_entry_reference": "JE-STRIPE-99",
            "session_id": "cs_test_123",
            "payment_intent_id": "pi_test_123",
        }

        with patch('packages.auth.deps.get_user_by_id', return_value=portal_user), \
             patch('modules.portal.controllers.portal_invoices_controller.StripeSettlementService.verify_and_reconcile_session', return_value=mock_reconciliation_result):
            resp = client.get('/api/portal/settlement/session/cs_test_123?verify=true', headers=portal_headers)

            assert resp.status_code == 200
            data = resp.json()
            assert data['reconciled'] is True
            assert data['payment_id'] == 99
            assert data['journal_entry_reference'] == 'JE-STRIPE-99'
