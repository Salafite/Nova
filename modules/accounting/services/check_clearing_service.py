import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.models.check_clearing import (
    CHECK_CLEARING_RECORD_REPO,
    STATEMENT_TRANSACTION_REPO,
    BANK_STATEMENT_REPO,
)
from modules.accounting.services.payment_service import PAYMENT_REPO

logger = logging.getLogger(__name__)

# Journal Entry & Line repositories
JOURNAL_ENTRY_REPO = CrudRepository('T0088', business_columns=['id', 'entry_date', 'reference', 'description', 'status', 'is_active'])
JOURNAL_LINE_REPO = CrudRepository('T0089', business_columns=['id', 'journal_entry_id', 'account_id', 'description', 'debit', 'credit', 'is_active'])


class CheckClearingService(CrudService):
    """
    Domain service for batch clearing of matched bank statement checks,
    updating ERP payment check statuses and posting General Ledger journal entries.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        bank_statement_repo: Optional[CrudRepository] = None,
        statement_transaction_repo: Optional[CrudRepository] = None,
        payment_repo: Optional[CrudRepository] = None,
        journal_entry_repo: Optional[CrudRepository] = None,
        journal_line_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or CHECK_CLEARING_RECORD_REPO)
        self.bank_statement_repo = bank_statement_repo or BANK_STATEMENT_REPO
        self.statement_transaction_repo = statement_transaction_repo or STATEMENT_TRANSACTION_REPO
        self.payment_repo = payment_repo or PAYMENT_REPO
        self.journal_entry_repo = journal_entry_repo or JOURNAL_ENTRY_REPO
        self.journal_line_repo = journal_line_repo or JOURNAL_LINE_REPO

    def clear_matched_checks_batch(
        self,
        statement_id: int,
        transaction_ids: Optional[List[int]] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Executes 1-click batch clearing for matched statement checks.
        Updates payment statuses to Cleared, updates clearing records, and creates GL journal entries.

        Args:
            statement_id: ID of the bank statement header (t0108).
            transaction_ids: Optional explicit list of transaction IDs to clear.
            conn: Optional DB transaction connection.

        Returns:
            Dict summary with cleared_count, total_amount, cleared_payment_ids, journal_entry_ids.
        """
        kwargs = {'conn': conn} if conn is not None else {}

        statement = self.bank_statement_repo.get(statement_id, **kwargs)
        if not statement:
            raise ValueError(f"Bank statement {statement_id} not found")

        txns = self.statement_transaction_repo.list(filters={'statement_id': statement_id}, **kwargs)

        if transaction_ids:
            target_txns = [t for t in txns if t['id'] in transaction_ids and t.get('match_status') in ('Matched', 'Pending')]
        else:
            target_txns = [t for t in txns if t.get('match_status') == 'Matched']

        if not target_txns:
            return {
                'statement_id': statement_id,
                'cleared_count': 0,
                'total_amount': 0.0,
                'cleared_payment_ids': [],
                'journal_entry_ids': [],
                'message': 'No matched transactions available for batch clearing',
            }

        cleared_payment_ids = []
        journal_entry_ids = []
        total_cleared_amount = 0.0

        for txn in target_txns:
            txn_id = txn['id']
            pay_id = txn.get('matched_payment_id')
            amount = abs(float(txn.get('amount', 0.0)))
            check_num = txn.get('check_number') or f"CHK-{txn_id}"
            clr_date = txn.get('transaction_date') or date.today()
            if isinstance(clr_date, str):
                try:
                    clr_date = datetime.strptime(clr_date[:10], '%Y-%m-%d').date()
                except ValueError:
                    clr_date = date.today()

            # 1. Update Payment status to Cleared
            if pay_id:
                payment = self.payment_repo.get(pay_id, **kwargs)
                if payment:
                    self.payment_repo.update(
                        pay_id,
                        {
                            'status': 'Cleared',
                            'check_clearing_status': 'Cleared',
                            'clearing_date': clr_date,
                        },
                        **kwargs,
                    )
                    cleared_payment_ids.append(pay_id)

            # 2. Update Statement Transaction match_status to Cleared
            self.statement_transaction_repo.update(
                txn_id,
                {
                    'match_status': 'Cleared',
                },
                **kwargs,
            )

            # 3. Upsert Check Clearing Record (t0110)
            existing_clearing = self.repo.list(
                filters={'statement_transaction_id': txn_id}, **kwargs
            )
            if not existing_clearing and pay_id:
                existing_clearing = self.repo.list(filters={'payment_id': pay_id}, **kwargs)

            clearing_payload = {
                'clearing_number': f"CLR-{txn_id:05d}",
                'statement_transaction_id': txn_id,
                'payment_id': pay_id,
                'check_number': check_num,
                'bank_name': statement.get('bank_name', 'Bank'),
                'payee_payer': txn.get('payee_name'),
                'amount': amount,
                'clearing_date': clr_date,
                'status': 'Cleared',
            }

            if existing_clearing:
                clr_rec_id = existing_clearing[0]['id']
                self.repo.update(clr_rec_id, clearing_payload, **kwargs)
            else:
                self.repo.create(clearing_payload, **kwargs)

            # 4. Create General Ledger Journal Entry (t0088) & Lines (t0089)
            je_ref = f"CHK-CLR-{check_num}"
            je_desc = f"Electronic Check Clearing - Check #{check_num} for ${amount:.2f}"

            try:
                je = self.journal_entry_repo.create(
                    {
                        'entry_date': clr_date,
                        'reference': je_ref,
                        'description': je_desc,
                        'status': 'Posted',
                    },
                    **kwargs,
                )
                je_id = je.get('id') if isinstance(je, dict) else getattr(je, 'id', None)

                if je_id:
                    journal_entry_ids.append(je_id)
                    # Line 1: Debit Bank Account (1000)
                    self.journal_line_repo.create(
                        {
                            'journal_entry_id': je_id,
                            'account_id': 1000, # Bank Account
                            'description': f"Bank deposit check clearing #{check_num}",
                            'debit': amount,
                            'credit': 0.0,
                        },
                        **kwargs,
                    )
                    # Line 2: Credit Undeposited Checks / Checks Receivable (1010)
                    self.journal_line_repo.create(
                        {
                            'journal_entry_id': je_id,
                            'account_id': 1010, # Undeposited Checks
                            'description': f"Clear undeposited check #{check_num}",
                            'debit': 0.0,
                            'credit': amount,
                        },
                        **kwargs,
                    )
            except Exception as e:
                logger.warning(f"Failed to post GL journal entry for check clearing {check_num}: {e}")

            total_cleared_amount += amount

        # 5. Update Bank Statement Header counts & status
        all_updated_txns = self.statement_transaction_repo.list(
            filters={'statement_id': statement_id}, **kwargs
        )
        matched_count = sum(1 for t in all_updated_txns if t.get('match_status') == 'Matched')
        cleared_count = sum(1 for t in all_updated_txns if t.get('match_status') == 'Cleared')
        unmatched_count = sum(1 for t in all_updated_txns if t.get('match_status') == 'Unmatched')
        pending_count = sum(1 for t in all_updated_txns if t.get('match_status') == 'Pending')

        new_stmt_status = 'Reconciled' if (pending_count == 0 and unmatched_count == 0) else 'Matched'
        if cleared_count > 0 and (matched_count > 0 or pending_count > 0):
            new_stmt_status = 'Partially Reconciled'

        self.bank_statement_repo.update(
            statement_id,
            {
                'matched_count': matched_count,
                'unmatched_count': unmatched_count,
                'status': new_stmt_status,
            },
            **kwargs,
        )

        return {
            'statement_id': statement_id,
            'cleared_count': len(target_txns),
            'total_amount': round(total_cleared_amount, 2),
            'cleared_payment_ids': cleared_payment_ids,
            'journal_entry_ids': journal_entry_ids,
            'statement_status': new_stmt_status,
        }

    def clear_single_check(
        self,
        payment_id: int,
        clearing_date: Optional[date] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Clears an individual check payment directly.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        clr_date = clearing_date or date.today()

        payment = self.payment_repo.get(payment_id, **kwargs)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        self.payment_repo.update(
            payment_id,
            {
                'status': 'Cleared',
                'check_clearing_status': 'Cleared',
                'clearing_date': clr_date,
            },
            **kwargs,
        )

        check_num = payment.get('reference') or f"PAY-{payment_id}"
        amount = abs(float(payment.get('amount', 0.0)))

        # Create GL journal entry
        je_ref = f"CHK-CLR-{check_num}"
        je_desc = f"Direct Check Clearing - Check #{check_num} for ${amount:.2f}"
        je = self.journal_entry_repo.create(
            {
                'entry_date': clr_date,
                'reference': je_ref,
                'description': je_desc,
                'status': 'Posted',
            },
            **kwargs,
        )
        je_id = je.get('id') if isinstance(je, dict) else getattr(je, 'id', None)

        if je_id:
            self.journal_line_repo.create(
                {
                    'journal_entry_id': je_id,
                    'account_id': 1000,
                    'description': f"Bank deposit check clearing #{check_num}",
                    'debit': amount,
                    'credit': 0.0,
                },
                **kwargs,
            )
            self.journal_line_repo.create(
                {
                    'journal_entry_id': je_id,
                    'account_id': 1010,
                    'description': f"Clear undeposited check #{check_num}",
                    'debit': 0.0,
                    'credit': amount,
                },
                **kwargs,
            )

        return {
            'payment_id': payment_id,
            'status': 'Cleared',
            'clearing_date': clr_date,
            'journal_entry_id': je_id,
        }


service = CheckClearingService()
repo = CHECK_CLEARING_RECORD_REPO
