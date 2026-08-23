import os
import logging
from typing import Optional, List, Dict, Any

from modules.portal.repositories.portal_repo import PortalRepository
from modules.portal.models.portal import (
    InvoiceCheckoutSessionRequest,
    BalanceSettlementCheckoutRequest,
    PortalCheckoutSessionResponse,
    PaymentSessionStatusResponse,
)
from packages.billing.stripe_service import (
    create_settlement_checkout_session,
    get_checkout_session,
    _get_stripe,
)

logger = logging.getLogger(__name__)


class StripeSettlementService:
    """Service for handling B2B Customer Portal online settlements via Stripe (Card & ACH).
    
    Supports:
    - Creating Stripe Checkout Sessions for individual invoices with Card and ACH (us_bank_account).
    - Creating Stripe Checkout Sessions for aggregate balance settlement.
    - Retrieving and verifying Checkout Session payment status.
    - Synchronizing session IDs and payment links with invoice records (T0090).
    """

    def __init__(self, portal_repo: Optional[PortalRepository] = None):
        self.portal_repo = portal_repo or PortalRepository()

    def get_portal_base_url(self) -> str:
        """Return the frontend base URL for customer portal redirects."""
        return os.environ.get("PORTAL_BASE_URL", "http://localhost:5173").rstrip("/")

    def create_invoice_checkout_session(
        self,
        customer_id: int,
        request: InvoiceCheckoutSessionRequest,
        user_email: Optional[str] = None,
    ) -> PortalCheckoutSessionResponse:
        """Create a Stripe Checkout Session for settling a specific customer invoice."""
        # 1. Fetch customer profile
        customer = self.portal_repo.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer account with ID {customer_id} does not exist.")

        # 2. Fetch invoice with ownership validation
        invoice = self.portal_repo.get_invoice_by_id(request.invoice_id, customer_id=customer_id)
        if not invoice:
            raise ValueError(f"Invoice #{request.invoice_id} was not found or does not belong to your account.")

        # 3. Validate invoice payment eligibility
        inv_status = (invoice.get("status") or "").strip()
        balance_due = invoice.get("balance_due", 0.0)
        total_amount = invoice.get("total_amount", 0.0)
        amount_to_pay = balance_due if balance_due > 0 else total_amount

        if inv_status == "Paid" or (balance_due <= 0 and total_amount > 0):
            raise ValueError(f"Invoice #{invoice.get('invoice_number', request.invoice_id)} is already fully settled.")

        if inv_status == "Cancelled":
            raise ValueError(f"Invoice #{invoice.get('invoice_number', request.invoice_id)} has been cancelled and cannot be paid.")

        if amount_to_pay <= 0:
            raise ValueError(f"Invoice has no outstanding balance to pay.")

        # 4. Determine URLs
        base_url = self.get_portal_base_url()
        success_url = request.success_url or f"{base_url}/portal/payment/result?session_id={{CHECKOUT_SESSION_ID}}&status=success&invoice_id={invoice['id']}"
        cancel_url = request.cancel_url or f"{base_url}/portal/invoices?session_id={{CHECKOUT_SESSION_ID}}&status=cancelled&invoice_id={invoice['id']}"

        # 5. Determine payment method types (default card + ACH us_bank_account)
        payment_methods = request.payment_method_types or ["card", "us_bank_account"]

        # 6. Create Stripe Checkout Session
        result = create_settlement_checkout_session(
            customer_id=customer_id,
            amount=amount_to_pay,
            settlement_type="invoice",
            invoice_id=invoice["id"],
            invoice_number=invoice.get("invoice_number", ""),
            customer_name=customer.get("name", ""),
            customer_email=user_email or customer.get("email"),
            payment_method_types=payment_methods,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if "error" in result:
            logger.error(f"Failed to create Stripe checkout session for invoice {invoice['id']}: {result['error']}")
            raise ValueError(result["error"])

        # 7. Persist session_id and payment_link to invoice in T0090
        session_id = result["session_id"]
        checkout_url = result["url"]
        self.portal_repo.update_invoice_stripe_session(
            invoice_id=invoice["id"],
            session_id=session_id,
            payment_link=checkout_url,
        )

        return PortalCheckoutSessionResponse(
            session_id=session_id,
            checkout_url=checkout_url,
            customer_id=customer_id,
            amount=amount_to_pay,
            amount_cents=result["amount_cents"],
            currency=result.get("currency", "usd"),
            settlement_type="invoice",
            invoice_id=invoice["id"],
            payment_method_types=payment_methods,
            status=result.get("status", "open"),
        )

    def create_balance_settlement_session(
        self,
        customer_id: int,
        request: BalanceSettlementCheckoutRequest,
        user_email: Optional[str] = None,
    ) -> PortalCheckoutSessionResponse:
        """Create a Stripe Checkout Session for aggregate balance settlement across invoices."""
        # 1. Fetch customer
        customer = self.portal_repo.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer account with ID {customer_id} does not exist.")

        # 2. Validate amount
        if request.amount <= 0:
            raise ValueError("Settlement amount must be greater than zero.")

        # 3. Validate optional specific invoice_ids
        if request.invoice_ids:
            for inv_id in request.invoice_ids:
                inv = self.portal_repo.get_invoice_by_id(inv_id, customer_id=customer_id)
                if not inv:
                    raise ValueError(f"Invoice ID {inv_id} was not found or does not belong to your account.")

        # 4. Determine URLs
        base_url = self.get_portal_base_url()
        success_url = request.success_url or f"{base_url}/portal/payment/result?session_id={{CHECKOUT_SESSION_ID}}&status=success&type=balance"
        cancel_url = request.cancel_url or f"{base_url}/portal/invoices?session_id={{CHECKOUT_SESSION_ID}}&status=cancelled&type=balance"

        payment_methods = request.payment_method_types or ["card", "us_bank_account"]

        # 5. Call billing service
        result = create_settlement_checkout_session(
            customer_id=customer_id,
            amount=request.amount,
            settlement_type="balance",
            invoice_ids=request.invoice_ids,
            customer_name=customer.get("name", ""),
            customer_email=user_email or customer.get("email"),
            payment_method_types=payment_methods,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if "error" in result:
            logger.error(f"Failed to create balance settlement checkout session for customer {customer_id}: {result['error']}")
            raise ValueError(result["error"])

        return PortalCheckoutSessionResponse(
            session_id=result["session_id"],
            checkout_url=result["url"],
            customer_id=customer_id,
            amount=request.amount,
            amount_cents=result["amount_cents"],
            currency=result.get("currency", "usd"),
            settlement_type="balance",
            invoice_id=None,
            payment_method_types=payment_methods,
            status=result.get("status", "open"),
        )

    def get_session_status(
        self,
        session_id: str,
        customer_id: Optional[int] = None,
    ) -> PaymentSessionStatusResponse:
        """Retrieve the live status and payment outcome of a Stripe checkout session."""
        result = get_checkout_session(session_id)
        if "error" in result:
            raise ValueError(result["error"])

        metadata = result.get("metadata", {})
        session_customer_id = metadata.get("customer_id")
        
        # Security check: if customer_id provided, ensure session matches
        if customer_id is not None and session_customer_id and session_customer_id != str(customer_id):
            raise ValueError("Checkout session does not belong to the authenticated customer.")

        invoice_id_val = None
        if metadata.get("invoice_id"):
            try:
                invoice_id_val = int(metadata["invoice_id"])
            except ValueError:
                pass

        cid_val = None
        if session_customer_id:
            try:
                cid_val = int(session_customer_id)
            except ValueError:
                pass

        return PaymentSessionStatusResponse(
            session_id=result["session_id"],
            status=result.get("status", "open"),
            payment_status=result.get("payment_status", "unpaid"),
            payment_intent_id=result.get("payment_intent_id"),
            amount_total=result.get("amount_total"),
            currency=result.get("currency", "usd"),
            customer_id=cid_val,
            invoice_id=invoice_id_val,
            customer_email=result.get("customer_email"),
        )

    def reconcile_checkout_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reconcile a completed Stripe Checkout Session for B2B portal settlement."""
        session_id = session_data.get("id") or session_data.get("session_id")
        payment_intent_id = session_data.get("payment_intent") or session_data.get("payment_intent_id")
        if isinstance(payment_intent_id, dict):
            payment_intent_id = payment_intent_id.get("id")

        metadata = session_data.get("metadata") or {}
        customer_id_str = metadata.get("customer_id")
        if not customer_id_str:
            logger.info(f"Skipping checkout session {session_id} reconciliation - no customer_id in metadata.")
            return {"skipped": True, "reason": "No customer_id in metadata"}

        customer_id = int(customer_id_str)
        settlement_type = metadata.get("settlement_type", "invoice")

        invoice_id = None
        if metadata.get("invoice_id"):
            try:
                invoice_id = int(metadata["invoice_id"])
            except (ValueError, TypeError):
                pass

        invoice_ids = None
        if metadata.get("invoice_ids"):
            try:
                invoice_ids = [int(i.strip()) for i in str(metadata["invoice_ids"]).split(",") if i.strip().isdigit()]
            except Exception:
                pass

        # Determine settlement amount
        amount = 0.0
        raw_total = session_data.get("amount_total")
        if raw_total is not None:
            amount = float(raw_total) / 100.0 if float(raw_total) > 1000 and metadata.get("amount") and float(raw_total) == float(metadata.get("amount_cents", 0)) else float(raw_total) if float(raw_total) < 1000 and not metadata.get("amount_cents") else float(raw_total) / 100.0
        if amount <= 0:
            if metadata.get("amount_cents"):
                amount = float(metadata["amount_cents"]) / 100.0
            elif metadata.get("amount"):
                amount = float(metadata["amount"])

        # Determine payment method
        payment_methods = session_data.get("payment_method_types") or []
        if isinstance(payment_methods, str):
            payment_methods = [payment_methods]
        
        if "us_bank_account" in payment_methods:
            method_name = "Stripe ACH"
        elif "card" in payment_methods:
            method_name = "Stripe Card"
        else:
            method_name = "Stripe Online"

        checkout_url = session_data.get("url")

        logger.info(f"Reconciling Stripe settlement for customer #{customer_id}, session {session_id}, amount ${amount:.2f}")
        return self.portal_repo.reconcile_settlement_transaction(
            customer_id=customer_id,
            amount=amount,
            settlement_type=settlement_type,
            invoice_id=invoice_id,
            invoice_ids=invoice_ids,
            session_id=session_id,
            payment_intent_id=payment_intent_id,
            payment_method=method_name,
            payment_link=checkout_url,
        )

    def reconcile_payment_intent(self, payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reconcile a succeeded payment intent for B2B portal settlement."""
        payment_intent_id = payment_intent_data.get("id")
        metadata = payment_intent_data.get("metadata") or {}
        customer_id_str = metadata.get("customer_id")
        if not customer_id_str:
            logger.info(f"Skipping payment intent {payment_intent_id} reconciliation - no customer_id in metadata.")
            return {"skipped": True, "reason": "No customer_id in metadata"}

        customer_id = int(customer_id_str)
        settlement_type = metadata.get("settlement_type", "invoice")

        invoice_id = None
        if metadata.get("invoice_id"):
            try:
                invoice_id = int(metadata["invoice_id"])
            except (ValueError, TypeError):
                pass

        invoice_ids = None
        if metadata.get("invoice_ids"):
            try:
                invoice_ids = [int(i.strip()) for i in str(metadata["invoice_ids"]).split(",") if i.strip().isdigit()]
            except Exception:
                pass

        amount = 0.0
        raw_amount = payment_intent_data.get("amount")
        if raw_amount is not None:
            amount = float(raw_amount) / 100.0
        elif metadata.get("amount_cents"):
            amount = float(metadata["amount_cents"]) / 100.0
        elif metadata.get("amount"):
            amount = float(metadata["amount"])

        payment_methods = payment_intent_data.get("payment_method_types") or []
        if isinstance(payment_methods, str):
            payment_methods = [payment_methods]

        if "us_bank_account" in payment_methods:
            method_name = "Stripe ACH"
        elif "card" in payment_methods:
            method_name = "Stripe Card"
        else:
            method_name = "Stripe Online"

        return self.portal_repo.reconcile_settlement_transaction(
            customer_id=customer_id,
            amount=amount,
            settlement_type=settlement_type,
            invoice_id=invoice_id,
            invoice_ids=invoice_ids,
            session_id=None,
            payment_intent_id=payment_intent_id,
            payment_method=method_name,
            payment_link=None,
        )

    def verify_and_reconcile_session(
        self,
        session_id: str,
        customer_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Verify checkout session status via Stripe and reconcile if paid."""
        session_info = get_checkout_session(session_id)
        if "error" in session_info:
            raise ValueError(session_info["error"])

        metadata = session_info.get("metadata", {})
        session_customer_id = metadata.get("customer_id")
        if customer_id is not None and session_customer_id and session_customer_id != str(customer_id):
            raise ValueError("Checkout session does not belong to the authenticated customer.")

        payment_status = session_info.get("payment_status")
        session_status = session_info.get("status")

        if payment_status in ("paid", "no_payment_required") or session_status == "complete":
            return self.reconcile_checkout_session(session_info)

        return {
            "reconciled": False,
            "session_id": session_id,
            "status": session_status,
            "payment_status": payment_status,
        }

