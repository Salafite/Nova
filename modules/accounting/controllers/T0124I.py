import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Depends, status, Response, Query

from modules.accounting.models.einvoice import (
    EInvoiceCreate,
    EInvoiceUpdate,
    EInvoiceResponse,
    ClearanceSubmissionRequest,
    ClearanceSubmissionResponse,
    QRCodeResponse,
    EINVOICE_RECORD_REPO,
)
from modules.accounting.services.einvoice_service import EInvoiceService
from modules.accounting.services.fiscal_pdf_service import FiscalPdfService, fiscal_pdf_service
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.services.base import CrudService
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

service = CrudService(EINVOICE_RECORD_REPO)
einvoice_service = EInvoiceService(repo=EINVOICE_RECORD_REPO)

router = create_crud_router(
    '/api/T0124I',
    'T0124 - E-Invoice Clearance Records',
    service,
    EInvoiceCreate,
    EInvoiceUpdate,
    EInvoiceResponse,
)


@router.get('/by-invoice/{invoice_id}', response_model=EInvoiceResponse)
def get_einvoice_by_invoice_id(
    invoice_id: int,
    user: dict = Depends(get_current_user),
):
    """Retrieve the e-invoice clearance and cryptographic record associated with a sales invoice."""
    rec = einvoice_service.get_by_invoice_id(invoice_id)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"No e-invoice clearance record found for invoice #{invoice_id}",
        )
    return rec


@router.get('/qr-code/{invoice_id}', response_model=QRCodeResponse)
def get_invoice_qr_code(
    invoice_id: int,
    user: dict = Depends(get_current_user),
):
    """Generate or retrieve the compliant Base64 TLV QR code payload for a sales invoice."""
    try:
        qr_response = einvoice_service.generate_qr_code(invoice_id)
        return qr_response
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Failed to generate QR code for invoice #{invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {exc}")


@router.post('/generate-xml/{invoice_id}')
def generate_invoice_ubl_xml(
    invoice_id: int,
    profile_id: Optional[int] = Query(None, description="Optional fiscal profile ID override"),
    subtype: Optional[str] = Query(None, description="Invoice subtype: 0100000 (Standard) | 0200000 (Simplified)"),
    user: dict = Depends(get_current_user),
):
    """Generate OASIS UBL 2.1 XML document for a sales invoice and persist draft clearance record."""
    try:
        xml_content = einvoice_service.generate_ubl_xml(
            invoice_id=invoice_id,
            profile_id=profile_id,
            subtype=subtype,
        )
        rec = einvoice_service.get_by_invoice_id(invoice_id)
        return {
            "invoice_id": invoice_id,
            "invoice_uuid": rec.get("invoice_uuid") if rec else None,
            "invoice_hash": rec.get("invoice_hash") if rec else None,
            "subtype": rec.get("subtype") if rec else subtype,
            "ubl_xml": xml_content,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Failed to generate UBL XML for invoice #{invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate UBL XML: {exc}")


@router.post('/sign/{invoice_id}', response_model=EInvoiceResponse)
def sign_invoice_cryptographically(
    invoice_id: int,
    profile_id: Optional[int] = Query(None, description="Optional fiscal profile ID override"),
    user: dict = Depends(get_current_user),
):
    """Compute canonical hash, sign with ECDSA private key, and embed digital signature into UBL XML."""
    try:
        signed_record = einvoice_service.sign_einvoice(
            invoice_id=invoice_id,
            profile_id=profile_id,
        )
        return signed_record
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Failed to cryptographically sign invoice #{invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sign e-invoice: {exc}")


@router.post('/submit-clearance', response_model=ClearanceSubmissionResponse)
def submit_invoice_clearance(
    payload: ClearanceSubmissionRequest,
    user: dict = Depends(get_current_user),
):
    """Submit an invoice to the fiscal authority for B2B clearance or B2C reporting."""
    try:
        result = einvoice_service.submit_clearance(
            invoice_id=payload.invoice_id,
            profile_id=payload.fiscal_profile_id,
            environment=payload.environment,
            auto_sign=payload.auto_sign,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Clearance submission failed for invoice #{payload.invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clearance submission failed: {exc}")


@router.post('/submit/{invoice_id}', response_model=ClearanceSubmissionResponse)
def submit_clearance_by_id(
    invoice_id: int,
    environment: Optional[str] = Query(None, description="Override environment: Sandbox | Simulation | Production"),
    auto_sign: bool = Query(True, description="Automatically sign before submission if not signed"),
    user: dict = Depends(get_current_user),
):
    """Convenience endpoint to submit an invoice for fiscal clearance by invoice ID."""
    try:
        result = einvoice_service.submit_clearance(
            invoice_id=invoice_id,
            environment=environment,
            auto_sign=auto_sign,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Clearance submission failed for invoice #{invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clearance submission failed: {exc}")


@router.get('/xml/{invoice_id}')
def download_invoice_ubl_xml(
    invoice_id: int,
    user: dict = Depends(get_current_user),
):
    """Download the official OASIS UBL 2.1 XML document for a sales invoice."""
    rec = einvoice_service.get_by_invoice_id(invoice_id)
    xml_content = rec.get("ubl_xml") if rec else None

    if not xml_content:
        # Generate XML if not existing
        try:
            xml_content = einvoice_service.generate_ubl_xml(invoice_id)
        except ValueError as val_err:
            raise HTTPException(status_code=404, detail=str(val_err))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Could not generate XML: {exc}")

    filename = f"einvoice_{invoice_id}.xml"
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/xml; charset=utf-8",
        },
    )


@router.get('/pdf/{invoice_id}')
def download_invoice_fiscal_pdf(
    invoice_id: int,
    user: dict = Depends(get_current_user),
):
    """Download the printable bilingual (English/Arabic) fiscal tax invoice with embedded QR code."""
    try:
        pdf_bytes = fiscal_pdf_service.generate_fiscal_invoice_pdf(invoice_id)
        filename = f"fiscal_invoice_{invoice_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Failed to generate fiscal PDF for invoice #{invoice_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate fiscal PDF: {exc}")
