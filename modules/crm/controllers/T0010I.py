from typing import Optional, Dict, Any, List, Union
from datetime import date, datetime
from fastapi import Depends, HTTPException, Query, Request, Response, Body, Path, status
from pydantic import BaseModel, Field

from modules.crm.services.customer_service import CustomerService
from modules.crm.services.aging_service import aging_service
from modules.sales.services.credit_service import CreditService
from modules.crm.services.customer_communication_service import (
    CustomerCommunicationService,
    customer_communication_service as default_customer_communication_service,
)
from modules.accounting.services.ar_reminder_service import (
    ARReminderService,
    ar_reminder_service as default_ar_reminder_service,
)
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership, apply_pagination_headers
from modules.core.context import set_current_tenant
from modules.crm.models import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerReminderPreferencesUpdate, CustomerReminderPreferencesResponse,
    CustomerCommunicationResponse,
)
from packages.auth.deps import get_current_user


# ----------------------------------------------------------------------
# Request Models for Customer Reminders & Dispatch
# ----------------------------------------------------------------------
class CustomerReminderDispatchRequest(BaseModel):
    rule_id: Optional[int] = Field(None, description="AR Reminder Rule ID (optional)")
    template_id: Optional[int] = Field(None, description="Template ID (optional)")
    channel: Optional[str] = Field(None, description="Channel override (EMAIL, WHATSAPP, BOTH)")
    custom_message: Optional[str] = Field(None, description="Custom message text override")
    attach_statement_pdf: bool = Field(True, description="Whether to attach account statement PDF")
    include_payment_link: bool = Field(True, description="Whether to include online payment link")
    recipient_email: Optional[str] = Field(None, description="Recipient email override")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone override")
    as_of_date: Optional[Union[date, str]] = Field(None, description="As of evaluation date")
    business_id: Optional[int] = Field(None, description="Business tenant ID")


class CustomerStatementDispatchRequest(BaseModel):
    channel: Optional[str] = Field(None, description="Channel override (EMAIL, WHATSAPP)")
    start_date: Optional[Union[date, str]] = Field(None, description="Statement start date")
    end_date: Optional[Union[date, str]] = Field(None, description="Statement end date")
    as_of_date: Optional[Union[date, str]] = Field(None, description="As of evaluation date")
    custom_message: Optional[str] = Field(None, description="Custom message / note")
    recipient_email: Optional[str] = Field(None, description="Recipient email override")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone override")
    business_id: Optional[int] = Field(None, description="Business tenant ID")


# ----------------------------------------------------------------------
# Repository & Service Setup
# ----------------------------------------------------------------------
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
        'is_vip',
        'exclude_from_reminders',
        'preferred_reminder_channel',
        'reminder_phone',
        'reminder_email',
        'last_reminder_sent_at',
        'last_statement_sent_at',
        'is_active',
    ],
)
service = CustomerService(repo)
router = create_crud_router('/api/T0010I', 'T0010 - Customers', service,
                            CustomerCreate, CustomerUpdate, CustomerResponse)

credit_service = CreditService(customer_repo=repo)
customer_comm_service: CustomerCommunicationService = default_customer_communication_service
ar_rem_service: ARReminderService = default_ar_reminder_service


def _sync_repos():
    """Ensure child services use the currently assigned repository."""
    if hasattr(customer_comm_service, 'customer_repo') and customer_comm_service.customer_repo != repo:
        customer_comm_service.customer_repo = repo
    if hasattr(ar_rem_service, 'customer_repo') and ar_rem_service.customer_repo != repo:
        ar_rem_service.customer_repo = repo


# ----------------------------------------------------------------------
# Existing Custom Endpoints (Aging, Payments, Invoices, Credit Status)
# ----------------------------------------------------------------------
@router.get('/reports/aging')
def all_customers_aging(as_of_date: Optional[str] = None, limit: int = 100, user: dict = Depends(get_current_user)):
    return aging_service.get_all_customers_aging(as_of_date=as_of_date, limit=limit)

