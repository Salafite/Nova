import logging
import re
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple, Union

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.models.check_clearing import (
    STATEMENT_TRANSACTION_REPO,
    BANK_STATEMENT_REPO,
    CHECK_CLEARING_RECORD_REPO,
)
from modules.accounting.services.payment_service import PAYMENT_REPO, CUSTOMER_REPO

logger = logging.getLogger(__name__)


def normalize_check_number(raw: Optional[str]) -> Optional[str]:
    """
    Normalizes check numbers by removing non-alphanumeric prefixes and stripping leading zeroes.
    Example: 'CHK# 000123' -> '123', '005041' -> '5041'.
    """
    if not raw:
        return None
    cleaned = re.sub(r'^(?:chk|check|num|#|\s)+', '', str(raw), flags=re.IGNORECASE)
    cleaned = re.sub(r'\D', '', cleaned)
    cleaned = cleaned.lstrip('0')
    return cleaned if cleaned else None


class CheckMatchingService(CrudService):
    """
    Domain service for auto-matching uploaded bank statement transactions
    against pending ERP payments and check clearing records.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        bank_statement_repo: Optional[CrudRepository] = None,
        payment_repo: Optional[CrudRepository] = None,
        check_clearing_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or STATEMENT_TRANSACTION_REPO)
        self.bank_statement_repo = bank_statement_repo or BANK_STATEMENT_REPO
        self.payment_repo = payment_repo or PAYMENT_REPO
        self.check_clearing_repo = check_clearing_repo or CHECK_CLEARING_RECORD_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO

    def calculate_match_score(
        self,
        statement_txn: Dict[str, Any],
        candidate_payment: Dict[str, Any],
        date_tolerance_days: int = 30,
    ) -> float:
        """
        Calculates a match confidence score between 0.00 and 1.00 for a statement transaction
        line and a candidate pending ERP payment.
        """
        score = 0.0

        txn_check = normalize_check_number(statement_txn.get('check_number'))
        pay_check = normalize_check_number(candidate_payment.get('reference') or candidate_payment.get('check_number'))

        memo_text = f"{statement_txn.get('memo', '')} {statement_txn.get('payee_name', '')}".strip().lower()

        # 1. Check Number Evaluation
        if txn_check and pay_check and txn_check == pay_check:
            score += 0.65
        elif pay_check and pay_check in memo_text:
            score += 0.50
        elif txn_check and txn_check in str(candidate_payment.get('notes', '')).lower():
            score += 0.45

        # 2. Amount Evaluation
        txn_amt = abs(float(statement_txn.get('amount', 0.0) or 0.0))
        pay_amt = abs(float(candidate_payment.get('amount', 0.0) or 0.0))

        if abs(txn_amt - pay_amt) < 0.01:
            score += 0.25
        elif pay_amt > 0 and abs(txn_amt - pay_amt) / pay_amt <= 0.02:
            score += 0.10

        # 3. Date Proximity Evaluation
        txn_date_val = statement_txn.get('transaction_date')
        pay_date_val = candidate_payment.get('payment_date') or candidate_payment.get('issue_date')

        txn_d = self._parse_date(txn_date_val)
        pay_d = self._parse_date(pay_date_val)

        if txn_d and pay_d:
            days_diff = abs((txn_d - pay_d).days)
            if days_diff == 0:
                score += 0.10
            elif days_diff <= 3:
                score += 0.08
            elif days_diff <= 7:
                score += 0.05
            elif days_diff <= date_tolerance_days:
                score += 0.02
            else:
                score -= 0.15

        # Cap score between 0.00 and 1.00
        return round(max(0.0, min(1.0, score)), 2)

    def match_statement_transactions(
        self,
        statement_id: int,
        date_tolerance_days: int = 30,
        min_score_threshold: float = 0.70,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Executes auto-matching algorithm on all pending transactions in a bank statement.

        Args:
            statement_id: ID of uploaded bank statement (t0108).
            date_tolerance_days: Proximity window for dates.
            min_score_threshold: Minimum match confidence score required for auto-match.
            conn: Optional DB transaction connection.

        Returns:
            Dict summary of total processed, matched, and unmatched transactions.
        """
        kwargs = {'conn': conn} if conn is not None else {}

        statement = self.bank_statement_repo.get(statement_id, **kwargs)
        if not statement:
            raise ValueError(f"Bank statement {statement_id} not found")

        # Get pending statement transaction lines
        all_txns = self.repo.list(filters={'statement_id': statement_id}, **kwargs)
        pending_txns = [t for t in all_txns if t.get('match_status') == 'Pending']

        if not pending_txns:
            return {
                'statement_id': statement_id,
                'total_transactions': len(all_txns),
                'matched_count': sum(1 for t in all_txns if t.get('match_status') == 'Matched'),
                'unmatched_count': sum(1 for t in all_txns if t.get('match_status') == 'Unmatched'),
                'matches': [],
            }

        # Fetch candidate payments
        candidate_payments = self.payment_repo.list(**kwargs)
        # Also check existing check clearing records
        existing_clearing_records = self.check_clearing_repo.list(**kwargs)

        matched_results = []
        used_payment_ids = set(
            t.get('matched_payment_id') for t in all_txns if t.get('matched_payment_id')
        )

        for txn in pending_txns:
            best_match: Optional[Dict[str, Any]] = None
            best_score = 0.0

            for payment in candidate_payments:
                pay_id = payment.get('id')
                if pay_id in used_payment_ids:
                    continue

                score = self.calculate_match_score(
                    statement_txn=txn,
                    candidate_payment=payment,
                    date_tolerance_days=date_tolerance_days,
                )

                if score > best_score:
                    best_score = score
                    best_match = payment

            txn_id = txn['id']
            if best_match and best_score >= min_score_threshold:
                pay_id = best_match['id']
                used_payment_ids.add(pay_id)

                # Update Statement Transaction (t0109)
                self.repo.update(
                    txn_id,
                    {
                        'match_status': 'Matched',
                        'matched_payment_id': pay_id,
                        'match_score': best_score,
                    },
                    **kwargs,
                )

                # Upsert Check Clearing Record (t0110)
                check_num = txn.get('check_number') or best_match.get('reference') or f"CHK-{txn_id}"
                cust_id = best_match.get('partner_id')
                payee_payer = txn.get('payee_name') or f"Customer {cust_id}"

                clearing_data = {
                    'clearing_number': f"CLR-{txn_id:05d}",
                    'payment_id': pay_id,
                    'statement_transaction_id': txn_id,
                    'customer_id': cust_id,
                    'check_number': check_num,
                    'bank_name': statement.get('bank_name', 'Bank'),
                    'payee_payer': payee_payer,
                    'amount': abs(float(txn.get('amount', 0.0))),
                    'issue_date': best_match.get('payment_date'),
                    'clearing_date': txn.get('transaction_date'),
                    'status': 'Matched',
                }

                # Check if clearing record already exists for payment or statement transaction
                existing = [
                    c for c in existing_clearing_records
                    if c.get('statement_transaction_id') == txn_id or c.get('payment_id') == pay_id
                ]

                if existing:
                    self.check_clearing_repo.update(existing[0]['id'], clearing_data, **kwargs)
                else:
                    self.check_clearing_repo.create(clearing_data, **kwargs)

                matched_results.append({
                    'transaction_id': txn_id,
                    'matched_payment_id': pay_id,
                    'check_number': check_num,
                    'amount': txn.get('amount'),
                    'score': best_score,
                })
            else:
                # Mark as unmatched if below threshold
                self.repo.update(
                    txn_id,
                    {
                        'match_status': 'Unmatched',
                        'match_score': best_score,
                    },
                    **kwargs,
                )

        # Update parent statement counts
        updated_all_txns = self.repo.list(filters={'statement_id': statement_id}, **kwargs)
        matched_count = sum(1 for t in updated_all_txns if t.get('match_status') == 'Matched')
        unmatched_count = sum(1 for t in updated_all_txns if t.get('match_status') == 'Unmatched')
        pending_count = sum(1 for t in updated_all_txns if t.get('match_status') == 'Pending')

        stmt_status = 'Matched' if matched_count > 0 else statement.get('status', 'Uploaded')
        if pending_count == 0 and unmatched_count == 0 and matched_count > 0:
            stmt_status = 'Reconciled'

        self.bank_statement_repo.update(
            statement_id,
            {
                'matched_count': matched_count,
                'unmatched_count': unmatched_count,
                'status': stmt_status,
            },
            **kwargs,
        )

        return {
            'statement_id': statement_id,
            'total_transactions': len(updated_all_txns),
            'matched_count': matched_count,
            'unmatched_count': unmatched_count,
            'pending_count': pending_count,
            'matches': matched_results,
        }

    def manual_match(
        self,
        statement_transaction_id: int,
        payment_id: int,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Manually matches a statement transaction with a payment.
        """
        kwargs = {'conn': conn} if conn is not None else {}

        txn = self.repo.get(statement_transaction_id, **kwargs)
        if not txn:
            raise ValueError(f"Statement transaction {statement_transaction_id} not found")

        payment = self.payment_repo.get(payment_id, **kwargs)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        score = self.calculate_match_score(txn, payment)

        self.repo.update(
            statement_transaction_id,
            {
                'match_status': 'Matched',
                'matched_payment_id': payment_id,
                'match_score': max(1.0, score), # manual match gets full 1.0 confidence
            },
            **kwargs,
        )

        # Update statement counts
        statement_id = txn['statement_id']
        all_txns = self.repo.list(filters={'statement_id': statement_id}, **kwargs)
        matched_count = sum(1 for t in all_txns if t.get('match_status') == 'Matched')
        unmatched_count = sum(1 for t in all_txns if t.get('match_status') == 'Unmatched')

        self.bank_statement_repo.update(
            statement_id,
            {
                'matched_count': matched_count,
                'unmatched_count': unmatched_count,
                'status': 'Matched',
            },
            **kwargs,
        )

        return {
            'statement_transaction_id': statement_transaction_id,
            'matched_payment_id': payment_id,
            'status': 'Matched',
        }

    @staticmethod
    def _parse_date(val: Any) -> Optional[date]:
        if not val:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str):
            try:
                return datetime.strptime(val[:10], '%Y-%m-%d').date()
            except ValueError:
                pass
        return None
