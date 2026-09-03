"""
Unit tests for BouncedCheckService (bounced check workflow, penalty fees, credit hold, reopened invoices).
"""

from datetime import date
import pytest
from unittest.mock import MagicMock

from modules.accounting.services.bounced_check_service import BouncedCheckService


def test_process_bounced_check():
    clr_repo = MagicMock()
    pay_repo = MagicMock()
    inv_repo = MagicMock()
    cust_repo = MagicMock()
    txn_repo = MagicMock()

    clr_repo.get.return_value = {
        "id": 1,
        "payment_id": 101,
        "statement_transaction_id": 10,
        "check_number": "1054",
        "amount": 1500.50,
        "customer_id": 5,
    }

    pay_repo.get.return_value = {
        "id": 101,
        "amount": 1500.50,
        "invoice_id": 42,
        "partner_id": 5,
        "reference": "1054",
        "notes": "",
    }

    inv_repo.get.return_value = {
        "id": 42,
        "partner_id": 5,
        "notes": "",
        "status": "Paid",
    }

    cust_repo.get.return_value = {
        "id": 5,
        "balance": 200.0,
    }

    service = BouncedCheckService(
        repo=clr_repo,
        payment_repo=pay_repo,
        invoice_repo=inv_repo,
        customer_repo=cust_repo,
        statement_transaction_repo=txn_repo,
    )

    res = service.process_bounced_check(
        clearing_record_id=1,
        bounced_reason="NSF - Non-Sufficient Funds",
        penalty_fee=35.0,
    )

    assert res["status"] == "Bounced"
    assert res["penalty_fee"] == 35.0
    assert res["payment_amount"] == 1500.50
    assert res["reopened_invoice_id"] == 42
    assert res["customer_id"] == 5

    # Verify payment status updated to Bounced
    pay_repo.update.assert_called_once()
    assert pay_repo.update.call_args[0][0] == 101
    assert pay_repo.update.call_args[0][1]["status"] == "Bounced"

    # Verify invoice status reopened to Issued
    inv_repo.update.assert_called_once()
    assert inv_repo.update.call_args[0][0] == 42
    assert inv_repo.update.call_args[0][1]["status"] == "Issued"

    # Verify customer balance increased by payment_amount + penalty_fee (200 + 1500.50 + 35 = 1735.50)
    cust_repo.update.assert_called_once()
    assert cust_repo.update.call_args[0][0] == 5
    assert cust_repo.update.call_args[0][1]["balance"] == 1735.50


def test_list_bounced_checks():
    clr_repo = MagicMock()
    clr_repo.list.return_value = [
        {"id": 1, "check_number": "1054", "status": "Bounced", "customer_id": 5},
    ]

    service = BouncedCheckService(repo=clr_repo)
    res = service.list_bounced_checks(customer_id=5)

    assert len(res) == 1
    assert res[0]["check_number"] == "1054"
    clr_repo.list.assert_called_once_with(filters={"status": "Bounced", "customer_id": 5})


def test_get_bounced_check_summary():
    clr_repo = MagicMock()
    clr_repo.list.return_value = [
        {"id": 1, "amount": 1000.0, "penalty_fee": 35.0, "status": "Bounced"},
        {"id": 2, "amount": 500.0, "penalty_fee": 25.0, "status": "Bounced"},
    ]

    service = BouncedCheckService(repo=clr_repo)
    summary = service.get_bounced_check_summary(customer_id=5)

    assert summary["total_bounced_count"] == 2
    assert summary["total_bounced_amount"] == 1500.0
    assert summary["total_penalty_fees"] == 60.0
