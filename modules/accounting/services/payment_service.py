import logging
from datetime import date, datetime
from typing import Optional, Union, Dict, Any, List
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.services.payment_term_service import (
    calculate_early_discount,
    calculate_discount_deadline,
    calculate_max_early_discount,
    resolve_effective_term,
    _parse_date,
    PAYMENT_TERM_REPO,
)

logger = logging.getLogger(__name__)

PAYMENT_REPO = CrudRepository(
    'T0091',
    business_columns=[
        'id',
        'payment_date',
        'invoice_id',
        'partner_id',
        'amount',
        'payment_method',
        'reference',
        'status',
        'notes',
        'stripe_payment_intent_id',
        'stripe_checkout_session_id',
        'payment_link',
    ],
)

INVOICE_REPO = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'sales_rep_id',
        'payment_term_id',
        'issue_date',
        'due_date',
        'discount_due_date',
        'discount_percentage',
        'discount_days',
        'early_discount_amount',
        'total_amount',
        'freight_amount',
        'discount_amount',
        'status',
        'notes',
        'is_catch_weight',
        'nominal_total_weight',
        'actual_total_weight',
        'weight_adjustment_amount',
    ],
)

CUSTOMER_REPO = CrudRepository(
    'T0010',
    business_columns=['id', 'name', 'credit_limit', 'balance', 'payment_term_id'],
)


