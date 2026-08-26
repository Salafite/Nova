import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from modules.sales.services.credit_service import CreditService, _to_float, _parse_date


def test_to_float_helper():
    assert _to_float(100) == 100.0
    assert _to_float("125.50") == 125.50
    assert _to_float(None) == 0.0
    assert _to_float("invalid") == 0.0


def test_parse_date_helper():
    today = date(2026, 8, 25)
    assert _parse_date(today) == today
    assert _parse_date("2026-08-25") == today
    assert _parse_date("2026-08-25T14:30:00Z") == today
    assert _parse_date(None) is None
    assert _parse_date("invalid-date") is None


def test_get_overdue_invoices():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    eval_date = date(2026, 8, 25)
    # Invoices setup
    # 1. 40 days overdue (due 2026-07-16) -> overdue > 30 days
    # 2. 10 days overdue (due 2026-08-15) -> not > 30 days overdue
    # 3. 45 days overdue (due 2026-07-11) but Paid -> ignored
    # 4. 50 days overdue (due 2026-07-06) but Cancelled -> ignored
    # 5. Future invoice (due 2026-09-01) -> not overdue
    mock_inv_repo.list.return_value = [
        {
            "id": 1,
            "invoice_number": "INV-001",
            "partner_id": 10,
            "issue_date": "2026-06-16",
            "due_date": "2026-07-16",
            "total_amount": 1500.00,
            "status": "Issued",
        },
        {
            "id": 2,
            "invoice_number": "INV-002",
            "partner_id": 10,
            "issue_date": "2026-07-15",
            "due_date": "2026-08-15",
            "total_amount": 800.00,
            "status": "Sent",
        },
        {
            "id": 3,
            "invoice_number": "INV-003",
            "partner_id": 10,
            "issue_date": "2026-06-01",
            "due_date": "2026-07-11",
            "total_amount": 2000.00,
            "status": "Paid",
        },
        {
            "id": 4,
            "invoice_number": "INV-004",
            "partner_id": 10,
            "issue_date": "2026-06-01",
            "due_date": "2026-07-06",
            "total_amount": 500.00,
            "status": "Cancelled",
        },
        {
            "id": 5,
            "invoice_number": "INV-005",
            "partner_id": 10,
            "issue_date": "2026-08-01",
            "due_date": "2026-09-01",
            "total_amount": 1200.00,
            "status": "Draft",
        },
    ]

    overdue = service.get_overdue_invoices(customer_id=10, threshold_days=30, as_of_date=eval_date)
    assert len(overdue) == 1
    assert overdue[0]["invoice_number"] == "INV-001"
    assert overdue[0]["days_overdue"] == 40
    assert overdue[0]["total_amount"] == 1500.00


def test_evaluate_order_credit_clean_account():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 10,
        "name": "Acme Corp",
        "credit_limit": 10000.00,
        "balance": 2000.00,
    }
    mock_inv_repo.list.return_value = []

    res = service.evaluate_order_credit(customer_id=10, order_amount=3000.00)
    assert res["is_hold_required"] is False
    assert res["hold_reason"] is None
    assert res["credit_limit_exceeded"] is False
    assert res["has_overdue_invoices"] is False
    assert res["available_credit"] == 8000.00
    assert res["total_exposure"] == 5000.00


def test_evaluate_order_credit_limit_exceeded():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 10,
        "name": "Acme Corp",
        "credit_limit": 5000.00,
        "balance": 4000.00,
    }
    mock_inv_repo.list.return_value = []

    res = service.evaluate_order_credit(customer_id=10, order_amount=1500.00)
    assert res["is_hold_required"] is True
    assert res["credit_limit_exceeded"] is True
    assert res["has_overdue_invoices"] is False
    assert "Customer credit limit exceeded" in res["hold_reason"]
    assert "Total exposure $5,500.00 > Limit $5,000.00" in res["hold_reason"]


def test_evaluate_order_credit_overdue_invoices_hold():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 20,
        "name": "Beta LLC",
        "credit_limit": 50000.00,
        "balance": 1000.00,
    }
    eval_date = date(2026, 8, 25)
    mock_inv_repo.list.return_value = [
        {
            "id": 101,
            "invoice_number": "INV-101",
            "partner_id": 20,
            "due_date": "2026-06-01",
            "total_amount": 2500.00,
            "status": "Overdue",
        },
        {
            "id": 102,
            "invoice_number": "INV-102",
            "partner_id": 20,
            "due_date": "2026-06-15",
            "total_amount": 1700.00,
            "status": "Issued",
        },
    ]

    res = service.evaluate_order_credit(customer_id=20, order_amount=500.00, as_of_date=eval_date)
    assert res["is_hold_required"] is True
    assert res["credit_limit_exceeded"] is False
    assert res["has_overdue_invoices"] is True
    assert res["overdue_invoices_count"] == 2
    assert res["overdue_invoices_amount"] == 4200.00
    assert "Customer has 2 invoices overdue by >30 days" in res["hold_reason"]
    assert "$4,200.00" in res["hold_reason"]


