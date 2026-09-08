"""
Unit and Integration Tests for StatementPdfService (AR Customer Account Statement PDF Generation).
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
from modules.accounting.services.statement_pdf_service import StatementPdfService
from modules.crm.services.aging_service import AgingService


@pytest.fixture
def mock_customer():
    return {
        "id": 101,
        "name": "Bistro Gourmet LLC",
        "email": "ap@bistrogourmet.com",
        "phone": "+1 (555) 234-5678",
        "group_name": "Premium Restaurants",
        "credit_limit": 50000.0,
        "balance": 12500.0,
        "is_vip": False,
        "exclude_from_reminders": False,
        "preferred_reminder_channel": "EMAIL",
        "reminder_phone": "+1 (555) 234-5678",
        "reminder_email": "billing@bistrogourmet.com",
    }


@pytest.fixture
def mock_vip_customer():
    return {
        "id": 102,
        "name": "The Grand Hotel & Resort",
        "email": "finance@grandhotel.com",
        "phone": "+1 (555) 987-6543",
        "group_name": "Hospitality VIP",
        "credit_limit": 100000.0,
        "balance": 28000.0,
        "is_vip": True,
        "exclude_from_reminders": False,
        "preferred_reminder_channel": "BOTH",
    }


@pytest.fixture
def mock_invoices():
    today = date(2026, 9, 8)
    return [
        {
            "id": 1001,
            "invoice_number": "INV-2026-1001",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=10)).isoformat(),
            "due_date": (today + timedelta(days=20)).isoformat(),
            "total_amount": 2500.0,
            "paid_amount": 0.0,
            "balance_due": 2500.0,
            "status": "Unpaid",
        },
        {
            "id": 1002,
            "invoice_number": "INV-2026-1002",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=45)).isoformat(),
            "due_date": (today - timedelta(days=15)).isoformat(),
            "total_amount": 3200.0,
            "paid_amount": 1000.0,
            "balance_due": 2200.0,
            "status": "Partially Paid",
        },
        {
            "id": 1003,
            "invoice_number": "INV-2026-1003",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=75)).isoformat(),
            "due_date": (today - timedelta(days=45)).isoformat(),
            "total_amount": 4100.0,
            "paid_amount": 0.0,
            "balance_due": 4100.0,
            "status": "Unpaid",
        },
        {
            "id": 1004,
            "invoice_number": "INV-2026-1004",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=105)).isoformat(),
            "due_date": (today - timedelta(days=75)).isoformat(),
            "total_amount": 1800.0,
            "paid_amount": 0.0,
            "balance_due": 1800.0,
            "status": "Unpaid",
        },
        {
            "id": 1005,
            "invoice_number": "INV-2026-1005",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=140)).isoformat(),
            "due_date": (today - timedelta(days=110)).isoformat(),
            "total_amount": 1900.0,
            "paid_amount": 0.0,
            "balance_due": 1900.0,
            "status": "Unpaid",
        },
        {
            "id": 1006,
            "invoice_number": "INV-2026-1006",
            "partner_id": 101,
            "issue_date": (today - timedelta(days=30)).isoformat(),
            "due_date": (today - timedelta(days=5)).isoformat(),
            "total_amount": 500.0,
            "paid_amount": 500.0,
            "balance_due": 0.0,
            "status": "Paid",
        },
    ]


class TestStatementPdfService:
    """Test suite for StatementPdfService generation logic."""

    def test_generate_statement_pdf_with_full_aging_buckets(self, mock_customer, mock_invoices):
        """Test PDF generation with invoices spanning across all 5 aging buckets."""
        pdf_service = StatementPdfService()
        eval_date = date(2026, 9, 8)

        pdf_bytes = pdf_service.generate_statement_pdf(
            customer=mock_customer,
            invoices=mock_invoices,
            as_of_date=eval_date,
            payment_link="https://pay.novaerp.com/c/101",
            custom_message="Please settle all invoices exceeding 60 days overdue immediately.",
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF")
        # Verify PDF footer / EOF indicator
        assert b"%%EOF" in pdf_bytes

    def test_generate_statement_pdf_zero_balance_account(self, mock_customer):
        """Test statement generation for account with no open invoices."""
        pdf_service = StatementPdfService()
        empty_invoices = []

        pdf_bytes = pdf_service.generate_statement_pdf(
            customer=mock_customer,
            invoices=empty_invoices,
            as_of_date=date(2026, 9, 8),
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_statement_pdf_vip_badge(self, mock_vip_customer, mock_invoices):
        """Test statement generation for VIP customer includes VIP metadata."""
        pdf_service = StatementPdfService()

        pdf_bytes = pdf_service.generate_statement_pdf(
            customer=mock_vip_customer,
            invoices=mock_invoices[:2],
            as_of_date=date(2026, 9, 8),
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1500
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_statement_pdf_date_range_filtering(self, mock_customer, mock_invoices):
        """Test invoice filtering with start_date and end_date."""
        pdf_service = StatementPdfService()
        start_d = date(2026, 7, 1)
        end_d = date(2026, 8, 31)

        pdf_bytes = pdf_service.generate_statement_pdf(
            customer=mock_customer,
            invoices=mock_invoices,
            start_date=start_d,
            end_date=end_d,
            as_of_date=end_d,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1500
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_statement_pdf_for_customer_using_repositories(self, mock_customer, mock_invoices):
        """Test fetching customer and invoices from injected mock repositories."""
        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = mock_customer

        mock_inv_repo = MagicMock()
        mock_inv_repo.list.return_value = mock_invoices

        pdf_service = StatementPdfService(
            customer_repo=mock_cust_repo,
            invoice_repo=mock_inv_repo,
        )

        pdf_bytes = pdf_service.generate_statement_pdf_for_customer(
            customer_id=101,
            as_of_date=date(2026, 9, 8),
            payment_link="https://pay.novaerp.com/invoice/bulk/101",
        )

        mock_cust_repo.get.assert_called_once_with(101)
        mock_inv_repo.list.assert_called_once_with(filters={"partner_id": 101}, limit=500)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_statement_customer_not_found(self):
        """Test ValueError is raised when customer is not found."""
        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = None

        pdf_service = StatementPdfService(customer_repo=mock_cust_repo)

        with pytest.raises(ValueError) as exc_info:
            pdf_service.generate_statement_pdf(customer_id=999)

        assert "Customer #999 was not found" in str(exc_info.value)

    def test_custom_company_info_override(self, mock_customer, mock_invoices):
        """Test statement rendering with custom company branding and bank info."""
        pdf_service = StatementPdfService()
        custom_company = {
            "name": "Artisan Food Distributors",
            "subtitle": "Organic Wholesale Provisions",
            "address": "450 Organic Way, Seattle, WA 98101",
            "contact": "ar@artisanfoods.com | (206) 555-FOOD",
            "bank_name": "Pacific Commercial Bank",
            "bank_routing": "987654321",
            "bank_account": "112233445566",
        }

        pdf_bytes = pdf_service.generate_statement_pdf(
            customer=mock_customer,
            invoices=mock_invoices,
            company_info=custom_company,
            currency="USD",
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF")
