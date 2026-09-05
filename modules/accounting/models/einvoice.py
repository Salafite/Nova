from typing import Optional, Any, Dict, List, Union
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin
from modules.core.repositories.base import CrudRepository


# ---------------------------------------------------------------------------
# Fiscal Authority Profile Models (T0125)
# ---------------------------------------------------------------------------

class FiscalProfileCreate(BaseModel):
    """Payload for creating a fiscal authority configuration profile."""
    profile_name: str = Field(..., max_length=100, description="Descriptive profile name, e.g. 'Main Branch ZATCA'")
    authority_code: str = Field('ZATCA', max_length=50, description="Tax authority: ZATCA | PEPPOL | NTS | GENERIC")
    seller_name: str = Field(..., max_length=255, description="Official legal seller name in English/Latin")
    seller_name_ar: Optional[str] = Field(None, max_length=255, description="Official legal seller name in Arabic")
    tax_id: str = Field(..., max_length=50, description="Tax Registration / VAT Identification Number")
    commercial_registration_number: Optional[str] = Field(None, max_length=50, description="Commercial Registration (CR) number")
    building_number: Optional[str] = Field(None, max_length=20, description="Building / postal unit number")
    street_name: Optional[str] = Field(None, max_length=255, description="Street name in English")
    street_name_ar: Optional[str] = Field(None, max_length=255, description="Street name in Arabic")
    district: Optional[str] = Field(None, max_length=100, description="District / neighborhood in English")
    district_ar: Optional[str] = Field(None, max_length=100, description="District / neighborhood in Arabic")
    city: Optional[str] = Field(None, max_length=100, description="City in English")
    city_ar: Optional[str] = Field(None, max_length=100, description="City in Arabic")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal / ZIP code")
    country_code: str = Field('SA', max_length=10, description="ISO-3166 2-letter country code")
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
    is_active: bool = Field(True, description="Whether this fiscal profile is active")
    business_id: Optional[int] = Field(None, description="Multi-tenant business organization ID")


class FiscalProfileUpdate(BaseModel):
    """Payload for updating an existing fiscal authority profile."""
    profile_name: Optional[str] = Field(None, max_length=100)
    authority_code: Optional[str] = Field(None, max_length=50)
    seller_name: Optional[str] = Field(None, max_length=255)
    seller_name_ar: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=50)
    commercial_registration_number: Optional[str] = Field(None, max_length=50)
    building_number: Optional[str] = Field(None, max_length=20)
    street_name: Optional[str] = Field(None, max_length=255)
    street_name_ar: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    district_ar: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    city_ar: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, max_length=10)
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
    is_active: Optional[bool] = None


class FiscalProfileResponse(AuditMixin):
    """Response representation of a fiscal authority profile."""
    id: int
    profile_name: str
    authority_code: str
    seller_name: str
    seller_name_ar: Optional[str] = None
    tax_id: str
    commercial_registration_number: Optional[str] = None
    building_number: Optional[str] = None
    street_name: Optional[str] = None
    street_name_ar: Optional[str] = None
    district: Optional[str] = None
    district_ar: Optional[str] = None
    city: Optional[str] = None
    city_ar: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: str
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
    is_active: bool = True


# ---------------------------------------------------------------------------
# E-Invoice Clearance & Cryptographic Record Models (T0124)
# ---------------------------------------------------------------------------

class EInvoiceCreate(BaseModel):
    """Payload for creating an e-invoice cryptographic/clearance record."""
    invoice_id: int = Field(..., description="Foreign key to sales invoice (t0090)")
    fiscal_profile_id: Optional[int] = Field(None, description="Foreign key to fiscal profile (t0125)")
    invoice_uuid: Optional[str] = Field(None, max_length=100, description="Standard UUID v4 for the e-invoice")
    invoice_type_code: str = Field('388', max_length=50, description="UN/ECE 1001 invoice code (388=Tax Invoice, 381=Credit, 383=Debit)")
    subtype: str = Field('0100000', max_length=50, description="Invoice subtype (0100000=Standard B2B, 0200000=Simplified B2C)")
    icv: int = Field(1, ge=1, description="Sequential Invoice Counter Value")
    pih: Optional[str] = Field(None, max_length=255, description="Previous Invoice Hash (Base64 SHA-256)")
    invoice_hash: str = Field(..., max_length=255, description="Canonical invoice SHA-256 hash")
    digital_signature: Optional[str] = Field(None, description="Cryptographic digital signature string")
    public_key: Optional[str] = Field(None, description="Public key used for verification")
    certificate: Optional[str] = Field(None, description="X.509 certificate string")
    qr_code_tlv: Optional[str] = Field(None, description="Base64 TLV encoded QR code payload")
    ubl_xml: Optional[str] = Field(None, description="Full UBL 2.1 XML document content")
    clearance_status: str = Field('Pending', max_length=30, description="Clearance status: Pending | Cleared | Reported | Rejected | Failed | Not_Submitted")
    clearance_date: Optional[datetime] = Field(None, description="Timestamp of clearance confirmation")
    clearance_id: Optional[str] = Field(None, max_length=100, description="Tax authority clearance ID or IRN")
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Structured validation response from authority")
    rejection_reason: Optional[str] = Field(None, description="Rejection or error detail from fiscal authority")
    environment: str = Field('Sandbox', max_length=30, description="Submission environment: Sandbox | Simulation | Production")
    is_reported: bool = Field(False, description="Whether the simplified invoice has been reported")
    is_cleared: bool = Field(False, description="Whether the standard invoice has been cleared")
    business_id: Optional[int] = Field(None, description="Multi-tenant business organization ID")