def test_evaluate_order_credit_both_limit_and_overdue_exceeded():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 30,
        "name": "Gamma Enterprises",
        "credit_limit": 5000.00,
        "balance": 4500.00,
    }
    eval_date = date(2026, 8, 25)
    mock_inv_repo.list.return_value = [
        {
            "id": 201,
            "invoice_number": "INV-201",
            "partner_id": 30,
            "due_date": "2026-05-01",
            "total_amount": 1200.00,
            "status": "Overdue",
        }
    ]

    res = service.evaluate_order_credit(customer_id=30, order_amount=1000.00, as_of_date=eval_date)
    assert res["is_hold_required"] is True
    assert res["credit_limit_exceeded"] is True
    assert res["has_overdue_invoices"] is True
    assert "Customer credit limit exceeded" in res["hold_reason"]
    assert "Customer has 1 invoice overdue by >30 days" in res["hold_reason"]


def test_get_customer_credit_status():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 40,
        "name": "Delta Traders",
        "credit_limit": 20000.00,
        "balance": 5000.00,
    }
    eval_date = date(2026, 8, 25)
    mock_inv_repo.list.return_value = [
        {
            "id": 301,
            "invoice_number": "INV-301",
            "partner_id": 40,
            "due_date": "2026-06-01",
            "total_amount": 3500.00,
            "status": "Overdue",
        }
    ]
    mock_order_repo.list.return_value = [
        {
            "id": 501,
            "order_number": "SO-501",
            "status": "Credit Hold",
        }
    ]

    status = service.get_customer_credit_status(customer_id=40, as_of_date=eval_date)
    assert status is not None
    assert status["customer_id"] == 40
    assert status["customer_name"] == "Delta Traders"
    assert status["credit_limit"] == 20000.00
    assert status["balance"] == 5000.00
    assert status["available_credit"] == 15000.00
    assert status["has_overdue_invoices"] is True
    assert status["overdue_invoices_count"] == 1
    assert status["overdue_invoices_amount"] == 3500.00
    assert status["on_hold"] is True
    assert status["has_hold_orders"] is True
    assert status["hold_orders_count"] == 1
    assert len(status["hold_reasons"]) == 1


def test_evaluate_order_credit_zero_limit_not_enforced():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 50,
        "name": "Enterprise Unlimited",
        "credit_limit": 0.0,
        "balance": 100000.0,
    }
    mock_inv_repo.list.return_value = []

    res = service.evaluate_order_credit(customer_id=50, order_amount=50000.0)
    assert res["is_hold_required"] is False
    assert res["credit_limit_exceeded"] is False
    assert res["available_credit"] == 0.0


def test_evaluate_order_credit_exact_boundary():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_cust_repo.get.return_value = {
        "id": 51,
        "name": "Boundary Test Customer",
        "credit_limit": 10000.0,
        "balance": 8000.0,
    }
    mock_inv_repo.list.return_value = []

    # Exposure = 8000 + 2000 = 10000 == limit -> Not exceeded
    res = service.evaluate_order_credit(customer_id=51, order_amount=2000.0)
    assert res["is_hold_required"] is False
    assert res["credit_limit_exceeded"] is False

    # Exposure = 8000 + 2000.01 = 10000.01 > limit -> Exceeded
    res2 = service.evaluate_order_credit(customer_id=51, order_amount=2000.01)
    assert res2["is_hold_required"] is True
    assert res2["credit_limit_exceeded"] is True


def test_evaluate_order_credit_customer_not_found():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )
    mock_cust_repo.get.return_value = None

    res = service.evaluate_order_credit(customer_id=999, order_amount=100.0)
    assert res["is_hold_required"] is False
    assert res["customer_name"] == "Unknown"

    status = service.get_customer_credit_status(customer_id=999)
    assert status is None


def test_get_overdue_invoices_skips_invalid_dates_and_statuses():
    mock_cust_repo = MagicMock()
    mock_inv_repo = MagicMock()
    mock_order_repo = MagicMock()

    service = CreditService(
        customer_repo=mock_cust_repo,
        invoice_repo=mock_inv_repo,
        order_repo=mock_order_repo,
    )

    mock_inv_repo.list.return_value = [
        {"id": 1, "partner_id": 60, "due_date": None, "status": "Issued"},
        {"id": 2, "partner_id": 60, "due_date": "not-a-date", "status": "Issued"},
        {"id": 3, "partner_id": 60, "due_date": "2026-01-01", "status": "Paid"},
        {"id": 4, "partner_id": 60, "due_date": "2026-01-01", "status": "Cancelled"},
    ]

    overdue = service.get_overdue_invoices(customer_id=60, as_of_date=date(2026, 8, 25))
    assert len(overdue) == 0

