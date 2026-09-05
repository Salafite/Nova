from typing import Optional, Any, Dict, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from modules.core.models.base import AuditMixin
from modules.core.repositories.base import CrudRepository


# ---------------------------------------------------------------------------
# Fiscal Authority Profile Models (T0125)
# ---------------------------------------------------------------------------

class FiscalProfileCreate(BaseModel):
    """Payload for creating a fiscal authority configuration profile."""
    profile_name: str = Field(..., max_length=100, description="Descriptive profile name, e.g. 'Main Store ZATCA'")
    authority_code: str = Field('ZATCA', max_length=50, description="Tax authority: ZATCA | PEPPOL | NTS | GENERIC")
    seller_name: Optional[str] = Field(None, max_length=255, description="Official legal seller name in English/Latin")
    seller_legal_name: Optional[str] = Field(None, max_length=255, description="Alias for seller_name")
    seller_name_ar: Optional[str] = Field(None, max_length=255, description="Official legal seller name in Arabic")
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax Registration / VAT Identification Number")
    seller_vat_number: Optional[str] = Field(None, max_length=50, description="Alias for tax_id")
    commercial_registration_number: Optional[str] = Field(None, max_length=50, description="Commercial Registration (CR) number")
    building_number: Optional[str] = Field(None, max_length=20, description="Building / postal unit number")
    street_name: Optional[str] = Field(None, max_length=255, description="Street name in English")
    street_name_ar: Optional[str] = Field(None, max_length=255, description="Street name in Arabic")
    district: Optional[str] = Field(None, max_length=100, description="District / neighborhood in English")
    district_ar: Optional[str] = Field(None, max_length=100, description="District / neighborhood in Arabic")
    city: Optional[str] = Field(None, max_length=100, description="City in English")
    seller_city: Optional[str] = Field(None, max_length=100, description="Alias for city")
    city_ar: Optional[str] = Field(None, max_length=100, description="City in Arabic")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal / ZIP code")
    country_code: str = Field('SA', max_length=10, description="ISO-3166 2-letter country code")
    seller_country_code: Optional[str] = Field(None, max_length=10, description="Alias for country_code")
    environment: str = Field('Sandbox', max_length=30, description="Environment: Sandbox | Simulation | Production")
    api_base_url: Optional[str] = Field(None, max_length=255, description="Fiscal authority gateway API base URL")
    api_key: Optional[str] = Field(None, max_length=255, description="API client key or username")
    api_secret: Optional[str] = Field(None, max_length=255, description="API client secret / password")
    auth_token: Optional[str] = Field(None, description="Active Bearer or session auth token")
    token_expires_at: Optional[datetime] = Field(None, description="Auth token expiration timestamp")
    csid: Optional[str] = Field(None, description="Cryptographic Stamp Identifier (CSID)")
    csid_secret: Optional[str] = Field(None, description="CSID secret or OTP")
    private_key: Optional[str] = Field(None, description="PEM encoded ECDSA/RSA private key")
    public_key: Optional[str] = Field(None, description="PEM encoded ECDSA/RSA public key")
    certificate: Optional[str] = Field(None, description="PEM encoded X.509 security certificate")
    is_default: bool = Field(False, description="Whether this profile is default for tenant")
    is_active: bool = Field(True, description="Whether this fiscal profile is active")
    business_id: Optional[int] = Field(None, description="Multi-tenant business organization ID")

    @model_validator(mode='after')
    def sync_aliases(self) -> 'FiscalProfileCreate':
        if not self.seller_name and self.seller_legal_name:
            self.seller_name = self.seller_legal_name
        elif not self.seller_legal_name and self.seller_name:
            self.seller_legal_name = self.seller_name

        if not self.tax_id and self.seller_vat_number:
            self.tax_id = self.seller_vat_number
        elif not self.seller_vat_number and self.tax_id:
            self.seller_vat_number = self.tax_id

        if not self.city and self.seller_city:
            self.city = self.seller_city
        elif not self.seller_city and self.city:
            self.seller_city = self.city

        if self.seller_country_code:
            self.country_code = self.seller_country_code

        if not self.seller_name and not self.seller_legal_name:
            raise ValueError("Either seller_name or seller_legal_name is required")
        if not self.tax_id and not self.seller_vat_number:
            raise ValueError("Either tax_id or seller_vat_number is required")

        return self