class EInvoiceUpdate(BaseModel):
    """Payload for updating an e-invoice record status, signatures, or clearance response."""
    fiscal_profile_id: Optional[int] = None
    invoice_type_code: Optional[str] = Field(None, max_length=50)
    subtype: Optional[str] = Field(None, max_length=50)
    icv: Optional[int] = Field(None, ge=1)
    pih: Optional[str] = Field(None, max_length=255)
    invoice_hash: Optional[str] = Field(None, max_length=255)
    digital_signature: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    qr_code_tlv: Optional[str] = None
    ubl_xml: Optional[str] = None
    clearance_status: Optional[str] = Field(None, max_length=30)
    clearance_date: Optional[datetime] = None
    clearance_id: Optional[str] = Field(None, max_length=100)
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    rejection_reason: Optional[str] = None
    environment: Optional[str] = Field(None, max_length=30)
    is_reported: Optional[bool] = None
    is_cleared: Optional[bool] = None


class EInvoiceResponse(AuditMixin):
    """Response representation of an e-invoice cryptographic/clearance record."""
    id: int
    invoice_id: int
    fiscal_profile_id: Optional[int] = None
    invoice_uuid: str
    invoice_type_code: str
    subtype: str
    icv: int
    pih: Optional[str] = None
    invoice_hash: str
    digital_signature: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None
    qr_code_tlv: Optional[str] = None
    ubl_xml: Optional[str] = None
    clearance_status: str
    clearance_date: Optional[datetime] = None
    clearance_id: Optional[str] = None
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    rejection_reason: Optional[str] = None
    environment: str
    is_reported: bool = False
    is_cleared: bool = False


# ---------------------------------------------------------------------------
# Clearance API Submission & QR Operation Models
# ---------------------------------------------------------------------------

class ClearanceSubmissionRequest(BaseModel):
    """Request payload to submit an invoice for fiscal clearance or reporting."""
    invoice_id: int = Field(..., description="Sales invoice ID to clear/report")
    fiscal_profile_id: Optional[int] = Field(None, description="Optional profile ID override (defaults to active profile)")
    environment: Optional[str] = Field(None, max_length=30, description="Override environment (Sandbox | Simulation | Production)")
    auto_sign: bool = Field(True, description="Automatically compute hash and sign if not already signed")


class ClearanceSubmissionResponse(BaseModel):
    """Response payload returned after tax authority clearance/reporting submission."""
    success: bool = Field(..., description="Whether the submission succeeded or cleared")
    invoice_id: int
    invoice_uuid: str
    clearance_status: str = Field(..., description="Cleared | Reported | Rejected | Failed")
    clearance_id: Optional[str] = Field(None, description="Clearance ID or IRN returned by the tax authority")
    qr_code_tlv: Optional[str] = Field(None, description="Base64 TLV QR code string")
    invoice_hash: Optional[str] = Field(None, description="SHA-256 canonical invoice hash")
    validation_results: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Validation messages or warnings from tax authority")
    error_message: Optional[str] = Field(None, description="Primary error message if submission failed")
    submitted_at: Optional[datetime] = Field(default_factory=datetime.now)


class QRCodeResponse(BaseModel):
    """Response containing Base64 TLV data and metadata for rendering QR codes."""
    invoice_id: int
    qr_code_tlv: str = Field(..., description="Base64-encoded TLV QR data")
    qr_image_data_uri: Optional[str] = Field(None, description="Data URI (data:image/png;base64,...) for instant frontend rendering")
    seller_name: str
    tax_id: str
    timestamp: str
    total_amount: float
    vat_total: float
    invoice_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# CrudRepositories for T0124 and T0125
# ---------------------------------------------------------------------------

EINVOICE_RECORD_REPO = CrudRepository(
    'T0124',
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
    'T0125',
    business_columns=[
        'id', 'profile_name', 'authority_code', 'seller_name', 'seller_name_ar',
        'tax_id', 'commercial_registration_number', 'building_number', 'street_name',
        'street_name_ar', 'district', 'district_ar', 'city', 'city_ar', 'postal_code',
        'country_code', 'environment', 'api_base_url', 'api_key', 'api_secret',
        'auth_token', 'token_expires_at', 'csid', 'csid_secret', 'private_key',
        'public_key', 'certificate', 'is_active'
    ]
)
