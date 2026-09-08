import logging
from typing import Optional, List, Dict, Any
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.connection import db_transaction

logger = logging.getLogger(__name__)

VALID_JE_STATUS_TRANSITIONS = {
    'Draft': ['Posted', 'Cancelled'],
    'Posted': [],
    'Cancelled': [],
}

JE_REPO = CrudRepository(
    'T0027',
    business_columns=['id', 'entry_date', 'reference', 'description', 'status'],
)

JEL_REPO = CrudRepository(
    'T0089',
    business_columns=['id', 'journal_entry_id', 'account_id', 'description', 'debit', 'credit', 'line_number', 'is_active'],
)


class JournalEntryService(CrudService):
    """
    Domain service for Journal Entries (T0027) and Ledger Lines (T0089).
    Ensures ACID balance integrity (debits equal credits) and atomic status transitions.
    """

    def __init__(self, repo: Optional[CrudRepository] = None, line_repo: Optional[CrudRepository] = None):
        super().__init__(repo or JE_REPO)
        self.line_repo = line_repo or JEL_REPO

    def update(self, id_val: int, payload: dict, conn=None):
        with db_transaction(conn) as tx_conn:
            get_fn = getattr(self.repo, 'get_for_update', self.repo.get)
            old = get_fn(int(id_val), conn=tx_conn)
            if not old:
                return None

            if 'status' in payload:
                old_status = old.get('status')
                new_status = payload['status']
                allowed = VALID_JE_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid JE status transition: {old_status} -> {new_status}')

            if payload.get('status') == 'Posted':
                lines = self.line_repo.list(filters={'journal_entry_id': int(id_val)}, conn=tx_conn)
                total_debit = round(sum(float(l.get('debit', 0.0) or 0.0) for l in lines if l.get('is_active', True)), 2)
                total_credit = round(sum(float(l.get('credit', 0.0) or 0.0) for l in lines if l.get('is_active', True)), 2)

                if not lines or total_debit <= 0 or total_credit <= 0 or abs(total_debit - total_credit) > 0.001:
                    from fastapi import HTTPException
                    msg = f"Cannot post unbalanced journal entry #{id_val}: Debits (${total_debit:.2f}) and credits (${total_credit:.2f}) do not match or are empty."
                    logger.warning(msg)
                    raise HTTPException(400, msg)

            return super().update(id_val, payload, conn=tx_conn)

    def delete(self, id_val: int, conn=None):
        with db_transaction(conn) as tx_conn:
            get_fn = getattr(self.repo, 'get_for_update', self.repo.get)
            old = get_fn(int(id_val), conn=tx_conn)
            if old and old.get('status') == 'Posted':
                from fastapi import HTTPException
                raise HTTPException(400, 'Cannot delete a posted journal entry')
            return super().delete(id_val, conn=tx_conn)

    def create_entry_with_lines(
        self,
        entry_payload: dict,
        lines: List[dict],
        conn=None,
    ) -> Dict[str, Any]:
        """
        Atomically create a journal entry (T0027) with its corresponding ledger lines (T0089).
        Verifies debit/credit equality if posting immediately.
        """
        with db_transaction(conn) as tx_conn:
            status = entry_payload.get('status', 'Draft')

            total_debit = round(sum(float(l.get('debit', 0.0) or 0.0) for l in lines), 2)
            total_credit = round(sum(float(l.get('credit', 0.0) or 0.0) for l in lines), 2)

            if status == 'Posted' and (not lines or total_debit <= 0 or total_credit <= 0 or abs(total_debit - total_credit) > 0.001):
                from fastapi import HTTPException
                msg = f"Cannot post unbalanced journal entry: Debits (${total_debit:.2f}) and credits (${total_credit:.2f}) do not match or are empty."
                logger.warning(msg)
                raise HTTPException(400, msg)

            entry = self.create(entry_payload, conn=tx_conn)
            je_id = entry['id']

            created_lines = []
            for idx, line in enumerate(lines, start=1):
                line_dict = dict(line)
                line_dict['journal_entry_id'] = je_id
                if 'line_number' not in line_dict:
                    line_dict['line_number'] = idx
                created_line = self.line_repo.create(line_dict, conn=tx_conn)
                created_lines.append(created_line)

            entry['lines'] = created_lines
            return entry

    def create_payment_journal_entry(
        self,
        partner_id: int,
        amount: float,
        reference: str,
        description: str,
        bank_account_id: int = 1,
        ar_account_id: int = 2,
        entry_date: Optional[Any] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Atomically create and post a balanced payment journal entry (T0027) with ledger lines (T0089)
        for payment settlements (debit Cash/Bank, credit A/R).
        """
        from datetime import date
        amt = round(float(amount), 2)
        if amt <= 0:
            raise ValueError("Payment journal entry amount must be greater than zero")

        entry_payload = {
            'entry_date': entry_date or date.today(),
            'reference': reference,
            'description': description,
            'status': 'Posted',
        }

        lines = [
            {
                'account_id': bank_account_id,
                'debit': amt,
                'credit': 0.0,
                'description': f"Debit Cash/Bank - {description}",
            },
            {
                'account_id': ar_account_id,
                'debit': 0.0,
                'credit': amt,
                'description': f"Credit Accounts Receivable - {description}",
            },
        ]

        return self.create_entry_with_lines(entry_payload, lines, conn=conn)