class FiscalProfileUpdate(BaseModel):
    """Payload for updating an existing fiscal authority profile."""
    profile_name: Optional[str] = Field(None, max_length=100)
    authority_code: Optional[str] = Field(None, max_length=50)
    seller_name: Optional[str] = Field(None, max_length=255)
    seller_legal_name: Optional[str] = Field(None, max_length=255)
    seller_name_ar: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=50)
    seller_vat_number: Optional[str] = Field(None, max_length=50)
    commercial_registration_number: Optional[str] = Field(None, max_length=50)
    building_number: Optional[str] = Field(None, max_length=20)
    street_name: Optional[str] = Field(None, max_length=255)
    street_name_ar: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    district_ar: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    seller_city: Optional[str] = Field(None, max_length=100)
    city_ar: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, max_length=10)
    seller_country_code: Optional[str] = Field(None, max_length=10)
    environment: Optional[str] = Field(None, max_length=30)
    api_base_url: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    api_secret: Optional[str] = Field(None, max_length=255)
    auth_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    csid: Optional[str] = None
    csid_secret: Optional[str] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def sync_aliases(self) -> 'FiscalProfileUpdate':
        if self.seller_legal_name and not self.seller_name:
            self.seller_name = self.seller_legal_name
        if self.seller_vat_number and not self.tax_id:
            self.tax_id = self.seller_vat_number
        if self.seller_city and not self.city:
            self.city = self.seller_city
        if self.seller_country_code and not self.country_code:
            self.country_code = self.seller_country_code
        return self


class FiscalProfileResponse(AuditMixin):
    """Response representation of a fiscal authority profile."""
    id: int
    profile_name: str
    authority_code: str
    seller_name: Optional[str] = None
    seller_legal_name: Optional[str] = None
    seller_name_ar: Optional[str] = None
    tax_id: Optional[str] = None
    seller_vat_number: Optional[str] = None
    commercial_registration_number: Optional[str] = None
    building_number: Optional[str] = None
    street_name: Optional[str] = None
    street_name_ar: Optional[str] = None
    district: Optional[str] = None
    district_ar: Optional[str] = None
    city: Optional[str] = None
    seller_city: Optional[str] = None
    city_ar: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = 'SA'
    seller_country_code: Optional[str] = None
    environment: str
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    auth_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    csid: Optional[str] = None
    csid_secret: Optional[str] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    is_default: bool = False
    is_active: bool = True

    @model_validator(mode='after')
    def sync_aliases(self) -> 'FiscalProfileResponse':
        if not self.seller_name and self.seller_legal_name:
            self.seller_name = self.seller_legal_name
        elif not self.seller_legal_name and self.seller_name:
            self.seller_legal_name = self.seller_name

        if not self.tax_id and self.seller_vat_number:
            self.tax_id = self.seller_vat_number
        elif not self.seller_vat_number and self.tax_id:
            self.seller_vat_number = self.tax_id

        if not self.city and self.seller_city:
            self.city = self.seller_city
        elif not self.seller_city and self.city:
            self.seller_city = self.city

        if not self.country_code and self.seller_country_code:
            self.country_code = self.seller_country_code
        elif not self.seller_country_code and self.country_code:
            self.seller_country_code = self.country_code

        return self


# ---------------------------------------------------------------------------
# E-Invoice Clearance & Cryptographic Record Models (T0124)
# ---------------------------------------------------------------------------

