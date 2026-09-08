import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from modules.accounting.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from modules.accounting.models.einvoice import (
    QRCodeResponse,
    ClearanceSubmissionResponse,
    EInvoiceResponse,
    ClearanceSubmissionRequest,
)
from modules.accounting.services.invoice_service import InvoiceService
from modules.accounting.services.fiscal_pdf_service import FiscalPdfService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, apply_pagination_headers
from modules.core.services.permission_service import get_required_permission
from packages.auth.deps import get_current_user, require_permission
from modules.core.context import set_current_tenant

logger = logging.getLogger(__name__)

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

fiscal_pdf_service = FiscalPdfService(
    einvoice_service=service.einvoice_service,
    invoice_repo=service.repo,
    customer_repo=service.customer_repo,
    line_repo=service.line_repo,
)

perm = get_required_permission(prefix='/api/T0090I', tag='T0090 - Invoices')
router = APIRouter(
    prefix='/api/T0090I',
    tags=['T0090 - Invoices'],
    dependencies=[Depends(require_permission(perm))],
)
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


# ---------------------------------------------------------------------------
# Fiscal Authority & E-Invoicing Endpoints
# ---------------------------------------------------------------------------

@router.get('/{id}/qr-code', response_model=QRCodeResponse)
@router.get('/{id}/qr', response_model=QRCodeResponse)
@router.get('/{id}/einvoice/qr-code', response_model=QRCodeResponse)
def get_invoice_qr_code(id: int):
    """Retrieve compliant Base64 TLV QR Code payload and metadata for an invoice."""
    try:
        einvoice_svc = service.einvoice_service
        if not einvoice_svc:
            raise HTTPException(500, "E-Invoice service is not configured")
        return einvoice_svc.generate_qr_code(id)
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate QR code for invoice {id}: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate QR code: {e}")


@router.post('/{id}/clearance', response_model=ClearanceSubmissionResponse)
@router.post('/{id}/submit-clearance', response_model=ClearanceSubmissionResponse)
@router.post('/{id}/einvoice/clearance', response_model=ClearanceSubmissionResponse)
def submit_invoice_clearance(
    id: int,
    profile_id: Optional[int] = Query(None, description="Optional fiscal profile ID override"),
    environment: Optional[str] = Query(None, description="Optional environment override: Sandbox | Simulation | Production"),
    auto_sign: bool = Query(True, description="Automatically compute hash and sign if not already signed"),
):
    """Submit invoice to the Fiscal Authority for clearance (B2B) or reporting (B2C)."""
    try:
        einvoice_svc = service.einvoice_service
        if not einvoice_svc:
            raise HTTPException(500, "E-Invoice service is not configured")
        return einvoice_svc.submit_clearance(
            invoice_id=id,
            profile_id=profile_id,
            environment=environment,
            auto_sign=auto_sign,
        )
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clearance submission failed for invoice {id}: {e}", exc_info=True)
        raise HTTPException(500, f"Clearance submission failed: {e}")


@router.get('/{id}/fiscal-pdf')
@router.get('/{id}/pdf')
@router.get('/{id}/einvoice/pdf')
def download_invoice_fiscal_pdf(
    id: int,
    profile_id: Optional[int] = Query(None, description="Optional fiscal profile ID override"),
):
    """Generate and download a printable bilingual fiscal tax invoice PDF with embedded QR code and security seals."""
    try:
        pdf_bytes = fiscal_pdf_service.generate_fiscal_pdf(invoice_id=id, profile_id=profile_id)
        filename = f"fiscal_invoice_{id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate fiscal PDF for invoice {id}: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate fiscal PDF: {e}")


@router.get('/{id}/einvoice', response_model=Optional[EInvoiceResponse])
@router.get('/{id}/einvoice/status', response_model=Optional[EInvoiceResponse])
def get_invoice_einvoice_record(id: int):
    """Retrieve the e-invoice clearance and cryptographic record for an invoice."""
    try:
        # Verify invoice exists
        inv = service.get(id)
        if not inv:
            raise HTTPException(404, f"Sales invoice #{id} not found")

        einvoice_svc = service.einvoice_service
        if not einvoice_svc:
            raise HTTPException(500, "E-Invoice service is not configured")

        rec = einvoice_svc.get_by_invoice_id(id)
        if not rec:
            # Generate draft XML and record if not yet initialized
            einvoice_svc.generate_ubl_xml(id)
            rec = einvoice_svc.get_by_invoice_id(id)

        return rec
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch e-invoice record for invoice {id}: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch e-invoice record: {e}")
