"""
Comprehensive End-to-End Integration Lifecycle Test Suite:
Dynamic Payment Terms, Automated Due Date Engine, Early Payment Discounts, and AR Customer Aging.

Verifies end-to-end workflow across modules (Accounting, Sales, CRM, MCP, REST APIs):
1. Customer Creation & Payment Term Assignment (T0010, T0096)
2. Sales Order Creation & Term Inheritance / Overrides (T0012, T0013)
3. Order Confirmation & Delivery -> Automated Dynamic Invoice Generation (T0090)
4. Accounts Receivable Aging Calculations Across All 5 Buckets (Current, 1-30, 31-60, 61-90, 90+)
5. Early Payment Discount Preview & Eligibility Evaluation
6. Payment Settlement Honoring Early Discounts & Customer Balance Clearing (T0091)
7. Overdue Aging Progression & Cutoff Enforcement for Late Payments
8. REST API End-to-End Execution via FastAPI TestClient
9. MCP Tool Calling Integration via accounting_mcp and sales_mcp
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient

from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService

from modules.accounting.services.payment_term_service import PaymentTermService
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.accounting.services.invoice_service import InvoiceService
from modules.accounting.services.payment_service import PaymentService
from modules.crm.services.aging_service import AgingService, calculate_aging

from modules.accounting.controllers.T0096I import router as payment_term_router
from modules.crm.controllers.T0010I import router as customer_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.accounting.controllers.T0090I import router as invoice_router
from modules.accounting.controllers.T0091I import router as payment_router

from packages.auth.deps import get_current_user
import packages.mcp.servers.accounting_mcp as accounting_mcp
import packages.mcp.servers.sales_mcp as sales_mcp


# ============================================================================
# In-Memory Deterministic Multi-Table Storage for E2E Integration
# ============================================================================

class E2EStore:
    """In-memory multi-table database store for dynamic payment terms end-to-end tests."""
    def __init__(self):
        self.tables = {}
        self.counters = {}

    def reset(self):
        self.tables.clear()
        self.counters.clear()

    def _normalize(self, table_name: str) -> str:
        tbl = str(table_name).lower().replace('"', '')
        if '.' in tbl:
            tbl = tbl.split('.')[-1]
        return tbl

    def _get_table(self, table_name: str):
        tbl = self._normalize(table_name)
        if tbl not in self.tables:
            self.tables[tbl] = {}
            self.counters[tbl] = 0
        return self.tables[tbl]

    def create(self, table_name: str, payload: dict, pk: str = 'id') -> dict:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        explicit_id = payload.get(pk)
        if explicit_id is not None:
            rec_id = int(explicit_id)
            if rec_id > self.counters.get(tbl, 0):
                self.counters[tbl] = rec_id
        else:
            self.counters[tbl] = self.counters.get(tbl, 0) + 1
            rec_id = self.counters[tbl]

        record = dict(payload)
        record[pk] = rec_id
        t_data[rec_id] = record
        return dict(record)

    def get(self, table_name: str, id_val, pk: str = 'id') -> dict:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        try:
            int_id = int(id_val)
        except (ValueError, TypeError):
            int_id = id_val
        rec = t_data.get(int_id)
        return dict(rec) if rec else None

    def update(self, table_name: str, id_val, payload: dict, pk: str = 'id') -> dict:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        try:
            int_id = int(id_val)
        except (ValueError, TypeError):
            int_id = id_val
        if int_id not in t_data:
            return None
        t_data[int_id].update(payload)
        return dict(t_data[int_id])

    def list(self, table_name: str, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None) -> list:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        results = []
        for row in t_data.values():
            match = True
            if filters:
                for k, v in filters.items():
                    if row.get(k) != v:
                        match = False
                        break
            if match:
                results.append(dict(row))

        if order_by:
            results.sort(key=lambda r: (r.get(order_by) is None, r.get(order_by)))
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        return results

    def delete(self, table_name: str, id_val, pk: str = 'id') -> bool:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        try:
            int_id = int(id_val)
        except (ValueError, TypeError):
            int_id = id_val
        if int_id in t_data:
            del t_data[int_id]
            return True
        return False

    def count(self, table_name: str, filters: dict = None) -> int:
        return len(self.list(table_name, filters=filters))


e2e_db = E2EStore()


class MockE2EConnection:
    def __init__(self):
        self.is_closed = False

    def cursor(self, cursor_factory=None):
        return MockE2ECursor()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.is_closed = True


class MockE2ECursor:
    def __init__(self):
        self._res = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, sql, params=None):
        sql_str = str(sql).lower()
        if 'nextval' in sql_str:
            self._res = (101,)
        elif 'last_value' in sql_str:
            self._res = (100,)
        else:
            self._res = None

    def fetchone(self):
        return self._res

    def fetchall(self):
        return [self._res] if self._res else []


TEST_USER = {
    'id': 1,
    'username': 'admin_accountant',
    'role': 'Admin',
    'permissions': ['*'],
    'business_id': 1,
}


@pytest.fixture(autouse=True)
def setup_dynamic_payment_terms_e2e_env():
    """Setup in-memory environment, seed standard payment terms, and patch CrudRepository."""
    e2e_db.reset()

    # Seed Standard Payment Terms (T0096)
    e2e_db.create('T0096', {
        'id': 1,
        'name': 'Net 30',
        'code': 'NET_30',
        'description': 'Payment due within 30 days',
        'due_days': 30,
        'discount_days': 0,
        'discount_percentage': 0.0,
        'is_active': True,
        'is_default': True,
    })
    e2e_db.create('T0096', {
        'id': 2,
        'name': 'Cash on Delivery (COD)',
        'code': 'COD',
        'description': 'Payment due upon delivery',
        'due_days': 0,
        'discount_days': 0,
        'discount_percentage': 0.0,
        'is_active': True,
        'is_default': False,
    })
    e2e_db.create('T0096', {
        'id': 3,
        'name': 'Net 15',
        'code': 'NET_15',
        'description': 'Payment due within 15 days',
        'due_days': 15,
        'discount_days': 0,
        'discount_percentage': 0.0,
        'is_active': True,
        'is_default': False,
    })
    e2e_db.create('T0096', {
        'id': 4,
        'name': 'Net 60',
        'code': 'NET_60',
        'description': 'Payment due within 60 days',
        'due_days': 60,
        'discount_days': 0,
        'discount_percentage': 0.0,
        'is_active': True,
        'is_default': False,
    })
    e2e_db.create('T0096', {
        'id': 5,
        'name': '2/10 Net 30',
        'code': '2_10_NET_30',
        'description': '2% discount if paid within 10 days, net due in 30 days',
        'due_days': 30,
        'discount_days': 10,
        'discount_percentage': 2.0,
        'is_active': True,
        'is_default': False,
    })
    e2e_db.create('T0096', {
        'id': 6,
        'name': '3/15 Net 45',
        'code': '3_15_NET_45',
        'description': '3% discount if paid within 15 days, net due in 45 days',
        'due_days': 45,
        'discount_days': 15,
        'discount_percentage': 3.0,
        'is_active': True,
        'is_default': False,
    })

    # Seed Base Product (T0003), Warehouse (T0008), and Stock (T0009)
    e2e_db.create('T0008', {'id': 1, 'name': 'Main Warehouse', 'location': 'HQ', 'is_active': True})
    e2e_db.create('T0003', {
        'id': 1,
        'name': 'Organic Olive Oil Extra Virgin',
        'sku': 'OIL-EVOO-5L',
        'price': 100.0,
        'is_active': True,
    })
    e2e_db.create('T0009', {
        'id': 1,
        'product_id': 1,
        'warehouse_id': 1,
        'qty': 500.0,
        'reserved_qty': 0.0,
    })

    mock_conn = MockE2EConnection()

    def mock_get_conn():
        return mock_conn

    def mock_rel_conn(c):
        pass

    def repo_create(self, payload: dict, conn=None, *args, **kwargs):
        return e2e_db.create(self.qualified, payload, pk=self.pk)

    def repo_get(self, id_val, conn=None, *args, **kwargs):
        return e2e_db.get(self.qualified, id_val, pk=self.pk)

    def repo_update(self, id_val, payload: dict, conn=None, *args, **kwargs):
        return e2e_db.update(self.qualified, id_val, payload, pk=self.pk)

    def repo_list(self, filters=None, order_by=None, limit=None, offset=None, conn=None, *args, **kwargs):
        return e2e_db.list(self.qualified, filters=filters, order_by=order_by, limit=limit, offset=offset)

    def repo_delete(self, id_val, conn=None, *args, **kwargs):
        return e2e_db.delete(self.qualified, id_val, pk=self.pk)

    def repo_count(self, filters=None, conn=None, *args, **kwargs):
        return e2e_db.count(self.qualified, filters=filters)

    with patch('packages.database.connection.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.connection.release_connection', side_effect=mock_rel_conn), \
         patch('modules.sales.services.sales_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.sales.services.sales_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.core.repositories.base.get_connection', side_effect=mock_get_conn), \
         patch('modules.core.repositories.base.release_connection', side_effect=mock_rel_conn), \
         patch('packages.database.sequence.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.sequence.release_connection', side_effect=mock_rel_conn), \
         patch.object(CrudRepository, 'create', repo_create), \
         patch.object(CrudRepository, 'get', repo_get), \
         patch.object(CrudRepository, 'get_for_update', repo_get), \
         patch.object(CrudRepository, 'update', repo_update), \
         patch.object(CrudRepository, 'list', repo_list), \
         patch.object(CrudRepository, 'delete', repo_delete), \
         patch.object(CrudRepository, 'count', repo_count):
        yield


def create_e2e_api_client():
    """Create FastAPI test client with payment terms, customer, sales, invoice, and payment routers."""
    app = FastAPI(title="Nova Dynamic Payment Terms E2E Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.include_router(payment_term_router)
    app.include_router(customer_router)
    app.include_router(sales_router)
    app.include_router(invoice_router)
    app.include_router(payment_router)
    return TestClient(app)


# ============================================================================
# End-to-End Workflow Verification Test Cases
# ============================================================================

class TestDynamicPaymentTermsE2ELifecycle:
    """
    Comprehensive End-to-End Integration Verification:
    Customer Term Assignment -> Sales Order Creation -> Delivery Completion ->
    Dynamic Invoice Due Date & Discount Cutoff -> AR Aging Bucket Classification ->
    Early Payment Discount Preview -> Payment Settlement & Customer Balance Clearing.
    """

    def test_e2e_happy_path_2_10_net_30_early_discount_and_aging_lifecycle(self):
        """
        Scenario 1: Complete end-to-end early payment discount lifecycle:
        1. Create customer linked to '2/10 Net 30' (term 5). Initial balance = 0.0.
        2. Verify initial AR aging report has 0.0 outstanding.
        3. Create Sales Order for $2,000.00 without explicit term -> inherits '2/10 Net 30'.
        4. Confirm & deliver order on 2026-08-01.
        5. Automatically generates invoice:
           - issue_date: 2026-08-01
           - due_date: 2026-08-31 (30 days)
           - discount_due_date: 2026-08-11 (10 days)
           - discount_percentage: 2.0%
           - early_discount_amount: $40.00 (2% of $2,000.00)
           - status: 'Unpaid'
        6. Customer balance updated to $2,000.00.
        7. AR aging on 2026-08-05 shows $2,000.00 in 'current' bucket.
        8. AR aging on 2026-09-15 (if unpaid) shows $2,000.00 in '1_30' overdue bucket.
        9. Preview early discount on 2026-08-08 (before cutoff 2026-08-11) -> eligible, $40 discount, $1960 net due.
        10. Post payment of $1,960.00 on 2026-08-08 -> honors $40 discount, marks invoice 'Paid', clears customer balance to 0.0.
        11. AR aging on 2026-09-15 after payment shows $0.00 outstanding, $2000 total paid.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        inv_repo = CrudRepository('T0090')
        pay_repo = CrudRepository('T0091')
        term_repo = CrudRepository('T0096')

        sales_svc = SalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            payment_term_repo=term_repo,
        )
        aging_svc = AgingService(customer_repo=cust_repo, invoice_repo=inv_repo)
        pay_svc = PaymentService(
            repo=pay_repo,
            invoice_repo=inv_repo,
            customer_repo=cust_repo,
            payment_term_repo=term_repo,
        )

        # 1. Setup Customer with 2/10 Net 30 payment term
        customer = cust_repo.create({
            'id': 101,
            'name': 'Gourmet Bistro Inc',
            'credit_limit': 20000.0,
            'balance': 0.0,
            'payment_term_id': 5,  # 2/10 Net 30
            'is_active': True,
        })
        assert customer['id'] == 101
        assert customer['payment_term_id'] == 5
        assert customer['balance'] == 0.0

        # 2. Verify initial AR aging is clean
        init_aging = aging_svc.get_customer_aging(101, as_of_date='2026-08-01')
        assert init_aging['balance'] == 0.0
        assert init_aging['aging']['current'] == 0.0
        assert init_aging['aging']['1_30'] == 0.0
        assert init_aging['aging']['total_outstanding'] == 0.0

        # 3. Create Sales Order without explicit payment_term_id -> inherits customer's 2/10 Net 30
        order = sales_svc.create({
            'id': 501,
            'order_number': 'SO-E2E-201',
            'customer_id': 101,
            'warehouse_id': 1,
            'status': 'Pending',
            'subtotal': 2000.0,
            'tax': 0.0,
            'grand_total': 2000.0,
            'order_date': date(2026, 8, 1),
        })
        assert order['payment_term_id'] == 5  # Inherited from customer

        # 4. Confirm & deliver order on 2026-08-01
        sales_svc.update(501, {'status': 'Confirmed'})
        order_repo.update(501, {'status': 'Shipped'})

        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-E2E-201'):
            sales_svc.update(501, {'status': 'Delivered'})

        # 5. Verify Invoice generated with dynamic due date & discount metadata
        invoices = inv_repo.list(filters={'sales_order_id': 501})
        assert len(invoices) == 1
        inv = invoices[0]
        inv_id = inv['id']

        assert inv['invoice_number'] == 'INV-E2E-201'
        assert inv['partner_id'] == 101
        assert inv['payment_term_id'] == 5
        assert inv['issue_date'] == date(2026, 8, 1)
        assert inv['due_date'] == date(2026, 8, 31)  # 2026-08-01 + 30 days
        assert inv['discount_due_date'] == date(2026, 8, 11)  # 2026-08-01 + 10 days
        assert inv['discount_percentage'] == 2.0
        assert inv['discount_days'] == 10
        assert inv['early_discount_amount'] == 40.0  # 2% of $2,000.00
        assert inv['total_amount'] == 2000.0
        assert inv['discount_amount'] == 0.0
        assert inv['status'] == 'Unpaid'

        # 6. Customer balance updated
        updated_cust = cust_repo.get(101)
        assert updated_cust['balance'] == 2000.0

        # 7. AR Aging on 2026-08-05 (before due date) -> 'current' bucket
        aging_current = aging_svc.get_customer_aging(101, as_of_date='2026-08-05')
        assert aging_current['balance'] == 2000.0
        assert aging_current['aging']['current'] == 2000.0
        assert aging_current['aging']['1_30'] == 0.0
        assert aging_current['aging']['total_outstanding'] == 2000.0
        assert aging_current['open_invoices_count'] == 1

        # 8. AR Aging on 2026-09-15 (15 days past 2026-08-31 due date) -> '1_30' bucket
        aging_overdue = aging_svc.get_customer_aging(101, as_of_date='2026-09-15')
        assert aging_overdue['aging']['current'] == 0.0
        assert aging_overdue['aging']['1_30'] == 2000.0
        assert aging_overdue['aging']['total_outstanding'] == 2000.0

        # 9. Evaluate Early Payment Discount preview on 2026-08-08 (3 days before Aug 11 cutoff)
        preview = pay_svc.evaluate_early_discount(
            invoice_id=inv_id,
            payment_date=date(2026, 8, 8),
        )
        assert preview['is_eligible'] is True
        assert preview['discount_percentage'] == 2.0
        assert preview['discount_amount'] == 40.0
        assert preview['net_amount_due'] == 1960.0
        assert preview['discount_due_date'] == date(2026, 8, 11)

        # 10. Record payment of net amount $1,960.00 on 2026-08-08
        settlement = pay_svc.settle_invoice_payment({
            'invoice_id': inv_id,
            'partner_id': 101,
            'amount': 1960.0,
            'payment_date': date(2026, 8, 8),
            'payment_method': 'Bank Transfer',
            'status': 'Completed',
        })

        assert settlement['payment']['amount'] == 1960.0
        assert "Early payment discount applied: $40.00" in settlement['payment']['notes']

        # Verify Invoice status and discount amount updated
        settled_inv = inv_repo.get(inv_id)
        assert settled_inv['discount_amount'] == 40.0
        assert settled_inv['status'] == 'Paid'

        # Verify Customer balance fully cleared ($2,000 credit = $1,960 cash + $40 discount)
        assert cust_repo.get(101)['balance'] == 0.0

        # 11. AR Aging as of 2026-09-15 after payment
        post_pay_aging = aging_svc.get_customer_aging(101, as_of_date='2026-09-15')
        assert post_pay_aging['balance'] == 0.0
        assert post_pay_aging['aging']['current'] == 0.0
        assert post_pay_aging['aging']['1_30'] == 0.0
        assert post_pay_aging['aging']['total_outstanding'] == 0.0
        assert post_pay_aging['aging']['total_paid'] == 2000.0
        assert post_pay_aging['open_invoices_count'] == 0
        assert post_pay_aging['paid_invoices_count'] == 1

    def test_e2e_late_payment_cutoff_enforcement_and_overdue_aging_progression(self):
        """
        Scenario 2: Verify discount cutoff enforcement and aging progression across all 5 buckets:
        1. Customer with '3/15 Net 45' (term 6).
        2. Order delivered on 2026-06-01 for $5,000.00.
        3. Invoice: issue_date=2026-06-01, due_date=2026-07-16 (45 days), discount_due_date=2026-06-16 (15 days), early_discount_amount=$150.00.
        4. Discount preview on 2026-06-25 (past cutoff) -> is_eligible=False, discount=0.0, net_amount_due=$5,000.00.
        5. Verify AR aging shifts across all 5 buckets over time:
           - 2026-07-01: 'current' ($5,000.00)
           - 2026-07-26: '1_30' ($5,000.00) - 10 days overdue
           - 2026-08-26: '31_60' ($5,000.00) - 41 days overdue
           - 2026-09-26: '61_90' ($5,000.00) - 72 days overdue
           - 2026-10-26: '90_plus' ($5,000.00) - 102 days overdue
        6. Full payment of $5,000.00 made on 2026-10-30 -> no discount, marks Paid, clears aging to 0.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        inv_repo = CrudRepository('T0090')
        pay_repo = CrudRepository('T0091')
        term_repo = CrudRepository('T0096')

        sales_svc = SalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            payment_term_repo=term_repo,
        )
        aging_svc = AgingService(customer_repo=cust_repo, invoice_repo=inv_repo)
        pay_svc = PaymentService(
            repo=pay_repo,
            invoice_repo=inv_repo,
            customer_repo=cust_repo,
            payment_term_repo=term_repo,
        )

        # 1. Customer setup
        cust_repo.create({
            'id': 102,
            'name': 'Long Term Wholesale LLC',
            'credit_limit': 50000.0,
            'balance': 0.0,
            'payment_term_id': 6,  # 3/15 Net 45
        })

        # 2. Create and deliver order
        order = sales_svc.create({
            'id': 502,
            'order_number': 'SO-E2E-202',
            'customer_id': 102,
            'warehouse_id': 1,
            'status': 'Pending',
            'subtotal': 5000.0,
            'tax': 0.0,
            'grand_total': 5000.0,
            'order_date': date(2026, 6, 1),
        })
        sales_svc.update(502, {'status': 'Confirmed'})
        order_repo.update(502, {'status': 'Shipped'})

        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-E2E-202'):
            sales_svc.update(502, {'status': 'Delivered'})

        inv = inv_repo.list(filters={'sales_order_id': 502})[0]
        inv_id = inv['id']

        # 3. Verify Invoice dates
        assert inv['issue_date'] == date(2026, 6, 1)
        assert inv['due_date'] == date(2026, 7, 16)  # 2026-06-01 + 45 days (June has 30 days)
        assert inv['discount_due_date'] == date(2026, 6, 16)  # 2026-06-01 + 15 days
        assert inv['discount_percentage'] == 3.0
        assert inv['early_discount_amount'] == 150.0

        # 4. Preview discount after cutoff (June 25) -> Ineligible
        late_preview = pay_svc.evaluate_early_discount(
            invoice_id=inv_id,
            payment_date=date(2026, 6, 25),
        )
        assert late_preview['is_eligible'] is False
        assert late_preview['discount_amount'] == 0.0
        assert late_preview['net_amount_due'] == 5000.0
        assert "past the early discount cutoff" in late_preview['message']

        # 5. Aging progression test across all 5 buckets
        # Bucket 1: Current (as of 2026-07-01, 15 days before due date 2026-07-16)
        aging_cur = aging_svc.get_customer_aging(102, as_of_date='2026-07-01')
        assert aging_cur['aging']['current'] == 5000.0
        assert aging_cur['aging']['1_30'] == 0.0

        # Bucket 2: 1-30 days overdue (as of 2026-07-26, 10 days overdue)
        aging_1_30 = aging_svc.get_customer_aging(102, as_of_date='2026-07-26')
        assert aging_1_30['aging']['current'] == 0.0
        assert aging_1_30['aging']['1_30'] == 5000.0
        assert aging_1_30['aging']['31_60'] == 0.0

        # Bucket 3: 31-60 days overdue (as of 2026-08-26, 41 days overdue)
        aging_31_60 = aging_svc.get_customer_aging(102, as_of_date='2026-08-26')
        assert aging_31_60['aging']['31_60'] == 5000.0
        assert aging_31_60['aging']['1_30'] == 0.0

        # Bucket 4: 61-90 days overdue (as of 2026-09-26, 72 days overdue)
        aging_61_90 = aging_svc.get_customer_aging(102, as_of_date='2026-09-26')
        assert aging_61_90['aging']['61_90'] == 5000.0
        assert aging_61_90['aging']['31_60'] == 0.0

        # Bucket 5: 90+ days overdue (as of 2026-10-26, 102 days overdue)
        aging_90_plus = aging_svc.get_customer_aging(102, as_of_date='2026-10-26')
        assert aging_90_plus['aging']['90_plus'] == 5000.0
        assert aging_90_plus['aging']['61_90'] == 0.0

        # 6. Settle full payment of $5,000.00 on 2026-10-30
        settlement = pay_svc.settle_invoice_payment({
            'invoice_id': inv_id,
            'partner_id': 102,
            'amount': 5000.0,
            'payment_date': date(2026, 10, 30),
            'payment_method': 'Wire',
            'status': 'Completed',
        })
        assert "Early payment discount applied" not in (settlement['payment'].get('notes') or '')
        assert settlement['invoice']['status'] == 'Paid'
        assert settlement['invoice']['discount_amount'] == 0.0
        assert settlement['customer']['balance'] == 0.0

        # Verify aging report is now 0 across all buckets
        clean_aging = aging_svc.get_customer_aging(102, as_of_date='2026-10-31')
        assert clean_aging['aging']['total_outstanding'] == 0.0
        assert clean_aging['aging']['90_plus'] == 0.0
        assert clean_aging['aging']['total_paid'] == 5000.0

    def test_e2e_cod_net15_net60_and_term_override_flows(self):
        """
        Scenario 3: Verify multiple orders with COD, Net 15, Net 60, and explicit overrides:
        - Customer A has Net 15. Order 1 uses Net 15 (+15 days).
        - Order 2 for Customer A explicitly overrides to COD (due_days=0 -> same day).
        - Order 3 for Customer A explicitly overrides to Net 60 (+60 days).
        - Customer B has no assigned term -> falls back to system default Net 30 (+30 days).
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        inv_repo = CrudRepository('T0090')
        term_repo = CrudRepository('T0096')

        sales_svc = SalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            payment_term_repo=term_repo,
        )

        # Customer A (Net 15)
        cust_a = cust_repo.create({
            'id': 201,
            'name': 'Retailer Alpha',
            'balance': 0.0,
            'payment_term_id': 3,  # Net 15
        })

        # Customer B (No term assigned)
        cust_b = cust_repo.create({
            'id': 202,
            'name': 'Retailer Beta (No Term)',
            'balance': 0.0,
            'payment_term_id': None,
        })

        # Order 1: Inherits Net 15
        o1 = sales_svc.create({
            'id': 601,
            'order_number': 'SO-O1',
            'customer_id': 201,
            'subtotal': 300.0,
            'grand_total': 300.0,
            'order_date': date(2026, 8, 10),
            'status': 'Pending',
        })
        assert o1['payment_term_id'] == 3

        # Order 2: Overrides to COD (term 2)
        o2 = sales_svc.create({
            'id': 602,
            'order_number': 'SO-O2',
            'customer_id': 201,
            'payment_term_id': 2,  # COD
            'subtotal': 400.0,
            'grand_total': 400.0,
            'order_date': date(2026, 8, 10),
            'status': 'Pending',
        })
        assert o2['payment_term_id'] == 2

        # Order 3: Overrides to Net 60 (term 4)
        o3 = sales_svc.create({
            'id': 603,
            'order_number': 'SO-O3',
            'customer_id': 201,
            'payment_term_id': 4,  # Net 60
            'subtotal': 500.0,
            'grand_total': 500.0,
            'order_date': date(2026, 8, 10),
            'status': 'Pending',
        })
        assert o3['payment_term_id'] == 4

        # Order 4: Customer B with no term -> falls back to default Net 30 (term 1)
        o4 = sales_svc.create({
            'id': 604,
            'order_number': 'SO-O4',
            'customer_id': 202,
            'subtotal': 600.0,
            'grand_total': 600.0,
            'order_date': date(2026, 8, 10),
            'status': 'Pending',
        })
        assert o4['payment_term_id'] == 1  # Default Net 30

        # Deliver all 4 orders
        for o_id in (601, 602, 603, 604):
            sales_svc.update(o_id, {'status': 'Confirmed'})
            order_repo.update(o_id, {'status': 'Shipped'})
            with patch('modules.sales.services.sales_service.generate_invoice_number', return_value=f'INV-{o_id}'):
                sales_svc.update(o_id, {'status': 'Delivered'})

        # Verify generated invoices
        inv1 = inv_repo.list(filters={'sales_order_id': 601})[0]
        assert inv1['payment_term_id'] == 3
        assert inv1['due_date'] == date(2026, 8, 25)  # 2026-08-10 + 15 days

        inv2 = inv_repo.list(filters={'sales_order_id': 602})[0]
        assert inv2['payment_term_id'] == 2
        assert inv2['due_date'] == date(2026, 8, 10)  # COD same day

        inv3 = inv_repo.list(filters={'sales_order_id': 603})[0]
        assert inv3['payment_term_id'] == 4
        assert inv3['due_date'] == date(2026, 10, 9)  # 2026-08-10 + 60 days

        inv4 = inv_repo.list(filters={'sales_order_id': 604})[0]
        assert inv4['payment_term_id'] == 1
        assert inv4['due_date'] == date(2026, 9, 9)  # 2026-08-10 + 30 days

    def test_e2e_http_rest_api_full_workflow(self):
        """
        Scenario 4: Complete end-to-end verification through HTTP REST API endpoints using TestClient:
        - GET /api/T0096I/standard-terms (Inspect available payment terms)
        - POST /api/T0010I (Create customer with payment_term_id=5 for 2/10 Net 30)
        - POST /api/T0012I/with-lines (Create sales order inheriting payment term)
        - POST /api/T0012I/{id}/confirm
        - POST /api/T0012I/{id}/deliver (Triggers invoice creation with dynamic due date & discount metadata)
        - GET /api/T0090I/{invoice_id} (Verify invoice due_date and discount fields)
        - GET /api/T0091I/invoice/{invoice_id}/discount-preview (Verify early discount preview endpoint)
        - POST /api/T0091I (Post payment honoring early discount)
        - GET /api/T0010I/{customer_id}/aging (Verify updated customer aging report)
        - GET /api/T0010I/reports/aging (Verify aggregate aging report across all customers)
        """
        client = create_e2e_api_client()

        # 1. Inspect standard payment terms via REST API
        terms_resp = client.get('/api/T0096I/standard-terms')
        assert terms_resp.status_code == 200
        terms_list = terms_resp.json()
        assert any(t['code'] == '2_10_NET_30' for t in terms_list)

        # 2. Create customer with payment_term_id = 5 (2/10 Net 30)
        cust_resp = client.post('/api/T0010I', json={
            'name': 'Artisan Fine Foods',
            'credit_limit': 15000.0,
            'balance': 0.0,
            'payment_term_id': 5,  # 2/10 Net 30
            'is_active': True,
        })
        assert cust_resp.status_code == 201
        customer = cust_resp.json()
        cust_id = customer['id']
        assert customer['payment_term_id'] == 5

        # 3. Create sales order with lines via REST endpoint
        so_resp = client.post('/api/T0012I/with-lines', json={
            'order': {
                'order_number': 'SO-REST-E2E-01',
                'customer_id': cust_id,
                'warehouse_id': 1,
                'status': 'Pending',
                'order_date': '2026-08-01',
            },
            'lines': [
                {
                    'product_id': 1,
                    'product_name': 'Organic Olive Oil Extra Virgin',
                    'qty': 10.0,
                    'unit_price': 100.0,
                    'line_total': 1000.0,
                    'line_number': 1,
                }
            ],
        })
        assert so_resp.status_code == 201
        order = so_resp.json()
        order_id = order['id']
        assert order['payment_term_id'] == 5
        assert order['grand_total'] == 1000.0

        # 4. Confirm sales order
        conf_resp = client.post(f'/api/T0012I/{order_id}/confirm')
        assert conf_resp.status_code == 200
        assert conf_resp.json()['status'] == 'Confirmed'

        # Set order to Shipped in DB store before delivery
        e2e_db.update('T0012', order_id, {'status': 'Shipped'})

        # 5. Deliver sales order
        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-REST-E2E-01'):
            deliv_resp = client.post(f'/api/T0012I/{order_id}/deliver')
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()['status'] == 'Delivered'

        # 6. Fetch generated invoice via REST endpoint
        inv_repo = CrudRepository('T0090')
        invoice_id = inv_repo.list(filters={'sales_order_id': order_id})[0]['id']

        inv_resp = client.get(f'/api/T0090I/{invoice_id}')
        assert inv_resp.status_code == 200
        inv_data = inv_resp.json()

        assert inv_data['invoice_number'] == 'INV-REST-E2E-01'
        assert inv_data['partner_id'] == cust_id
        assert inv_data['payment_term_id'] == 5
        assert inv_data['issue_date'] == '2026-08-01'
        assert inv_data['due_date'] == '2026-08-31'
        assert inv_data['discount_due_date'] == '2026-08-11'
        assert inv_data['discount_percentage'] == 2.0
        assert inv_data['discount_days'] == 10
        assert inv_data['early_discount_amount'] == 20.0  # 2% of $1,000.00
        assert inv_data['total_amount'] == 1000.0
        assert inv_data['status'] == 'Unpaid'

        # 7. Preview early discount via REST endpoint
        prev_resp = client.get(f'/api/T0091I/invoice/{invoice_id}/discount-preview?payment_date=2026-08-05')
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()

        assert prev_data['is_eligible'] is True
        assert prev_data['discount_percentage'] == 2.0
        assert prev_data['discount_amount'] == 20.0
        assert prev_data['net_amount_due'] == 980.0
        assert prev_data['discount_due_date'] == '2026-08-11'

        # 8. Post payment of net amount $980.00 via REST endpoint
        pay_resp = client.post('/api/T0091I', json={
            'invoice_id': invoice_id,
            'partner_id': cust_id,
            'amount': 980.0,
            'payment_date': '2026-08-05',
            'payment_method': 'Credit Card',
            'status': 'Completed',
        })
        assert pay_resp.status_code == 201
        pay_data = pay_resp.json()
        assert pay_data['amount'] == 980.0
        assert "Early payment discount applied: $20.00" in pay_data['notes']

        # Verify Invoice status is now Paid
        inv_check_resp = client.get(f'/api/T0090I/{invoice_id}')
        assert inv_check_resp.json()['status'] == 'Paid'
        assert inv_check_resp.json()['discount_amount'] == 20.0

        # 9. Check Customer Aging endpoint
        aging_resp = client.get(f'/api/T0010I/{cust_id}/aging?as_of_date=2026-08-25')
        assert aging_resp.status_code == 200
        aging_data = aging_resp.json()

        assert aging_data['customer_id'] == cust_id
        assert aging_data['balance'] == 0.0
        assert aging_data['aging']['total_outstanding'] == 0.0
        assert aging_data['aging']['current'] == 0.0
        assert aging_data['aging']['1_30'] == 0.0
        assert aging_data['aging']['total_paid'] == 1000.0

        # 10. Check All Customers Aging Report endpoint
        rep_resp = client.get('/api/T0010I/reports/aging?as_of_date=2026-08-25')
        assert rep_resp.status_code == 200
        rep_data = rep_resp.json()
        assert 'total_aging' in rep_data
        assert rep_data['total_aging']['total_outstanding'] == 0.0

    def test_e2e_mcp_servers_tool_calling_workflow(self):
        """
        Scenario 5: Verify AI Agent MCP tool calling end-to-end:
        - accounting_mcp._list_terms() (List available terms)
        - accounting_mcp._get_payment_term() (Lookup specific term)
        - sales_mcp._list_customers()
        - sales_mcp._create_order()
        - accounting_mcp._preview_invoice_early_discount()
        - accounting_mcp._list_invoices()
        - sales_mcp._get_customer_aging()
        """
        # Step 1: Query terms via accounting_mcp
        terms = accounting_mcp._list_terms(is_active=True)
        assert len(terms) >= 5
        term_map = {t['code']: t for t in terms}
        assert '2_10_NET_30' in term_map
        assert term_map['2_10_NET_30']['discount_percentage'] == 2.0

        # Step 2: Get single term
        single_term = accounting_mcp._get_payment_term(code='2_10_NET_30')
        assert single_term['name'] == '2/10 Net 30'
        assert single_term['due_days'] == 30

        # Step 3: Setup customer and create sales order via sales_mcp
        cust_repo = CrudRepository('T0010')
        cust = cust_repo.create({
            'id': 301,
            'name': 'AI Assisted Partner',
            'credit_limit': 10000.0,
            'balance': 0.0,
            'payment_term_id': 5,  # 2/10 Net 30
        })

        order = sales_mcp._create_order(
            customer_id=301,
            warehouse_id=1,
            grand_total=1500.0,
            order_number='SO-MCP-E2E-01',
            order_date='2026-08-01',
        )
        assert order['id'] is not None
        assert order['payment_term_id'] == 5

        # Deliver order
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        inv_repo = CrudRepository('T0090')
        term_repo = CrudRepository('T0096')

        sales_svc = SalesOrderService(
            repo=order_repo,
            line_repo=line_repo,
            customer_repo=cust_repo,
            inv_repo=inv_repo,
            payment_term_repo=term_repo,
        )
        sales_svc.update(order['id'], {'status': 'Confirmed'})
        order_repo.update(order['id'], {'status': 'Shipped'})

        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-MCP-E2E-01'):
            sales_svc.update(order['id'], {'status': 'Delivered'})

        invoices = accounting_mcp._list_invoices(partner_id=301)
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv['invoice_number'] == 'INV-MCP-E2E-01'
        assert inv['due_date'] == date(2026, 8, 31)
        assert inv['discount_due_date'] == date(2026, 8, 11)
        assert inv['early_discount_amount'] == 30.0  # 2% of $1,500.00

        # Step 4: Preview early discount via accounting_mcp tool handler
        disc_preview = accounting_mcp._preview_invoice_early_discount(
            invoice_id=inv['id'],
            payment_date='2026-08-05',
        )
        assert disc_preview['is_eligible'] is True
        assert disc_preview['discount_amount'] == 30.0
        assert disc_preview['net_amount_due'] == 1470.0

        # Step 5: Query customer aging via sales_mcp tool handler
        aging = sales_mcp._get_customer_aging(id=301, as_of_date='2026-08-10')
        assert aging['customer_id'] == 301
        assert aging['customer_name'] == 'AI Assisted Partner'
        assert aging['aging']['current'] == 1500.0
        assert aging['aging']['total_outstanding'] == 1500.0
