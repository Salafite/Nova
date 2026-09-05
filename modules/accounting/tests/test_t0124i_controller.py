import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.auth.deps import get_current_user
from modules.accounting.controllers.T0124I import (
    router as t0124_router,
    service as t0124_service,
    einvoice_service as t0124_einvoice_svc,
    fiscal_pdf_service as t0124_pdf_svc,
)
from modules.accounting.controllers.T0125I import (
    router as t0125_router,
    service as t0125_service,
    einvoice_service as t0125_einvoice_svc,
)
from modules.accounting.models.einvoice import (
    QRCodeResponse,
    ClearanceSubmissionResponse,
    EInvoiceResponse,
    FiscalProfileResponse,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "admin",
        "role": "Admin",
        "business_id": 1,
        "permissions": ["*"],
    }
    app.include_router(t0124_router)
    app.include_router(t0125_router)
    return TestClient(app)


@pytest.fixture
def mock_einvoice_record():
    return {
        "id": 10,
        "invoice_id": 101,
        "fiscal_profile_id": 1,
        "invoice_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "invoice_type": "Standard",
        "invoice_type_code": "388",
        "subtype": "0100000",
        "icv": 5,
        "pih": "NWZlY2ViNjZmZmM4NmY1...",
        "invoice_hash": "a" * 44,
        "digital_signature": "MEQCIFyZ...",
        "public_key": "MFkwEwYHKoZIzj0CAQY...",
        "certificate": "-----BEGIN CERTIFICATE-----...",
        "qr_code_tlv": "AQZOYW1l...",
        "ubl_xml": "<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'><ID>INV-101</ID></Invoice>",
        "clearance_status": "Cleared",
        "clearance_date": "2026-09-05T08:00:00Z",
        "clearance_id": "IRN-998877",
        "validation_results": {"status": "PASS", "info": []},
        "environment": "Sandbox",
        "is_reported": False,
        "is_cleared": True,
    }


# ===========================================================================
# CRUD Endpoints (T0124I)
# ===========================================================================

