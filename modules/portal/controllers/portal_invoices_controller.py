import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.services.invoice_pdf_service import InvoicePdfService
from modules.portal.services.stripe_settlement_service import StripeSettlementService
from modules.portal.models.portal import (
    PortalInvoiceResponse,
    InvoiceCheckoutSessionRequest,
    BalanceSettlementCheckoutRequest,
    PortalCheckoutSessionResponse,
    PaymentSessionStatusResponse,
)
from packages.auth.deps import get_current_portal_customer, require_portal_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["Customer Portal Invoices"])


def get_portal_repo() -> PortalRepository:
    return PortalRepository()


def get_pdf_service() -> InvoicePdfService:
    return InvoicePdfService()


def get_settlement_service() -> StripeSettlementService:
    return StripeSettlementService()


# ----------------------------------------------------------------------
# Customer Invoices Query & Detail Endpoints
# ----------------------------------------------------------------------

@router.get("/invoices")
def list_portal_invoices(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by invoice status (Unpaid, Paid, Partially Paid, Cancelled)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_customer: dict = Depends(get_current_portal_customer),
    portal_repo: PortalRepository = Depends(get_portal_repo),
):
    """List customer invoices with open balance and payment details, strictly isolated to customer account."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        invoices, total = portal_repo.get_invoices(
            customer_id=customer_id,
            status=status_filter,
            page=page,
            limit=limit,
        )
        return {
            "items": invoices,
            "total": total,
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to list invoices for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/invoices/{id}", response_model=PortalInvoiceResponse)
def get_portal_invoice_detail(
    id: int,
    current_customer: dict = Depends(get_current_portal_customer),
    portal_repo: PortalRepository = Depends(get_portal_repo),
):
    """Retrieve detailed invoice record with paid amount and balance due, scoped to authenticated customer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        invoice = portal_repo.get_invoice_by_id(invoice_id=id, customer_id=customer_id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invoice #{id} not found")
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch invoice #{id} for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/invoices/{id}/pdf")
def download_invoice_pdf(
    id: int,
    current_customer: dict = Depends(get_current_portal_customer),
    pdf_svc: InvoicePdfService = Depends(get_pdf_service),
):
    """Generate and download a printable PDF invoice document for the authenticated customer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        pdf_bytes = pdf_svc.generate_invoice_pdf(invoice_id=id, customer_id=customer_id)
        filename = f"invoice_{id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate PDF for invoice #{id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error generating PDF invoice")


# ----------------------------------------------------------------------
# Stripe Online Checkout & Settlement Endpoints
# ----------------------------------------------------------------------

@router.post("/invoices/{id}/checkout-session", response_model=PortalCheckoutSessionResponse)
def create_invoice_checkout_session(
    id: int,
    body: Optional[InvoiceCheckoutSessionRequest] = None,
    current_customer: dict = Depends(require_portal_permission("PORTAL_PAY")),
    settlement_svc: StripeSettlementService = Depends(get_settlement_service),
):
    """Create a hosted Stripe Checkout Session to settle an individual invoice via Credit Card or ACH transfer."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    req = body or InvoiceCheckoutSessionRequest()
    req.invoice_id = id
    user_email = current_customer.get("email")

    try:
        return settlement_svc.create_invoice_checkout_session(
            customer_id=customer_id,
            request=req,
            user_email=user_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create checkout session for invoice #{id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/settlement/checkout-session", response_model=PortalCheckoutSessionResponse)
def create_balance_settlement_checkout_session(
    body: BalanceSettlementCheckoutRequest,
    current_customer: dict = Depends(require_portal_permission("PORTAL_PAY")),
    settlement_svc: StripeSettlementService = Depends(get_settlement_service),
):
    """Create a hosted Stripe Checkout Session to settle outstanding customer balance across multiple invoices."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )
    user_email = current_customer.get("email")

    try:
        return settlement_svc.create_balance_settlement_session(
            customer_id=customer_id,
            request=body,
            user_email=user_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create balance settlement checkout session for customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/settlement/session/{session_id}")
def get_or_verify_settlement_session(
    session_id: str,
    verify: bool = Query(True, description="Verify status and trigger automatic AR reconciliation if completed"),
    current_customer: dict = Depends(get_current_portal_customer),
    settlement_svc: StripeSettlementService = Depends(get_settlement_service),
):
    """Check payment status of a Stripe checkout session and automatically reconcile settled transactions."""
    customer_id = current_customer.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a customer account",
        )

    try:
        if verify:
            return settlement_svc.verify_and_reconcile_session(session_id=session_id, customer_id=customer_id)
        else:
            return settlement_svc.get_session_status(session_id=session_id, customer_id=customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to verify settlement session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
