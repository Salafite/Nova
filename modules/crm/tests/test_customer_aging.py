"""
Unit and integration tests for Accounts Receivable (AR) Customer Aging Service and calculation engine.
"""

from datetime import date, timedelta
import pytest
from unittest.mock import MagicMock
from modules.crm.services.aging_service import (
    AgingService,
    calculate_aging,
    classify_overdue_days,
    parse_date,
)


class TestAgingDateParsing:
    """Test date parsing utility."""

    def test_parse_none(self):
        assert parse_date(None) is None

    def test_parse_date_object(self):
        d = date(2026, 8, 25)
        assert parse_date(d) == d

    def test_parse_iso_string(self):
        assert parse_date("2026-08-25") == date(2026, 8, 25)
        assert parse_date("2026-08-25T14:30:00") == date(2026, 8, 25)

    def test_parse_invalid_string(self):
        assert parse_date("not-a-date") is None
        assert parse_date("") is None


class TestOverdueClassification:
    """Test classification of overdue days into 5 standard buckets."""

    def test_current_bucket(self):
        # 0 or negative days overdue -> 'current'
        assert classify_overdue_days(0) == 'current'
        assert classify_overdue_days(-5) == 'current'
        assert classify_overdue_days(-30) == 'current'

    def test_1_to_30_days_bucket(self):
        assert classify_overdue_days(1) == '1_30'
        assert classify_overdue_days(15) == '1_30'
        assert classify_overdue_days(30) == '1_30'

    def test_31_to_60_days_bucket(self):
        assert classify_overdue_days(31) == '31_60'
        assert classify_overdue_days(45) == '31_60'
        assert classify_overdue_days(60) == '31_60'

    def test_61_to_90_days_bucket(self):
        assert classify_overdue_days(61) == '61_90'
        assert classify_overdue_days(75) == '61_90'
        assert classify_overdue_days(90) == '61_90'

    def test_90_plus_bucket(self):
        assert classify_overdue_days(91) == '90_plus'
        assert classify_overdue_days(120) == '90_plus'
        assert classify_overdue_days(365) == '90_plus'


class TestAgingCalculation:
    """Test calculate_aging across various invoice scenarios."""

    def test_empty_invoices(self):
        res = calculate_aging([])
        assert res['current'] == 0.0
        assert res['1_30'] == 0.0
        assert res['31_60'] == 0.0
        assert res['61_90'] == 0.0
        assert res['90_plus'] == 0.0
        assert res['total_outstanding'] == 0.0
        assert res['total_paid'] == 0.0

    def test_all_5_buckets_categorization(self):
        as_of = date(2026, 8, 25)
        invoices = [
            # Current: due in future (2026-09-05)
            {'id': 1, 'total_amount': 100.0, 'due_date': '2026-09-05', 'status': 'Unpaid'},
            # Current: due today (2026-08-25)
            {'id': 2, 'total_amount': 50.0, 'due_date': '2026-08-25', 'status': 'Unpaid'},
            # 1-30 days: due 10 days ago (2026-08-15)
            {'id': 3, 'total_amount': 200.0, 'due_date': '2026-08-15', 'status': 'Unpaid'},
            # 1-30 days: due 30 days ago (2026-07-26)
            {'id': 4, 'total_amount': 75.0, 'due_date': '2026-07-26', 'status': 'Overdue'},
            # 31-60 days: due 45 days ago (2026-07-11)
            {'id': 5, 'total_amount': 300.0, 'due_date': '2026-07-11', 'status': 'Overdue'},
            # 61-90 days: due 75 days ago (2026-06-11)
            {'id': 6, 'total_amount': 400.0, 'due_date': '2026-06-11', 'status': 'Overdue'},
            # 90+ days: due 120 days ago (2026-04-27)
            {'id': 7, 'total_amount': 500.0, 'due_date': '2026-04-27', 'status': 'Overdue'},
            # Paid invoice
            {'id': 8, 'total_amount': 1000.0, 'due_date': '2026-07-01', 'status': 'Paid'},
            # Cancelled invoice
            {'id': 9, 'total_amount': 999.0, 'due_date': '2026-07-01', 'status': 'Cancelled'},
        ]

        res = calculate_aging(invoices, as_of_date=as_of)

        assert res['current'] == 150.0 # 100 + 50
        assert res['1_30'] == 275.0   # 200 + 75
        assert res['31_60'] == 300.0  # 300
        assert res['61_90'] == 400.0  # 400
        assert res['90_plus'] == 500.0# 500
        # Backward-compatible aliases
        assert res['30'] == 275.0
        assert res['60'] == 300.0
        assert res['90'] == 400.0

        assert res['total_outstanding'] == 150.0 + 275.0 + 300.0 + 400.0 + 500.0 # 1625.0
        assert res['total_paid'] == 1000.0

    def test_single_invoice_aging_method(self):
        svc = AgingService()
        as_of = date(2026, 8, 25)

        inv_current = {'id': 10, 'invoice_number': 'INV-001', 'total_amount': 250.0, 'due_date': '2026-08-30', 'status': 'Unpaid'}
        detail_current = svc.calculate_invoice_aging(inv_current, as_of_date=as_of)
        assert detail_current['bucket'] == 'current'
        assert detail_current['days_overdue'] == 0
        assert detail_current['is_outstanding'] is True

        inv_overdue = {'id': 11, 'invoice_number': 'INV-002', 'total_amount': 350.0, 'due_date': '2026-07-20', 'status': 'Overdue'}
        detail_overdue = svc.calculate_invoice_aging(inv_overdue, as_of_date=as_of)
        assert detail_overdue['bucket'] == '31_60' # (2026-08-25 - 2026-07-20) = 36 days
        assert detail_overdue['days_overdue'] == 36
        assert detail_overdue['is_outstanding'] is True

        inv_paid = {'id': 12, 'invoice_number': 'INV-003', 'total_amount': 400.0, 'due_date': '2026-07-01', 'status': 'Paid'}
        detail_paid = svc.calculate_invoice_aging(inv_paid, as_of_date=as_of)
        assert detail_paid['is_paid'] is True
        assert detail_paid['is_outstanding'] is False


