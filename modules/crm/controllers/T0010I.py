from datetime import date
from typing import Optional
from fastapi import Depends, HTTPException
from modules.crm.services.customer_service import CustomerService
from modules.crm.services.aging_service import aging_service
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
