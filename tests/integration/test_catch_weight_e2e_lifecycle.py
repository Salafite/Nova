import re
import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient

from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService

from modules.inventory.controllers.T0003I import router as product_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from modules.accounting.controllers.T0090I import router as invoice_router

from packages.auth.deps import get_current_user
import packages.mcp.servers.inventory_mcp as inv_mcp
import packages.mcp.servers.sales_mcp as sales_mcp
import packages.mcp.servers.warehouse_mcp as wh_mcp


# ============================================================================
# In-Memory Deterministic Storage for End-to-End Lifecycle Verification
# ============================================================================

class E2ETableStore:
    """In-memory multi-table database store for end-to-end integration tests."""
    def __init__(self):
        self.tables = {}
        self.counters = {}

    def reset(self):
        self.tables.clear()
        self.counters.clear()

    def _normalize(self, table_name: str) -> str:
        tbl = table_name.lower().replace('"', '')
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
            rec_id = explicit_id
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
        rec = t_data.get(id_val)
        return dict(rec) if rec else None

    def update(self, table_name: str, id_val, payload: dict, pk: str = 'id') -> dict:
        tbl = self._normalize(table_name)
        t_data = self._get_table(tbl)
        if id_val not in t_data:
            return None
        t_data[id_val].update(payload)
        return dict(t_data[id_val])

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
        if id_val in t_data:
            del t_data[id_val]
            return True
        return False

    def count(self, table_name: str, filters: dict = None) -> int:
        return len(self.list(table_name, filters=filters))


e2e_store = E2ETableStore()


class MockE2EConnection:
    """Mock connection satisfying database transaction calls."""
    def __init__(self):
        self.is_closed = False
        self._is_mock = True

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


TEST_ADMIN = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}


@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """Setup in-memory repositories and mock environment before every test."""
    e2e_store.reset()

    # Pre-seed base UOMs, Warehouse, and Customer
    e2e_store.create('T0001', {'id': 1, 'uom_code': 'CASE', 'uom_name': 'Case / Box', 'is_active': True})
    e2e_store.create('T0001', {'id': 2, 'uom_code': 'kg', 'uom_name': 'Kilogram', 'is_active': True})
    e2e_store.create('T0001', {'id': 3, 'uom_code': 'EA', 'uom_name': 'Each', 'is_active': True})

    e2e_store.create('T0008', {'id': 1, 'name': 'Central Cold Storage', 'location': 'Building A', 'is_active': True})
    e2e_store.create('T0010', {'id': 100, 'name': 'Artisan Fromagerie Ltd', 'credit_limit': 50000.0, 'balance': 1000.0})

    mock_conn = MockE2EConnection()

    def mock_get_conn():
        return mock_conn

    def mock_rel_conn(c):
        pass

    def repo_create(self, payload: dict, conn=None):
        return e2e_store.create(self.qualified, payload, pk=self.pk)

    def repo_get(self, id_val, conn=None):
        return e2e_store.get(self.qualified, id_val, pk=self.pk)

    def repo_update(self, id_val, payload: dict, conn=None):
        return e2e_store.update(self.qualified, id_val, payload, pk=self.pk)

    def repo_list(self, filters=None, order_by=None, limit=None, offset=None, conn=None):
        return e2e_store.list(self.qualified, filters=filters, order_by=order_by, limit=limit, offset=offset)

    def repo_delete(self, id_val, conn=None):
        return e2e_store.delete(self.qualified, id_val, pk=self.pk)

    def repo_count(self, filters=None, conn=None):
        return e2e_store.count(self.qualified, filters=filters)

    with patch('packages.database.connection.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.connection.release_connection', side_effect=mock_rel_conn), \
         patch('modules.sales.services.sales_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.sales.services.sales_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.sales.services.enhanced_sales_order_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.sales.services.enhanced_sales_order_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.warehouse.services.pick_list_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.warehouse.services.pick_list_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.core.repositories.base.get_connection', side_effect=mock_get_conn), \
         patch('modules.core.repositories.base.release_connection', side_effect=mock_rel_conn), \
         patch('packages.database.sequence.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.sequence.release_connection', side_effect=mock_rel_conn), \
         patch.object(CrudRepository, 'create', repo_create), \
         patch.object(CrudRepository, 'get', repo_get), \
         patch.object(CrudRepository, 'update', repo_update), \
         patch.object(CrudRepository, 'list', repo_list), \
         patch.object(CrudRepository, 'delete', repo_delete), \
         patch.object(CrudRepository, 'count', repo_count):
        yield


