import pytest
from unittest.mock import MagicMock, patch

from modules.accounting.services.fiscal_pdf_service import FiscalPdfService, fiscal_pdf_service
from modules.accounting.models.einvoice import QRCodeResponse


@pytest.fixture
def mock_invoice_data():
    return {
        "id": 101,
        "invoice_number": "INV-2026-0001",
        "invoice_type": "Sales",
        "partner_id": 12,
        "sales_order_id": 55,
        "total_amount": 1150.0,
        "paid_amount": 0.0,
        "status": "Unpaid",
        "issue_date": "2026-09-05",
        "due_date": "2026-10-05",
        "notes": "Standard 30-day payment term applies.",
    }


@pytest.fixture
def mock_customer_data():
    return {
        "id": 12,
        "name": "Al-Amal Global Enterprises",
        "tax_id": "310098765400003",
        "vat_number": "310098765400003",
        "email": "procurement@al-amal.example.sa",
        "phone": "+966 11 234 5678",
        "address": "Bldg 45, King Abdulaziz Road, Riyadh, SA",
    }


@pytest.fixture
def mock_order_lines():
    return [
        {
            "id": 1,
            "sales_order_id": 55,
            "product_id": 10,
            "product_name": "Industrial Server Rack 42U",
            "qty": 2.0,
            "unit_price": 500.0,
            "line_total": 1000.0,
        }
    ]


@pytest.fixture
def mock_einvoice_record():
    return {
        "id": 1,
        "invoice_id": 101,
        "fiscal_profile_id": 1,
        "invoice_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "invoice_type_code": "388",
        "subtype": "0100000",
        "icv": 7,
        "pih": "NWZlY2ViNjZmZmM4NmY1MmIy...",
        "invoice_hash": "2f4b2383c50058b76b29d4dbd7fb0819c9616e09e39665e8a0a9c68cf59600a7",
        "digital_signature": "MEQCIFyZ8x3hDk7P...",
        "qr_code_tlv": "AQZOYW1lAg8zMDAwMTIzNDU2MDAwMDMDBTIwMjYtMDktMDU=",
        "clearance_status": "Cleared",
        "clearance_id": "IRN-2026-ZATCA-9988",
    }


@pytest.fixture
def mock_profile_data():
    return {
        "id": 1,
        "profile_name": "Main ZATCA Production Profile",
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
        "environment": "Production",
        "is_active": True,
    }


