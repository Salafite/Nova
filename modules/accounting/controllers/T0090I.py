from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from modules.accounting.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from modules.accounting.services.invoice_service import InvoiceService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, apply_pagination_headers
from modules.core.services.permission_service import get_required_permission
from packages.auth.deps import get_current_user, require_permission
from modules.core.context import set_current_tenant

repo = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'purchase_order_id',
        'purchase_return_id',
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
        'stripe_payment_intent_id',
        'stripe_checkout_session_id',
        'payment_link',
        'business_id',
        'is_active',
    ],
)
service = InvoiceService(repo)

perm = get_required_permission(prefix='/api/T0090I', tag='T0090 - Invoices')
router = APIRouter(
    prefix='/api/T0090I',
    tags=['T0090 - Invoices'],
    dependencies=[Depends(require_permission(perm))],
)


@router.get('/debit-memos', response_model=List[InvoiceResponse])
def list_debit_memos(
    response: Response,
    request: Request,
    purchase_return_id: Optional[int] = Query(None, description="Filter debit memos by linked Purchase Return (RMA) ID"),
    partner_id: Optional[int] = Query(None, description="Filter debit memos by Supplier ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g., Unpaid, Paid, Cancelled)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
    order_by: Optional[str] = Query(None, description="Field name to order results by"),
    user: dict = Depends(get_current_user),
):
    """
    Retrieve and filter supplier debit memos, including those linked to RMA / Purchase Return records.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0

    try:
        items = service.get_debit_memos(
            purchase_return_id=purchase_return_id,
            partner_id=partner_id,
            status=status_filter,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
        total_count = service.count_debit_memos(
            purchase_return_id=purchase_return_id,
            partner_id=partner_id,
            status=status_filter,
        )
        apply_pagination_headers(
            response=response,
            request=request,
            total_count=total_count,
            limit=limit,
            offset=offset,
        )
        return items
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to list debit memos: {e}")


@router.get('/by-purchase-return/{return_id}', response_model=InvoiceResponse)
def get_debit_memo_by_purchase_return(
    return_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve the supplier debit memo generated for a specific RMA / Purchase Return record.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        record = service.get_debit_memo_by_purchase_return(return_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No debit memo found for Purchase Return (RMA) #{return_id}",
            )
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to get debit memo for RMA #{return_id}: {e}")


@router.get('/rma/{return_id}', response_model=InvoiceResponse)
def get_debit_memo_for_rma(
    return_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Convenience alias to retrieve the supplier debit memo generated for a specific RMA record.
    """
    return get_debit_memo_by_purchase_return(return_id=return_id, user=user)


@router.post('/from-order/{order_id}', status_code=status.HTTP_201_CREATED)
def create_invoice_from_order(order_id: int):
    """Generate a catch-weight adjusted invoice from a sales order."""
    try:
        return service.recalculate_and_invoice_order(order_id)
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to create invoice from order: {e}")


@router.get('/{id}/catch-weight-breakdown')
def get_invoice_catch_weight_breakdown(id: int):
    """Retrieve catch-weight breakdown details for an invoice."""
    try:
        return service.get_catch_weight_breakdown(id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to get catch-weight breakdown: {e}")


# Attach standard CRUD endpoints (GET /, GET /{id}, POST /, PUT /{id}, DELETE /{id}, GET /count)
create_crud_router(
    '/api/T0090I',
    'T0090 - Invoices',
    service,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    router=router,
)




