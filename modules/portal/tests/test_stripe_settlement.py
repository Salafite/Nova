import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from modules.portal.services.stripe_settlement_service import StripeSettlementService
from modules.portal.models.portal import (
    InvoiceCheckoutSessionRequest,
    BalanceSettlementCheckoutRequest,
    PortalCheckoutSessionResponse,
    PaymentSessionStatusResponse,
)


@pytest.fixture
def mock_portal_repo():
    repo = MagicMock()
    # Default customer setup
    repo.get_customer_by_id.return_value = {
        "id": 10,
        "name": "Acme Restaurant Group",
        "email": "buyer@acme.com",
        "balance": 1500.0,
        "credit_limit": 5000.0,
        "available_credit": 3500.0,
    }
    # Default invoice setup
    repo.get_invoice_by_id.return_value = {
        "id": 42,
        "invoice_number": "INV-2026-00042",
        "partner_id": 10,
        "total_amount": 500.0,
        "paid_amount": 0.0,
        "balance_due": 500.0,
        "status": "Unpaid",
        "stripe_checkout_session_id": None,
        "payment_link": None,
    }
    return repo


@pytest.fixture
def settlement_service(mock_portal_repo):
    return StripeSettlementService(portal_repo=mock_portal_repo)


def test_create_invoice_checkout_session_success(settlement_service, mock_portal_repo):
    with patch("modules.portal.services.stripe_settlement_service.create_settlement_checkout_session") as mock_stripe_create:
        mock_stripe_create.return_value = {
            "session_id": "cs_test_inv_42",
            "url": "https://checkout.stripe.com/pay/cs_test_inv_42",
            "amount": 500.0,
            "amount_cents": 50000,
            "currency": "usd",
            "settlement_type": "invoice",
            "status": "open",
        }

        req = InvoiceCheckoutSessionRequest(
            invoice_id=42,
            payment_method_types=["card", "us_bank_account"],
        )

        resp = settlement_service.create_invoice_checkout_session(
            customer_id=10,
            request=req,
            user_email="buyer@acme.com",
        )

        assert isinstance(resp, PortalCheckoutSessionResponse)
        assert resp.session_id == "cs_test_inv_42"
        assert resp.checkout_url == "https://checkout.stripe.com/pay/cs_test_inv_42"
        assert resp.amount == 500.0
        assert resp.amount_cents == 50000
        assert resp.settlement_type == "invoice"
        assert resp.invoice_id == 42
        assert "us_bank_account" in resp.payment_method_types

        # Verify repo updated invoice session
        mock_portal_repo.update_invoice_stripe_session.assert_called_once_with(
            invoice_id=42,
            session_id="cs_test_inv_42",
            payment_link="https://checkout.stripe.com/pay/cs_test_inv_42",
        )


def test_create_invoice_checkout_session_already_paid(settlement_service, mock_portal_repo):
    mock_portal_repo.get_invoice_by_id.return_value = {
        "id": 42,
        "invoice_number": "INV-2026-00042",
        "partner_id": 10,
        "total_amount": 500.0,
        "paid_amount": 500.0,
        "balance_due": 0.0,
        "status": "Paid",
    }

    req = InvoiceCheckoutSessionRequest(invoice_id=42)
    with pytest.raises(ValueError, match="already fully settled"):
        settlement_service.create_invoice_checkout_session(customer_id=10, request=req)


def test_create_invoice_checkout_session_not_owner(settlement_service, mock_portal_repo):
    mock_portal_repo.get_invoice_by_id.return_value = None
    req = InvoiceCheckoutSessionRequest(invoice_id=999)
    with pytest.raises(ValueError, match="was not found or does not belong"):
        settlement_service.create_invoice_checkout_session(customer_id=10, request=req)