class TestCustomerAgingService:
    """Test get_customer_aging and get_all_customers_aging with mock repositories."""

    def test_get_customer_aging_found(self):
        mock_cust_repo = MagicMock()
        mock_inv_repo = MagicMock()

        mock_cust_repo.get.return_value = {
            'id': 1,
            'name': 'Acme Corp',
            'balance': 1500.0,
        }
        mock_inv_repo.list.return_value = [
            {'id': 1, 'partner_id': 1, 'total_amount': 500.0, 'due_date': '2026-08-25', 'status': 'Unpaid'},
            {'id': 2, 'partner_id': 1, 'total_amount': 1000.0, 'due_date': '2026-08-10', 'status': 'Unpaid'},
        ]

        svc = AgingService(customer_repo=mock_cust_repo, invoice_repo=mock_inv_repo)
        result = svc.get_customer_aging(1, as_of_date='2026-08-25')

        assert result is not None
        assert result['customer_id'] == 1
        assert result['customer_name'] == 'Acme Corp'
        assert result['balance'] == 1500.0
        assert result['aging']['current'] == 500.0
        assert result['aging']['1_30'] == 1000.0
        assert result['aging']['total_outstanding'] == 1500.0
        assert result['invoices_count'] == 2
        assert result['open_invoices_count'] == 2

    def test_get_customer_aging_not_found(self):
        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = None
        svc = AgingService(customer_repo=mock_cust_repo)
        result = svc.get_customer_aging(999)
        assert result is None

    def test_get_all_customers_aging(self):
        mock_cust_repo = MagicMock()
        mock_inv_repo = MagicMock()

        mock_cust_repo.list.return_value = [
            {'id': 1, 'name': 'Customer 1', 'balance': 500.0},
            {'id': 2, 'name': 'Customer 2', 'balance': 300.0},
        ]
        mock_inv_repo.list.side_effect = lambda filters: (
            [{'id': 1, 'partner_id': 1, 'total_amount': 500.0, 'due_date': '2026-08-25', 'status': 'Unpaid'}]
            if filters.get('partner_id') == 1
            else [{'id': 2, 'partner_id': 2, 'total_amount': 300.0, 'due_date': '2026-08-01', 'status': 'Unpaid'}]
        )

        svc = AgingService(customer_repo=mock_cust_repo, invoice_repo=mock_inv_repo)
        summary = svc.get_all_customers_aging(as_of_date='2026-08-25')

        assert summary['customer_count'] == 2
        assert summary['total_aging']['current'] == 500.0
        assert summary['total_aging']['1_30'] == 300.0
        assert summary['total_aging']['total_outstanding'] == 800.0
