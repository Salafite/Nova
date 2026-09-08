"""
Unit tests for CheckClearingService (1-click batch check clearing & GL journal entry posting).
"""

from datetime import date
import pytest
from unittest.mock import MagicMock

from modules.accounting.services.check_clearing_service import CheckClearingService


def test_clear_matched_checks_batch():
    stmt_repo = MagicMock()
    txn_repo = MagicMock()
    pay_repo = MagicMock()
    clr_repo = MagicMock()
    je_repo = MagicMock()
    jl_repo = MagicMock()

    stmt_repo.get.return_value = {
        "id": 1,
        "bank_name": "Chase Bank",
        "account_number": "123456",
        "status": "Matched",
    }

    txns = [
        {
            "id": 10,
            "statement_id": 1,
            "matched_payment_id": 101,
            "amount": 1500.50,
            "check_number": "1054",
            "transaction_date": date(2026, 1, 15),
            "match_status": "Matched",
            "payee_name": "US Foods",
        },
        {
            "id": 11,
            "statement_id": 1,
            "matched_payment_id": 102,
            "amount": 2500.00,
            "check_number": "1055",
            "transaction_date": date(2026, 1, 16),
            "match_status": "Matched",
            "payee_name": "Sysco",
        },
    ]
    txn_repo.list.side_effect = [
        txns,
        [
            {**t, "match_status": "Cleared"} for t in txns
        ]
    ]

    pay_repo.get.side_effect = lambda pay_id, **kw: {
        "id": pay_id,
        "amount": 1500.50 if pay_id == 101 else 2500.00,
        "status": "Pending",
    }

    clr_repo.list.return_value = []
    je_repo.create.return_value = {"id": 501}

    service = CheckClearingService(
        repo=clr_repo,
        bank_statement_repo=stmt_repo,
        statement_transaction_repo=txn_repo,
        payment_repo=pay_repo,
        journal_entry_repo=je_repo,
        journal_line_repo=jl_repo,
    )

    res = service.clear_matched_checks_batch(statement_id=1)

    assert res["statement_id"] == 1
    assert res["cleared_count"] == 2
    assert res["total_amount"] == 4000.50
    assert len(res["cleared_payment_ids"]) == 2
    assert len(res["journal_entry_ids"]) == 2

    # Check updates to payment repo
    pay_repo.update.assert_any_call(
        101,
        {
            "status": "Cleared",
            "check_clearing_status": "Cleared",
            "clearing_date": date(2026, 1, 15),
        },
    )

    # Check journal lines created (2 per transaction)
    assert jl_repo.create.call_count == 4


def test_clear_single_check():
    pay_repo = MagicMock()
    je_repo = MagicMock()
    jl_repo = MagicMock()

    pay_repo.get.return_value = {
        "id": 101,
        "reference": "1054",
        "amount": 1500.50,
        "status": "Pending",
    }
    je_repo.create.return_value = {"id": 601}

    service = CheckClearingService(
        payment_repo=pay_repo,
        journal_entry_repo=je_repo,
        journal_line_repo=jl_repo,
    )

    res = service.clear_single_check(payment_id=101, clearing_date=date(2026, 1, 20))

    assert res["payment_id"] == 101
    assert res["status"] == "Cleared"
    assert res["journal_entry_id"] == 601

    pay_repo.update.assert_called_once_with(
        101,
        {
            "status": "Cleared",
            "check_clearing_status": "Cleared",
            "clearing_date": date(2026, 1, 20),
        },
    )
