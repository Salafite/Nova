"""
Nova ERP — Credit Evaluation Engine Service
Centralized service for customer credit limit evaluation, available credit calculation,
and overdue invoice threshold (>30 days) verification for automatic credit hold workflows.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Union

from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService

logger = logging.getLogger(__name__)

# Default repositories for CRM customers, Invoices, and Sales Orders
DEFAULT_CUSTOMER_REPO = CrudRepository(
    'T0010',
    business_columns=[
        'id',
        'name',
        'group_name',
        'phone',
        'email',
        'credit_limit',
        'balance',
        'default_price_list_id',
        'default_tax_rate_id',
        'payment_term_id',
        'is_active',
    ],
)

DEFAULT_INVOICE_REPO = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'sales_rep_id',
        'issue_date',
        'due_date',
        'total_amount',
        'freight_amount',
        'discount_amount',
        'status',
        'notes',
    ],
)

DEFAULT_ORDER_REPO = CrudRepository(
    'T0012',
    business_columns=[
        'id',
        'order_number',
        'customer_id',
        'subtotal',
        'tax',
        'grand_total',
        'status',
        'order_date',
        'hold_reason',
        'hold_released_by',
        'hold_released_at',
        'hold_release_reason',
    ],
)


def _to_float(value: Any) -> float:
    """Safely coerce a numeric or string value to float."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError, ArithmeticError):
        return 0.0


