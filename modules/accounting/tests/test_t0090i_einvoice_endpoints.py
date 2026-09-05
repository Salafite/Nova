import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.accounting.controllers.T0090I import router, service, fiscal_pdf_service
from modules.accounting.models.einvoice import (
    QRCodeResponse,
    ClearanceSubmissionResponse,
    EInvoiceResponse,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_invoice():
    return {
        "id": 101,
        "invoice_number": "INV-2026-001",
        "invoice_type": "Sales",
        "partner_id": 5,
        "sales_order_id": 12,
        "total_amount": 1150.0,
        "status": "Unpaid",
        "issue_date": "2026-09-05",
        "due_date": "2026-10-05",
    }


def test_get_invoice_qr_code(client, mock_invoice):
    """Test GET /api/T0090I/{id}/qr-code returns valid Base64 TLV QR response."""
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=None):
        response = client.get("/api/T0090I/101/qr-code")
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_id"] == 101
        assert "qr_code_tlv" in data
        assert len(data["qr_code_tlv"]) > 0
        assert data["total_amount"] == 1150.0
        assert data["vat_total"] == 150.0
        assert data["seller_name"] is not None


def test_get_invoice_qr_alias(client, mock_invoice):
    """Test GET /api/T0090I/{id}/qr short alias."""
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=None):
        response = client.get("/api/T0090I/101/qr")
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_id"] == 101
        assert data["qr_code_tlv"] is not None


def test_get_invoice_qr_not_found(client):
    """Test GET /api/T0090I/{id}/qr-code for non-existent invoice returns 404."""
    with patch.object(service.repo, "get", return_value=None):
        response = client.get("/api/T0090I/999/qr-code")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_submit_invoice_clearance(client, mock_invoice):
    """Test POST /api/T0090I/{id}/clearance returns clearance submission response."""
    mock_record = {
        "id": 1,
        "invoice_id": 101,
        "invoice_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "invoice_hash": "a" * 44,
        "digital_signature": "b" * 64,
        "qr_code_tlv": "AQ...",
        "ubl_xml": "<Invoice/>",
        "subtype": "0100000",
        "clearance_status": "Draft",
    }
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=mock_record), \
         patch.object(service.einvoice_service.repo, "update", return_value=None):
        response = client.post("/api/T0090I/101/clearance")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["clearance_status"] in ("Cleared", "Reported", "Pending")
        assert data["clearance_id"] is not None


def test_submit_invoice_clearance_not_found(client):
    """Test POST /api/T0090I/{id}/clearance for non-existent invoice returns 404."""
    with patch.object(service.repo, "get", return_value=None), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=None):
        response = client.post("/api/T0090I/999/clearance")
        assert response.status_code == 404


def test_download_invoice_fiscal_pdf(client, mock_invoice):
    """Test GET /api/T0090I/{id}/fiscal-pdf returns printable PDF bytes."""
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(fiscal_pdf_service.invoice_repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=None):
        response = client.get("/api/T0090I/101/fiscal-pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "fiscal_invoice_101.pdf" in response.headers.get("content-disposition", "")
        assert response.content.startswith(b"%PDF")


def test_download_invoice_pdf_alias(client, mock_invoice):
    """Test GET /api/T0090I/{id}/pdf short alias."""
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(fiscal_pdf_service.invoice_repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=None):
        response = client.get("/api/T0090I/101/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


def test_download_invoice_pdf_not_found(client):
    """Test GET /api/T0090I/{id}/fiscal-pdf for non-existent invoice returns 404."""
    with patch.object(service.repo, "get", return_value=None), \
         patch.object(fiscal_pdf_service.invoice_repo, "get", return_value=None):
        response = client.get("/api/T0090I/999/fiscal-pdf")
        assert response.status_code == 404


def test_get_invoice_einvoice_record(client, mock_invoice):
    """Test GET /api/T0090I/{id}/einvoice returns e-invoice clearance record."""
    mock_record = {
        "id": 1,
        "invoice_id": 101,
        "invoice_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "invoice_type_code": "388",
        "subtype": "0100000",
        "icv": 1,
        "invoice_hash": "a" * 44,
        "clearance_status": "Cleared",
        "is_cleared": True,
        "is_reported": False,
    }
    with patch.object(service.repo, "get", return_value=mock_invoice), \
         patch.object(service.einvoice_service, "get_by_invoice_id", return_value=mock_record):
        response = client.get("/api/T0090I/101/einvoice")
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_id"] == 101
        assert data["clearance_status"] == "Cleared"
        assert data["is_cleared"] is True