def test_list_einvoices(client, mock_einvoice_record):
    """Test GET /api/T0124I/ lists clearance records."""
    with patch.object(t0124_service, "list", return_value=[mock_einvoice_record]):
        resp = client.get("/api/T0124I/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["invoice_id"] == 101
        assert data[0]["clearance_status"] == "Cleared"


def test_get_einvoice_by_id(client, mock_einvoice_record):
    """Test GET /api/T0124I/{id} returns specific clearance record."""
    with patch.object(t0124_service, "get", return_value=mock_einvoice_record):
        resp = client.get("/api/T0124I/10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 10
        assert data["invoice_id"] == 101


def test_get_einvoice_by_id_not_found(client):
    """Test GET /api/T0124I/{id} for non-existent record returns 404."""
    with patch.object(t0124_service, "get", return_value=None):
        resp = client.get("/api/T0124I/999")
        assert resp.status_code == 404


def test_create_einvoice_record(client, mock_einvoice_record):
    """Test POST /api/T0124I/ creates a new e-invoice record."""
    create_payload = {
        "invoice_id": 101,
        "fiscal_profile_id": 1,
        "invoice_type_code": "388",
        "subtype": "0100000",
        "icv": 5,
        "clearance_status": "Draft",
    }
    with patch.object(t0124_service, "create", return_value=mock_einvoice_record):
        resp = client.post("/api/T0124I/", json=create_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["invoice_id"] == 101


def test_update_einvoice_record(client, mock_einvoice_record):
    """Test PUT /api/T0124I/{id} updates record."""
    updated = dict(mock_einvoice_record)
    updated["clearance_status"] = "Reported"
    with patch.object(t0124_service, "update", return_value=updated):
        resp = client.put("/api/T0124I/10", json={"clearance_status": "Reported"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["clearance_status"] == "Reported"


def test_delete_einvoice_record(client):
    """Test DELETE /api/T0124I/{id} deletes record."""
    with patch.object(t0124_service, "delete", return_value=True):
        resp = client.delete("/api/T0124I/10")
        assert resp.status_code in (200, 204)


# ===========================================================================
# Custom Clearance & Operation Endpoints (T0124I)
# ===========================================================================

def test_get_einvoice_by_invoice_id(client, mock_einvoice_record):
    """Test GET /api/T0124I/by-invoice/{invoice_id} returns record."""
    with patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=mock_einvoice_record):
        resp = client.get("/api/T0124I/by-invoice/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_id"] == 101
        assert data["invoice_uuid"] == "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_get_einvoice_by_invoice_id_not_found(client):
    """Test GET /api/T0124I/by-invoice/{invoice_id} not found returns 404."""
    with patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=None):
        resp = client.get("/api/T0124I/by-invoice/999")
        assert resp.status_code == 404
        assert "No e-invoice clearance record found" in resp.json()["detail"]


def test_get_invoice_qr_code(client):
    """Test GET /api/T0124I/qr-code/{invoice_id} returns QRCodeResponse."""
    qr_mock = QRCodeResponse(
        invoice_id=101,
        qr_code_tlv="AQZOYW1l...",
        qr_image_data_uri="data:image/png;base64,iVBORw0KGgoAAA...",
        seller_name="Nova Global Trading LLC",
        tax_id="300012345600003",
        timestamp="2026-09-05T08:00:00Z",
        total_amount=1150.0,
        vat_total=150.0,
    )
    with patch.object(t0124_einvoice_svc, "generate_qr_code", return_value=qr_mock):
        resp = client.get("/api/T0124I/qr-code/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_id"] == 101
        assert data["qr_code_tlv"] == "AQZOYW1l..."
        assert data["seller_name"] == "Nova Global Trading LLC"


def test_get_invoice_qr_code_value_error(client):
    """Test GET /api/T0124I/qr-code/{invoice_id} returns 404 when invoice doesn't exist."""
    with patch.object(t0124_einvoice_svc, "generate_qr_code", side_effect=ValueError("Invoice #999 not found")):
        resp = client.get("/api/T0124I/qr-code/999")
        assert resp.status_code == 404
        assert "Invoice #999 not found" in resp.json()["detail"]


def test_get_invoice_qr_code_exception(client):
    """Test GET /api/T0124I/qr-code/{invoice_id} returns 500 on unexpected exception."""
    with patch.object(t0124_einvoice_svc, "generate_qr_code", side_effect=RuntimeError("QR Gen Error")):
        resp = client.get("/api/T0124I/qr-code/101")
        assert resp.status_code == 500
        assert "Failed to generate QR code" in resp.json()["detail"]


def test_generate_invoice_ubl_xml(client, mock_einvoice_record):
    """Test POST /api/T0124I/generate-xml/{invoice_id} returns generated XML structure."""
    with patch.object(t0124_einvoice_svc, "generate_ubl_xml", return_value="<Invoice>XML Payload</Invoice>"), \
         patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=mock_einvoice_record):
        resp = client.post("/api/T0124I/generate-xml/101?subtype=0100000&profile_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_id"] == 101
        assert data["ubl_xml"] == "<Invoice>XML Payload</Invoice>"
        assert data["invoice_uuid"] == "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_generate_invoice_ubl_xml_not_found(client):
    """Test POST /api/T0124I/generate-xml/{invoice_id} handles 404."""
    with patch.object(t0124_einvoice_svc, "generate_ubl_xml", side_effect=ValueError("Invoice not found")):
        resp = client.post("/api/T0124I/generate-xml/999")
        assert resp.status_code == 404


def test_sign_invoice_cryptographically(client, mock_einvoice_record):
    """Test POST /api/T0124I/sign/{invoice_id} signs and returns EInvoiceResponse."""
    with patch.object(t0124_einvoice_svc, "sign_einvoice", return_value=mock_einvoice_record):
        resp = client.post("/api/T0124I/sign/101?profile_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_id"] == 101
        assert data["digital_signature"] == "MEQCIFyZ..."


def test_sign_invoice_not_found(client):
    """Test POST /api/T0124I/sign/{invoice_id} returns 404 when invoice missing."""
    with patch.object(t0124_einvoice_svc, "sign_einvoice", side_effect=ValueError("Invoice missing")):
        resp = client.post("/api/T0124I/sign/999")
        assert resp.status_code == 404


def test_submit_invoice_clearance(client):
    """Test POST /api/T0124I/submit-clearance with payload body."""
    submission_resp = ClearanceSubmissionResponse(
        success=True,
        invoice_id=101,
        invoice_uuid="uuid-101",
        clearance_status="Cleared",
        clearance_id="IRN-101-CLEARED",
        qr_code_tlv="AQZOYW1l...",
        invoice_hash="hash-101",
        validation_results={"status": "PASS"},
    )
    with patch.object(t0124_einvoice_svc, "submit_clearance", return_value=submission_resp):
        payload = {
            "invoice_id": 101,
            "invoice_type": "Standard",
            "fiscal_profile_id": 1,
            "environment": "Sandbox",
            "auto_sign": True,
        }
        resp = client.post("/api/T0124I/submit-clearance", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["clearance_status"] == "Cleared"
        assert data["clearance_id"] == "IRN-101-CLEARED"


def test_submit_invoice_clearance_validation_error(client):
    """Test POST /api/T0124I/submit-clearance returns 400 on ValueError."""
    with patch.object(t0124_einvoice_svc, "submit_clearance", side_effect=ValueError("Invalid VAT Number")):
        resp = client.post("/api/T0124I/submit-clearance", json={"invoice_id": 101})
        assert resp.status_code == 400
        assert "Invalid VAT Number" in resp.json()["detail"]


def test_submit_clearance_by_id(client):
    """Test POST /api/T0124I/submit/{invoice_id} convenience endpoint."""
    submission_resp = ClearanceSubmissionResponse(
        success=True,
        invoice_id=101,
        invoice_uuid="uuid-101",
        clearance_status="Cleared",
        clearance_id="IRN-101-CLEARED",
        qr_code_tlv="AQZOYW1l...",
        invoice_hash="hash-101",
    )
    with patch.object(t0124_einvoice_svc, "submit_clearance", return_value=submission_resp):
        resp = client.post("/api/T0124I/submit/101?environment=Sandbox&auto_sign=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["clearance_status"] == "Cleared"


def test_download_invoice_ubl_xml_existing(client, mock_einvoice_record):
    """Test GET /api/T0124I/xml/{invoice_id} downloads existing UBL XML."""
    with patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=mock_einvoice_record):
        resp = client.get("/api/T0124I/xml/101")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        assert "einvoice_101.xml" in resp.headers["content-disposition"]
        assert "<Invoice" in resp.text


def test_download_invoice_ubl_xml_generated_on_the_fly(client):
    """Test GET /api/T0124I/xml/{invoice_id} generates XML on-the-fly when record lacks XML."""
    with patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=None), \
         patch.object(t0124_einvoice_svc, "generate_ubl_xml", return_value="<Invoice>On The Fly XML</Invoice>"):
        resp = client.get("/api/T0124I/xml/101")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        assert "<Invoice>On The Fly XML</Invoice>" in resp.text


def test_download_invoice_ubl_xml_not_found(client):
    """Test GET /api/T0124I/xml/{invoice_id} returns 404 if invoice doesn't exist."""
    with patch.object(t0124_einvoice_svc, "get_by_invoice_id", return_value=None), \
         patch.object(t0124_einvoice_svc, "generate_ubl_xml", side_effect=ValueError("Invoice not found")):
        resp = client.get("/api/T0124I/xml/999")
        assert resp.status_code == 404


def test_download_invoice_fiscal_pdf(client):
    """Test GET /api/T0124I/pdf/{invoice_id} returns PDF bytes."""
    dummy_pdf_bytes = b"%PDF-1.4 dummy fiscal pdf bytes"
    with patch.object(t0124_pdf_svc, "generate_fiscal_invoice_pdf", return_value=dummy_pdf_bytes):
        resp = client.get("/api/T0124I/pdf/101")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "fiscal_invoice_101.pdf" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF")


def test_download_invoice_fiscal_pdf_not_found(client):
    """Test GET /api/T0124I/pdf/{invoice_id} returns 404 when invoice not found."""
    with patch.object(t0124_pdf_svc, "generate_fiscal_invoice_pdf", side_effect=ValueError("Invoice #999 not found")):
        resp = client.get("/api/T0124I/pdf/999")
        assert resp.status_code == 404


# ===========================================================================
# Fiscal Authority Profiles Endpoints (T0125I)
# ===========================================================================

def test_get_current_active_profile(client):
    """Test GET /api/T0125I/active/current returns active fiscal profile."""
    profile_data = {
        "id": 1,
        "profile_name": "Active ZATCA Profile",
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
        "is_default": True,
    }
    with patch.object(t0125_einvoice_svc, "get_active_fiscal_profile", return_value=profile_data):
        resp = client.get("/api/T0125I/active/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile_name"] == "Active ZATCA Profile"
        assert data["tax_id"] == "300012345600003"


def test_get_current_active_profile_fallback(client):
    """Test GET /api/T0125I/active/current returns default fallback structure when no DB profile exists."""
    with patch.object(t0125_einvoice_svc, "get_active_fiscal_profile", return_value={}):
        resp = client.get("/api/T0125I/active/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 0
        assert data["authority_code"] == "ZATCA"
        assert data["tax_id"] == "300012345600003"


def test_generate_fiscal_keypair(client):
    """Test POST /api/T0125I/generate-keypair generates valid ECDSA keys."""
    resp = client.post("/api/T0125I/generate-keypair")
    assert resp.status_code == 200
    data = resp.json()
    assert "private_key" in data
    assert "-----BEGIN EC PRIVATE KEY-----" in data["private_key"]
    assert "public_key" in data
    assert "-----BEGIN PUBLIC KEY-----" in data["public_key"]
    assert data["algorithm"] == "ECDSA_secp256k1"