class TestFiscalPdfService:

    def test_generate_fiscal_pdf_complete(
        self, mock_invoice_data, mock_customer_data, mock_order_lines, mock_einvoice_record, mock_profile_data
    ):
        """Test generating a complete bilingual fiscal tax invoice PDF."""
        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = mock_customer_data

        mock_line_repo = MagicMock()
        mock_line_repo.list.return_value = mock_order_lines

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_by_invoice_id.return_value = mock_einvoice_record
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1lAg8zMDAwMTIzNDU2MDAwMDMDBTIwMjYtMDktMDU=",
            seller_name="Nova Global Trading LLC",
            tax_id="300012345600003",
            timestamp="2026-09-05T08:00:00Z",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=mock_cust_repo,
            line_repo=mock_line_repo,
        )

        pdf_bytes = service.generate_fiscal_pdf(invoice_id=101)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_fiscal_pdf_reported_status(
        self, mock_invoice_data, mock_customer_data, mock_order_lines, mock_einvoice_record, mock_profile_data
    ):
        """Test generating fiscal PDF for a B2C simplified invoice with Reported status."""
        mock_einvoice_record["clearance_status"] = "Reported"
        mock_einvoice_record["subtype"] = "0200000"

        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = mock_customer_data

        mock_line_repo = MagicMock()
        mock_line_repo.list.return_value = mock_order_lines

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_by_invoice_id.return_value = mock_einvoice_record
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1l...",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=mock_cust_repo,
            line_repo=mock_line_repo,
        )

        pdf_bytes = service.generate_fiscal_pdf(invoice_id=101)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_fiscal_pdf_draft_and_pending_status(
        self, mock_invoice_data, mock_customer_data, mock_einvoice_record, mock_profile_data
    ):
        """Test generating fiscal PDF with Draft and Pending clearance statuses."""
        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = mock_customer_data

        mock_line_repo = MagicMock()
        mock_line_repo.list.return_value = []

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1l...",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=mock_cust_repo,
            line_repo=mock_line_repo,
        )

        # Test Draft status
        mock_einvoice_record["clearance_status"] = "Draft"
        mock_einvoice_svc.get_by_invoice_id.return_value = mock_einvoice_record
        pdf_draft = service.generate_fiscal_pdf(invoice_id=101)
        assert pdf_draft.startswith(b"%PDF")

        # Test Pending status
        mock_einvoice_record["clearance_status"] = "Pending"
        mock_einvoice_svc.get_by_invoice_id.return_value = mock_einvoice_record
        pdf_pending = service.generate_fiscal_pdf(invoice_id=101)
        assert pdf_pending.startswith(b"%PDF")

    def test_generate_fiscal_pdf_without_lines(
        self, mock_invoice_data, mock_customer_data, mock_profile_data
    ):
        """Test generating fiscal PDF when no line items exist (fallback summary line)."""
        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = mock_customer_data

        mock_line_repo = MagicMock()
        mock_line_repo.list.return_value = []

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_by_invoice_id.return_value = None
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1l...",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=mock_cust_repo,
            line_repo=mock_line_repo,
        )

        pdf_bytes = service.generate_fiscal_pdf(invoice_id=101)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_fiscal_pdf_without_customer(
        self, mock_invoice_data, mock_profile_data
    ):
        """Test generating fiscal PDF when invoice has no partner_id/customer."""
        mock_invoice_data["partner_id"] = None
        mock_invoice_data["customer_name"] = "Walk-in Retail Buyer"

        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_cust_repo = MagicMock()

        mock_line_repo = MagicMock()
        mock_line_repo.list.return_value = []

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_by_invoice_id.return_value = None
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1l...",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=mock_cust_repo,
            line_repo=mock_line_repo,
        )

        pdf_bytes = service.generate_fiscal_pdf(invoice_id=101)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_fiscal_pdf_not_found(self):
        """Test generating fiscal PDF raises ValueError when invoice does not exist."""
        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = None

        service = FiscalPdfService(invoice_repo=mock_inv_repo)

        with pytest.raises(ValueError, match="Invoice #999 not found"):
            service.generate_fiscal_pdf(invoice_id=999)

    def test_generate_fiscal_invoice_pdf_alias(
        self, mock_invoice_data, mock_profile_data
    ):
        """Test generate_fiscal_invoice_pdf method alias."""
        mock_inv_repo = MagicMock()
        mock_inv_repo.get.return_value = mock_invoice_data

        mock_einvoice_svc = MagicMock()
        mock_einvoice_svc.get_by_invoice_id.return_value = None
        mock_einvoice_svc.get_active_fiscal_profile.return_value = mock_profile_data
        mock_einvoice_svc.generate_qr_code.return_value = QRCodeResponse(
            invoice_id=101,
            qr_code_tlv="AQZOYW1l...",
            total_amount=1150.0,
            vat_total=150.0,
        )

        service = FiscalPdfService(
            einvoice_service=mock_einvoice_svc,
            invoice_repo=mock_inv_repo,
            customer_repo=MagicMock(),
            line_repo=MagicMock(),
        )

        pdf_bytes = service.generate_fiscal_invoice_pdf(invoice_id=101)
        assert pdf_bytes.startswith(b"%PDF")

    def test_create_qr_drawing_helper(self):
        """Test _create_qr_drawing constructs a valid ReportLab Drawing."""
        service = FiscalPdfService()
        drawing = service._create_qr_drawing("AQZOYW1l...", size=120.0)
        assert drawing.width == 120.0
        assert drawing.height == 120.0
        assert len(drawing.contents) == 1

    def test_module_singleton_instance(self):
        """Test that the module exports a valid fiscal_pdf_service singleton."""
        assert fiscal_pdf_service is not None
        assert isinstance(fiscal_pdf_service, FiscalPdfService)
