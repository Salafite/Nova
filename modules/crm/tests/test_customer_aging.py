"""
Unit and integration tests for Accounts Receivable (AR) Customer Aging Service, calculation engine, and T0010I endpoints.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from modules.crm.services.aging_service import (
    AgingService,
    calculate_aging,
    calculate_invoice_aging,
    classify_overdue_days,
    parse_date,
)
from modules.crm.controllers import T0010I
from packages.auth.deps import get_current_user


# ---------------------------------------------------------------------------
# 1. Date Parsing Unit Tests
# ---------------------------------------------------------------------------

class TestAgingDateParsing:
    """Test date parsing utility across formats, datetimes, and edge cases."""

    @pytest.mark.parametrize("input_val, expected", [
        (None, None),
        ("", None),
        ("   ", None),
        ("not-a-date", None),
        (date(2026, 8, 25), date(2026, 8, 25)),
        (datetime(2026, 8, 25, 14, 30, 0), date(2026, 8, 25)),
        ("2026-08-25", date(2026, 8, 25)),
        ("2026-08-25T14:30:00", date(2026, 8, 25)),
        ("2026-08-25T14:30:00Z", date(2026, 8, 25)),
        ("25/08/2026", date(2026, 8, 25)),
        ("08/25/2026", date(2026, 8, 25)),
        ("2026/08/25", date(2026, 8, 25)),
    ])
    def test_parse_date_variants(self, input_val, expected):
        assert parse_date(input_val) == expected


# ---------------------------------------------------------------------------
# 2. Overdue Classification Unit Tests
# ---------------------------------------------------------------------------

class TestOverdueClassification:
    """Test classification of overdue days into 5 standard buckets and boundary conditions."""

    @pytest.mark.parametrize("days_overdue, expected_bucket", [
        (-60, 'current'),
        (-30, 'current'),
        (-1, 'current'),
        (0, 'current'),
        (1, '1_30'),
        (15, '1_30'),
        (30, '1_30'),
        (31, '31_60'),
        (45, '31_60'),
        (60, '31_60'),
        (61, '61_90'),
        (75, '61_90'),
        (90, '61_90'),
        (91, '90_plus'),
        (120, '90_plus'),
        (365, '90_plus'),
    ])
    def test_classify_overdue_days_buckets(self, days_overdue, expected_bucket):
        assert classify_overdue_days(days_overdue) == expected_bucket


# ---------------------------------------------------------------------------
# 3. Aging Calculation Unit Tests
# ---------------------------------------------------------------------------

class TestAgingCalculation:
    """Test calculate_aging and calculate_invoice_aging across various invoice scenarios."""

    def test_empty_invoices(self):
        res = calculate_aging([])
        assert res['current'] == 0.0
        assert res['1_30'] == 0.0
        assert res['31_60'] == 0.0
        assert res['61_90'] == 0.0
        assert res['90_plus'] == 0.0
        assert res['30'] == 0.0
        assert res['60'] == 0.0
        assert res['90'] == 0.0
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

        assert res['current'] == 150.0   # 100 + 50
        assert res['1_30'] == 275.0     # 200 + 75
        assert res['31_60'] == 300.0    # 300
        assert res['61_90'] == 400.0    # 400
        assert res['90_plus'] == 500.0  # 500
        # Backward-compatible aliases
        assert res['30'] == 275.0
        assert res['60'] == 300.0
        assert res['90'] == 400.0

        assert res['total_outstanding'] == 150.0 + 275.0 + 300.0 + 400.0 + 500.0  # 1625.0
        assert res['total_paid'] == 1000.0

    def test_single_invoice_aging_method(self):
        svc = AgingService()
        as_of = date(2026, 8, 25)

        inv_current = {'id': 10, 'invoice_number': 'INV-001', 'total_amount': 250.0, 'due_date': '2026-08-30', 'status': 'Unpaid'}
        detail_current = svc.calculate_invoice_aging(inv_current, as_of_date=as_of)
        assert detail_current['bucket'] == 'current'
        assert detail_current['days_overdue'] == 0
        assert detail_current['is_outstanding'] is True
        assert detail_current['is_paid'] is False

        inv_overdue = {'id': 11, 'invoice_number': 'INV-002', 'total_amount': 350.0, 'due_date': '2026-07-20', 'status': 'Overdue'}
        detail_overdue = svc.calculate_invoice_aging(inv_overdue, as_of_date=as_of)
        assert detail_overdue['bucket'] == '31_60'  # (2026-08-25 - 2026-07-20) = 36 days
        assert detail_overdue['days_overdue'] == 36
        assert detail_overdue['is_outstanding'] is True

        inv_paid = {'id': 12, 'invoice_number': 'INV-003', 'total_amount': 400.0, 'due_date': '2026-07-01', 'status': 'Paid'}
        detail_paid = svc.calculate_invoice_aging(inv_paid, as_of_date=as_of)
        assert detail_paid['is_paid'] is True
        assert detail_paid['is_outstanding'] is False
        assert detail_paid['bucket'] is None

        inv_void = {'id': 13, 'invoice_number': 'INV-004', 'total_amount': 600.0, 'due_date': '2026-07-01', 'status': 'Void'}
        detail_void = svc.calculate_invoice_aging(inv_void, as_of_date=as_of)
        assert detail_void['is_paid'] is False
        assert detail_void['is_outstanding'] is False
        assert detail_void['bucket'] is None

    def test_invoice_missing_due_date_falls_back_to_issue_date(self):
        as_of = date(2026, 8, 25)
        invoices = [
            # Missing due_date, issue_date 15 days ago -> 1_30 bucket
            {'id': 20, 'total_amount': 250.0, 'due_date': None, 'issue_date': '2026-08-10', 'status': 'Unpaid'},
        ]
        res = calculate_aging(invoices, as_of_date=as_of)
        assert res['1_30'] == 250.0
        assert res['total_outstanding'] == 250.0

    def test_invoice_missing_both_due_date_and_issue_date_defaults_to_current(self):
        as_of = date(2026, 8, 25)
        invoices = [
            # Missing both due_date and issue_date -> defaults to as_of (current)
            {'id': 21, 'total_amount': 150.0, 'due_date': None, 'issue_date': None, 'status': 'Unpaid'},
        ]
        res = calculate_aging(invoices, as_of_date=as_of)
        assert res['current'] == 150.0
        assert res['total_outstanding'] == 150.0

    def test_status_case_insensitivity_and_variations(self):
        as_of = date(2026, 8, 25)
        invoices = [
            {'id': 31, 'total_amount': 100.0, 'due_date': '2026-07-01', 'status': 'PAID'},
            {'id': 32, 'total_amount': 200.0, 'due_date': '2026-07-01', 'status': 'paid'},
            {'id': 33, 'total_amount': 300.0, 'due_date': '2026-07-01', 'status': 'Cancelled'},
            {'id': 34, 'total_amount': 400.0, 'due_date': '2026-07-01', 'status': 'VOID'},
        ]
        res = calculate_aging(invoices, as_of_date=as_of)
        assert res['total_paid'] == 300.0  # 100 + 200
        assert res['total_outstanding'] == 0.0
        assert res['90_plus'] == 0.0

    def test_invoice_with_none_or_missing_amount_handled_safely(self):
        as_of = date(2026, 8, 25)
        invoices = [
            {'id': 41, 'total_amount': None, 'due_date': '2026-08-25', 'status': 'Unpaid'},
            {'id': 42, 'due_date': '2026-08-25', 'status': 'Unpaid'},
        ]
        res = calculate_aging(invoices, as_of_date=as_of)
        assert res['current'] == 0.0
        assert res['total_outstanding'] == 0.0


# ---------------------------------------------------------------------------
# 4. Customer Aging Service Unit & Integration Tests
# ---------------------------------------------------------------------------

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
            {'id': 3, 'partner_id': 1, 'total_amount': 300.0, 'due_date': '2026-08-01', 'status': 'Paid'},
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
        assert result['aging']['total_paid'] == 300.0
        assert result['invoices_count'] == 3
        assert result['open_invoices_count'] == 2
        assert result['paid_invoices_count'] == 1

    def test_get_customer_aging_not_found(self):
        mock_cust_repo = MagicMock()
        mock_cust_repo.get.return_value = None
        svc = AgingService(customer_repo=mock_cust_repo)
        result = svc.get_customer_aging(999)
        assert result is None

    def test_get_customer_aging_with_preloaded_customer_and_invoices(self):
        mock_cust_repo = MagicMock()
        mock_inv_repo = MagicMock()
        svc = AgingService(customer_repo=mock_cust_repo, invoice_repo=mock_inv_repo)

        custom_cust = {'id': 5, 'name': 'Preloaded Client', 'balance': 750.0}
        custom_invs = [{'id': 50, 'partner_id': 5, 'total_amount': 750.0, 'due_date': '2026-08-20', 'status': 'Unpaid'}]

        result = svc.get_customer_aging(
            customer_id=5,
            as_of_date='2026-08-25',
            customer=custom_cust,
            invoices=custom_invs,
        )

        assert result['customer_name'] == 'Preloaded Client'
        assert result['aging']['1_30'] == 750.0
        mock_cust_repo.get.assert_not_called()
        mock_inv_repo.list.assert_not_called()

    def test_get_customer_aging_no_invoices(self):
        mock_cust_repo = MagicMock()
        mock_inv_repo = MagicMock()

        mock_cust_repo.get.return_value = {'id': 2, 'name': 'Clean Slate Inc', 'balance': 0.0}
        mock_inv_repo.list.return_value = []

        svc = AgingService(customer_repo=mock_cust_repo, invoice_repo=mock_inv_repo)
        result = svc.get_customer_aging(2, as_of_date='2026-08-25')

        assert result['customer_id'] == 2
        assert result['invoices_count'] == 0
        assert result['open_invoices_count'] == 0
        assert result['paid_invoices_count'] == 0
        assert result['aging']['total_outstanding'] == 0.0

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
        assert len(summary['customers']) == 2

    def test_get_all_customers_aging_empty_customer_list(self):
        mock_cust_repo = MagicMock()
        mock_cust_repo.list.return_value = []
        svc = AgingService(customer_repo=mock_cust_repo)
        summary = svc.get_all_customers_aging()
        assert summary['customer_count'] == 0
        assert summary['customers'] == []
        assert summary['total_aging']['total_outstanding'] == 0.0


# ---------------------------------------------------------------------------
# 5. CRM Customer Controller (T0010I) Endpoints Integration Tests
# ---------------------------------------------------------------------------

class TestCustomerAgingEndpoints:
    """Tests for T0010I customer aging and reports routes using TestClient."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        self.app = FastAPI()
        self.app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "username": "accountant",
            "role": "Admin",
            "business_id": 1,
        }
        self.app.include_router(T0010I.router)
        self.client = TestClient(self.app)

    def test_get_customer_aging_endpoint_success(self, monkeypatch):
        """GET /api/T0010I/{id}/aging returns aging report for customer."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = {'id': 10, 'name': 'Alpha Co', 'balance': 850.0}
        monkeypatch.setattr(T0010I, 'repo', mock_repo)

        mock_aging_svc = MagicMock()
        mock_aging_svc.get_customer_aging.return_value = {
            'customer_id': 10,
            'customer_name': 'Alpha Co',
            'balance': 850.0,
            'as_of_date': '2026-08-25',
            'aging': {
                'current': 350.0,
                '1_30': 500.0,
                '31_60': 0.0,
                '61_90': 0.0,
                '90_plus': 0.0,
                '30': 500.0,
                '60': 0.0,
                '90': 0.0,
                'total_outstanding': 850.0,
                'total_paid': 100.0,
            },
            'invoices_count': 2,
            'open_invoices_count': 2,
            'paid_invoices_count': 1,
        }
        monkeypatch.setattr(T0010I, 'aging_service', mock_aging_svc)

        resp = self.client.get('/api/T0010I/10/aging?as_of_date=2026-08-25')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data['customer_id'] == 10
        assert data['customer_name'] == 'Alpha Co'
        assert data['aging']['current'] == 350.0
        assert data['aging']['1_30'] == 500.0
        assert data['aging']['total_outstanding'] == 850.0

        mock_aging_svc.get_customer_aging.assert_called_once_with(
            10,
            as_of_date='2026-08-25',
            customer={'id': 10, 'name': 'Alpha Co', 'balance': 850.0},
        )

    def test_get_customer_aging_endpoint_404_when_customer_not_found(self, monkeypatch):
        """GET /api/T0010I/{id}/aging returns 404 when customer does not exist."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        monkeypatch.setattr(T0010I, 'repo', mock_repo)

        with patch('modules.crm.controllers.T0010I.check_record_ownership'):
            resp = self.client.get('/api/T0010I/999/aging')
            assert resp.status_code == status.HTTP_404_NOT_FOUND
            assert resp.json()['detail'] == 'Customer not found'

    def test_get_all_customers_aging_report_endpoint(self, monkeypatch):
        """GET /api/T0010I/reports/aging returns aggregate aging across all customers."""
        mock_aging_svc = MagicMock()
        mock_aging_svc.get_all_customers_aging.return_value = {
            'as_of_date': '2026-08-25',
            'total_aging': {
                'current': 1500.0,
                '1_30': 800.0,
                '31_60': 200.0,
                '61_90': 0.0,
                '90_plus': 0.0,
                '30': 800.0,
                '60': 200.0,
                '90': 0.0,
                'total_outstanding': 2500.0,
                'total_paid': 500.0,
            },
            'customers': [],
            'customer_count': 0,
        }
        monkeypatch.setattr(T0010I, 'aging_service', mock_aging_svc)

        resp = self.client.get('/api/T0010I/reports/aging?as_of_date=2026-08-25&limit=50')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data['as_of_date'] == '2026-08-25'
        assert data['total_aging']['total_outstanding'] == 2500.0
        mock_aging_svc.get_all_customers_aging.assert_called_once_with(
            as_of_date='2026-08-25',
            limit=50,
        )
