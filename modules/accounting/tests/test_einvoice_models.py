"""Unit tests for E-Invoice and Fiscal Authority Pydantic domain models."""
from datetime import datetime
import pytest
from pydantic import ValidationError

from modules.accounting.models.einvoice import (
    FiscalProfileCreate,
    FiscalProfileUpdate,
    FiscalProfileResponse,
    EInvoiceCreate,
    EInvoiceUpdate,
    EInvoiceResponse,
    ClearanceSubmissionRequest,
    ClearanceSubmissionResponse,
    QRCodeResponse,
    FISCAL_PROFILE_REPO,
    EINVOICE_REPO,
    EINVOICE_RECORD_REPO,
)
from modules.accounting.models import (
    FiscalProfileCreate as ImportedFiscalProfileCreate,
    EInvoiceCreate as ImportedEInvoiceCreate,
    ClearanceSubmissionRequest as ImportedClearanceSubmissionRequest,
    QRCodeResponse as ImportedQRCodeResponse,
    FISCAL_PROFILE_REPO as ImportedFiscalRepo,
    EINVOICE_REPO as ImportedEInvoiceRepo,
)


def test_models_exported_in_package():
    """Verify all domain models are properly exported from modules.accounting.models."""
    assert ImportedFiscalProfileCreate is FiscalProfileCreate
    assert ImportedEInvoiceCreate is EInvoiceCreate
    assert ImportedClearanceSubmissionRequest is ClearanceSubmissionRequest
    assert ImportedQRCodeResponse is QRCodeResponse
    assert ImportedFiscalRepo is FISCAL_PROFILE_REPO
    assert ImportedEInvoiceRepo is EINVOICE_REPO
    assert EINVOICE_RECORD_REPO is EINVOICE_REPO


def test_fiscal_profile_create_defaults_and_validation():
    """Verify FiscalProfileCreate required fields, default values, and validations."""
    profile_data = {
        "profile_name": "Riyadh Main Branch",
        "seller_name": "Nova Distribution Corp",
        "tax_id": "310123456700003",
    }
    model = FiscalProfileCreate(**profile_data)
    assert model.profile_name == "Riyadh Main Branch"
    assert model.authority_code == "ZATCA"
    assert model.seller_name == "Nova Distribution Corp"
    assert model.seller_name_ar is None
    assert model.country_code == "SA"
    assert model.environment == "Sandbox"
    assert model.is_active is True
    assert model.business_id is None

    # Missing required field
    with pytest.raises(ValidationError):
        FiscalProfileCreate(profile_name="Test")


def test_fiscal_profile_update():
    """Verify FiscalProfileUpdate allows partial field modifications."""
    update_model = FiscalProfileUpdate(
        environment="Production",
        api_base_url="https://gw.fatoora.zatca.gov.sa/e-invoicing/simulation",
        is_active=False,
    )
    assert update_model.environment == "Production"
    assert update_model.api_base_url == "https://gw.fatoora.zatca.gov.sa/e-invoicing/simulation"
    assert update_model.is_active is False
    assert update_model.seller_name is None


def test_fiscal_profile_response():
    """Verify FiscalProfileResponse includes audit fields and business_id."""
    resp_data = {
        "id": 1,
        "profile_name": "HQ Profile",
        "authority_code": "ZATCA",
        "seller_name": "Nova Corp",
        "tax_id": "310123456700003",
        "country_code": "SA",
        "environment": "Sandbox",
        "business_id": 42,
        "created_at": datetime(2026, 1, 1, 10, 0, 0),
        "created_by": 1,
        "update_number": 1,
    }
    resp = FiscalProfileResponse(**resp_data)
    assert resp.id == 1
    assert resp.business_id == 42
    assert resp.created_at == datetime(2026, 1, 1, 10, 0, 0)
    assert resp.is_active is True


