from datetime import datetime
import json
import pytest
from unittest.mock import patch, MagicMock
import httpx

from modules.accounting.models.einvoice import (
    ClearanceSubmissionResponse,
    FiscalProfileResponse,
)
from modules.accounting.services.fiscal_authority_service import FiscalAuthorityService
from modules.accounting.services.ubl_builder_service import UBLBuilderService
from modules.accounting.services.einvoice_crypto_service import EInvoiceCryptoService
from modules.accounting.services.tlv_qr_service import generate_zatca_qr_tlv


@pytest.fixture
def sample_fiscal_profile():
    return FiscalProfileResponse(
        id=1,
        profile_name="HQ ZATCA Profile",
        authority_code="ZATCA",
        seller_name="Nova Global Trading LLC",
        seller_name_ar="شركة نوفا للتجارة العامة",
        tax_id="300012345600003",
        commercial_registration_number="1010123456",
        building_number="1234",
        street_name="King Fahd Road",
        city="Riyadh",
        district="Al Olaya",
        postal_code="12211",
        country_code="SA",
        environment="Sandbox",
        api_base_url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal",
        csid="BINARY_CSID_TOKEN_EXAMPLE_123==",
        csid_secret="CSID_SECRET_456",
        is_active=True,
    )


@pytest.fixture
def sample_invoice_payload():
    invoice_id = 9001
    invoice_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ubl_xml = UBLBuilderService.build_invoice_xml(
        invoice_id="INV-2026-001",
        invoice_uuid=invoice_uuid,
        issue_date="2026-09-05",
        issue_time="08:00:00",
        invoice_type_code="388",
        subtype="0100000",
        currency_code="SAR",
        seller={"name": "Nova Global Trading", "tax_id": "300012345600003"},
        buyer={"name": "Acme Retailers", "tax_id": "300098765400003"},
        line_items=[{"name": "Wholesale Coffee Beans", "quantity": 10, "unit_price": 50.0, "tax_rate": 15.0}],
    )
    invoice_hash = EInvoiceCryptoService.compute_sha256_hash(ubl_xml)
    qr_code_tlv = generate_zatca_qr_tlv(
        seller_name="Nova Global Trading",
        vat_number="300012345600003",
        timestamp="2026-09-05T08:00:00Z",
        total_amount=575.0,
        vat_total=75.0,
        invoice_hash=invoice_hash,
    )
    return {
        "invoice_id": invoice_id,
        "invoice_uuid": invoice_uuid,
        "invoice_hash": invoice_hash,
        "ubl_xml": ubl_xml,
        "qr_code_tlv": qr_code_tlv,
    }


def test_fiscal_authority_service_initialization_from_profile(sample_fiscal_profile):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)
    assert service.environment == "Sandbox"
    assert service.csid == "BINARY_CSID_TOKEN_EXAMPLE_123=="
    assert service.csid_secret == "CSID_SECRET_456"
    assert "https://gw-fatoora.zatca.gov.sa" in service.base_url

    headers = service._get_auth_headers()
    assert headers["Accept-Version"] == "V2"
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")


def test_fiscal_authority_service_simulation_headers(sample_fiscal_profile):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile, environment_override="Simulation")
    assert service.environment == "Simulation"
    headers = service._get_auth_headers()
    assert headers.get("Clearance-Status") == "1"


def test_clearance_submission_success(sample_fiscal_profile, sample_invoice_payload):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)

    mock_response_data = {
        "clearanceStatus": "CLEARED",
        "clearanceId": "CLR-SA-2026-9988",
        "clearedInvoice": "MOCK_CLEARED_XML",
        "validationResults": {
            "infoMessages": [{"code": "INFO-01", "message": "Cleared with standard scheme"}],
            "warningMessages": [],
            "errorMessages": [],
            "status": "PASS",
        },
    }

    with patch.object(service, "_execute_request_with_retry") as mock_exec:
        mock_exec.return_value = {
            "status_code": 200,
            "success": True,
            "data": mock_response_data,
        }

        res = service.submit_clearance(
            invoice_id=sample_invoice_payload["invoice_id"],
            invoice_uuid=sample_invoice_payload["invoice_uuid"],
            invoice_hash=sample_invoice_payload["invoice_hash"],
            signed_ubl_xml=sample_invoice_payload["ubl_xml"],
            qr_code_tlv=sample_invoice_payload["qr_code_tlv"],
        )

        assert isinstance(res, ClearanceSubmissionResponse)
        assert res.success is True
        assert res.clearance_status == "Cleared"
        assert res.clearance_id == "CLR-SA-2026-9988"
        assert res.invoice_uuid == sample_invoice_payload["invoice_uuid"]
        assert res.error_message is None


