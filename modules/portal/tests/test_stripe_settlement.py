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
        {"total_paid": 500.0},  # total paid query from t0091
        {"total_amount": 500.0},  # total amount query from t0090
        {"id": 42, "total_amount": 500.0, "status": "Paid"},  # updated invoice
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


def test_portal_repo_reconcile_settlement_multiple_invoices():
    """Test PortalRepository reconciliation logic with multiple specific invoice IDs."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # idempotency: no existing payment
        {"id": 10, "name": "Acme", "balance": 1500.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},  # customer
        {"id": 56, "payment_date": date(2026, 8, 23), "invoice_id": None, "partner_id": 10, "amount": 800.0, "payment_method": "Stripe ACH", "reference": "cs_ach_800", "status": "Completed", "notes": "Notes", "stripe_payment_intent_id": None, "stripe_checkout_session_id": "cs_ach_800", "payment_link": None, "created_at": None},  # payment
        # invoice 1
        {"total_paid": 400.0},
        {"total_amount": 400.0},
        {"id": 41},
        # invoice 2
        {"total_paid": 400.0},
        {"total_amount": 400.0},
        {"id": 42},
        # customer balance
        {"balance": 700.0},
        # COA bank and AR
        {"id": 1},
        {"id": 2},
        # JE
        {"id": 302, "entry_date": date(2026, 8, 23), "reference": "JE-STRIPE-56", "description": "Stripe receipt", "status": "Posted", "created_at": None},
        {"id": 1003},
        {"id": 1004},
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        result = repo.reconcile_settlement_transaction(
            customer_id=10,
            amount=800.0,
            settlement_type="balance",
            invoice_ids=[41, 42],
            session_id="cs_ach_800",
            payment_method="Stripe ACH",
        )

    assert result["reconciled"] is True
    assert result["payment_id"] == 56
    assert result["customer_id"] == 10
    assert result["amount"] == 800.0
    assert result["invoices_updated"] == [41, 42]
    assert result["new_customer_balance"] == 700.0
    assert result["journal_entry_id"] == 302


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


def test_create_invoice_checkout_session_cancelled_invoice_raises(settlement_service, mock_portal_repo):
    mock_portal_repo.get_invoice_by_id.return_value = {
        "id": 42,
        "invoice_number": "INV-2026-00042",
        "partner_id": 10,
        "total_amount": 500.0,
        "paid_amount": 0.0,
        "balance_due": 500.0,
        "status": "Cancelled",
    }
    req = InvoiceCheckoutSessionRequest(invoice_id=42)
    with pytest.raises(ValueError, match="has been cancelled"):
        settlement_service.create_invoice_checkout_session(customer_id=10, request=req)


def test_create_invoice_checkout_session_customer_not_found(settlement_service, mock_portal_repo):
    mock_portal_repo.get_customer_by_id.return_value = None
    req = InvoiceCheckoutSessionRequest(invoice_id=42)
    with pytest.raises(ValueError, match="does not exist"):
        settlement_service.create_invoice_checkout_session(customer_id=999, request=req)


def test_create_balance_settlement_session_invalid_amount(settlement_service):
    with pytest.raises(Exception):
        BalanceSettlementCheckoutRequest(amount=0.0)

    mock_req = MagicMock()
    mock_req.amount = -10.0
    mock_req.invoice_ids = None
    with pytest.raises(ValueError, match="must be greater than zero"):
        settlement_service.create_balance_settlement_session(customer_id=10, request=mock_req)



def test_create_balance_settlement_session_invoice_not_found(settlement_service, mock_portal_repo):
    mock_portal_repo.get_invoice_by_id.return_value = None
    req = BalanceSettlementCheckoutRequest(amount=500.0, invoice_ids=[999])
    with pytest.raises(ValueError, match="was not found or does not belong"):
        settlement_service.create_balance_settlement_session(customer_id=10, request=req)


def test_reconcile_checkout_session_skipped_no_customer_id(settlement_service):
    session_data = {
        "id": "cs_test_no_meta",
        "metadata": {},
    }
    res = settlement_service.reconcile_checkout_session(session_data)
    assert res.get("skipped") is True


def test_reconcile_payment_intent_success(settlement_service, mock_portal_repo):
    mock_portal_repo.reconcile_settlement_transaction.return_value = {
        "reconciled": True,
        "payment_id": 105,
        "customer_id": 10,
        "amount": 250.0,
        "invoice_id": 42,
    }

    pi_data = {
        "id": "pi_test_portal_intent",
        "amount": 25000,
        "payment_method_types": ["card"],
        "metadata": {
            "customer_id": "10",
            "settlement_type": "invoice",
            "invoice_id": "42",
        },
    }

    res = settlement_service.reconcile_payment_intent(pi_data)
    assert res["reconciled"] is True
    assert res["payment_id"] == 105
    mock_portal_repo.reconcile_settlement_transaction.assert_called_once_with(
        customer_id=10,
        amount=250.0,
        settlement_type="invoice",
        invoice_id=42,
        invoice_ids=None,
        session_id=None,
        payment_intent_id="pi_test_portal_intent",
        payment_method="Stripe Card",
        payment_link=None,
    )


def test_reconcile_payment_intent_skipped_without_customer_id(settlement_service):
    pi_data = {
        "id": "pi_test_no_cust",
        "metadata": {"other": "value"},
    }
    res = settlement_service.reconcile_payment_intent(pi_data)
    assert res.get("skipped") is True


def test_verify_and_reconcile_session_unpaid_not_reconciled(settlement_service):
    with patch("modules.portal.services.stripe_settlement_service.get_checkout_session") as mock_get_sess:
        mock_get_sess.return_value = {
            "session_id": "cs_test_unpaid",
            "status": "open",
            "payment_status": "unpaid",
            "metadata": {"customer_id": "10"},
        }
        res = settlement_service.verify_and_reconcile_session("cs_test_unpaid", customer_id=10)
        assert res["reconciled"] is False
        assert res["status"] == "open"
        assert res["payment_status"] == "unpaid"


def test_create_invoice_checkout_session_custom_urls(settlement_service, mock_portal_repo):
    with patch("modules.portal.services.stripe_settlement_service.create_settlement_checkout_session") as mock_stripe_create:
        mock_stripe_create.return_value = {
            "session_id": "cs_test_custom_url",
            "url": "https://checkout.stripe.com/pay/cs_test_custom_url",
            "amount": 500.0,
            "amount_cents": 50000,
            "currency": "usd",
            "settlement_type": "invoice",
            "status": "open",
        }

        req = InvoiceCheckoutSessionRequest(
            invoice_id=42,
            success_url="https://portal.mycompany.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://portal.mycompany.com/cancel",
        )

        resp = settlement_service.create_invoice_checkout_session(
            customer_id=10,
            request=req,
            user_email="buyer@acme.com",
        )

        assert resp.session_id == "cs_test_custom_url"
        mock_stripe_create.assert_called_once()
        kwargs = mock_stripe_create.call_args[1]
        assert kwargs["success_url"] == "https://portal.mycompany.com/success?session_id={CHECKOUT_SESSION_ID}"
        assert kwargs["cancel_url"] == "https://portal.mycompany.com/cancel"


def test_create_balance_settlement_session_custom_urls(settlement_service, mock_portal_repo):
    with patch("modules.portal.services.stripe_settlement_service.create_settlement_checkout_session") as mock_stripe_create:
        mock_stripe_create.return_value = {
            "session_id": "cs_test_bal_custom",
            "url": "https://checkout.stripe.com/pay/cs_test_bal_custom",
            "amount": 800.0,
            "amount_cents": 80000,
            "currency": "usd",
            "settlement_type": "balance",
            "status": "open",
        }

        req = BalanceSettlementCheckoutRequest(
            amount=800.0,
            success_url="https://portal.mycompany.com/success",
            cancel_url="https://portal.mycompany.com/cancel",
        )

        resp = settlement_service.create_balance_settlement_session(
            customer_id=10,
            request=req,
            user_email="buyer@acme.com",
        )

        assert resp.session_id == "cs_test_bal_custom"
        kwargs = mock_stripe_create.call_args[1]
        assert kwargs["success_url"] == "https://portal.mycompany.com/success"
        assert kwargs["cancel_url"] == "https://portal.mycompany.com/cancel"


def test_portal_repo_reconcile_partial_invoice_payment():
    """Test that paying less than invoice total sets invoice status to 'Partially Paid'."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # idempotency
        {"id": 10, "name": "Acme", "balance": 1500.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},  # customer
        {"id": 60, "payment_date": date(2026, 8, 23), "invoice_id": 42, "partner_id": 10, "amount": 200.0, "payment_method": "Stripe Card", "reference": "pi_part_123", "status": "Completed", "notes": "Notes", "stripe_payment_intent_id": "pi_part_123", "stripe_checkout_session_id": "cs_part_123", "payment_link": None, "created_at": None},  # payment
        {"total_paid": 200.0},   # total paid so far
        {"total_amount": 500.0}, # invoice total is 500
        {"id": 42, "total_amount": 500.0, "status": "Partially Paid"}, # invoice updated
        {"balance": 1300.0},     # customer balance
        {"id": 1},               # Bank account
        {"id": 2},               # AR account
        {"id": 305, "entry_date": date(2026, 8, 23), "reference": "JE-STRIPE-60", "description": "Stripe receipt", "status": "Posted", "created_at": None},
        {"id": 1009},
        {"id": 1010},
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        result = repo.reconcile_settlement_transaction(
            customer_id=10,
            amount=200.0,
            settlement_type="invoice",
            invoice_id=42,
            session_id="cs_part_123",
            payment_intent_id="pi_part_123",
            payment_method="Stripe Card",
        )

    assert result["reconciled"] is True
    assert result["amount"] == 200.0
    assert result["new_customer_balance"] == 1300.0
    assert result["journal_entry_id"] == 305