def test_create_balance_settlement_session(settlement_service, mock_portal_repo):
    with patch("modules.portal.services.stripe_settlement_service.create_settlement_checkout_session") as mock_stripe_create:
        mock_stripe_create.return_value = {
            "session_id": "cs_test_bal_10",
            "url": "https://checkout.stripe.com/pay/cs_test_bal_10",
            "amount": 1000.0,
            "amount_cents": 100000,
            "currency": "usd",
            "settlement_type": "balance",
            "status": "open",
        }

        req = BalanceSettlementCheckoutRequest(
            amount=1000.0,
            invoice_ids=[42, 43],
            payment_method_types=["card", "us_bank_account"],
        )

        resp = settlement_service.create_balance_settlement_session(
            customer_id=10,
            request=req,
            user_email="buyer@acme.com",
        )

        assert resp.session_id == "cs_test_bal_10"
        assert resp.amount == 1000.0
        assert resp.settlement_type == "balance"


def test_get_session_status_and_security(settlement_service):
    with patch("modules.portal.services.stripe_settlement_service.get_checkout_session") as mock_get_sess:
        mock_get_sess.return_value = {
            "session_id": "cs_test_status",
            "status": "complete",
            "payment_status": "paid",
            "payment_intent_id": "pi_123",
            "amount_total": 500.0,
            "currency": "usd",
            "customer_email": "buyer@acme.com",
            "metadata": {"customer_id": "10", "invoice_id": "42"},
        }

        status_resp = settlement_service.get_session_status("cs_test_status", customer_id=10)
        assert isinstance(status_resp, PaymentSessionStatusResponse)
        assert status_resp.status == "complete"
        assert status_resp.payment_status == "paid"
        assert status_resp.customer_id == 10
        assert status_resp.invoice_id == 42

        # Customer mismatch security check
        with pytest.raises(ValueError, match="does not belong to the authenticated customer"):
            settlement_service.get_session_status("cs_test_status", customer_id=99)


def test_reconcile_checkout_session_single_invoice(settlement_service, mock_portal_repo):
    mock_portal_repo.reconcile_settlement_transaction.return_value = {
        "reconciled": True,
        "already_processed": False,
        "payment_id": 101,
        "customer_id": 10,
        "amount": 500.0,
        "invoice_id": 42,
        "invoices_updated": [42],
        "new_customer_balance": 1000.0,
        "journal_entry_id": 201,
        "journal_entry_reference": "JE-STRIPE-101",
        "session_id": "cs_test_inv_42",
        "payment_intent_id": "pi_test_inv_42",
    }

    session_data = {
        "id": "cs_test_inv_42",
        "payment_intent": "pi_test_inv_42",
        "amount_total": 50000,
        "currency": "usd",
        "payment_method_types": ["card"],
        "url": "https://checkout.stripe.com/pay/cs_test_inv_42",
        "metadata": {
            "customer_id": "10",
            "settlement_type": "invoice",
            "invoice_id": "42",
            "amount": "500.00",
            "amount_cents": "50000",
        },
    }

    result = settlement_service.reconcile_checkout_session(session_data)

    assert result["reconciled"] is True
    assert result["payment_id"] == 101
    assert result["invoice_id"] == 42
    assert result["new_customer_balance"] == 1000.0
    assert result["journal_entry_reference"] == "JE-STRIPE-101"

    mock_portal_repo.reconcile_settlement_transaction.assert_called_once_with(
        customer_id=10,
        amount=500.0,
        settlement_type="invoice",
        invoice_id=42,
        invoice_ids=None,
        session_id="cs_test_inv_42",
        payment_intent_id="pi_test_inv_42",
        payment_method="Stripe Card",
        payment_link="https://checkout.stripe.com/pay/cs_test_inv_42",
    )


def test_reconcile_checkout_session_ach_method(settlement_service, mock_portal_repo):
    mock_portal_repo.reconcile_settlement_transaction.return_value = {
        "reconciled": True,
        "payment_id": 102,
        "customer_id": 10,
        "amount": 1000.0,
    }

    session_data = {
        "id": "cs_test_ach",
        "payment_intent": "pi_test_ach",
        "amount_total": 100000,
        "payment_method_types": ["us_bank_account"],
        "metadata": {
            "customer_id": "10",
            "settlement_type": "balance",
            "amount": "1000.00",
        },
    }

    result = settlement_service.reconcile_checkout_session(session_data)
    assert result["reconciled"] is True
    mock_portal_repo.reconcile_settlement_transaction.assert_called_once_with(
        customer_id=10,
        amount=1000.0,
        settlement_type="balance",
        invoice_id=None,
        invoice_ids=None,
        session_id="cs_test_ach",
        payment_intent_id="pi_test_ach",
        payment_method="Stripe ACH",
        payment_link=None,
    )