class EInvoiceCreate(BaseModel):
    """Payload for creating an e-invoice cryptographic/clearance record."""
    invoice_id: int = Field(..., description="Foreign key to sales invoice (t0090)")
    fiscal_profile_id: Optional[int] = Field(None, description="Foreign key to fiscal profile (t0125)")
    invoice_uuid: Optional[str] = Field(None, max_length=100, description="Standard UUID v4 for the e-invoice")
    invoice_type: Optional[str] = Field('Standard', max_length=50, description="Invoice type: Standard | Simplified | Credit | Debit")
    invoice_type_code: str = Field('388', max_length=50, description="UN/ECE 1001 invoice code (388=Tax Invoice, 381=Credit, 383=Debit)")
    subtype: str = Field('0100000', max_length=50, description="Invoice subtype (0100000=Standard B2B, 0200000=Simplified B2C)")
    icv: Optional[int] = Field(1, ge=1, description="Sequential Invoice Counter Value")
    invoice_counter_number: Optional[int] = Field(None, ge=1, description="Alias for icv")
    pih: Optional[str] = Field(None, max_length=255, description="Previous Invoice Hash (Base64 SHA-256)")
    invoice_hash: Optional[str] = Field(None, max_length=255, description="Canonical invoice SHA-256 hash")
    digital_signature: Optional[str] = Field(None, description="Cryptographic digital signature string")
    public_key: Optional[str] = Field(None, description="Public key used for verification")
    certificate: Optional[str] = Field(None, description="X.509 certificate string")
    qr_code_tlv: Optional[str] = Field(None, description="Base64 TLV encoded QR code payload")
    qr_code_payload: Optional[str] = Field(None, description="Alias for qr_code_tlv")
    ubl_xml: Optional[str] = Field(None, description="Full UBL 2.1 XML document content")
    clearance_status: str = Field('Draft', max_length=30, description="Clearance status: Draft | Pending | Cleared | Reported | Rejected | Failed | Not_Submitted")
    clearance_date: Optional[datetime] = Field(None, description="Timestamp of clearance confirmation")
    clearance_id: Optional[str] = Field(None, max_length=100, description="Tax authority clearance ID or IRN")
    clearance_uuid: Optional[str] = Field(None, max_length=100, description="Alias for clearance_id")
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Structured validation response from authority")
    rejection_reason: Optional[str] = Field(None, description="Rejection or error detail from fiscal authority")
    environment: str = Field('Sandbox', max_length=30, description="Submission environment: Sandbox | Simulation | Production")
    is_reported: bool = Field(False, description="Whether the simplified invoice has been reported")
    is_cleared: bool = Field(False, description="Whether the standard invoice has been cleared")
    business_id: Optional[int] = Field(None, description="Multi-tenant business organization ID")

    @model_validator(mode='after')
    def sync_aliases(self) -> 'EInvoiceCreate':
        if self.invoice_counter_number is not None:
            self.icv = self.invoice_counter_number
        elif self.icv is not None:
            self.invoice_counter_number = self.icv

        if self.qr_code_payload is not None and not self.qr_code_tlv:
            self.qr_code_tlv = self.qr_code_payload
        elif self.qr_code_tlv is not None and not self.qr_code_payload:
            self.qr_code_payload = self.qr_code_tlv

        if self.clearance_uuid is not None and not self.clearance_id:
            self.clearance_id = self.clearance_uuid
        elif self.clearance_id is not None and not self.clearance_uuid:
            self.clearance_uuid = self.clearance_id

        return self