@router.get('/{id}/aging')
def customer_aging(id: int, as_of_date: Optional[str] = None, user: dict = Depends(get_current_user)):
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    result = aging_service.get_customer_aging(id, as_of_date=as_of_date, customer=customer)
    return result


@router.get('/{id}/payments')
def customer_payments(
    id: int,
    response: Response,
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
    order_by: Optional[str] = Query('payment_date', description="Field name to order results by"),
    user: dict = Depends(get_current_user),
):
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    pay_repo = CrudRepository('T0091', business_columns=['id', 'payment_date', 'invoice_id', 'partner_id', 'amount', 'payment_method', 'reference', 'status', 'notes'])
    filters = {'partner_id': id}
    payments = pay_repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset)
    total_count = pay_repo.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return payments

@router.get('/{id}/invoices')
def customer_invoices(
    id: int,
    response: Response,
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
    order_by: Optional[str] = Query('issue_date', description="Field name to order results by"),
    user: dict = Depends(get_current_user),
):
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, 'Customer not found')
    inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status'])
    filters = {'partner_id': id}
    invoices = inv_repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset)
    total_count = inv_repo.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return invoices


@router.get('/{id}/credit-status')
def customer_credit_status(id: int, user: dict = Depends(get_current_user)):
    _sync_repos()
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
        'overdue_invoices': overdue_invoices,
    }