def test_verify_and_reconcile_session(settlement_service):
    with patch("modules.portal.services.stripe_settlement_service.get_checkout_session") as mock_get_sess, \
         patch.object(settlement_service, "reconcile_checkout_session") as mock_reconcile:
        
        mock_get_sess.return_value = {
            "session_id": "cs_test_verify",
            "status": "complete",
            "payment_status": "paid",
            "metadata": {"customer_id": "10", "settlement_type": "invoice", "invoice_id": "42"},
        }
        mock_reconcile.return_value = {"reconciled": True, "payment_id": 103}

        res = settlement_service.verify_and_reconcile_session("cs_test_verify", customer_id=10)
        assert res["reconciled"] is True
        mock_reconcile.assert_called_once()


def test_portal_repo_reconcile_settlement_transaction_unit():
    """Direct test of PortalRepository reconciliation logic with mocked database cursor."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # idempotency: no existing payment
        {"id": 10, "name": "Acme", "balance": 1500.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},  # customer
        {"id": 55, "payment_date": date(2026, 8, 23), "invoice_id": 42, "partner_id": 10, "amount": 500.0, "payment_method": "Stripe Card", "reference": "pi_123", "status": "Completed", "notes": "Notes", "stripe_payment_intent_id": "pi_123", "stripe_checkout_session_id": "cs_123", "payment_link": None, "created_at": None},  # payment
        {"total_amount": 500.0},  # invoice total
        {"total_paid": 500.0},    # invoice paid sum
        {"balance": 1000.0},      # updated customer balance
        {"id": 1},                # COA bank account
        {"id": 2},                # COA AR account
        {"id": 301, "entry_date": date(2026, 8, 23), "reference": "JE-STRIPE-55", "description": "Stripe receipt", "status": "Posted", "created_at": None},  # JE header
        {"id": 1001, "journal_entry_id": 301, "account_id": 1, "debit": 500.0, "credit": 0.0, "description": "Bank debit"},  # JE line 1
        {"id": 1002, "journal_entry_id": 301, "account_id": 2, "debit": 0.0, "credit": 500.0, "description": "AR credit"},    # JE line 2
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        result = repo.reconcile_settlement_transaction(
            customer_id=10,
            amount=500.0,
            settlement_type="invoice",
            invoice_id=42,
            session_id="cs_123",
            payment_intent_id="pi_123",
            payment_method="Stripe Card",
        )

    assert result["reconciled"] is True
    assert result["already_processed"] is False
    assert result["payment_id"] == 55
    assert result["customer_id"] == 10
    assert result["amount"] == 500.0
    assert result["invoice_id"] == 42
    assert 42 in result["invoices_updated"]
    assert result["new_customer_balance"] == 1000.0
    assert result["journal_entry_id"] == 301
    assert result["journal_entry_reference"] == "JE-STRIPE-55"
    mock_conn.commit.assert_called_once()


def test_portal_repo_reconcile_idempotency():
    """Test that repeat reconciliations with same session/intent don't create duplicate entries."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # Idempotency check returns existing payment record
    mock_cur.fetchone.side_effect = [
        {
            "id": 55,
            "payment_date": date(2026, 8, 23),
            "invoice_id": 42,
            "partner_id": 10,
            "amount": 500.0,
            "payment_method": "Stripe Card",
            "reference": "pi_123",
            "status": "Completed",
            "notes": None,
            "stripe_payment_intent_id": "pi_123",
            "stripe_checkout_session_id": "cs_123",
            "payment_link": None,
            "created_at": None,
        },
        {"id": 10, "name": "Acme", "balance": 1000.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        result = repo.reconcile_settlement_transaction(
            customer_id=10,
            amount=500.0,
            settlement_type="invoice",
            invoice_id=42,
            session_id="cs_123",
            payment_intent_id="pi_123",
        )

    assert result["reconciled"] is True
    assert result["already_processed"] is True
    assert result["payment_id"] == 55
    assert result["journal_entry_id"] is None

