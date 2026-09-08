import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from modules.accounting.models import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceCatchWeightBreakdownResponse,
)
from modules.accounting.models.einvoice import (
    QRCodeResponse,
    ClearanceSubmissionResponse,
    EInvoiceResponse,
    ClearanceSubmissionRequest,
)
from modules.accounting.services.invoice_service import InvoiceService
from modules.accounting.services.fiscal_pdf_service import FiscalPdfService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

logger = logging.getLogger(__name__)

repo = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
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
    ],
)
service = InvoiceService(repo)
fiscal_pdf_service = FiscalPdfService(
    einvoice_service=service.einvoice_service,
    invoice_repo=service.repo,
    customer_repo=service.customer_repo,
    line_repo=service.line_repo,
)

router = create_crud_router(
    '/api/T0090I',
    'T0090 - Invoices',
    service,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
)


@router.post('/from-order/{order_id}', status_code=201)
def create_invoice_from_order(order_id: int):
    """Generate a catch-weight adjusted invoice from a sales order."""
    try:
        return service.recalculate_and_invoice_order(order_id)
    except ValueError as e:
        if 'not found' in str(e).lower():
            raise HTTPException(404, str(e))
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create invoice from order: {e}")


@router.get('/{id}/catch-weight-breakdown', response_model=InvoiceCatchWeightBreakdownResponse)
def get_invoice_catch_weight_breakdown(id: int):
    """Retrieve catch-weight breakdown details for an invoice."""
    try:
        return service.get_catch_weight_breakdown(id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get catch-weight breakdown: {e}")


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
