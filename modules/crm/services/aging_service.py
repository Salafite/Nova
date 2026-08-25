"""
AR (Accounts Receivable) Aging Service for Nova ERP.

Provides reusable aging calculation methods across 5 standard overdue buckets:
- current: Not overdue (due_date >= as_of_date)
- 1_30: 1 to 30 days overdue
- 31_60: 31 to 60 days overdue
- 61_90: 61 to 90 days overdue
- 90_plus: 91+ days overdue

Also provides backward-compatible aliases ('30', '60', '90') and summary metrics.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from modules.core.repositories.base import CrudRepository


def parse_date(val: Any) -> Optional[date]:
    """Parse a date from string, datetime, date object, or return None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # Handle ISO strings like 2026-08-25T12:00:00 or 2026-08-25
        clean_str = val_str[:10]
        try:
            return date.fromisoformat(clean_str)
        except (ValueError, TypeError):
            pass
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(val_str, fmt).date()
            except (ValueError, TypeError):
                continue
    return None


def classify_overdue_days(days_overdue: int) -> str:
    """Classify the number of overdue days into one of the 5 standard buckets."""
    if days_overdue <= 0:
        return 'current'
    elif days_overdue <= 30:
        return '1_30'
    elif days_overdue <= 60:
        return '31_60'
    elif days_overdue <= 90:
        return '61_90'
    else:
        return '90_plus'


