from datetime import date
from fastapi import Depends, HTTPException
from modules.crm.services.customer_service import CustomerService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.crm.models import CustomerCreate, CustomerUpdate, CustomerResponse
from packages.auth.deps import get_current_user
from modules.sales.services.credit_service import CreditService

repo = CrudRepository('T0010', business_columns=['id', 'name', 'group_name', 'phone', 'email', 'credit_limit', 'balance', 'default_price_list_id', 'default_tax_rate_id', 'payment_term_id', 'is_active'])
service = CustomerService(repo)
credit_service = CreditService(customer_repo=repo)
router = create_crud_router('/api/T0010I', 'T0010 - Customers', service,
                            CustomerCreate, CustomerUpdate, CustomerResponse)
@router.get('/{id}/credit-status')
def customer_credit_status(id: int, user: dict = Depends(get_current_user)):
    """
    Retrieve live customer balance, credit limit, available credit,
    overdue >30 days amount and count, and credit hold status.
    """
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    credit_status = credit_service.get_customer_credit_status(id)
    if not credit_status:
        raise HTTPException(404, 'Customer not found')
    return credit_status

@router.get('/{id}/aging')
def customer_aging(id: int, user: dict = Depends(get_current_user)):
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'partner_id', 'issue_date', 'due_date', 'total_amount', 'status'])
    invoices = inv_repo.list(filters={'partner_id': id})
    today = date.today()
    aging = {'current': 0, '30': 0, '60': 0, '90_plus': 0, 'total_outstanding': 0, 'total_paid': 0}
    for inv in invoices:
        if inv['status'] == 'Paid':
            aging['total_paid'] += inv['total_amount']
            continue
        if inv['status'] == 'Cancelled':
            continue
        aging['total_outstanding'] += inv['total_amount']
        due = inv['due_date']
        days_overdue = (today - due).days if due < today else 0
        if days_overdue <= 0:
            aging['current'] += inv['total_amount']
        elif days_overdue <= 30:
            aging['30'] += inv['total_amount']
        elif days_overdue <= 60:
            aging['60'] += inv['total_amount']
        else:
            aging['90_plus'] += inv['total_amount']
    return {
        'customer_id': id,
        'customer_name': customer['name'],
        'balance': customer.get('balance', 0),
        'aging': aging,
    }

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
