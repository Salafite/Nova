import pytest
from unittest.mock import MagicMock
from datetime import date
from modules.portal.services.invoice_pdf_service import InvoicePdfService


class TestInvoicePdfService:
    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def pdf_service(self, mock_repo):
        return InvoicePdfService(portal_repo=mock_repo)

    def test_generate_invoice_pdf_with_order_lines(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = {
            "id": 101,
            "invoice_number": "INV-2026-00101",
            "invoice_type": "Sales",
            "partner_id": 50,
            "customer_name": "Bistro Bella",
            "sales_order_id": 501,
            "sales_order_number": "SO-00501",
            "issue_date": date(2026, 8, 20),
            "due_date": date(2026, 9, 20),
            "total_amount": 450.0,
            "paid_amount": 0.0,
            "balance_due": 450.0,
            "status": "Unpaid",
            "notes": "Net 30 terms apply.",
            "payment_link": "https://checkout.stripe.com/pay/cs_test_abc123",
        }
        mock_repo.get_customer_by_id.return_value = {
            "id": 50,
            "name": "Bistro Bella",
            "group_name": "Restaurant Wholesale",
            "email": "buyer@bistro.com",
            "phone": "+1 555 123 4567",
        }
        mock_repo.get_order_by_id.return_value = {
            "id": 501,
            "order_number": "SO-00501",
            "subtotal": 450.0,
            "tax": 0.0,
            "grand_total": 450.0,
        }
        mock_repo.get_order_lines.return_value = [
            {
                "id": 1,
                "sales_order_id": 501,
                "product_id": 10,
                "product_code": "FLOUR-50LB",
                "product_name": "Organic Bread Flour 50lb",
                "uom_name": "Bag",
                "qty": 5.0,
                "unit_price": 50.0,
                "line_total": 250.0,
            },
            {
                "id": 2,
                "sales_order_id": 501,
                "product_id": 12,
                "product_code": "YEAST-5LB",
                "product_name": "Active Dry Yeast 5lb",
                "uom_name": "Tub",
                "qty": 4.0,
                "unit_price": 50.0,
                "line_total": 200.0,
            }
        ]

        pdf_bytes = pdf_service.generate_invoice_pdf(invoice_id=101, customer_id=50)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")
        mock_repo.get_invoice_by_id.assert_called_once_with(101, customer_id=50)
        mock_repo.get_order_lines.assert_called_once_with(501)

    def test_generate_invoice_pdf_paid_status(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = {
            "id": 102,
            "invoice_number": "INV-2026-00102",
            "invoice_type": "Sales",
            "partner_id": 50,
            "customer_name": "Bistro Bella",
            "sales_order_id": None,
            "issue_date": date(2026, 8, 1),
            "due_date": date(2026, 8, 15),
            "total_amount": 1200.0,
            "paid_amount": 1200.0,
            "balance_due": 0.0,
            "status": "Paid",
            "notes": "Paid in full via Stripe Card.",
            "payment_link": None,
        }
        mock_repo.get_customer_by_id.return_value = {
            "id": 50,
            "name": "Bistro Bella",
            "email": "buyer@bistro.com",
        }

        pdf_bytes = pdf_service.generate_invoice_pdf(invoice_id=102, customer_id=50)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_invoice_pdf_not_found(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = None

        with pytest.raises(ValueError, match="Invoice #999 was not found"):
            pdf_service.generate_invoice_pdf(invoice_id=999, customer_id=50)

    def test_generate_invoice_pdf_customer_isolation_mismatch(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = None  # get_invoice_by_id returns None when customer_id does not match

        with pytest.raises(ValueError, match="Invoice #101 was not found or does not belong to your account"):
            pdf_service.generate_invoice_pdf(invoice_id=101, customer_id=999)

    def test_generate_invoice_pdf_partially_paid_with_link(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = {
            "id": 103,
            "invoice_number": "INV-2026-00103",
            "invoice_type": "Sales",
            "partner_id": 50,
            "customer_name": "Bistro Bella",
            "sales_order_id": None,
            "issue_date": date(2026, 8, 10),
            "due_date": date(2026, 9, 10),
            "total_amount": 1000.0,
            "paid_amount": 400.0,
            "balance_due": 600.0,
            "status": "Partially Paid",
            "notes": "Partial settlement received.",
            "payment_link": "https://checkout.stripe.com/pay/cs_test_partial",
        }
        mock_repo.get_customer_by_id.return_value = {
            "id": 50,
            "name": "Bistro Bella",
        }

        pdf_bytes = pdf_service.generate_invoice_pdf(invoice_id=103, customer_id=50)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_invoice_pdf_missing_customer_record(self, pdf_service, mock_repo):
        mock_repo.get_invoice_by_id.return_value = {
            "id": 104,
            "invoice_number": "INV-2026-00104",
            "invoice_type": "Sales",
            "partner_id": 50,
            "customer_name": "Direct Client",
            "sales_order_id": None,
            "issue_date": date(2026, 8, 12),
            "due_date": date(2026, 8, 26),
            "total_amount": 300.0,
            "paid_amount": 0.0,
            "balance_due": 300.0,
            "status": "Unpaid",
            "notes": None,
            "payment_link": None,
        }
        mock_repo.get_customer_by_id.return_value = None

        pdf_bytes = pdf_service.generate_invoice_pdf(invoice_id=104, customer_id=50)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")