class AgingService:
    """Reusable Accounts Receivable Aging calculation and reporting service."""

    def __init__(
        self,
        customer_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
    ):
        self._customer_repo = customer_repo or CrudRepository(
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
        self._invoice_repo = invoice_repo or CrudRepository(
            'T0090',
            business_columns=[
                'id',
                'invoice_number',
                'invoice_type',
                'partner_id',
                'sales_order_id',
                'issue_date',
                'due_date',
                'discount_due_date',
                'discount_percentage',
                'discount_days',
                'early_discount_amount',
                'total_amount',
                'status',
            ],
        )

    def calculate_invoice_aging(
        self,
        invoice: Dict[str, Any],
        as_of_date: Optional[Union[date, str]] = None,
    ) -> Dict[str, Any]:
        """Calculate aging classification and days overdue for a single invoice."""
        as_of = parse_date(as_of_date) or date.today()
        status = invoice.get('status', 'Unpaid')
        amount = float(invoice.get('total_amount', 0) or 0)

        if str(status).lower() == 'paid':
            return {
                'invoice_id': invoice.get('id'),
                'invoice_number': invoice.get('invoice_number'),
                'status': status,
                'amount': round(amount, 2),
                'days_overdue': 0,
                'bucket': None,
                'is_outstanding': False,
                'is_paid': True,
            }

        if str(status).lower() in ('cancelled', 'void'):
            return {
                'invoice_id': invoice.get('id'),
                'invoice_number': invoice.get('invoice_number'),
                'status': status,
                'amount': round(amount, 2),
                'days_overdue': 0,
                'bucket': None,
                'is_outstanding': False,
                'is_paid': False,
            }

        due = parse_date(invoice.get('due_date')) or parse_date(invoice.get('issue_date')) or as_of
        days_overdue = (as_of - due).days if due < as_of else 0
        bucket = classify_overdue_days(days_overdue)

        return {
            'invoice_id': invoice.get('id'),
            'invoice_number': invoice.get('invoice_number'),
            'status': status,
            'amount': round(amount, 2),
            'issue_date': parse_date(invoice.get('issue_date')),
            'due_date': due,
            'days_overdue': days_overdue,
            'bucket': bucket,
            'is_outstanding': True,
            'is_paid': False,
        }

    def calculate_aging(
        self,
        invoices: List[Dict[str, Any]],
        as_of_date: Optional[Union[date, str]] = None,
    ) -> Dict[str, float]:
        """
        Calculate aging breakdown across all 5 buckets for a collection of invoices.

        Returns dictionary with:
        - current: 0 days overdue (due_date >= as_of_date)
        - 1_30: 1 to 30 days overdue
        - 31_60: 31 to 60 days overdue
        - 61_90: 61 to 90 days overdue
        - 90_plus: 91+ days overdue
        - 30: backward-compatible alias for 1_30
        - 60: backward-compatible alias for 31_60
        - 90: backward-compatible alias for 61_90
        - total_outstanding: sum of all open invoice amounts
        - total_paid: sum of all paid invoice amounts
        """
        as_of = parse_date(as_of_date) or date.today()

        aging = {
            'current': 0.0,
            '1_30': 0.0,
            '31_60': 0.0,
            '61_90': 0.0,
            '90_plus': 0.0,
            '30': 0.0,
            '60': 0.0,
            '90': 0.0,
            'total_outstanding': 0.0,
            'total_paid': 0.0,
        }

        for inv in invoices:
            status = str(inv.get('status', 'Unpaid'))
            status_lower = status.lower()
            amount = float(inv.get('total_amount', 0) or 0)

            if status_lower == 'paid':
                aging['total_paid'] += amount
                continue

            if status_lower in ('cancelled', 'void'):
                continue

            aging['total_outstanding'] += amount

            due = parse_date(inv.get('due_date')) or parse_date(inv.get('issue_date')) or as_of
            days_overdue = (as_of - due).days if due < as_of else 0
            bucket = classify_overdue_days(days_overdue)
            aging[bucket] += amount

        # Backward compatibility aliases
        aging['30'] = aging['1_30']
        aging['60'] = aging['31_60']
        aging['90'] = aging['61_90']

        # Round all monetary values to 2 decimal places
        for k in aging:
            aging[k] = round(aging[k], 2)

        return aging

    def get_customer_aging(
        self,
        customer_id: int,
        as_of_date: Optional[Union[date, str]] = None,
        customer: Optional[Dict[str, Any]] = None,
        invoices: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete aging report for a customer, including aging buckets and invoice summary.
        """
        if customer is None:
            customer = self._customer_repo.get(customer_id)
            if not customer:
                return None

        if invoices is None:
            invoices = self._invoice_repo.list(filters={'partner_id': customer_id})

        as_of = parse_date(as_of_date) or date.today()
        aging = self.calculate_aging(invoices, as_of_date=as_of)

        open_invoices_count = sum(
            1 for inv in invoices
            if str(inv.get('status', '')).lower() not in ('paid', 'cancelled', 'void')
        )
        paid_invoices_count = sum(
            1 for inv in invoices
            if str(inv.get('status', '')).lower() == 'paid'
        )

        return {
            'customer_id': customer_id,
            'customer_name': customer.get('name', ''),
            'balance': float(customer.get('balance', 0) or 0),
            'as_of_date': as_of.isoformat(),
            'aging': aging,
            'invoices_count': len(invoices),
            'open_invoices_count': open_invoices_count,
            'paid_invoices_count': paid_invoices_count,
        }

    def get_all_customers_aging(
        self,
        as_of_date: Optional[Union[date, str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get aggregate aging report across all active customers.
        """
        as_of = parse_date(as_of_date) or date.today()
        customers = self._customer_repo.list(limit=limit)
        customer_agings = []

        total_aging = {
            'current': 0.0,
            '1_30': 0.0,
            '31_60': 0.0,
            '61_90': 0.0,
            '90_plus': 0.0,
            '30': 0.0,
            '60': 0.0,
            '90': 0.0,
            'total_outstanding': 0.0,
            'total_paid': 0.0,
        }

        for cust in customers:
            c_id = cust['id']
            c_aging_res = self.get_customer_aging(c_id, as_of_date=as_of, customer=cust)
            if c_aging_res:
                customer_agings.append(c_aging_res)
                c_aging = c_aging_res['aging']
                for key in ('current', '1_30', '31_60', '61_90', '90_plus', 'total_outstanding', 'total_paid'):
                    total_aging[key] += c_aging.get(key, 0.0)

        total_aging['30'] = total_aging['1_30']
        total_aging['60'] = total_aging['31_60']
        total_aging['90'] = total_aging['61_90']

        for k in total_aging:
            total_aging[k] = round(total_aging[k], 2)

        return {
            'as_of_date': as_of.isoformat(),
            'total_aging': total_aging,
            'customers': customer_agings,
            'customer_count': len(customer_agings),
        }


aging_service = AgingService()
calculate_aging = aging_service.calculate_aging
calculate_invoice_aging = aging_service.calculate_invoice_aging
get_customer_aging = aging_service.get_customer_aging
get_all_customers_aging = aging_service.get_all_customers_aging