# ----------------------------------------------------------------------
# Customer Communication Timeline Endpoints
# ----------------------------------------------------------------------
@router.get('/{id}/communications')
def customer_communications(
    id: int,
    response: Response = None,
    request: Request = None,
    channel: Optional[str] = Query(None, description="Filter by channel (EMAIL, WHATSAPP, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (SENT, DELIVERED, READ, FAILED, etc.)"),
    communication_type: Optional[str] = Query(None, description="Filter by type (REMINDER, STATEMENT, etc.)"),
    start_date: Optional[str] = Query(None, description="Filter start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter end date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: dict = Depends(get_current_user),
):
    """Retrieve paginated communication timeline and delivery history for a customer."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, f"Customer #{id} not found")

    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0

    try:
        timeline = customer_comm_service.get_customer_timeline(
            customer_id=id,
            channel=channel,
            status=status,
            communication_type=communication_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        if response and request:
            apply_pagination_headers(
                response=response,
                request=request,
                total_count=timeline.get('total', 0),
                limit=limit,
                offset=offset,
            )
        return timeline
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to retrieve communications: {str(e)}")


# ----------------------------------------------------------------------
# Customer Reminder Preferences & VIP Settings Endpoints
# ----------------------------------------------------------------------
@router.get('/{id}/reminder-preferences')
def get_customer_reminder_preferences(
    id: int,
    user: dict = Depends(get_current_user),
):
    """Get customer VIP status, reminder exclusion flags, and communication channels."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'GET')
        raise HTTPException(404, f"Customer #{id} not found")

    try:
        prefs = customer_comm_service.get_customer_preferences(id)
        return prefs
    except ValueError as e:
        raise HTTPException(404 if 'not found' in str(e).lower() or 'not exist' in str(e).lower() else 400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get reminder preferences: {str(e)}")


@router.put('/{id}/reminder-preferences')
@router.patch('/{id}/reminder-preferences')
def update_customer_reminder_preferences(
    id: int,
    payload: CustomerReminderPreferencesUpdate = Body(...),
    user: dict = Depends(get_current_user),
):
    """Update customer VIP status, reminder exclusion flags, and communication contact details."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'PUT')
        raise HTTPException(404, f"Customer #{id} not found")

    try:
        updated = customer_comm_service.update_customer_preferences(id, payload)
        return updated
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to update reminder preferences: {str(e)}")


# ----------------------------------------------------------------------
# On-Demand Manual Reminder & Statement Dispatch Endpoints
# ----------------------------------------------------------------------
@router.post('/{id}/reminders/dispatch')
@router.post('/{id}/dispatch-reminder')
def dispatch_customer_reminder(
    id: int,
    payload: Optional[CustomerReminderDispatchRequest] = Body(None),
    user: dict = Depends(get_current_user),
):
    """Trigger an on-demand AR payment reminder to this customer via WhatsApp or Email."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'POST')
        raise HTTPException(404, f"Customer #{id} not found")

    req = payload or CustomerReminderDispatchRequest()
    dispatched_by = user.get('id') if isinstance(user, dict) else None

    try:
        result = ar_rem_service.send_customer_reminder(
            customer_id=id,
            rule_id=req.rule_id,
            template_id=req.template_id,
            channel=req.channel,
            custom_message=req.custom_message,
            as_of_date=req.as_of_date,
            dispatched_by=dispatched_by,
            attach_statement_pdf=req.attach_statement_pdf,
            include_payment_link=req.include_payment_link,
            recipient_email=req.recipient_email,
            recipient_phone=req.recipient_phone,
            business_id=req.business_id or b_id,
        )
        return result
    except ValueError as e:
        err_str = str(e)
        if 'not found' in err_str.lower() or 'does not exist' in err_str.lower():
            raise HTTPException(404, err_str)
        raise HTTPException(400, err_str)
    except Exception as e:
        raise HTTPException(500, f"Failed to dispatch reminder: {str(e)}")


@router.post('/{id}/statements/dispatch')
@router.post('/{id}/dispatch-statement')
def dispatch_customer_statement(
    id: int,
    payload: Optional[CustomerStatementDispatchRequest] = Body(None),
    user: dict = Depends(get_current_user),
):
    """Trigger on-demand branded account statement PDF dispatch for this customer."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'POST')
        raise HTTPException(404, f"Customer #{id} not found")

    req = payload or CustomerStatementDispatchRequest()

    try:
        result = ar_rem_service.dispatch_customer_statement(
            customer_id=id,
            channel=req.channel,
            start_date=req.start_date,
            end_date=req.end_date,
            as_of_date=req.as_of_date,
            custom_message=req.custom_message,
            recipient_email=req.recipient_email,
            recipient_phone=req.recipient_phone,
            business_id=req.business_id or b_id,
        )
        return result
    except ValueError as e:
        err_str = str(e)
        if 'not found' in err_str.lower() or 'does not exist' in err_str.lower():
            raise HTTPException(404, err_str)
        raise HTTPException(400, err_str)
    except Exception as e:
        raise HTTPException(500, f"Failed to dispatch statement: {str(e)}")


# ----------------------------------------------------------------------
# Communication Retry Endpoints
# ----------------------------------------------------------------------
@router.post('/{id}/communications/{comm_id}/retry')
def retry_customer_communication(
    id: int,
    comm_id: int,
    custom_recipient: Optional[str] = Query(None, description="Optional override recipient address"),
    user: dict = Depends(get_current_user),
):
    """Retry a failed communication dispatch for this customer."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'POST')
        raise HTTPException(404, f"Customer #{id} not found")

    comm = customer_comm_service.get_communication(comm_id)
    if not comm or comm.get('customer_id') != id:
        raise HTTPException(404, f"Communication #{comm_id} not found for customer #{id}")

    try:
        res = customer_comm_service.retry_communication(comm_id, custom_recipient=custom_recipient)
        return res
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to retry communication: {str(e)}")


@router.post('/{id}/communications/retry-failed')
def retry_all_failed_customer_communications(
    id: int,
    max_retries: int = Query(3, ge=1, le=10),
    user: dict = Depends(get_current_user),
):
    """Batch retry all failed communications for this customer that have not exceeded max retries."""
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    _sync_repos()
    customer = repo.get(id)
    if not customer:
        check_record_ownership(repo, id, user, 'T0010', 'POST')
        raise HTTPException(404, f"Customer #{id} not found")

    try:
        res = customer_comm_service.retry_all_failed(customer_id=id, max_retries=max_retries)
        return res
    except Exception as e:
        raise HTTPException(500, f"Failed to retry failed communications: {str(e)}")