def test_einvoice_create_defaults_and_validation():
    """Verify EInvoiceCreate defaults and validation."""
    einvoice_data = {
        "invoice_id": 105,
        "invoice_hash": "NWNmMDhmZTE0YTQyMWYyNDM1NWFiMTI4ODQ3NzA2OGY=",
    }
    einvoice = EInvoiceCreate(**einvoice_data)
    assert einvoice.invoice_id == 105
    assert einvoice.invoice_type_code == "388"
    assert einvoice.subtype == "0100000"
    assert einvoice.icv == 1
    assert einvoice.clearance_status == "Pending"
    assert einvoice.environment == "Sandbox"
    assert einvoice.is_reported is False
    assert einvoice.is_cleared is False

    # ICV must be positive
    with pytest.raises(ValidationError):
        EInvoiceCreate(
            invoice_id=1,
            invoice_hash="xyz",
            icv=0,
        )


def test_einvoice_update():
    """Verify EInvoiceUpdate partial updates."""
    update = EInvoiceUpdate(
        clearance_status="Cleared",
        clearance_id="IRN-2026-0001",
        is_cleared=True,
    )
    assert update.clearance_status == "Cleared"
    assert update.clearance_id == "IRN-2026-0001"
    assert update.is_cleared is True
    assert update.invoice_hash is None


def test_einvoice_response():
    """Verify EInvoiceResponse serialization and AuditMixin properties."""
    resp_data = {
        "id": 10,
        "invoice_id": 105,
        "invoice_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "invoice_type_code": "388",
        "subtype": "0100000",
        "icv": 5,
        "invoice_hash": "aGFzaC1leGFtcGxlLXNoYTI1Ng==",
        "clearance_status": "Cleared",
        "clearance_id": "CLR-9999",
        "environment": "Simulation",
        "is_cleared": True,
        "business_id": 10,
        "created_at": datetime(2026, 9, 1, 12, 0, 0),
        "validation_results": {"warnings": [], "info": ["Schema passed"]},
    }
    resp = EInvoiceResponse(**resp_data)
    assert resp.id == 10
    assert resp.invoice_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert resp.validation_results["info"] == ["Schema passed"]
    assert resp.business_id == 10


def test_clearance_submission_request_and_response():
    """Verify ClearanceSubmissionRequest and ClearanceSubmissionResponse."""
    req = ClearanceSubmissionRequest(invoice_id=500, auto_sign=True)
    assert req.invoice_id == 500
    assert req.auto_sign is True
    assert req.environment is None

    res = ClearanceSubmissionResponse(
        success=True,
        invoice_id=500,
        invoice_uuid="550e8400-e29b-41d4-a716-446655440000",
        clearance_status="Cleared",
        clearance_id="AUTH-CLEARANCE-12345",
        qr_code_tlv="AQxOb3ZhIENvcnBvcmF0aW9uAg8zMTAxMjM0NTY3MDAwMDM=",
        invoice_hash="aGFzaC1leGFtcGxl",
    )
    assert res.success is True
    assert res.clearance_status == "Cleared"
    assert res.clearance_id == "AUTH-CLEARANCE-12345"
    assert res.submitted_at is not None


def test_qrcode_response():
    """Verify QRCodeResponse data structure."""
    qr = QRCodeResponse(
        invoice_id=200,
        qr_code_tlv="AQxOb3ZhIENvcnBvcmF0aW9uAg8zMTAxMjM0NTY3MDAwMDM=",
        qr_image_data_uri="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
        seller_name="Nova Distribution Corp",
        tax_id="310123456700003",
        timestamp="2026-09-05T08:00:00Z",
        total_amount=1150.00,
        vat_total=150.00,
        invoice_hash="aGFzaDEyMw==",
    )
    assert qr.invoice_id == 200
    assert qr.total_amount == 1150.00
    assert qr.vat_total == 150.00
    assert qr.qr_image_data_uri.startswith("data:image/png;base64,")


def test_repository_configurations():
    """Verify table names and business columns in repository definitions."""
    assert EINVOICE_RECORD_REPO.table_name == "t0124"
    assert "invoice_uuid" in EINVOICE_RECORD_REPO.business_columns
    assert "qr_code_tlv" in EINVOICE_RECORD_REPO.business_columns
    assert "clearance_status" in EINVOICE_RECORD_REPO.business_columns

    assert FISCAL_PROFILE_REPO.table_name == "t0125"
    assert "authority_code" in FISCAL_PROFILE_REPO.business_columns
    assert "tax_id" in FISCAL_PROFILE_REPO.business_columns
    assert "csid" in FISCAL_PROFILE_REPO.business_columns
