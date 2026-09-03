import pytest
from datetime import date
from unittest.mock import MagicMock
from modules.accounting.services.check_matching_service import (
    CheckMatchingService,
    normalize_check_number,
)


def test_normalize_check_number():
    assert normalize_check_number('0001054') == '1054'
    assert normalize_check_number('CHK# 005041') == '5041'
    assert normalize_check_number('Check #9876') == '9876'
    assert normalize_check_number('1054') == '1054'
    assert normalize_check_number(None) is None


def test_calculate_match_score():
    service = CheckMatchingService(
        repo=MagicMock(),
        bank_statement_repo=MagicMock(),
        payment_repo=MagicMock(),
        check_clearing_repo=MagicMock(),
        customer_repo=MagicMock(),
    )

    statement_txn = {
        'check_number': '1054',
        'amount': -1500.50,
        'transaction_date': date(2026, 1, 15),
        'payee_name': 'US Foods',
        'memo': 'Payment for invoice',
    }

    # Exact match candidate payment
    payment_exact = {
        'id': 101,
        'reference': '1054',
        'amount': 1500.50,
        'payment_date': date(2026, 1, 15),
        'partner_id': 50,
    }

    score_exact = service.calculate_match_score(statement_txn, payment_exact)
    assert score_exact == 1.0  # 0.65 (check) + 0.25 (amt) + 0.10 (date)

    # Different check number and amount candidate
    payment_mismatch = {
        'id': 102,
        'reference': '9999',
        'amount': 2500.00,
        'payment_date': date(2026, 1, 1),
    }

    score_mismatch = service.calculate_match_score(statement_txn, payment_mismatch)
    assert score_mismatch < 0.50


def test_match_statement_transactions():
    stmt_repo = MagicMock()
    txn_repo = MagicMock()
    pay_repo = MagicMock()
    clr_repo = MagicMock()
    cust_repo = MagicMock()

    # Mock Statement (t0108)
    stmt_repo.get.return_value = {
        'id': 1,
        'statement_number': 'STMT-00001',
        'bank_name': 'Chase Bank',
        'account_number': '123456',
        'status': 'Uploaded',
    }

    # Mock Statement Transactions (t0109)
    txns = [
        {
            'id': 10,
            'statement_id': 1,
            'check_number': '2045',
            'amount': 3250.00,
            'transaction_date': date(2026, 1, 18),
            'payee_name': 'Metro Market',
            'match_status': 'Pending',
        },
        {
            'id': 11,
            'statement_id': 1,
            'check_number': '9999',
            'amount': 89.99,
            'transaction_date': date(2026, 1, 20),
            'payee_name': 'Unknown Payee',
            'match_status': 'Pending',
        },
    ]
    txn_repo.list.return_value = txns

    # Mock Pending ERP Payments (t0091)
    payments = [
        {
            'id': 501,
            'reference': '2045',
            'amount': 3250.00,
            'payment_date': date(2026, 1, 18),
            'partner_id': 12,
        }
    ]
    pay_repo.list.return_value = payments
    clr_repo.list.return_value = []

    service = CheckMatchingService(
        repo=txn_repo,
        bank_statement_repo=stmt_repo,
        payment_repo=pay_repo,
        check_clearing_repo=clr_repo,
        customer_repo=cust_repo,
    )

    # Re-mock txn_repo list for second query after updates
    def mock_list_txns(filters=None, **kwargs):
        return [
            {
                'id': 10,
                'statement_id': 1,
                'match_status': 'Matched',
                'matched_payment_id': 501,
                'match_score': 1.0,
            },
            {
                'id': 11,
                'statement_id': 1,
                'match_status': 'Unmatched',
                'match_score': 0.0,
            },
        ]

    txn_repo.list.side_effect = [txns, mock_list_txns()]

    res = service.match_statement_transactions(statement_id=1, min_score_threshold=0.70)

    assert res['statement_id'] == 1
    assert res['matched_count'] == 1
    assert res['unmatched_count'] == 1
    assert len(res['matches']) == 1
    assert res['matches'][0]['transaction_id'] == 10
    assert res['matches'][0]['matched_payment_id'] == 501

    # Verify updates
    txn_repo.update.assert_any_call(
        10,
        {
            'match_status': 'Matched',
            'matched_payment_id': 501,
            'match_score': 1.0,
        },
    )
    clr_repo.create.assert_called_once()
    stmt_repo.update.assert_called_with(
        1,
        {
            'matched_count': 1,
            'unmatched_count': 1,
            'status': 'Matched',
        },
    )


def test_manual_match():
    stmt_repo = MagicMock()
    txn_repo = MagicMock()
    pay_repo = MagicMock()

    txn_repo.get.return_value = {
        'id': 10,
        'statement_id': 1,
        'check_number': '1054',
        'amount': 1500.50,
        'transaction_date': date(2026, 1, 15),
        'payee_name': 'US Foods',
        'match_status': 'Pending',
    }

    pay_repo.get.return_value = {
        'id': 101,
        'reference': '1054',
        'amount': 1500.50,
        'payment_date': date(2026, 1, 15),
    }

    txn_repo.list.return_value = [
        {'id': 10, 'statement_id': 1, 'match_status': 'Matched'}
    ]

    service = CheckMatchingService(
        repo=txn_repo,
        bank_statement_repo=stmt_repo,
        payment_repo=pay_repo,
    )

    res = service.manual_match(statement_transaction_id=10, payment_id=101)

    assert res['statement_transaction_id'] == 10
    assert res['matched_payment_id'] == 101
    assert res['status'] == 'Matched'

    txn_repo.update.assert_called_with(
        10,
        {
            'match_status': 'Matched',
            'matched_payment_id': 101,
            'match_score': 1.0,
        },
    )
    stmt_repo.update.assert_called_with(
        1,
        {
            'matched_count': 1,
            'unmatched_count': 0,
            'status': 'Matched',
        },
    )