def test_clearance_submission_rejection(sample_fiscal_profile, sample_invoice_payload):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)

    mock_response_data = {
        "clearanceStatus": "REJECTED",
        "validationResults": {
            "errorMessages": [
                {"code": "ERR-VAT-01", "message": "Customer VAT Number format invalid"}
            ],
            "status": "FAIL",
        },
    }

    with patch.object(service, "_execute_request_with_retry") as mock_exec:
        mock_exec.return_value = {
            "status_code": 400,
            "success": False,
            "data": mock_response_data,
        }

        res = service.submit_clearance(
            invoice_id=sample_invoice_payload["invoice_id"],
            invoice_uuid=sample_invoice_payload["invoice_uuid"],
            invoice_hash=sample_invoice_payload["invoice_hash"],
            signed_ubl_xml=sample_invoice_payload["ubl_xml"],
        )

        assert res.success is False
        assert res.clearance_status == "Rejected"
        assert "ERR-VAT-01" in res.error_message
        assert "Customer VAT Number format invalid" in res.error_message


def test_reporting_submission_success(sample_fiscal_profile, sample_invoice_payload):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)

    mock_response_data = {
        "reportingStatus": "REPORTED",
        "reportingId": "REP-SA-2026-5544",
        "validationResults": {
            "infoMessages": [],
            "warningMessages": [],
            "errorMessages": [],
            "status": "PASS",
        },
    }

    with patch.object(service, "_execute_request_with_retry") as mock_exec:
        mock_exec.return_value = {
            "status_code": 200,
            "success": True,
            "data": mock_response_data,
        }

        res = service.submit_reporting(
            invoice_id=sample_invoice_payload["invoice_id"],
            invoice_uuid=sample_invoice_payload["invoice_uuid"],
            invoice_hash=sample_invoice_payload["invoice_hash"],
            signed_ubl_xml=sample_invoice_payload["ubl_xml"],
        )

        assert res.success is True
        assert res.clearance_status == "Reported"
        assert res.clearance_id == "REP-SA-2026-5544"


def test_compliance_check(sample_fiscal_profile, sample_invoice_payload):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)

    mock_response_data = {
        "validationResults": {
            "status": "PASS",
            "infoMessages": [{"code": "CMP-01", "message": "Compliance Verified"}],
        },
    }

    with patch.object(service, "_execute_request_with_retry") as mock_exec:
        mock_exec.return_value = {
            "status_code": 200,
            "success": True,
            "data": mock_response_data,
        }

        res = service.check_compliance(
            invoice_id=sample_invoice_payload["invoice_id"],
            invoice_uuid=sample_invoice_payload["invoice_uuid"],
            invoice_hash=sample_invoice_payload["invoice_hash"],
            signed_ubl_xml=sample_invoice_payload["ubl_xml"],
        )

        assert res.success is True
        assert res.clearance_status == "Cleared"


def test_csid_onboarding_methods(sample_fiscal_profile):
    service = FiscalAuthorityService.from_profile(sample_fiscal_profile)

    with patch.object(service, "_execute_request_with_retry") as mock_exec:
        mock_exec.return_value = {
            "status_code": 200,
            "data": {
                "binarySecurityToken": "NEW_CSID_TOKEN==",
                "secret": "NEW_SECRET_123",
                "requestID": "REQ-12345",
            },
        }

        csid_res = service.request_compliance_csid("CSR_BASE64_DATA", "123456")
        assert csid_res["binarySecurityToken"] == "NEW_CSID_TOKEN=="
        assert csid_res["secret"] == "NEW_SECRET_123"

        mock_exec.return_value = {
            "status_code": 200,
            "data": {
                "binarySecurityToken": "PROD_CSID_TOKEN==",
                "secret": "PROD_SECRET_789",
            },
        }

        prod_res = service.request_production_csid("REQ-12345")
        assert prod_res["binarySecurityToken"] == "PROD_CSID_TOKEN=="


def test_sandbox_mock_fallback_mode(sample_invoice_payload):
    # Service with mock_mode enabled
    service = FiscalAuthorityService(environment="Sandbox", mock_mode=True)
    res = service.submit_clearance(
        invoice_id=sample_invoice_payload["invoice_id"],
        invoice_uuid=sample_invoice_payload["invoice_uuid"],
        invoice_hash=sample_invoice_payload["invoice_hash"],
        signed_ubl_xml=sample_invoice_payload["ubl_xml"],
    )
    assert res.success is True
    assert res.clearance_status == "Cleared"
    assert res.clearance_id.startswith("CLR-SA-")