def test_portal_repo_reconcile_general_balance_open_invoices_auto_paid():
    """Test general balance settlement where unpaid invoices are auto-marked Paid if covered."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # idempotency
        {"id": 10, "name": "Acme", "balance": 600.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},  # customer
        {"id": 70, "payment_date": date(2026, 8, 23), "invoice_id": None, "partner_id": 10, "amount": 600.0, "payment_method": "Stripe Card", "reference": "pi_bal_70", "status": "Completed", "notes": "Notes", "stripe_payment_intent_id": "pi_bal_70", "stripe_checkout_session_id": "cs_bal_70", "payment_link": None, "created_at": None},
        # total_paid for open invoice 1
        {"total_paid": 300.0},
        # update invoice 1
        {"id": 10},
        # customer balance
        {"balance": 0.0},
        {"id": 1},
        {"id": 2},
        {"id": 310, "entry_date": date(2026, 8, 23), "reference": "JE-STRIPE-70", "description": "Stripe receipt", "status": "Posted", "created_at": None},
        {"id": 1015},
        {"id": 1016},
    ]

    mock_cur.fetchall.side_effect = [
        [{"id": 10, "total_amount": 300.0}], # open invoices query
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        result = repo.reconcile_settlement_transaction(
            customer_id=10,
            amount=600.0,
            settlement_type="balance",
            invoice_id=None,
            invoice_ids=None,
            session_id="cs_bal_70",
            payment_intent_id="pi_bal_70",
            payment_method="Stripe Card",
        )

    assert result["reconciled"] is True
    assert result["payment_id"] == 70
    assert result["new_customer_balance"] == 0.0
    assert result["invoices_updated"] == [10]


def test_portal_repo_reconcile_db_error_triggers_rollback():
    """Test that a database exception during reconciliation triggers a rollback and raises."""
    from modules.portal.repositories.portal_repo import PortalRepository

    repo = PortalRepository()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # idempotency check with session_id
        {"id": 10, "name": "Acme", "balance": 1000.0, "credit_limit": 5000.0, "min_order_amount": 0.0, "order_cutoff_time": None, "allow_reorders": True, "default_price_list_id": None, "default_tax_rate_id": None, "payment_term_id": None, "is_active": True},
        Exception("Database disk error during payment insertion"),
    ]

    with patch("modules.portal.repositories.portal_repo.get_connection", return_value=mock_conn), \
         patch("modules.portal.repositories.portal_repo.release_connection"):
        with pytest.raises(Exception, match="Database disk error"):
            repo.reconcile_settlement_transaction(
                customer_id=10,
                amount=500.0,
                settlement_type="invoice",
                invoice_id=42,
                session_id="cs_test_err_rollback",
            )

    mock_conn.rollback.assert_called_once()


def test_stripe_settlement_service_default_init():
    service = StripeSettlementService()
    assert service.portal_repo is not None


def test_reconcile_checkout_session_missing_amount():
    from modules.portal.services.stripe_settlement_service import StripeSettlementService
    mock_repo = MagicMock()
    service = StripeSettlementService(portal_repo=mock_repo)

    mock_repo.reconcile_settlement_transaction.return_value = {
        "reconciled": True,
        "payment_id": 99,
    }

    session_data = {
        "id": "cs_test_fallback_amt",
        "amount_total": 0,
        "payment_method_types": ["card"],
        "metadata": {
            "customer_id": "10",
            "settlement_type": "invoice",
            "invoice_id": "42",
            "amount": "150.75",
        },
    }

    res = service.reconcile_checkout_session(session_data)
    assert res["reconciled"] is True
    mock_repo.reconcile_settlement_transaction.assert_called_once_with(
        customer_id=10,
        amount=150.75,
        settlement_type="invoice",
        invoice_id=42,
        invoice_ids=None,
        session_id="cs_test_fallback_amt",
        payment_intent_id=None,
        payment_method="Stripe Card",
        payment_link=None,
    )




