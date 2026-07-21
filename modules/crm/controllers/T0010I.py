from datetime import date
from fastapi import HTTPException
from modules.crm.services.customer_service import CustomerService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.crm.models import CustomerCreate, CustomerUpdate, CustomerResponse

repo = CrudRepository('T0010', business_columns=['id', 'name', 'group_name', 'phone', 'email', 'credit_limit', 'balance', 'default_price_list_id', 'default_tax_rate_id', 'payment_term_id', 'is_active'])
service = CustomerService(repo)
router = create_crud_router('/api/T0010I', 'T0010 - Customers', service,
                            CustomerCreate, CustomerUpdate, CustomerResponse)
@router.get('/{id}/aging')
def customer_aging(id: int):
    customer = repo.get(id)
    if not customer:
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
def customer_payments(id: int, limit: int = 50):
    customer = repo.get(id)
    if not customer:
        raise HTTPException(404, 'Customer not found')
    pay_repo = CrudRepository('T0091', business_columns=['id', 'payment_date', 'invoice_id', 'partner_id', 'amount', 'payment_method', 'reference', 'status', 'notes'])
    payments = pay_repo.list(filters={'partner_id': id}, order_by='payment_date', limit=limit)
    return payments

@router.get('/{id}/invoices')
def customer_invoices(id: int):
    customer = repo.get(id)
    if not customer:
        raise HTTPException(404, 'Customer not found')
    inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status'])
    invoices = inv_repo.list(filters={'partner_id': id}, order_by='issue_date')
    return invoices
