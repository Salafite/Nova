"""
Unit and integration tests for GET /api/T0010I/{id}/credit-status endpoint in CRM controller.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from modules.crm.controllers import T0010I
from modules.sales.services.credit_service import CreditService


class InMemoryRepo:
    """In-memory CRUD repository for customer credit tests."""

    def __init__(self, table_name, items=None):
        self.table_name = table_name
        self.items = {item['id']: dict(item) for item in (items or [])}
        self._next_id = max(self.items.keys(), default=0) + 1

    def get(self, id_val, conn=None, **kwargs):
        item = self.items.get(id_val)
        return dict(item) if item else None

    def get_unscoped(self, id_val, conn=None, **kwargs):
        item = self.items.get(id_val)
        return dict(item) if item else None

    def list(self, filters=None, limit=1000, order_by=None, offset=0, conn=None, **kwargs):
        results = list(self.items.values())
        if filters:
            for k, v in filters.items():
                results = [r for r in results if r.get(k) == v]
        if order_by and isinstance(order_by, str):
            results.sort(key=lambda x: (x.get(order_by) is None, x.get(order_by)))
        return [dict(r) for r in results[offset:offset + limit]]

    def create(self, payload, conn=None, **kwargs):
        new_id = payload.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        record = dict(payload, id=new_id)
        self.items[new_id] = record
        return dict(record)

    def update(self, id_val, payload, conn=None, **kwargs):
        if id_val not in self.items:
            return None
        self.items[id_val].update(payload)
        return dict(self.items[id_val])

    def delete(self, id_val, conn=None, **kwargs):
        return self.items.pop(id_val, None) is not None


class TestCustomerCreditStatusEndpoint:
    """Tests for GET /api/T0010I/{id}/credit-status endpoint."""

    def setup_method(self):
        self.today = date.today()
        self.customers = [
            {
                'id': 1,
                'name': 'Acme Corp',
                'credit_limit': 10000.0,
                'balance': 2500.0,
                'business_id': 1,
            },
            {
                'id': 2,
                'name': 'Delinquent Overdue Inc',
                'credit_limit': 15000.0,
                'balance': 3000.0,
                'business_id': 1,
            },
            {
                'id': 3,
                'name': 'Over Credit Limit Ltd',
                'credit_limit': 5000.0,
                'balance': 8000.0,
                'business_id': 1,
            },
        ]
        self.invoices = [
            # Open regular invoice for Acme Corp
            {
                'id': 101,
                'invoice_number': 'INV-00101',
                'partner_id': 1,
                'issue_date': str(self.today - timedelta(days=10)),
                'due_date': str(self.today + timedelta(days=20)),
                'total_amount': 2500.0,
                'status': 'Issued',
                'business_id': 1,
            },
            # Overdue invoice (>30 days overdue) for Delinquent Overdue Inc
            {
                'id': 102,
                'invoice_number': 'INV-00102',
                'partner_id': 2,
                'issue_date': str(self.today - timedelta(days=75)),
                'due_date': str(self.today - timedelta(days=45)),  # 45 days overdue (>30)
                'total_amount': 3000.0,
                'status': 'Issued',
                'business_id': 1,
            },
        ]
        self.orders = [
            {
                'id': 501,
                'order_number': 'SO-00501',
                'customer_id': 3,
                'grand_total': 3000.0,
                'status': 'Credit Hold',
                'hold_reason': 'Customer credit limit exceeded: Balance $8,000.00 > Limit $5,000.00',
                'business_id': 1,
            }
        ]

        self.customer_repo = InMemoryRepo('T0010', self.customers)
        self.invoice_repo = InMemoryRepo('T0090', self.invoices)
        self.order_repo = InMemoryRepo('T0012', self.orders)

        self.credit_service = CreditService(
            customer_repo=self.customer_repo,
            invoice_repo=self.invoice_repo,
            order_repo=self.order_repo,
        )

        self.orig_repo = T0010I.repo
        self.orig_credit_service = T0010I.credit_service
        T0010I.repo = self.customer_repo
        T0010I.credit_service = self.credit_service

        self.user = {'id': 10, 'username': 'salesrep', 'role': 'sales', 'business_id': 1}

    def teardown_method(self):
        T0010I.repo = self.orig_repo
        T0010I.credit_service = self.orig_credit_service

    def test_get_credit_status_healthy_customer(self):
        res = T0010I.customer_credit_status(id=1, user=self.user)
        assert res['customer_id'] == 1
        assert res['customer_name'] == 'Acme Corp'
        assert res['credit_limit'] == 10000.0
        assert res['balance'] == 2500.0
        assert res['available_credit'] == 7500.0
        assert res['credit_limit_exceeded'] is False
        assert res['overdue_invoices_count'] == 0
        assert res['overdue_invoices_amount'] == 0.0
        assert res['has_overdue_invoices'] is False
        assert res['is_delinquent'] is False
        assert res['on_hold'] is False
        assert res['has_hold_orders'] is False

    def test_get_credit_status_delinquent_overdue_invoices(self):
        res = T0010I.customer_credit_status(id=2, user=self.user)
        assert res['customer_id'] == 2
        assert res['balance'] == 3000.0
        assert res['credit_limit'] == 15000.0
        assert res['available_credit'] == 12000.0
        assert res['credit_limit_exceeded'] is False
        assert res['overdue_invoices_count'] == 1
        assert res['overdue_invoices_amount'] == 3000.0
        assert res['has_overdue_invoices'] is True
        assert res['is_delinquent'] is True
        assert res['on_hold'] is True
        assert len(res['hold_reasons']) > 0
        assert 'overdue by >30 days' in res['hold_reasons'][0]

    def test_get_credit_status_credit_limit_exceeded_and_hold_orders(self):
        res = T0010I.customer_credit_status(id=3, user=self.user)
        assert res['customer_id'] == 3
        assert res['balance'] == 8000.0
        assert res['credit_limit'] == 5000.0
        assert res['available_credit'] == 0.0
        assert res['raw_available_credit'] == -3000.0
        assert res['credit_limit_exceeded'] is True
        assert res['is_delinquent'] is True
        assert res['on_hold'] is True
        assert res['has_hold_orders'] is True
        assert res['hold_orders_count'] == 1
        assert len(res['hold_reasons']) > 0

    def test_get_credit_status_customer_not_found(self):
        with pytest.raises(HTTPException) as exc_info:
            T0010I.customer_credit_status(id=999, user=self.user)
        assert exc_info.value.status_code == 404