def create_e2e_api_client():
    """Create FastAPI test client with all catch-weight routers wired."""
    app = FastAPI(title="Nova Catch-Weight E2E Test Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(invoice_router)
    return TestClient(app)


# ============================================================================
# End-to-End Workflow Verification Test Cases
# ============================================================================

class TestCatchWeightE2ELifecycle:
    """
    Comprehensive End-to-End Lifecycle Verification:
    Covers Product Setup -> Sales Order -> Confirmation -> Pick List Generation ->
    Scale Weight Capture -> Tolerance Check -> Supervisor Approval (if discrepancy) ->
    Pick List Completion -> Order Recalculation & Delivery -> Invoice Generation & Customer Balance.
    """

    def test_e2e_happy_path_within_tolerance_lifecycle(self):
        """
        Complete end-to-end happy path where weighed catch-weight items fall within allowed tolerance:
        - Setup dual UOM product (Parmigiano Wheel, nominal 40kg/case, +/- 5% tolerance, $15/kg).
        - Place order for 2 cases (nominal 80kg, initial subtotal $1,200.00, 5% tax = $60, total = $1,260.00).
        - Confirm order -> Generates pick list with dual UOM parameters.
        - Picker weighs 78.4kg on scale (-2.0% variance within 5% tolerance).
        - Pick list marked Within Tolerance, picking completed successfully.
        - Order delivered -> Automatically recalculates final billing:
          78.4kg * $15/kg = $1,176.00 subtotal (-$24.00 adjustment), tax = $58.80, grand total = $1,234.80.
        - Invoice created with exact catch-weight metadata and customer balance incremented.
        """
        product_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')
        cust_repo = CrudRepository('T0010')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # 1. Master Data Setup: Dual UOM Product
        cheese = product_repo.create({
            'id': 1,
            'name': 'Parmigiano Reggiano 24M Wheel',
            'sku': 'CHEESE-PARM-40KG',
            'price': 600.0,  # $600/case nominal
            'is_catch_weight': True,
            'pricing_uom_id': 2,  # kg
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        assert cheese['is_catch_weight'] is True
        assert cheese['nominal_weight'] == 40.0
        assert cheese['tolerance_pct'] == 5.0

        # Seed initial stock
        stock_repo = CrudRepository('T0009')
        stock_repo.create({'id': 1, 'product_id': 1, 'warehouse_id': 1, 'qty': 100, 'reserved_qty': 0})

        # 2. Create Sales Order with Dual UOM Line
        order = order_repo.create({
            'id': 501,
            'order_number': 'SO-E2E-001',
            'customer_id': 100,
            'warehouse_id': 1,
            'status': 'Draft',
            'subtotal': 1200.0,
            'tax': 60.0,
            'grand_total': 1260.0,
            'order_date': '2026-08-24',
        })
        line = line_repo.create({
            'id': 1001,
            'sales_order_id': 501,
            'product_id': 1,
            'product_name': 'Parmigiano Reggiano 24M Wheel',
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
        })

        # 3. Confirm Order -> Generates Pick List
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-E2E-001'):
            sales_svc.update(501, {'status': 'Confirmed'})

        assert order_repo.get(501)['status'] == 'Confirmed'
        pick_lists = pl_repo.list(filters={'sales_order_id': 501})
        assert len(pick_lists) == 1
        pkl = pick_lists[0]
        assert pkl['pick_list_number'] == 'PKL-E2E-001'

        # Verify Pick List Items populated with dual UOM attributes
        pl_items = pli_repo.list(filters={'pick_list_id': pkl['id']})
        assert len(pl_items) == 1
        pli = pl_items[0]
        assert pli['nominal_weight'] == 80.0
        assert pli['tolerance_pct'] == 5.0
        assert pli['catch_weight_uom'] == 'kg'
        assert pli['tolerance_status'] == 'Not Applicable'

        # 4. Warehouse Picking & Scale Weighing (78.4 kg actual)
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=2.0,
            catch_weight_actual=78.4,
            catch_weight_uom='kg',
            pick_list_id=pkl['id'],
        )
        assert pick_res['tolerance_status'] == 'Within Tolerance'
        assert pick_res['tolerance_variance_pct'] == -2.0

        # Discrepancies should be empty
        discrepancies = pick_svc.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 0

        # 5. Complete Picking -> Order becomes Shipped
        complete_res = pick_svc.complete_picking(pkl['id'])
        assert complete_res['status'] == 'Completed'
        assert order_repo.get(501)['status'] == 'Shipped'

        # 6. Deliver Order -> Recalculates Catch-Weight Total & Generates Invoice
        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-E2E-001'):
            sales_svc.update(501, {'status': 'Delivered'})

        # Verify updated order totals
        updated_order = order_repo.get(501)
        assert updated_order['status'] == 'Delivered'
        assert updated_order['subtotal'] == 1176.0  # 78.4kg * $15/kg
        assert updated_order['tax'] == 58.80  # 5% of $1,176.00
        assert updated_order['grand_total'] == 1234.80

        # Verify updated sales line
        updated_line = line_repo.get(1001)
        assert updated_line['catch_weight_actual'] == 78.4
        assert updated_line['recalculated_total'] == 1176.0

        # Verify Invoice Created
        invoices = inv_repo.list(filters={'sales_order_id': 501})
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv['invoice_number'] == 'INV-E2E-001'
        assert inv['is_catch_weight'] is True
        assert inv['nominal_total_weight'] == 80.0
        assert inv['actual_total_weight'] == 78.4
        assert inv['weight_adjustment_amount'] == -24.0
        assert inv['total_amount'] == 1234.80
        assert 'Catch-weight adjustment: -24.00' in inv['notes']

        # Verify Customer Balance updated: 1000.0 (initial) + 1234.80 = 2234.80
        cust = cust_repo.get(100)
        assert cust['balance'] == 2234.80

    def test_e2e_out_of_tolerance_discrepancy_and_supervisor_approval_lifecycle(self):
        """
        Complete end-to-end workflow with out-of-tolerance discrepancy:
        - Scale weight exceeds tolerance (92.0kg on 80.0kg nominal -> +15.0% > 5.0% tolerance).
        - Picking completion is blocked with error.
        - Order delivery is blocked with error.
        - Supervisor approves discrepancy with audit notes.
        - Picking completion succeeds.
        - Order delivery succeeds, recalculating final price to $1,380.00 (+ $180.00 adjustment).
        """
        product_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')
        cust_repo = CrudRepository('T0010')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        product_repo.create({
            'id': 2,
            'name': 'Gouda Reserve Wheel',
            'sku': 'CHEESE-GOUDA-40',
            'price': 600.0,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
            'is_active': True,
        })
        stock_repo = CrudRepository('T0009')
        stock_repo.create({'id': 2, 'product_id': 2, 'warehouse_id': 1, 'qty': 100, 'reserved_qty': 0})

        order = order_repo.create({
            'id': 502,
            'order_number': 'SO-E2E-002',
            'customer_id': 100,
            'warehouse_id': 1,
            'status': 'Draft',
            'subtotal': 1200.0,
            'tax': 0.0,
            'grand_total': 1200.0,
            'order_date': '2026-08-24',
        })
        line = line_repo.create({
            'id': 1002,
            'sales_order_id': 502,
            'product_id': 2,
            'product_name': 'Gouda Reserve Wheel',
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'unit_price_pricing_uom': 15.0,
            'nominal_weight': 80.0,
        })

        # Confirm order
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-E2E-002'):
            sales_svc.update(502, {'status': 'Confirmed'})

        pkl = pl_repo.list(filters={'sales_order_id': 502})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Record out-of-tolerance weight (92.0 kg actual -> +15.0% variance)
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=2.0,
            catch_weight_actual=92.0,
            catch_weight_uom='kg',
            pick_list_id=pkl['id'],
        )
        assert pick_res['tolerance_status'] == 'Out of Tolerance'
        assert pick_res['tolerance_variance_pct'] == 15.0
        assert pick_res['supervisor_approved'] is False

        # Verify discrepancy detected
        discrepancies = pick_svc.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 1
        assert discrepancies[0]['id'] == pli['id']

        # Verification: complete_picking is blocked
        with pytest.raises(ValueError, match="Unapproved catch-weight tolerance discrepancies exist"):
            pick_svc.complete_picking(pkl['id'])

        # Verification: order delivery is blocked
        order_repo.update(502, {'status': 'Shipped'})  # simulate edge condition
        with pytest.raises(HTTPException) as exc_info:
            sales_svc.update(502, {'status': 'Delivered'})
        assert exc_info.value.status_code == 400
        assert "Unapproved catch-weight tolerance discrepancies exist" in exc_info.value.detail

        # Supervisor Approval Workflow
        approval_res = pick_svc.approve_tolerance(
            pick_list_id=pkl['id'],
            item_id=pli['id'],
            supervisor_id=88,
            supervisor_notes="Overweight batch approved by Head of QA per Certificate of Analysis",
        )
        assert approval_res['has_discrepancies'] is False
        assert approval_res['discrepancy_count'] == 0

        # Verify item metadata updated
        approved_item = pli_repo.get(pli['id'])
        assert approved_item['supervisor_approved'] is True
        assert approved_item['tolerance_status'] == 'Approved'
        assert approved_item['supervisor_approved_by'] == 88
        assert "QA" in approved_item['supervisor_notes']

        # Picking completion now succeeds
        complete_res = pick_svc.complete_picking(pkl['id'])
        assert complete_res['status'] == 'Completed'

        # Order delivery now succeeds
        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-E2E-002'):
            sales_svc.update(502, {'status': 'Delivered'})

        updated_order = order_repo.get(502)
        assert updated_order['status'] == 'Delivered'
        assert updated_order['subtotal'] == 1380.0  # 92.0kg * $15/kg
        assert updated_order['grand_total'] == 1380.0

        inv = inv_repo.list(filters={'sales_order_id': 502})[0]
        assert inv['total_amount'] == 1380.0
        assert inv['actual_total_weight'] == 92.0
        assert inv['weight_adjustment_amount'] == 180.0
        assert 'Catch-weight adjustment: +180.00' in inv['notes']

    def test_e2e_mixed_order_multi_item_complex_adjustments(self):
        """
        Multi-item mixed order with multiple lines:
        - Line 1: Catch-weight Cheddar (40kg nom, 36kg actual -> underweight -$48 adjustment).
        - Line 2: Catch-weight Prosciutto (10kg nom, 10.8kg actual -> overweight +$20 adjustment).
        - Line 3: Fixed-weight Olive Oil (4 units @ $30 = $120, non-catch-weight).
        - Evaluates combined adjustments (-$28 net) and generates itemized billing.
        """
        product_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')
        cust_repo = CrudRepository('T0010')
        stock_repo = CrudRepository('T0009')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # Products
        product_repo.create({'id': 10, 'name': 'Cheddar Block', 'sku': 'CHED-20', 'price': 240.0, 'is_catch_weight': True, 'pricing_uom_id': 2, 'nominal_weight': 20.0, 'tolerance_pct': 15.0})
        product_repo.create({'id': 11, 'name': 'Prosciutto Di Parma', 'sku': 'PROSC-10', 'price': 250.0, 'is_catch_weight': True, 'pricing_uom_id': 2, 'nominal_weight': 10.0, 'tolerance_pct': 10.0})
        product_repo.create({'id': 12, 'name': 'Olive Oil 5L', 'sku': 'OIL-5L', 'price': 30.0, 'is_catch_weight': False})

        # Seed stock for products 10, 11, 12
        stock_repo.create({'id': 10, 'product_id': 10, 'warehouse_id': 1, 'qty': 100, 'reserved_qty': 0})
        stock_repo.create({'id': 11, 'product_id': 11, 'warehouse_id': 1, 'qty': 100, 'reserved_qty': 0})
        stock_repo.create({'id': 12, 'product_id': 12, 'warehouse_id': 1, 'qty': 100, 'reserved_qty': 0})

        # Order: 2 Cheddar (40kg nom = $480), 1 Prosciutto (10kg nom = $250), 4 Olive Oil ($120) -> Subtotal = $850.00
        order = order_repo.create({
            'id': 503,
            'order_number': 'SO-E2E-003',
            'customer_id': 100,
            'warehouse_id': 1,
            'status': 'Draft',
            'subtotal': 850.0,
            'tax': 0.0,
            'grand_total': 850.0,
            'order_date': '2026-08-24',
        })
        line1 = line_repo.create({
            'id': 1011, 'sales_order_id': 503, 'product_id': 10, 'product_name': 'Cheddar Block',
            'qty': 2.0, 'unit_price': 240.0, 'line_total': 480.0, 'line_number': 1,
            'is_catch_weight': True, 'pricing_uom_id': 2, 'unit_price_pricing_uom': 12.0, 'nominal_weight': 40.0,
        })
        line2 = line_repo.create({
            'id': 1012, 'sales_order_id': 503, 'product_id': 11, 'product_name': 'Prosciutto Di Parma',
            'qty': 1.0, 'unit_price': 250.0, 'line_total': 250.0, 'line_number': 2,
            'is_catch_weight': True, 'pricing_uom_id': 2, 'unit_price_pricing_uom': 25.0, 'nominal_weight': 10.0,
        })
        line3 = line_repo.create({
            'id': 1013, 'sales_order_id': 503, 'product_id': 12, 'product_name': 'Olive Oil 5L',
            'qty': 4.0, 'unit_price': 30.0, 'line_total': 120.0, 'line_number': 3,
            'is_catch_weight': False,
        })

        # Confirm & pick
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-E2E-003'):
            sales_svc.update(503, {'status': 'Confirmed'})

        pkl = pl_repo.list(filters={'sales_order_id': 503})[0]
        pl_items = pli_repo.list(filters={'pick_list_id': pkl['id']})

        it_ched = next(i for i in pl_items if i['product_id'] == 10)
        it_prosc = next(i for i in pl_items if i['product_id'] == 11)
        it_oil = next(i for i in pl_items if i['product_id'] == 12)

        # Scale weights:
        # Cheddar: 36.0kg (36kg * $12 = $432, -$48 adj)
        # Prosciutto: 10.8kg (10.8kg * $25 = $270, +$20 adj)
        # Oil: standard 4 units
        pick_svc.pick_item(item_id=it_ched['id'], qty_picked=2.0, catch_weight_actual=36.0, catch_weight_uom='kg')
        pick_svc.pick_item(item_id=it_prosc['id'], qty_picked=1.0, catch_weight_actual=10.8, catch_weight_uom='kg')
        pick_svc.pick_item(item_id=it_oil['id'], qty_picked=4.0)

        # Complete picking
        pick_svc.complete_picking(pkl['id'])

        # Recalculate order preview
        preview = sales_svc.recalculate_order_catch_weight(503)
        assert preview['is_catch_weight'] is True
        assert preview['original_subtotal'] == 850.0
        assert preview['recalculated_subtotal'] == 822.0  # 432 + 270 + 120
        assert preview['weight_adjustment_amount'] == -28.0
        assert preview['nominal_total_weight'] == 50.0  # 40 + 10
        assert preview['actual_total_weight'] == 46.8  # 36 + 10.8

        # Deliver order
        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-E2E-003'):
            sales_svc.update(503, {'status': 'Delivered'})

        inv = inv_repo.list(filters={'sales_order_id': 503})[0]
        assert inv['total_amount'] == 822.0
        assert inv['weight_adjustment_amount'] == -28.0
        assert inv['nominal_total_weight'] == 50.0
        assert inv['actual_total_weight'] == 46.8

    def test_e2e_http_rest_api_workflow(self):
        """
        Complete end-to-end verification through HTTP REST API endpoints using FastAPI TestClient:
        - POST /api/T0003I/ (Create catch-weight product)
        - POST /api/T0012I/with-lines (Create sales order with dual UOM lines)
        - POST /api/T0012I/{id}/confirm (Confirm order -> creates pick list)
        - GET /api/T0101I/{id}/detail (Get pick list details)
        - POST /api/T0101I/{id}/pick-item/{item_id} (Record scale weight)
        - GET /api/T0101I/{id}/discrepancies (Check discrepancy list)
        - POST /api/T0101I/{id}/approve-tolerance (Approve out-of-tolerance variance)
        - POST /api/T0101I/{id}/complete (Complete pick list)
        - GET /api/T0012I/{id}/recalculate-preview (Preview recalculation breakdown)
        - POST /api/T0012I/{id}/deliver (Deliver order & generate invoice)
        - GET /api/T0090I/{id}/catch-weight-breakdown (Verify invoice breakdown)
        """
        client = create_e2e_api_client()

        # 1. Create catch-weight product via REST API
        prod_resp = client.post('/api/T0003I', json={
            'name': 'Artisan Gorgonzola Dolce',
            'sku': 'CHEESE-GORG-12',
            'price': 180.0,
            'cost_price': 120.0,
            'is_catch_weight': True,
            'pricing_uom_id': 2,
            'nominal_weight': 12.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
        })
        assert prod_resp.status_code == 201
        product = prod_resp.json()
        assert product['is_catch_weight'] is True
        assert product['nominal_weight'] == 12.0
        assert product['tolerance_pct'] == 5.0
        product_id = product['id']

        # Seed warehouse stock
        stock_repo = CrudRepository('T0009')
        stock_repo.create({'id': 20, 'product_id': product_id, 'warehouse_id': 1, 'qty': 50, 'reserved_qty': 0})

        # 2. Create sales order with dual UOM line
        so_resp = client.post('/api/T0012I/with-lines', json={
            'order': {
                'order_number': 'SO-REST-001',
                'customer_id': 100,
                'warehouse_id': 1,
                'status': 'Pending',
                'order_date': '2026-08-24',
            },
            'lines': [
                {
                    'product_id': product_id,
                    'product_name': 'Artisan Gorgonzola Dolce',
                    'qty': 2.0,  # 2 wheels = 24kg nominal
                    'unit_price': 180.0,
                    'is_catch_weight': True,
                    'pricing_uom_id': 2,
                    'unit_price_pricing_uom': 15.0,
                    'nominal_weight': 24.0,
                    'line_number': 1,
                }
            ]
        })
        assert so_resp.status_code == 201
        so_data = so_resp.json()
        order_id = so_data['id']

        # 3. Confirm sales order via REST endpoint
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-REST-001'):
            confirm_resp = client.post(f'/api/T0012I/{order_id}/confirm')
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()['status'] == 'Confirmed'

        # 4. Get Pick List detail
        pl_repo = CrudRepository('T0101')
        pkl = pl_repo.list(filters={'sales_order_id': order_id})[0]
        pkl_id = pkl['id']

        detail_resp = client.get(f'/api/T0101I/{pkl_id}/detail')
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail['items']) == 1
        item_id = detail['items'][0]['id']
        assert detail['items'][0]['nominal_weight'] == 24.0

        # 5. Record scale weight exceeding tolerance (+10% on 5% tolerance -> 26.4kg)
        pick_resp = client.post(f'/api/T0101I/{pkl_id}/pick-item/{item_id}', json={
            'qty_picked': 2.0,
            'catch_weight_actual': 26.4,
            'catch_weight_uom': 'kg',
        })
        assert pick_resp.status_code == 200
        picked = pick_resp.json()
        assert picked['tolerance_status'] == 'Out of Tolerance'
        assert picked['tolerance_variance_pct'] == 10.0

        # 6. Check discrepancies endpoint
        disc_resp = client.get(f'/api/T0101I/{pkl_id}/discrepancies')
        assert disc_resp.status_code == 200
        discs = disc_resp.json()
        assert len(discs) == 1
        assert discs[0]['id'] == item_id

        # 7. Complete picking is blocked
        blocked_comp = client.post(f'/api/T0101I/{pkl_id}/complete')
        assert blocked_comp.status_code == 400
        assert "discrepancies" in blocked_comp.json()['detail'].lower()

        # 8. Approve tolerance discrepancy via REST endpoint
        appr_resp = client.post(f'/api/T0101I/{pkl_id}/approve-tolerance', json={
            'item_id': item_id,
            'supervisor_id': 99,
            'supervisor_notes': 'Oversized Gorgonzola approved by Warehouse Supervisor',
        })
        assert appr_resp.status_code == 200
        assert appr_resp.json()['has_discrepancies'] is False

        # 9. Complete picking succeeds
        comp_resp = client.post(f'/api/T0101I/{pkl_id}/complete')
        assert comp_resp.status_code == 200
        assert comp_resp.json()['status'] == 'Completed'

        # 10. Preview recalculation breakdown
        prev_resp = client.get(f'/api/T0012I/{order_id}/recalculate-preview')
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()
        assert prev_data['original_subtotal'] == 360.0
        assert prev_data['recalculated_subtotal'] == 396.0  # 26.4kg * $15 = $396.00
        assert prev_data['weight_adjustment_amount'] == 36.0

        # 11. Deliver order via REST endpoint
        with patch('modules.sales.services.sales_service.generate_invoice_number', return_value='INV-REST-001'):
            deliv_resp = client.post(f'/api/T0012I/{order_id}/deliver')
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()['status'] == 'Delivered'
        assert deliv_resp.json()['subtotal'] == 396.0

        # 12. Fetch Invoice Catch-Weight Breakdown
        inv_repo = CrudRepository('T0090')
        invoice_id = inv_repo.list(filters={'sales_order_id': order_id})[0]['id']

        inv_breakdown_resp = client.get(f'/api/T0090I/{invoice_id}/catch-weight-breakdown')
        assert inv_breakdown_resp.status_code == 200
        inv_breakdown = inv_breakdown_resp.json()
        assert inv_breakdown['is_catch_weight'] is True
        assert inv_breakdown['nominal_total_weight'] == 24.0
        assert inv_breakdown['actual_total_weight'] == 26.4
        assert inv_breakdown['weight_adjustment_amount'] == 36.0

    def test_e2e_mcp_servers_tool_calling_workflow(self):
        """
        Verify that AI agents can execute the entire Catch-Weight & Dual UOM workflow
        using MCP tools across inventory_mcp, sales_mcp, and warehouse_mcp.
        """
        # Step 1: Create dual UOM product via inventory_mcp tool handler
        prod = inv_mcp._create_product(
            name="Manchego Curado 3M",
            sku="CHEESE-MANCH-30",
            price=450.0,
            is_catch_weight=True,
            pricing_uom_id=2,
            nominal_weight=30.0,
            tolerance_pct=5.0,
            pricing_basis="weight",
        )
        assert prod['is_catch_weight'] is True
        assert prod['nominal_weight'] == 30.0
        prod_id = prod['id']

        # Seed stock
        stock_repo = CrudRepository('T0009')
        stock_repo.create({'id': 30, 'product_id': prod_id, 'warehouse_id': 1, 'qty': 50, 'reserved_qty': 0})

        # Step 2: Create Sales Order and Line via sales_mcp tool handler
        order = sales_mcp._create_order(
            customer_id=100,
            warehouse_id=1,
            subtotal=450.0,
            grand_total=450.0,
        )
        order_id = order['id']

        sales_mcp._create_order_line(
            sales_order_id=order_id,
            product_name="Manchego Curado 3M",
            product_id=prod_id,
            qty=1.0,
            unit_price=450.0,
            is_catch_weight=True,
            pricing_uom_id=2,
            unit_price_pricing_uom=15.0,
            nominal_weight=30.0,
        )

        # Step 3: Confirm order via sales_mcp tool handler
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-MCP-001'):
            sales_mcp._confirm_order(order_id)

        # Step 4: Get pick list via warehouse_mcp tool handler
        pick_lists = wh_mcp._list_pick(sales_order_id=order_id)
        assert len(pick_lists) == 1
        pkl_id = pick_lists[0]['id']

        pkl_detail = wh_mcp._get_pick_list(pkl_id)
        assert len(pkl_detail['items']) == 1
        pli_id = pkl_detail['items'][0]['id']

        # Step 5: Pick item with scale weight via warehouse_mcp tool handler (28.8kg -> -4.0% within 5% tolerance)
        pick_res = wh_mcp._pick_item(
            item_id=pli_id,
            qty_picked=1.0,
            catch_weight_actual=28.8,
            catch_weight_uom="kg",
            pick_list_id=pkl_id,
        )
        assert pick_res['tolerance_status'] == 'Within Tolerance'

        # Step 6: Recalculate catch weight via sales_mcp tool handler
        recalc = sales_mcp._recalculate_order_catch_weight(order_id)
        assert recalc['recalculated_subtotal'] == 432.0  # 28.8kg * $15 = $432.00
        assert recalc['weight_adjustment_amount'] == -18.0

        # Step 7: Filter orders by catch_weight via sales_mcp tool handler
        cw_orders = sales_mcp._list_orders(is_catch_weight=True)
        assert any(o['id'] == order_id for o in cw_orders)