class EInvoiceUpdate(BaseModel):
    """Payload for updating an e-invoice record status, signatures, or clearance response."""
    fiscal_profile_id: Optional[int] = None
    invoice_type: Optional[str] = Field(None, max_length=50)
    invoice_type_code: Optional[str] = Field(None, max_length=50)
    subtype: Optional[str] = Field(None, max_length=50)
    icv: Optional[int] = Field(None, ge=1)
    invoice_counter_number: Optional[int] = Field(None, ge=1)
    pih: Optional[str] = Field(None, max_length=255)
    invoice_hash: Optional[str] = Field(None, max_length=255)
    digital_signature: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    qr_code_tlv: Optional[str] = None
    qr_code_payload: Optional[str] = None
    ubl_xml: Optional[str] = None
    clearance_status: Optional[str] = Field(None, max_length=30)
    clearance_date: Optional[datetime] = None
    clearance_id: Optional[str] = Field(None, max_length=100)
    clearance_uuid: Optional[str] = Field(None, max_length=100)
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    rejection_reason: Optional[str] = None
    environment: Optional[str] = Field(None, max_length=30)
    is_reported: Optional[bool] = None
    is_cleared: Optional[bool] = None

    @model_validator(mode='after')
    def sync_aliases(self) -> 'EInvoiceUpdate':
        if self.invoice_counter_number is not None and self.icv is None:
            self.icv = self.invoice_counter_number
        if self.qr_code_payload is not None and self.qr_code_tlv is None:
            self.qr_code_tlv = self.qr_code_payload
        if self.clearance_uuid is not None and self.clearance_id is None:
            self.clearance_id = self.clearance_uuid
        return self


class EInvoiceResponse(AuditMixin):
    """Response representation of an e-invoice cryptographic/clearance record."""
    id: int
    invoice_id: int
    fiscal_profile_id: Optional[int] = None
    invoice_uuid: Optional[str] = None
    invoice_type: Optional[str] = 'Standard'
    invoice_type_code: Optional[str] = '388'
    subtype: Optional[str] = '0100000'
    icv: Optional[int] = 1
    invoice_counter_number: Optional[int] = 1
    pih: Optional[str] = None
    invoice_hash: Optional[str] = None
    digital_signature: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    qr_code_tlv: Optional[str] = None
    qr_code_payload: Optional[str] = None
    ubl_xml: Optional[str] = None
    clearance_status: str = 'Draft'
    clearance_date: Optional[datetime] = None
    clearance_id: Optional[str] = None
    clearance_uuid: Optional[str] = None
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    rejection_reason: Optional[str] = None
    environment: Optional[str] = 'Sandbox'
    is_reported: bool = False
    is_cleared: bool = False

    @model_validator(mode='after')
    def sync_aliases(self) -> 'EInvoiceResponse':
        if self.invoice_counter_number is not None and self.icv is None:
            self.icv = self.invoice_counter_number
        elif self.icv is not None and self.invoice_counter_number is None:
            self.invoice_counter_number = self.icv

        if self.qr_code_payload is not None and not self.qr_code_tlv:
            self.qr_code_tlv = self.qr_code_payload
        elif self.qr_code_tlv is not None and not self.qr_code_payload:
            self.qr_code_payload = self.qr_code_tlv

        if self.clearance_uuid is not None and not self.clearance_id:
            self.clearance_id = self.clearance_uuid
        elif self.clearance_id is not None and not self.clearance_uuid:
            self.clearance_uuid = self.clearance_id

        return self


# ---------------------------------------------------------------------------
# Clearance API Submission & QR Operation Models
# ---------------------------------------------------------------------------

class ClearanceSubmissionRequest(BaseModel):
    """Request payload to submit an invoice for fiscal clearance or reporting."""
    invoice_id: int = Field(..., description="Sales invoice ID to clear/report")
    invoice_type: Optional[str] = Field('Standard', description="Invoice type: Standard | Simplified")
    fiscal_profile_id: Optional[int] = Field(None, description="Optional profile ID override (defaults to active profile)")
    environment: Optional[str] = Field(None, max_length=30, description="Override environment (Sandbox | Simulation | Production)")
    auto_sign: bool = Field(True, description="Automatically compute hash and sign if not already signed")