class PaymentService(CrudService):
    """
    Domain service for Payments (T0091), handling early payment discount evaluation,
    invoice settlement, and customer balance reconciliation.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        payment_term_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or PAYMENT_REPO)
        self.invoice_repo = invoice_repo or INVOICE_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.payment_term_repo = payment_term_repo or PAYMENT_TERM_REPO

    def evaluate_early_discount(
        self,
        invoice_id: int,
        payment_date: Optional[Union[date, datetime, str]] = None,
        payment_amount: Optional[float] = None,
        grace_days: int = 0,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether an early payment discount is valid for a given invoice on the specified payment date.

        Args:
            invoice_id: ID of the invoice being evaluated.
            payment_date: Date on which payment is to be made (defaults to today).
            payment_amount: Optional specific payment amount being proposed.
            grace_days: Optional grace period days allowed past discount cutoff date.
            conn: Optional database connection / transaction.

        Returns:
            Dict containing eligibility status, discount percentage, discount savings amount,
            net amount due, cutoff dates, and balance summary.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        invoice = self.invoice_repo.get(int(invoice_id), **kwargs)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        pay_date = _parse_date(payment_date)
        inv_total = round(float(invoice.get('total_amount', 0.0) or 0.0), 2)

        # Get existing payments for this invoice
        try:
            prev_payments = self.repo.list(filters={'invoice_id': invoice_id}, **kwargs)
            completed_payments = [
                p for p in prev_payments
                if p.get('status') in ('Completed', 'Settled', 'Success', 'Paid')
            ]
            amount_already_paid = round(
                sum(float(p.get('amount', 0.0) or 0.0) for p in completed_payments), 2
            )
        except Exception as e:
            logger.warning(f"Could not fetch previous payments for invoice {invoice_id}: {e}")
            amount_already_paid = 0.0

        existing_inv_discount = round(float(invoice.get('discount_amount', 0.0) or 0.0), 2)
        balance_due = round(max(0.0, inv_total - amount_already_paid - existing_inv_discount), 2)

        # Extract or resolve payment term and discount metadata
        term_id = invoice.get('payment_term_id')
        discount_due_date = invoice.get('discount_due_date')
        discount_pct = float(invoice.get('discount_percentage', 0.0) or 0.0)

        term = None
        if discount_due_date is None or discount_pct <= 0:
            term = resolve_effective_term(
                payment_term_id=term_id,
                customer_id=invoice.get('partner_id'),
                customer_repo=self.customer_repo,
                term_repo=self.payment_term_repo,
                conn=conn,
            )
            if term:
                if discount_pct <= 0:
                    discount_pct = (
                        float(term.get('discount_percentage', 0.0) or 0.0)
                        if isinstance(term, dict)
                        else float(getattr(term, 'discount_percentage', 0.0) or 0.0)
                    )
                if discount_due_date is None:
                    issue_d = invoice.get('issue_date') or pay_date
                    discount_due_date = calculate_discount_deadline(base_date=issue_d, term=term)

        # Base amount to apply discount on: payment_amount if provided, else current balance_due
        eval_base_amt = round(float(payment_amount), 2) if payment_amount is not None and float(payment_amount) > 0 else balance_due

        discount_eval = calculate_early_discount(
            total_amount=eval_base_amt,
            payment_date=pay_date,
            discount_due_date=discount_due_date,
            discount_percentage=discount_pct,
            term=term,
            grace_days=grace_days,
        )

        is_eligible = bool(discount_eval.get('is_eligible', False))
        discount_amount = float(discount_eval.get('discount_amount', 0.0) or 0.0)
        net_amount_due = (
            round(max(0.0, balance_due - discount_amount), 2)
            if is_eligible
            else balance_due
        )

        return {
            'invoice_id': invoice_id,
            'invoice_number': invoice.get('invoice_number'),
            'partner_id': invoice.get('partner_id'),
            'invoice_total': inv_total,
            'amount_already_paid': amount_already_paid,
            'existing_discount': existing_inv_discount,
            'balance_due': balance_due,
            'is_eligible': is_eligible,
            'discount_percentage': discount_pct,
            'discount_amount': discount_amount,
            'net_amount_due': net_amount_due,
            'discount_due_date': discount_due_date,
            'cutoff_date': discount_eval.get('cutoff_date'),
            'payment_date': pay_date,
            'message': discount_eval.get('message', ''),
        }

    def preview_payment_discount(
        self,
        invoice_id: int,
        payment_date: Optional[Union[date, datetime, str]] = None,
        payment_amount: Optional[float] = None,
        grace_days: int = 0,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Helper method to preview early payment discount details for UI and API endpoints.
        """
        return self.evaluate_early_discount(
            invoice_id=invoice_id,
            payment_date=payment_date,
            payment_amount=payment_amount,
            grace_days=grace_days,
            conn=conn,
        )

    def create(
        self,
        payload: dict,
        apply_early_discount: bool = True,
        grace_days: int = 0,
        conn=None,
    ) -> dict:
        """
        Record a payment (T0091), honoring early payment discounts if eligible,
        settling invoice status, and updating customer balance.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        payment_dict = dict(payload)

        # Normalize payment date
        pay_date = _parse_date(payment_dict.get('payment_date'))
        payment_dict['payment_date'] = pay_date

        amt = round(float(payment_dict.get('amount', 0.0) or 0.0), 2)
        if amt <= 0:
            raise ValueError("Payment amount must be greater than 0")

        status = payment_dict.get('status', 'Completed')
        invoice_id = payment_dict.get('invoice_id')
        partner_id = payment_dict.get('partner_id')

        discount_credit = 0.0
        total_settlement_credit = amt

        if invoice_id:
            inv = self.invoice_repo.get(int(invoice_id), **kwargs)
            if not inv:
                raise ValueError(f"Invoice {invoice_id} not found")

            # Fallback partner_id from invoice if omitted
            if not partner_id:
                partner_id = inv.get('partner_id')
                payment_dict['partner_id'] = partner_id

            if apply_early_discount and status in ('Completed', 'Settled', 'Success', 'Paid'):
                eval_res = self.evaluate_early_discount(
                    invoice_id=invoice_id,
                    payment_date=pay_date,
                    grace_days=grace_days,
                    conn=conn,
                )

                if eval_res.get('is_eligible') and eval_res.get('discount_amount', 0) > 0:
                    max_discount = float(eval_res['discount_amount'])
                    balance_due = float(eval_res['balance_due'])
                    net_due = float(eval_res['net_amount_due'])

                    # Check if paying full net due or paying full balance due
                    if amt >= net_due and net_due > 0:
                        discount_credit = max_discount
                        total_settlement_credit = round(amt + discount_credit, 2)
                    elif amt > 0 and balance_due > 0:
                        # Proportional early discount for partial payments
                        pct = float(eval_res['discount_percentage'])
                        discount_credit = round(amt * (pct / (100.0 - pct)), 2)
                        discount_credit = min(discount_credit, max_discount)
                        total_settlement_credit = round(amt + discount_credit, 2)

                    # Annotate payment notes with discount details
                    if discount_credit > 0:
                        pct_val = eval_res['discount_percentage']
                        pct_str = f"{int(pct_val)}%" if isinstance(pct_val, (int, float)) and float(pct_val).is_integer() else f"{pct_val}%"
                        discount_note = f"Early payment discount applied: ${discount_credit:.2f} ({pct_str})"
                        existing_notes = payment_dict.get('notes') or ''
                        if discount_note not in existing_notes:
                            payment_dict['notes'] = (
                                f"{existing_notes.strip()} [{discount_note}]".strip()
                                if existing_notes
                                else discount_note
                            )

                        # Update invoice discount_amount
                        current_inv_disc = float(inv.get('discount_amount', 0.0) or 0.0)
                        new_inv_disc = round(current_inv_disc + discount_credit, 2)
                        self.invoice_repo.update(invoice_id, {'discount_amount': new_inv_disc}, **kwargs)
                        logger.info(
                            f"Applied early discount of ${discount_credit:.2f} on invoice {invoice_id}"
                        )

            # Create payment record
            payment_record = super().create(payment_dict, **kwargs)

            # Check if invoice is now fully settled and update status
            if status in ('Completed', 'Settled', 'Success', 'Paid'):
                try:
                    all_payments = self.repo.list(filters={'invoice_id': invoice_id}, **kwargs)
                    total_paid_cash = sum(
                        float(p.get('amount', 0.0) or 0.0)
                        for p in all_payments
                        if p.get('status') in ('Completed', 'Settled', 'Success', 'Paid')
                    )
                    inv_refresh = self.invoice_repo.get(int(invoice_id), **kwargs) or inv
                    total_disc = float(inv_refresh.get('discount_amount', 0.0) or 0.0)
                    inv_total = float(inv_refresh.get('total_amount', 0.0) or 0.0)

                    if (total_paid_cash + total_disc) >= (inv_total - 0.01):
                        self.invoice_repo.update(invoice_id, {'status': 'Paid'}, **kwargs)
                        logger.info(f"Invoice {invoice_id} fully settled and status updated to Paid")
                except Exception as e:
                    logger.error(f"Failed to check/update invoice {invoice_id} status: {e}")

            # Update customer balance
            if status in ('Completed', 'Settled', 'Success', 'Paid') and partner_id and self.customer_repo:
                try:
                    customer = self.customer_repo.get(int(partner_id), **kwargs)
                    if customer:
                        cur_bal = float(customer.get('balance', 0.0) or 0.0)
                        new_bal = round(max(0.0, cur_bal - total_settlement_credit), 2)
                        self.customer_repo.update(int(partner_id), {'balance': new_bal}, **kwargs)
                        logger.info(
                            f"Updated customer {partner_id} balance from {cur_bal:.2f} to {new_bal:.2f} (credit: {total_settlement_credit:.2f})"
                        )
                except Exception as e:
                    logger.error(f"Failed to update customer {partner_id} balance: {e}")
                    raise RuntimeError(f"Failed to update customer balance: {e}") from e

            return payment_record

        else:
            # Payment unlinked to specific invoice (e.g. on-account customer deposit)
            payment_record = super().create(payment_dict, **kwargs)

            if status in ('Completed', 'Settled', 'Success', 'Paid') and partner_id and self.customer_repo:
                try:
                    customer = self.customer_repo.get(int(partner_id), **kwargs)
                    if customer:
                        cur_bal = float(customer.get('balance', 0.0) or 0.0)
                        new_bal = round(max(0.0, cur_bal - amt), 2)
                        self.customer_repo.update(int(partner_id), {'balance': new_bal}, **kwargs)
                        logger.info(
                            f"Updated customer {partner_id} balance from {cur_bal:.2f} to {new_bal:.2f} (credit: {amt:.2f})"
                        )
                except Exception as e:
                    logger.error(f"Failed to update customer {partner_id} balance: {e}")
                    raise RuntimeError(f"Failed to update customer balance: {e}") from e

            return payment_record

    def settle_invoice_payment(
        self,
        payment_payload: dict,
        apply_early_discount: bool = True,
        grace_days: int = 0,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Convenience method to execute invoice payment settlement and return full structured result.
        """
        payment_record = self.create(
            payload=payment_payload,
            apply_early_discount=apply_early_discount,
            grace_days=grace_days,
            conn=conn,
        )
        invoice_id = payment_payload.get('invoice_id')
        invoice_record = self.invoice_repo.get(invoice_id, conn=conn) if invoice_id else None
        partner_id = payment_payload.get('partner_id') or (invoice_record.get('partner_id') if invoice_record else None)
        customer_record = self.customer_repo.get(partner_id, conn=conn) if partner_id else None

        return {
            'payment': payment_record,
            'invoice': invoice_record,
            'customer': customer_record,
        }


# Module-level default repository and service instances
repo = PAYMENT_REPO
service = PaymentService(PAYMENT_REPO, INVOICE_REPO, CUSTOMER_REPO, PAYMENT_TERM_REPO)
