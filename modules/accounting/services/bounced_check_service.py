import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Union

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.models.check_clearing import (
    CHECK_CLEARING_RECORD_REPO,
    STATEMENT_TRANSACTION_REPO,
    BANK_STATEMENT_REPO,
)
from modules.accounting.services.payment_service import (
    PAYMENT_REPO,
    INVOICE_REPO,
    CUSTOMER_REPO,
)

logger = logging.getLogger(__name__)


def _parse_date(val: Any) -> Optional[date]:
    """Parse date from string, datetime, or date object."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val_str = val.strip()[:10]
        try:
            return datetime.strptime(val_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


class BouncedCheckService(CrudService):
    """
    Domain service for handling bounced / returned customer check workflows.
    Reopens customer invoice balances (t0090 status 'Issued'), marks checks as Bounced (t0110 & t0091),
    records NSF penalty fees, and updates customer account balances.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        payment_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        statement_transaction_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or CHECK_CLEARING_RECORD_REPO)
        self.payment_repo = payment_repo or PAYMENT_REPO
        self.invoice_repo = invoice_repo or INVOICE_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.statement_transaction_repo = statement_transaction_repo or STATEMENT_TRANSACTION_REPO

    def process_bounced_check(
        self,
        clearing_record_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        statement_transaction_id: Optional[int] = None,
        check_number: Optional[str] = None,
        bounced_date: Optional[Union[date, datetime, str]] = None,
        bounced_reason: str = "NSF - Non-Sufficient Funds",
        penalty_fee: float = 0.0,
        notes: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Process a bounced customer check transaction:
        1. Update check clearing record (T0118) status to 'Bounced' with reason & penalty fee.
        2. Update payment (T0091) status to 'Bounced'.
        3. Reopen original customer invoice balance (T0090) to status 'Issued'.
        4. Revert customer balance credit (T0010), adding back payment amount + penalty fee.
        5. Update bank statement transaction (T0117) match_status to 'Bounced' if linked.

        Args:
            clearing_record_id: ID of check clearing record (T0118).
            payment_id: ID of Nova payment (T0091).
            statement_transaction_id: ID of bank statement transaction (T0117).
            check_number: Check number if searching by check number.
            bounced_date: Date check bounced (defaults to today).
            bounced_reason: Reason check bounced (e.g. NSF, Stop Payment).
            penalty_fee: NSF / penalty fee charged to customer.
            notes: Additional notes for the bounced check workflow.
            conn: Optional database transaction connection.

        Returns:
            Dict containing detailed summary of updated records.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        bounced_d = _parse_date(bounced_date) or date.today()
        penalty_amt = round(max(0.0, float(penalty_fee or 0.0)), 2)

        # 1. Resolve Check Clearing Record (T0118)
        clearing_record: Optional[Dict[str, Any]] = None

        if clearing_record_id:
            clearing_record = self.repo.get(clearing_record_id, **kwargs)
            if not clearing_record:
                raise ValueError(f"Check clearing record {clearing_record_id} not found")
        elif payment_id:
            matches = self.repo.list(filters={'payment_id': payment_id}, **kwargs)
            if matches:
                clearing_record = matches[0]
        elif statement_transaction_id:
            matches = self.repo.list(filters={'statement_transaction_id': statement_transaction_id}, **kwargs)
            if matches:
                clearing_record = matches[0]
        elif check_number:
            matches = self.repo.list(filters={'check_number': check_number}, **kwargs)
            if matches:
                clearing_record = matches[0]

        # Extract identifiers from clearing record if available
        if clearing_record:
            payment_id = payment_id or clearing_record.get('payment_id')
            statement_transaction_id = statement_transaction_id or clearing_record.get('statement_transaction_id')
            check_number = check_number or clearing_record.get('check_number')

        # 2. Retrieve & Update Payment Record (T0091)
        payment_record: Optional[Dict[str, Any]] = None
        payment_amount = 0.0
        invoice_id = None
        customer_id = clearing_record.get('customer_id') if clearing_record else None

        if payment_id:
            payment_record = self.payment_repo.get(payment_id, **kwargs)
            if payment_record:
                payment_amount = float(payment_record.get('amount', 0.0) or 0.0)
                invoice_id = payment_record.get('invoice_id')
                customer_id = customer_id or payment_record.get('partner_id')

                # Update payment status to Bounced
                existing_notes = payment_record.get('notes') or ''
                bounce_note = f"[Bounced check {check_number or ''}: {bounced_reason}]"
                updated_notes = (
                    f"{existing_notes.strip()} {bounce_note}".strip()
                    if bounce_note not in existing_notes
                    else existing_notes
                )

                payment_record = self.payment_repo.update(
                    payment_id,
                    {
                        'status': 'Bounced',
                        'notes': updated_notes,
                    },
                    **kwargs,
                )
                logger.info(f"Payment {payment_id} marked as Bounced")

        # 3. Retrieve & Reopen Invoice (T0090)
        invoice_record: Optional[Dict[str, Any]] = None
        if invoice_id:
            invoice_record = self.invoice_repo.get(invoice_id, **kwargs)
            if invoice_record:
                customer_id = customer_id or invoice_record.get('partner_id')
                inv_notes = invoice_record.get('notes') or ''
                reopen_note = f"[Check {check_number or payment_id} bounced - Invoice reopened]"
                updated_inv_notes = (
                    f"{inv_notes.strip()} {reopen_note}".strip()
                    if reopen_note not in inv_notes
                    else inv_notes
                )

                # Reopen invoice to 'Issued' status
                invoice_record = self.invoice_repo.update(
                    invoice_id,
                    {
                        'status': 'Issued',
                        'notes': updated_inv_notes,
                    },
                    **kwargs,
                )
                logger.info(f"Invoice {invoice_id} status reopened to Issued due to bounced check")

        # 4. Revert Customer Balance Credit & Charge Penalty Fee (T0010)
        customer_record: Optional[Dict[str, Any]] = None
        if customer_id and self.customer_repo:
            customer_record = self.customer_repo.get(customer_id, **kwargs)
            if customer_record:
                cur_balance = float(customer_record.get('balance', 0.0) or 0.0)
                # Customer debt increases by (bounced payment amount + NSF penalty fee)
                reverted_balance = round(cur_balance + payment_amount + penalty_amt, 2)

                customer_record = self.customer_repo.update(
                    customer_id,
                    {'balance': reverted_balance},
                    **kwargs,
                )
                logger.info(
                    f"Customer {customer_id} balance updated from ${cur_balance:.2f} to ${reverted_balance:.2f} "
                    f"(reverted payment: ${payment_amount:.2f}, penalty fee: ${penalty_amt:.2f})"
                )

        # 5. Update Statement Transaction (T0117) if linked
        if statement_transaction_id and self.statement_transaction_repo:
            stmt_txn = self.statement_transaction_repo.get(statement_transaction_id, **kwargs)
            if stmt_txn:
                self.statement_transaction_repo.update(
                    statement_transaction_id,
                    {'match_status': 'Bounced'},
                    **kwargs,
                )
                logger.info(f"Statement transaction {statement_transaction_id} match_status set to Bounced")

        # 6. Upsert / Update Check Clearing Record (T0118)
        clearing_data = {
            'payment_id': payment_id,
            'statement_transaction_id': statement_transaction_id,
            'customer_id': customer_id,
            'check_number': check_number or (payment_record.get('reference') if payment_record else 'CHK-UNKNOWN'),
            'amount': payment_amount or (float(clearing_record.get('amount', 0.0)) if clearing_record else 0.0),
            'status': 'Bounced',
            'bounced_date': bounced_d,
            'bounced_reason': bounced_reason,
            'penalty_fee': penalty_amt,
            'notes': notes or (clearing_record.get('notes') if clearing_record else f"Bounced check: {bounced_reason}"),
        }

        if clearing_record:
            clearing_record = self.repo.update(clearing_record['id'], clearing_data, **kwargs)
        else:
            # Generate clearing_number if creating new record
            clearing_num = f"CLR-BNC-{payment_id or 0:05d}"
            clearing_data['clearing_number'] = clearing_num
            clearing_record = self.repo.create(clearing_data, **kwargs)

        logger.info(f"Check clearing record {clearing_record.get('id')} finalized with status Bounced")

        return {
            'clearing_record': clearing_record,
            'payment': payment_record,
            'invoice': invoice_record,
            'customer': customer_record,
            'bounced_check_number': check_number or clearing_data.get('check_number'),
            'bounced_date': str(bounced_d),
            'bounced_reason': bounced_reason,
            'penalty_fee': penalty_amt,
            'payment_amount': payment_amount,
            'reopened_invoice_id': invoice_id,
            'customer_id': customer_id,
            'status': 'Bounced',
        }

    def list_bounced_checks(
        self,
        customer_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve list of all check clearing records with status 'Bounced'.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        query_filters = {'status': 'Bounced'}
        if customer_id:
            query_filters['customer_id'] = customer_id
        if filters:
            query_filters.update(filters)

        return self.repo.list(filters=query_filters, **kwargs)

    def get_bounced_check_summary(
        self,
        customer_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Retrieve summary metrics for bounced checks (count, total amount, total penalty fees).
        """
        bounced_list = self.list_bounced_checks(customer_id=customer_id, conn=conn)
        total_count = len(bounced_list)
        total_amount = sum(float(b.get('amount', 0.0) or 0.0) for b in bounced_list)
        total_penalties = sum(float(b.get('penalty_fee', 0.0) or 0.0) for b in bounced_list)

        return {
            'customer_id': customer_id,
            'total_bounced_count': total_count,
            'total_bounced_amount': round(total_amount, 2),
            'total_penalty_fees': round(total_penalties, 2),
            'bounced_checks': bounced_list,
        }


# Default module instance
service = BouncedCheckService()
