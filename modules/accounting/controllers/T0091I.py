from typing import Optional
from fastapi import HTTPException, Query
from modules.accounting.models import PaymentCreate, PaymentUpdate, PaymentResponse
from modules.accounting.services.payment_service import PaymentService, repo, service
from modules.core.controllers.base import create_crud_router

router = create_crud_router(
    '/api/T0091I',
    'T0091 - Payments',
    service,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
)


@router.get('/preview-discount/{invoice_id}')
@router.get('/invoice/{invoice_id}/discount-preview')
def preview_invoice_payment_discount(
    invoice_id: int,
    payment_date: Optional[str] = Query(None, description="Payment date in YYYY-MM-DD format"),
    payment_amount: Optional[float] = Query(None, description="Proposed payment amount"),
    grace_days: int = Query(0, description="Grace period days"),
):
    """
    Preview early payment discount details and net amount due for an invoice.
    """
    try:
        return service.preview_payment_discount(
            invoice_id=invoice_id,
            payment_date=payment_date,
            payment_amount=payment_amount,
            grace_days=grace_days,
        )
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to preview payment discount: {e}")

