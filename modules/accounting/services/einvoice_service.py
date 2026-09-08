import logging
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any, Union

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.connection import db_transaction

from modules.accounting.models.einvoice import (
    EINVOICE_RECORD_REPO,
    FISCAL_PROFILE_REPO,
    ClearanceSubmissionResponse,
    QRCodeResponse,
    FiscalProfileResponse,
    EInvoiceResponse,
)
from modules.accounting.services.tlv_qr_service import (
    generate_zatca_qr_tlv,
    encode_tlv_base64,
    decode_tlv,
)
from modules.accounting.services.ubl_builder_service import (
    UBLBuilderService,
    generate_ubl_invoice_xml,
    SUBTYPE_STANDARD_B2B,
    SUBTYPE_SIMPLIFIED_B2C,
    INVOICE_TYPE_TAX_INVOICE,
)
from modules.accounting.services.einvoice_crypto_service import EInvoiceCryptoService
from modules.accounting.services.fiscal_authority_service import FiscalAuthorityService
from modules.accounting.services.invoice_service import (
    INVOICE_REPO,
    CUSTOMER_REPO,
    LINE_REPO,
)

logger = logging.getLogger(__name__)


class EInvoiceService(CrudService):
    """Core domain service for Government e-Invoicing & Fiscal Authority Integration.

    Orchestrates:
    - Base64 Tag-Length-Value (TLV) QR code generation (ZATCA Phase 1 & 2 compliant)
    - OASIS UBL 2.1 XML document creation for Standard B2B and Simplified B2C invoices
    - Cryptographic SHA-256 canonical hashing & Previous Invoice Hash (PIH) chain maintenance
    - ECDSA/RSA digital signing & X.509 certificate embedding
    - Direct integration with Fiscal Authority clearance (B2B) and reporting (B2C) gateways
    - Lifecycle hooks for core sales invoice workflows
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        fiscal_profile_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        line_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or EINVOICE_RECORD_REPO)
        self.fiscal_profile_repo = fiscal_profile_repo or FISCAL_PROFILE_REPO
        self.invoice_repo = invoice_repo or INVOICE_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.line_repo = line_repo or LINE_REPO

    def get_active_fiscal_profile(
        self,
        profile_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Fetch the active fiscal authority profile (T0130).

        If profile_id is supplied, retrieves that specific profile.
        Otherwise, finds active profile marked as default, or first active profile.
        Falls back to a default organization profile if none is configured.
        """
        if profile_id:
            profile = self.fiscal_profile_repo.get(profile_id, conn=conn)
            if profile:
                return profile

        try:
            profiles = self.fiscal_profile_repo.list(filters={"is_active": True}, conn=conn)
            if profiles:
                # Find default profile or return first active
                default_profile = next((p for p in profiles if p.get("is_default")), profiles[0])
                return default_profile
        except Exception as exc:
            logger.warning(f"Could not query fiscal profiles: {exc}")

        # Fallback profile for initial development or unconfigured tenants
        return {
            "id": None,
            "profile_name": "Default Fiscal Profile",
            "authority_code": "ZATCA",
            "seller_name": "Nova Global Trading LLC",
            "seller_name_ar": "شركة نوفا للتجارة العامة",
            "tax_id": "300012345600003",
            "commercial_registration_number": "1010123456",
            "building_number": "1234",
            "street_name": "King Fahd Road",
            "district": "Al Olaya",
            "city": "Riyadh",
            "postal_code": "12211",
            "country_code": "SA",
            "environment": "Sandbox",
            "is_active": True,
        }

    def get_by_invoice_id(self, invoice_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve existing e-invoice clearance record (T0129) by sales invoice ID."""
        try:
            records = self.repo.list(filters={"invoice_id": invoice_id}, conn=conn)
            if records:
                return records[0]
        except Exception as exc:
            logger.warning(f"Could not query e-invoice record for invoice {invoice_id}: {exc}")
        return None

    def get_next_icv(self, conn=None) -> int:
        """Compute the next sequential Invoice Counter Value (ICV)."""
        try:
            records = self.repo.list(limit=5000, conn=conn)
            if records:
                max_icv = max((int(r.get("icv") or 0) for r in records), default=0)
                return max_icv + 1
        except Exception as exc:
            logger.warning(f"Could not compute next ICV: {exc}")
        return 1

    def get_previous_invoice_hash(self, conn=None) -> str:
        """Fetch the Previous Invoice Hash (PIH) for cryptographic chain audit trail."""
        try:
            records = self.repo.list(limit=5000, conn=conn)
            if records:
                # Filter records with an invoice_hash and sort by id descending
                hashed = [r for r in records if r.get("invoice_hash")]
                if hashed:
                    hashed.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
                    return hashed[0]["invoice_hash"]
        except Exception as exc:
            logger.warning(f"Could not query previous invoice hash: {exc}")

        return EInvoiceCryptoService.get_genesis_pih()

    def generate_qr_code(self, invoice_id: int, conn=None) -> QRCodeResponse:
        """Generate or retrieve Base64 TLV QR Code data for an invoice."""
        inv = self.invoice_repo.get(invoice_id, conn=conn)
        if not inv:
            raise ValueError(f"Sales invoice {invoice_id} not found")

        # Check if record already exists
        rec = self.get_by_invoice_id(invoice_id, conn=conn)
        if rec and rec.get("qr_code_tlv"):
            profile = self.get_active_fiscal_profile(rec.get("fiscal_profile_id"), conn=conn)
            total = float(inv.get("total_amount") or 0.0)
            vat = round(total - (total / 1.15), 2)
            ts = inv.get("issue_date") or datetime.now(timezone.utc).isoformat()
            if isinstance(ts, (date, datetime)):
                ts = ts.isoformat()

            return QRCodeResponse(
                invoice_id=invoice_id,
                qr_code_tlv=rec["qr_code_tlv"],
                seller_name=profile.get("seller_name", "Nova Enterprises"),
                tax_id=profile.get("tax_id", "300000000000003"),
                timestamp=str(ts),
                total_amount=total,
                vat_total=vat,
                invoice_hash=rec.get("invoice_hash"),
            )

        # Build fresh TLV QR Code
        profile = self.get_active_fiscal_profile(conn=conn)
        seller_name = profile.get("seller_name", "Nova Global Trading LLC")
        tax_id = profile.get("tax_id", "300012345600003")

        total_amount = float(inv.get("total_amount") or 0.0)
        vat_total = round(total_amount - (total_amount / 1.15), 2)

        issue_date = inv.get("issue_date") or datetime.now(timezone.utc).date()
        if isinstance(issue_date, (date, datetime)):
            ts_str = f"{issue_date.isoformat()}T12:00:00Z" if isinstance(issue_date, date) and not isinstance(issue_date, datetime) else issue_date.isoformat()
        else:
            ts_str = str(issue_date)

        inv_hash = rec.get("invoice_hash") if rec else None
        ecdsa_sig = rec.get("digital_signature") if rec else None
        pub_key = rec.get("public_key") if rec else None

        qr_tlv = generate_zatca_qr_tlv(
            seller_name=seller_name,
            vat_number=tax_id,
            timestamp=ts_str,
            total_amount=total_amount,
            vat_total=vat_total,
            invoice_hash=inv_hash,
            ecdsa_signature=ecdsa_sig,
            public_key=pub_key,
        )

        return QRCodeResponse(
            invoice_id=invoice_id,
            qr_code_tlv=qr_tlv,
            seller_name=seller_name,
            tax_id=tax_id,
            timestamp=ts_str,
            total_amount=total_amount,
            vat_total=vat_total,
            invoice_hash=inv_hash,
        )

    def generate_ubl_xml(
        self,
        invoice_id: int,
        profile_id: Optional[int] = None,
        subtype: Optional[str] = None,
        conn=None,
    ) -> str:
        """Generate OASIS UBL 2.1 XML document for a sales invoice and persist draft T0129 record."""
        with db_transaction(conn) as tx_conn:
            inv = self.invoice_repo.get(invoice_id, conn=tx_conn)
            if not inv:
                raise ValueError(f"Sales invoice {invoice_id} not found")

            profile = self.get_active_fiscal_profile(profile_id, conn=tx_conn)

            # Customer details
            customer = None
            partner_id = inv.get("partner_id")
            if partner_id:
                try:
                    customer = self.customer_repo.get(partner_id, conn=tx_conn)
                except Exception as exc:
                    logger.warning(f"Could not fetch customer {partner_id}: {exc}")

            # Line items
            lines = []
            sales_order_id = inv.get("sales_order_id")
            if sales_order_id:
                try:
                    lines = self.line_repo.list(filters={"sales_order_id": sales_order_id}, conn=tx_conn)
                except Exception as exc:
                    logger.warning(f"Could not fetch lines for order {sales_order_id}: {exc}")

            # Resolve subtype: standard B2B if buyer has VAT/tax ID, simplified B2C otherwise
            if not subtype:
                if customer and (customer.get("tax_id") or customer.get("vat_number")):
                    resolved_subtype = SUBTYPE_STANDARD_B2B
                else:
                    resolved_subtype = SUBTYPE_SIMPLIFIED_B2C
            else:
                resolved_subtype = subtype

            # Retrieve or generate UUID and ICV
            rec = self.get_by_invoice_id(invoice_id, conn=tx_conn)
            inv_uuid = (rec.get("invoice_uuid") if rec else None) or str(uuid.uuid4())
            icv = (int(rec.get("icv")) if rec and rec.get("icv") else None) or self.get_next_icv(conn=tx_conn)
            pih = (rec.get("pih") if rec and rec.get("pih") else None) or self.get_previous_invoice_hash(conn=tx_conn)

            # Base QR TLV
            qr_res = self.generate_qr_code(invoice_id, conn=tx_conn)
            qr_tlv = qr_res.qr_code_tlv

            xml_content = generate_ubl_invoice_xml(
                invoice=inv,
                supplier_profile=profile,
                customer=customer,
                lines=lines,
                subtype=resolved_subtype,
                icv=icv,
                pih=pih,
                qr_code_tlv=qr_tlv,
            )

            # Compute preliminary invoice hash
            inv_hash = EInvoiceCryptoService.compute_sha256_hash(xml_content)

            # Update or create T0129 record
            record_payload = {
                "invoice_id": invoice_id,
                "fiscal_profile_id": profile.get("id"),
                "invoice_uuid": inv_uuid,
                "invoice_type_code": INVOICE_TYPE_TAX_INVOICE,
                "subtype": resolved_subtype,
                "icv": icv,
                "pih": pih,
                "invoice_hash": inv_hash,
                "qr_code_tlv": qr_tlv,
                "ubl_xml": xml_content,
                "clearance_status": rec.get("clearance_status", "Draft") if rec else "Draft",
                "environment": profile.get("environment", "Sandbox"),
            }

            if rec:
                self.repo.update(rec["id"], record_payload, conn=tx_conn)
            else:
                self.repo.create(record_payload, conn=tx_conn)

            return xml_content

    def sign_einvoice(
        self,
        invoice_id: int,
        profile_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Cryptographically sign invoice UBL XML with ECDSA private key and embed signature."""
        with db_transaction(conn) as tx_conn:
            rec = self.get_by_invoice_id(invoice_id, conn=tx_conn)
            if not rec or not rec.get("ubl_xml"):
                self.generate_ubl_xml(invoice_id, profile_id=profile_id, conn=tx_conn)
                rec = self.get_by_invoice_id(invoice_id, conn=tx_conn)

            profile = self.get_active_fiscal_profile(profile_id or (rec.get("fiscal_profile_id") if rec else None), conn=tx_conn)
            priv_key = profile.get("private_key")
            pub_key = profile.get("public_key")
            cert = profile.get("certificate")

            # Generate keypair if profile does not have keys configured
            if not priv_key:
                priv_key, generated_pub = EInvoiceCryptoService.generate_ecdsa_keypair()
                pub_key = pub_key or generated_pub

            ubl_xml = rec.get("ubl_xml", "")
            invoice_hash = EInvoiceCryptoService.compute_sha256_hash(ubl_xml)
            signature = EInvoiceCryptoService.sign_invoice_hash(invoice_hash, priv_key)
            signed_xml = EInvoiceCryptoService.embed_signature_in_ubl_xml(ubl_xml, signature, cert)

            # Regenerate QR code with signature & public key
            inv = self.invoice_repo.get(invoice_id, conn=tx_conn)
            total = float(inv.get("total_amount") or 0.0)
            vat = round(total - (total / 1.15), 2)
            ts = inv.get("issue_date") or datetime.now(timezone.utc).isoformat()
            if isinstance(ts, (date, datetime)):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)

            qr_tlv = generate_zatca_qr_tlv(
                seller_name=profile.get("seller_name", "Nova Enterprises"),
                vat_number=profile.get("tax_id", "300000000000003"),
                timestamp=ts_str,
                total_amount=total,
                vat_total=vat,
                invoice_hash=invoice_hash,
                ecdsa_signature=signature,
                public_key=pub_key,
                certificate_stamp=cert,
            )

            update_data = {
                "invoice_hash": invoice_hash,
                "digital_signature": signature,
                "public_key": pub_key,
                "certificate": cert,
                "qr_code_tlv": qr_tlv,
                "ubl_xml": signed_xml,
            }

            self.repo.update(rec["id"], update_data, conn=tx_conn)
            return self.repo.get(rec["id"], conn=tx_conn)

    def submit_clearance(
        self,
        invoice_id: int,
        profile_id: Optional[int] = None,
        environment: Optional[str] = None,
        auto_sign: bool = True,
        conn=None,
    ) -> ClearanceSubmissionResponse:
        """Submit invoice to the Fiscal Authority for clearance (B2B) or reporting (B2C)."""
        with db_transaction(conn) as tx_conn:
            rec = self.get_by_invoice_id(invoice_id, conn=tx_conn)
            if not rec or not rec.get("digital_signature"):
                if auto_sign:
                    rec = self.sign_einvoice(invoice_id, profile_id=profile_id, conn=tx_conn)
                else:
                    raise ValueError(f"Invoice {invoice_id} must be cryptographically signed before submission")

            profile = self.get_active_fiscal_profile(profile_id or rec.get("fiscal_profile_id"), conn=tx_conn)
            fiscal_service = FiscalAuthorityService.from_profile(profile, environment_override=environment)

            subtype = rec.get("subtype", SUBTYPE_STANDARD_B2B)
            if subtype == SUBTYPE_STANDARD_B2B:
                result = fiscal_service.submit_clearance(
                    invoice_id=invoice_id,
                    invoice_uuid=rec["invoice_uuid"],
                    invoice_hash=rec["invoice_hash"],
                    signed_ubl_xml=rec["ubl_xml"],
                    qr_code_tlv=rec.get("qr_code_tlv"),
                )
            else:
                result = fiscal_service.submit_reporting(
                    invoice_id=invoice_id,
                    invoice_uuid=rec["invoice_uuid"],
                    invoice_hash=rec["invoice_hash"],
                    signed_ubl_xml=rec["ubl_xml"],
                    qr_code_tlv=rec.get("qr_code_tlv"),
                )

            # Persist clearance outcome to T0129
            update_payload = {
                "clearance_status": result.clearance_status,
                "clearance_id": result.clearance_id,
                "clearance_date": result.submitted_at or datetime.now(timezone.utc),
                "validation_results": result.validation_results,
                "rejection_reason": result.error_message,
                "is_cleared": result.clearance_status == "Cleared",
                "is_reported": result.clearance_status == "Reported",
                "environment": environment or profile.get("environment", "Sandbox"),
            }

            self.repo.update(rec["id"], update_payload, conn=tx_conn)
            return result

    def process_invoice_einvoice(
        self,
        invoice: Dict[str, Any],
        auto_submit: bool = False,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Lifecycle hook: automatically generate QR and e-invoice record on invoice creation."""
        invoice_id = invoice.get("id")
        if not invoice_id:
            return None

        try:
            self.generate_ubl_xml(invoice_id, conn=conn)
            if auto_submit:
                self.sign_einvoice(invoice_id, conn=conn)
                self.submit_clearance(invoice_id, conn=conn)
            return self.get_by_invoice_id(invoice_id, conn=conn)
        except Exception as exc:
            logger.warning(f"Could not auto-process e-invoice for invoice {invoice_id}: {exc}")
            return None