class ClearanceSubmissionResponse(BaseModel):
    """Response payload returned after tax authority clearance/reporting submission."""
    success: bool = Field(..., description="Whether the submission succeeded or cleared")
    invoice_id: Optional[int] = Field(None, description="Sales invoice ID")
    invoice_uuid: Optional[str] = Field(None, description="Invoice UUID")
    clearance_status: str = Field(..., description="Cleared | Reported | Rejected | Failed | Draft | Pending")
    clearance_id: Optional[str] = Field(None, description="Clearance ID or IRN returned by the tax authority")
    clearance_uuid: Optional[str] = Field(None, description="Alias for clearance_id")
    qr_code_tlv: Optional[str] = Field(None, description="Base64 TLV QR code string")
    qr_code_payload: Optional[str] = Field(None, description="Alias for qr_code_tlv")
    invoice_hash: Optional[str] = Field(None, description="SHA-256 canonical invoice hash")
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Validation messages or warnings from tax authority")
    error_message: Optional[str] = Field(None, description="Primary error message if submission failed")
    submitted_at: Optional[datetime] = Field(default_factory=datetime.now)

    @model_validator(mode='after')
    def sync_aliases(self) -> 'ClearanceSubmissionResponse':
        if self.clearance_uuid is not None and not self.clearance_id:
            self.clearance_id = self.clearance_uuid
        elif self.clearance_id is not None and not self.clearance_uuid:
            self.clearance_uuid = self.clearance_id

        if self.qr_code_payload is not None and not self.qr_code_tlv:
            self.qr_code_tlv = self.qr_code_payload
        elif self.qr_code_tlv is not None and not self.qr_code_payload:
            self.qr_code_payload = self.qr_code_tlv
        return self


class QRCodeResponse(BaseModel):
    """Response containing Base64 TLV data and metadata for rendering QR codes."""
    invoice_id: int
    qr_code_tlv: Optional[str] = Field(None, description="Base64-encoded TLV QR data")
    qr_code_payload: Optional[str] = Field(None, description="Alias for qr_code_tlv")
    qr_image_data_uri: Optional[str] = Field(None, description="Data URI (data:image/png;base64,...) for instant frontend rendering")
    seller_name: Optional[str] = Field(None, description="Seller business name")
    tax_id: Optional[str] = Field(None, description="Seller tax / VAT registration ID")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    total_amount: Optional[float] = Field(None, description="Total amount with tax")
    vat_total: Optional[float] = Field(None, description="Total VAT amount")
    invoice_hash: Optional[str] = None

    @model_validator(mode='after')
    def sync_aliases(self) -> 'QRCodeResponse':
        if self.qr_code_payload is not None and not self.qr_code_tlv:
            self.qr_code_tlv = self.qr_code_payload
        elif self.qr_code_tlv is not None and not self.qr_code_payload:
            self.qr_code_payload = self.qr_code_tlv
        return self


# ---------------------------------------------------------------------------
# CrudRepositories for T0124 and T0125
# ---------------------------------------------------------------------------

EINVOICE_RECORD_REPO = CrudRepository(
    't0124',
    business_columns=[
        'id', 'invoice_id', 'fiscal_profile_id', 'invoice_uuid', 'invoice_type_code',
        'subtype', 'icv', 'pih', 'invoice_hash', 'digital_signature', 'public_key',
        'certificate', 'qr_code_tlv', 'ubl_xml', 'clearance_status', 'clearance_date',
        'clearance_id', 'validation_results', 'rejection_reason', 'environment',
        'is_reported', 'is_cleared'
    ]
)

EINVOICE_REPO = EINVOICE_RECORD_REPO

FISCAL_PROFILE_REPO = CrudRepository(
    't0125',
    business_columns=[
        'id', 'profile_name', 'authority_code', 'seller_name', 'seller_name_ar',
        'tax_id', 'commercial_registration_number', 'building_number', 'street_name',
        'street_name_ar', 'district', 'district_ar', 'city', 'city_ar', 'postal_code',
        'country_code', 'environment', 'api_base_url', 'api_key', 'api_secret',
        'auth_token', 'token_expires_at', 'csid', 'csid_secret', 'private_key',
        'public_key', 'certificate', 'is_active'
    ]
)