def _parse_date(value: Any) -> Optional[date]:
    """Parse a date from string, datetime, or date object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        val_str = value.strip()
        if not val_str:
            return None
        # Handle ISO strings with time or timezone e.g. 2026-08-25T12:00:00Z
        val_str = val_str[:10]
        try:
            return datetime.strptime(val_str, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


class CreditService(CrudService):
    """
    Central service for evaluating customer credit standing, credit limits,
    available credit balances, and delinquent invoice thresholds.
    """

    def __init__(
        self,
        customer_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        order_repo: Optional[CrudRepository] = None,
    ):
        self.customer_repo = customer_repo or DEFAULT_CUSTOMER_REPO
        self.invoice_repo = invoice_repo or DEFAULT_INVOICE_REPO
        self.order_repo = order_repo or DEFAULT_ORDER_REPO
        # Initialize CrudService with customer_repo as primary target
        super().__init__(self.customer_repo)

    def get_overdue_invoices(
        self,
        customer_id: int,
        threshold_days: int = 30,
        as_of_date: Optional[Union[date, str]] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all open/unsettled invoices for a customer where due_date is
        overdue by more than `threshold_days` relative to `as_of_date`.

        :param customer_id: Customer ID (partner_id in t0090)
        :param threshold_days: Number of days overdue to trigger delinquent flag (default 30)
        :param as_of_date: Reference date for aging calculation (default today)
        :param conn: Optional active DB connection
        :return: List of overdue invoice detail dictionaries
        """
        ref_date = _parse_date(as_of_date) or date.today()
        invoices = self.invoice_repo.list(filters={'partner_id': customer_id}, conn=conn)

        overdue_list = []
        for inv in invoices:
            status = inv.get('status')
            # Exclude paid and cancelled invoices
            if status in ('Paid', 'Cancelled'):
                continue

            due = _parse_date(inv.get('due_date'))
            if not due:
                continue

            days_overdue = (ref_date - due).days if due < ref_date else 0
            if days_overdue > threshold_days:
                total_amount = _to_float(inv.get('total_amount', 0.0))
                overdue_list.append({
                    'id': inv.get('id'),
                    'invoice_number': inv.get('invoice_number'),
                    'issue_date': str(inv.get('issue_date')),
                    'due_date': str(due),
                    'total_amount': round(total_amount, 2),
                    'days_overdue': days_overdue,
                    'status': status,
                })

        # Sort descending by days overdue
        overdue_list.sort(key=lambda x: x['days_overdue'], reverse=True)
        return overdue_list

    def get_customer_credit_status(
        self,
        customer_id: int,
        as_of_date: Optional[Union[date, str]] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve comprehensive real-time credit status metrics for a customer.

        :param customer_id: Customer ID
        :param as_of_date: Reference evaluation date
        :param conn: Optional active DB connection
        :return: Credit status dictionary or None if customer not found
        """
        customer = self.customer_repo.get(customer_id, conn=conn)
        if not customer:
            logger.warning(f"CreditService.get_customer_credit_status: Customer {customer_id} not found")
            return None

        credit_limit = _to_float(customer.get('credit_limit', 0.0))
        balance = _to_float(customer.get('balance', 0.0))
        available_credit = max(0.0, credit_limit - balance) if credit_limit > 0 else 0.0
        raw_available_credit = (credit_limit - balance) if credit_limit > 0 else 0.0
        credit_limit_exceeded = bool(credit_limit > 0 and balance > credit_limit)

        overdue_invoices = self.get_overdue_invoices(
            customer_id=customer_id,
            threshold_days=30,
            as_of_date=as_of_date,
            conn=conn,
        )
        overdue_invoices_count = len(overdue_invoices)
        overdue_invoices_amount = sum(inv['total_amount'] for inv in overdue_invoices)
        has_overdue_invoices = overdue_invoices_count > 0

        # Check existing orders on Credit Hold
        hold_orders = []
        if self.order_repo:
            try:
                hold_orders = self.order_repo.list(
                    filters={'customer_id': customer_id, 'status': 'Credit Hold'},
                    conn=conn,
                )
            except Exception as e:
                logger.warning(f"Could not check hold orders for customer {customer_id}: {e}")

        hold_reasons = []
        if credit_limit_exceeded:
            hold_reasons.append(
                f"Customer credit limit exceeded: Balance ${balance:,.2f} > Limit ${credit_limit:,.2f}"
            )
        if has_overdue_invoices:
            inv_plural = "invoices" if overdue_invoices_count != 1 else "invoice"
            hold_reasons.append(
                f"Customer has {overdue_invoices_count} {inv_plural} overdue by >30 days (total overdue: ${overdue_invoices_amount:,.2f})"
            )

        is_delinquent = credit_limit_exceeded or has_overdue_invoices
        has_hold_orders = len(hold_orders) > 0

        return {
            'customer_id': customer.get('id'),
            'customer_name': customer.get('name'),
            'credit_limit': round(credit_limit, 2),
            'balance': round(balance, 2),
            'available_credit': round(available_credit, 2),
            'raw_available_credit': round(raw_available_credit, 2),
            'credit_limit_exceeded': credit_limit_exceeded,
            'is_credit_limit_enforced': bool(credit_limit > 0),
            'overdue_invoices_count': overdue_invoices_count,
            'overdue_invoices_amount': round(overdue_invoices_amount, 2),
            'has_overdue_invoices': has_overdue_invoices,
            'overdue_invoices': overdue_invoices,
            'is_delinquent': is_delinquent,
            'on_hold': is_delinquent or has_hold_orders,
            'has_hold_orders': has_hold_orders,
            'hold_orders_count': len(hold_orders),
            'hold_reasons': hold_reasons,
        }

    def evaluate_order_credit(
        self,
        customer_id: int,
        order_amount: float = 0.0,
        as_of_date: Optional[Union[date, str]] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether a proposed sales order of `order_amount` for `customer_id`
        violates credit limit or delinquent overdue payment thresholds.

        :param customer_id: Customer ID
        :param order_amount: Grand total of the new order
        :param as_of_date: Evaluation date
        :param conn: Optional active DB connection
        :return: Evaluation result dictionary with `is_hold_required`, `hold_reason`, and metrics
        """
        customer = self.customer_repo.get(customer_id, conn=conn)
        if not customer:
            logger.warning(f"CreditService.evaluate_order_credit: Customer {customer_id} not found")
            return {
                'is_hold_required': False,
                'hold_reason': None,
                'credit_limit_exceeded': False,
                'has_overdue_invoices': False,
                'customer_id': customer_id,
                'customer_name': 'Unknown',
                'credit_limit': 0.0,
                'current_balance': 0.0,
                'order_amount': _to_float(order_amount),
                'total_exposure': _to_float(order_amount),
                'available_credit': 0.0,
                'overdue_invoices_count': 0,
                'overdue_invoices_amount': 0.0,
                'overdue_invoices': [],
                'reasons': [],
            }

        order_amount_f = _to_float(order_amount)
        credit_limit = _to_float(customer.get('credit_limit', 0.0))
        balance = _to_float(customer.get('balance', 0.0))
        total_exposure = balance + order_amount_f
        available_credit = max(0.0, credit_limit - balance) if credit_limit > 0 else 0.0

        # Check 1: Credit limit exceeded by total exposure
        credit_limit_exceeded = bool(credit_limit > 0 and total_exposure > credit_limit)

        # Check 2: Unpaid invoices overdue by > 30 days
        overdue_invoices = self.get_overdue_invoices(
            customer_id=customer_id,
            threshold_days=30,
            as_of_date=as_of_date,
            conn=conn,
        )
        overdue_invoices_count = len(overdue_invoices)
        overdue_invoices_amount = sum(inv['total_amount'] for inv in overdue_invoices)
        has_overdue_invoices = overdue_invoices_count > 0

        reasons: List[str] = []
        if credit_limit_exceeded:
            reasons.append(
                f"Customer credit limit exceeded: Total exposure ${total_exposure:,.2f} > Limit ${credit_limit:,.2f}"
            )
        if has_overdue_invoices:
            inv_plural = "invoices" if overdue_invoices_count != 1 else "invoice"
            reasons.append(
                f"Customer has {overdue_invoices_count} {inv_plural} overdue by >30 days (total overdue: ${overdue_invoices_amount:,.2f})"
            )

        is_hold_required = bool(credit_limit_exceeded or has_overdue_invoices)
        hold_reason = "; ".join(reasons) if reasons else None

        return {
            'is_hold_required': is_hold_required,
            'hold_reason': hold_reason,
            'credit_limit_exceeded': credit_limit_exceeded,
            'has_overdue_invoices': has_overdue_invoices,
            'customer_id': customer_id,
            'customer_name': customer.get('name', ''),
            'credit_limit': round(credit_limit, 2),
            'current_balance': round(balance, 2),
            'order_amount': round(order_amount_f, 2),
            'total_exposure': round(total_exposure, 2),
            'available_credit': round(available_credit, 2),
            'overdue_invoices_count': overdue_invoices_count,
            'overdue_invoices_amount': round(overdue_invoices_amount, 2),
            'overdue_invoices': overdue_invoices,
            'reasons': reasons,
        }
