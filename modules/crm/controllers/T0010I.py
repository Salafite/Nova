from datetime import date
from typing import Optional
from fastapi import Depends, HTTPException
from modules.crm.services.customer_service import CustomerService
from modules.crm.services.aging_service import aging_service
from modules.sales.services.credit_service import CreditService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.crm.models import CustomerCreate, CustomerUpdate, CustomerResponse
from packages.auth.deps import get_current_user

repo = CrudRepository(
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
        'min_order_amount',
        'order_cutoff_time',
        'allow_reorders',
        'is_active',
    ],
)
service = CustomerService(repo)
router = create_crud_router('/api/T0010I', 'T0010 - Customers', service,
                            CustomerCreate, CustomerUpdate, CustomerResponse)

credit_service = CreditService(customer_repo=repo)

@router.get('/reports/aging')
def all_customers_aging(as_of_date: Optional[str] = None, limit: int = 100, user: dict = Depends(get_current_user)):
    return aging_service.get_all_customers_aging(as_of_date=as_of_date, limit=limit)

@router.get('/{id}/aging')
def customer_aging(id: int, as_of_date: Optional[str] = None, user: dict = Depends(get_current_user)):
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    result = aging_service.get_customer_aging(id, as_of_date=as_of_date, customer=customer)
    return result


@router.get('/{id}/payments')
def customer_payments(id: int, limit: int = 50, user: dict = Depends(get_current_user)):
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    pay_repo = CrudRepository('T0091', business_columns=['id', 'payment_date', 'invoice_id', 'partner_id', 'amount', 'payment_method', 'reference', 'status', 'notes'])
    payments = pay_repo.list(filters={'partner_id': id}, order_by='payment_date', limit=limit)
    return payments

@router.get('/{id}/invoices')
def customer_invoices(id: int, user: dict = Depends(get_current_user)):
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status'])
    invoices = inv_repo.list(filters={'partner_id': id}, order_by='issue_date')
    return invoices


def customer_credit_status(id: int, user: dict = None):
    customer = credit_service.customer_repo.get(id)
    if not customer:
        raise HTTPException(404, f"Customer {id} not found")

    overdue_invoices = credit_service.get_overdue_invoices(id)
    overdue_amount = sum(inv.get('total_amount', 0) for inv in overdue_invoices)
    credit_eval = credit_service.evaluate_order_credit(customer_id=id, order_amount=0)

    credit_limit = customer.get('credit_limit', 0)
    balance = customer.get('balance', 0)
    raw_available_credit = credit_limit - balance if credit_limit > 0 else 0
    available_credit = max(0, raw_available_credit)

    hold_reasons = []
    if credit_eval.get('credit_limit_exceeded'):
        hold_reasons.append(f"Credit limit exceeded: balance ${balance:,.2f} > limit ${credit_limit:,.2f}")
    if overdue_invoices:
        hold_reasons.append(f"Customer has {len(overdue_invoices)} overdue invoice(s) overdue by >30 days totaling ${overdue_amount:,.2f}")

    hold_orders = []
    if hasattr(credit_service, 'order_repo') and credit_service.order_repo:
        try:
            all_orders = credit_service.order_repo.list(filters={'customer_id': id})
            hold_orders = [o for o in (all_orders or []) if o.get('status') == 'Credit Hold']
        except Exception:
            pass
    hold_orders_count = len(hold_orders)

    return {
        'customer_id': id,
        'customer_name': customer.get('name', ''),
        'credit_limit': credit_limit,
        'balance': balance,
        'available_credit': available_credit,
        'raw_available_credit': raw_available_credit,
        'credit_limit_exceeded': credit_eval.get('credit_limit_exceeded', False),
        'overdue_invoices_count': len(overdue_invoices),
        'overdue_invoices_amount': overdue_amount,
        'has_overdue_invoices': len(overdue_invoices) > 0,
        'is_delinquent': credit_eval.get('has_overdue_invoices', False) or credit_eval.get('credit_limit_exceeded', False),
        'on_hold': credit_eval.get('is_hold_required', False) or len(hold_orders) > 0,
        'has_hold_orders': hold_orders_count > 0,
        'hold_orders_count': hold_orders_count,
        'hold_reasons': hold_reasons,
    }
