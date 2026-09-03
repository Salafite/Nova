"""
Nova ERP — Check Auto-Matching Algorithm Service

Matches uploaded bank statement transactions against pending payments in Nova ERP using:
1. Exact check number match
2. Amount validation
3. Date proximity window
4. Fuzzy payee/reference matching
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.models.check_clearing import (
    BANK_STATEMENT_REPO,
    STATEMENT_TRANSACTION_REPO,
    CHECK_CLEARING_RECORD_REPO,
)
from modules.accounting.services.payment_service import PAYMENT_REPO

logger = logging.getLogger(__name__)


def calculate_match_score(
    stmt_txn: Dict[str, Any],
    payment: Dict[str, Any],
    date_window_days: int = 30,
) -> float:
    """
    Calculate confidence match score between a bank statement transaction and an ERP payment.
    Returns float score between 0.0 and 100.0.
    """
    score = 0.0

    stmt_chk = str(stmt_txn.get('check_number') or '').strip().lstrip('0')
    stmt_amt = abs(round(float(stmt_txn.get('amount', 0.0) or 0.0), 2))
    stmt_payee = str(stmt_txn.get('payee_name') or stmt_txn.get('memo') or '').lower()

    ref = str(payment.get('reference') or payment.get('check_number') or '').strip()
    pay_chk = ref.lstrip('0') if ref else ''
    pay_amt = abs(round(float(payment.get('amount', 0.0) or 0.0), 2))
    pay_notes = str(payment.get('notes') or '').lower()

    stmt_date = stmt_txn.get('transaction_date')
    if isinstance(stmt_date, str):
        stmt_date = datetime.strptime(stmt_date, '%Y-%m-%d').date()
    pay_date = payment.get('payment_date') or payment.get('issue_date')
    if isinstance(pay_date, str):
        pay_date = datetime.strptime(pay_date, '%Y-%m-%d').date()

    # 1. Check number matching (50 points)
    chk_match = False
    if stmt_chk and pay_chk and stmt_chk == pay_chk:
        score += 50.0
        chk_match = True
    elif stmt_chk and (stmt_chk in ref or stmt_chk in pay_notes):
        score += 40.0
        chk_match = True

    # 2. Amount matching (40 points)
    amt_match = False
    if abs(stmt_amt - pay_amt) < 0.01:
        score += 40.0
        amt_match = True
    elif abs(stmt_amt - pay_amt) <= 1.00:
        score += 25.0

    # 3. Date proximity window matching (10 points)
    if stmt_date and pay_date:
        days_diff = abs((stmt_date - pay_date).days)
        if days_diff <= date_window_days:
            score += max(0.0, 10.0 * (1.0 - (days_diff / date_window_days)))

    # Bonus for payee string matching if check number is absent
    if not chk_match and stmt_payee and pay_notes and (stmt_payee in pay_notes or pay_notes in stmt_payee):
        score += 15.0

    return min(100.0, round(score, 2))


class CheckMatchingService:
    """Domain service for auto-matching bank statement check items with ERP payments."""

    def __init__(
        self,
        statement_repo: Optional[CrudRepository] = None,
        txn_repo: Optional[CrudRepository] = None,
        payment_repo: Optional[CrudRepository] = None,
        clearing_repo: Optional[CrudRepository] = None,
    ):
        self.statement_repo = statement_repo or BANK_STATEMENT_REPO
        self.txn_repo = txn_repo or STATEMENT_TRANSACTION_REPO
        self.payment_repo = payment_repo or PAYMENT_REPO
        self.clearing_repo = clearing_repo or CHECK_CLEARING_RECORD_REPO

    def auto_match_statement(
        self,
        statement_id: int,
        date_window_days: int = 30,
        min_score_threshold: float = 60.0,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Auto-matches all pending statement transactions for statement_id against pending payments.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        statement = self.statement_repo.get(statement_id, **kwargs)
        if not statement:
            raise ValueError(f"Bank statement {statement_id} not found")

        txns = self.txn_repo.list(filters={'statement_id': statement_id}, **kwargs)
        if not txns:
            return {'statement_id': statement_id, 'matched_count': 0, 'unmatched_count': 0, 'matches': []}

        # Fetch candidate payments in ERP that are Pending or Completed check payments
        all_payments = self.payment_repo.list(**kwargs)
        candidate_payments = [
            p for p in all_payments
            if str(p.get('status')).lower() not in ('cancelled', 'voided', 'bounced')
        ]

        matched_results = []
        matched_payment_ids = set()
        matched_count = 0
        unmatched_count = 0

        for txn in txns:
            if txn.get('match_status') == 'Cleared':
                matched_count += 1
                continue

            best_payment = None
            best_score = 0.0

            for payment in candidate_payments:
                if payment.get('id') in matched_payment_ids:
                    continue

                score = calculate_match_score(txn, payment, date_window_days=date_window_days)
                if score > best_score:
                    best_score = score
                    best_payment = payment

            if best_payment and best_score >= min_score_threshold:
                matched_count += 1
                matched_payment_ids.add(best_payment['id'])

                # Update transaction match details
                self.txn_repo.update(
                    txn['id'],
                    {
                        'match_status': 'Matched',
                        'matched_payment_id': best_payment['id'],
                        'match_score': best_score,
                    },
                    **kwargs,
                )

                matched_results.append({
                    'transaction_id': txn['id'],
                    'check_number': txn.get('check_number'),
                    'amount': txn.get('amount'),
                    'transaction_date': txn.get('transaction_date'),
                    'matched_payment_id': best_payment['id'],
                    'matched_payment_reference': best_payment.get('reference'),
                    'matched_amount': best_payment.get('amount'),
                    'match_score': best_score,
                    'status': 'Matched',
                })
            else:
                unmatched_count += 1
                self.txn_repo.update(
                    txn['id'],
                    {
                        'match_status': 'Unmatched',
                        'match_score': best_score if best_payment else 0.0,
                    },
                    **kwargs,
                )

                matched_results.append({
                    'transaction_id': txn['id'],
                    'check_number': txn.get('check_number'),
                    'amount': txn.get('amount'),
                    'transaction_date': txn.get('transaction_date'),
                    'matched_payment_id': None,
                    'match_score': 0.0,
                    'status': 'Unmatched',
                })

        # Update statement header summary
        new_status = 'Matched' if matched_count > 0 else 'Uploaded'
        self.statement_repo.update(
            statement_id,
            {
                'matched_count': matched_count,
                'unmatched_count': unmatched_count,
                'status': new_status,
            },
            **kwargs,
        )

        return {
            'statement_id': statement_id,
            'total_transactions': len(txns),
            'matched_count': matched_count,
            'unmatched_count': unmatched_count,
            'matches': matched_results,
        }
