"""
Unit tests for E-Invoice and Fiscal Profile Pydantic models.
"""

import pytest
from datetime import datetime
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
    EINVOICE_RECORD_REPO,
    EINVOICE_REPO,
    FISCAL_PROFILE_REPO,
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


def test_fiscal_profile_models():
    create_data = {
        "profile_name": "Main Store ZATCA",
        "authority_code": "ZATCA",
        "environment": "Sandbox",
        "seller_legal_name": "Nova Distribution Ltd",
        "seller_vat_number": "310122393500003",
        "seller_city": "Riyadh",
        "seller_country_code": "SA",
        "is_default": True,
    }
    profile_req = FiscalProfileCreate(**create_data)
    assert profile_req.profile_name == "Main Store ZATCA"
    assert profile_req.seller_vat_number == "310122393500003"
    assert profile_req.seller_name == "Nova Distribution Ltd"
    assert profile_req.tax_id == "310122393500003"
    assert profile_req.is_default is True

    update_req = FiscalProfileUpdate(environment="Production", auth_token="token123")
    assert update_req.environment == "Production"
    assert update_req.auth_token == "token123"

    resp_data = {
        "id": 1,
        "created_at": datetime.now(),
        "created_by": 10,
        "updated_at": datetime.now(),
        "updated_by": 10,
        "update_number": 1,
        "business_id": 1,
        **create_data,
    }
    profile_resp = FiscalProfileResponse(**resp_data)
    assert profile_resp.id == 1
    assert profile_resp.business_id == 1


def test_einvoice_models():
    einv_create = EInvoiceCreate(
        invoice_id=100,
        invoice_type="Standard",
        invoice_counter_number=1,
        qr_code_payload="AQ1Cb2JzIEZhc2hpb25zAg8zMTAxMjIzOTM1MDAwMDM=",
    )
    assert einv_create.invoice_id == 100
    assert einv_create.clearance_status == "Draft"
    assert einv_create.icv == 1
    assert einv_create.qr_code_tlv == "AQ1Cb2JzIEZhc2hpb25zAg8zMTAxMjIzOTM1MDAwMDM="

    einv_update = EInvoiceUpdate(
        clearance_status="Cleared",
        clearance_uuid="uuid-123-abc",
    )
    assert einv_update.clearance_status == "Cleared"
    assert einv_update.clearance_uuid == "uuid-123-abc"
    assert einv_update.clearance_id == "uuid-123-abc"


def test_clearance_and_qr_models():
    req = ClearanceSubmissionRequest(invoice_id=42, invoice_type="Standard")
    assert req.invoice_id == 42

    res = ClearanceSubmissionResponse(
        success=True,
        clearance_status="Cleared",
        clearance_uuid="IRN-2023-001",
        qr_code_payload="AQ1Cb2Jz...",
    )
    assert res.success is True
    assert res.clearance_status == "Cleared"
    assert res.clearance_id == "IRN-2023-001"
    assert res.qr_code_tlv == "AQ1Cb2Jz..."

    qr = QRCodeResponse(
        invoice_id=42,
        qr_code_payload="AQ1Cb2Jz...",
        seller_name="Nova Store",
        total_amount=115.0,
    )
    assert qr.invoice_id == 42
    assert qr.total_amount == 115.0
    assert qr.qr_code_tlv == "AQ1Cb2Jz..."


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
