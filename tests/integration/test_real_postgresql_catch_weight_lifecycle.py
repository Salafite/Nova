"""
Real PostgreSQL End-to-End Integration Test Suite for Dual-UOM & Catch-Weight Lifecycle.

This test suite runs directly against the real PostgreSQL container (schema "Nova")
verifying tolerance calculations, scale weight capture, order recalculation,
invoice weight adjustments, inventory deductions, and multi-tenant isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from packages.database.sequence import (
    generate_invoice_number,
    generate_pick_list_number,
    get_current_sequence_value,
)
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


pytestmark = [pytest.mark.real_db, pytest.mark.integration]


TEST_ADMIN = {
    'id': 1,
    'username': 'admin',
    'role': 'Admin',
    'permissions': ['*'],
}


def create_real_db_api_client():
    """Create FastAPI test client with all catch-weight routers wired for real DB tests."""
    app = FastAPI(title="Nova Real PostgreSQL Catch-Weight Test Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(invoice_router)
    return TestClient(app)


def _seed_base_uoms(uom_repo):
    """Ensure standard UOMs exist in T0001."""
    existing = uom_repo.list()
    uom_map = {u['uom_code']: u['id'] for u in existing}
    if 'CASE' not in uom_map:
        rec = uom_repo.create({'uom_code': 'CASE', 'uom_name': 'Case / Box', 'is_active': True})
        uom_map['CASE'] = rec['id']
    if 'kg' not in uom_map:
        rec = uom_repo.create({'uom_code': 'kg', 'uom_name': 'Kilogram', 'is_active': True})
        uom_map['kg'] = rec['id']
    if 'EA' not in uom_map:
        rec = uom_repo.create({'uom_code': 'EA', 'uom_name': 'Each', 'is_active': True})
        uom_map['EA'] = rec['id']
    return uom_map


# ============================================================================
# 1. Master Data & Tolerance Calculation Tests
# ============================================================================

class TestRealPostgresToleranceAndWeighing:
    """
    Verifies dual UOM product configuration, weight variance calculations,
    and tolerance status persistence in real PostgreSQL tables.
    """

    def test_real_postgres_master_data_and_schema_persistence(self, isolated_tenant, real_db_conn):
        """
        Verify that dual UOM catch-weight columns and constraints exist and persist
        in PostgreSQL table 't0003' with correct data types and values.
        """
        uom_repo = CrudRepository('T0001')
        product_repo = CrudRepository('T0003')
        uom_map = _seed_base_uoms(uom_repo)

        product = product_repo.create({
            'name': 'Parmigiano Reggiano 24M',
            'sku': 'CW-PARM-40KG',
            'price': 600.00,
            'cost_price': 400.00,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        assert product['id'] is not None
        assert product['is_catch_weight'] is True
        assert float(product['nominal_weight']) == 40.0
        assert float(product['tolerance_pct']) == 5.0
        assert product['pricing_basis'] == 'weight'
        assert product['pricing_uom_id'] == uom_map['kg']

        # Verify directly via raw SQL in PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, sku, is_catch_weight, pricing_uom_id,
                       nominal_weight, tolerance_pct, pricing_basis, business_id
                FROM "Nova"."t0003"
                WHERE id = %s;
                """,
                (product['id'],)
            )
            row = cur.fetchone()
            assert row is not None
            assert row['is_catch_weight'] is True
            assert float(row['nominal_weight']) == 40.0
            assert float(row['tolerance_pct']) == 5.0
            assert row['pricing_basis'] == 'weight'
            assert row['pricing_uom_id'] == uom_map['kg']
            assert row['business_id'] == isolated_tenant

    def test_real_postgres_tolerance_calculations_mathematical_accuracy(self, isolated_tenant):
        """
        Test tolerance variance percentage calculations across various weight bounds.
        """
        pl_service = PickListService()

        # Variance calculation checks
        # Exact match
        assert pl_service.calculate_weight_variance(40.0, 40.0) == 0.0
        # -2.5% variance
        assert pl_service.calculate_weight_variance(40.0, 39.0) == -2.5
        # +5.0% variance
        assert pl_service.calculate_weight_variance(40.0, 42.0) == 5.0
        # +10.0% variance
        assert pl_service.calculate_weight_variance(40.0, 44.0) == 10.0
        # None handling
        assert pl_service.calculate_weight_variance(None, 40.0) is None
        assert pl_service.calculate_weight_variance(40.0, None) is None

        # Tolerance evaluation status checks
        # Within tolerance (+4% on 5% limit)
        var_pct, status = pl_service.evaluate_tolerance(nominal_weight=100.0, actual_weight=104.0, tolerance_pct=5.0)
        assert var_pct == 4.0
        assert status == 'Within Tolerance'

        # Out of tolerance (+8% on 5% limit)
        var_pct, status = pl_service.evaluate_tolerance(nominal_weight=100.0, actual_weight=108.0, tolerance_pct=5.0)
        assert var_pct == 8.0
        assert status == 'Out of Tolerance'

        # Out of tolerance with supervisor approval -> 'Approved'
        var_pct, status = pl_service.evaluate_tolerance(
            nominal_weight=100.0, actual_weight=108.0, tolerance_pct=5.0, supervisor_approved=True
        )
        assert var_pct == 8.0
        assert status == 'Approved'

        # Exact boundary lower limit (-5.0% on 5% limit)
        var_pct, status = pl_service.evaluate_tolerance(nominal_weight=100.0, actual_weight=95.0, tolerance_pct=5.0)
        assert var_pct == -5.0
        assert status == 'Within Tolerance'


# ============================================================================
# 2. Positive End-to-End Happy Path Lifecycle Test
# ============================================================================

class TestRealPostgresCatchWeightHappyPathLifecycle:
    """
    Tests the complete happy-path Order-to-Cash catch-weight lifecycle in real PostgreSQL:
    1. Product Setup (Dual-UOM cheese wheel, nominal 40kg, 5% tolerance, $15/kg).
    2. Initial Stock Inbound into Warehouse.
    3. Customer Setup with credit limit and balance.
    4. Sales Order Creation with Dual-UOM line.
    5. Order Confirmation -> Stock Reservation in T0009 & Pick List in T0101/T0102.
    6. Warehouse Scale Weight Capture (78.4kg on 80.0kg nominal -> -2.0% variance).
    7. Pick List Completion -> Shipped status.
    8. Order Delivery -> Catch-Weight Recalculation ($1,176.00 subtotal, -$24.00 adjustment).
    9. Real Invoice Generation with Sequence seq_invoice_number & Customer Balance update.
    10. Physical Inventory Deduction in T0009 & Stock Movement in T0064.
    """

    def test_real_postgres_e2e_happy_path_lifecycle(self, isolated_tenant, real_db_conn):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')
        movement_repo = CrudRepository('T0064')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        stock_svc = StockMovementService()

        uom_map = _seed_base_uoms(uom_repo)

        # 1. Master Data Setup
        wh = wh_repo.create({'name': 'Main Cold Storage', 'location': 'Dock A', 'is_active': True})
        wh_id = wh['id']

        cust = customer_repo.create({'name': 'Artisan Cheese Shop', 'credit_limit': 20000.0, 'balance': 500.0})
        cust_id = cust['id']

        cheese = product_repo.create({
            'name': 'Parmigiano Reggiano Wheel',
            'sku': 'CW-PARM-HP-01',
            'price': 600.0,  # $600/case nominal
            'cost_price': 380.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        prod_id = cheese['id']

        # 2. Stock Inbound: 50 cases in warehouse
        stock_record = stock_repo.create({
            'product_id': prod_id,
            'warehouse_id': wh_id,
            'qty': 50.0,
            'reserved_qty': 0.0,
        })

        # 3. Create Sales Order with Dual UOM Line (2 cases, nominal 80kg)
        order = order_repo.create({
            'order_number': 'SO-CW-HP-001',
            'customer_id': cust_id,
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 1200.0,
            'tax': 60.0,
            'grand_total': 1260.0,
            'order_date': '2026-08-26',
        })
        order_id = order['id']

        line = line_repo.create({
            'sales_order_id': order_id,
            'product_id': prod_id,
            'product_name': 'Parmigiano Reggiano Wheel',
            'qty': 2.0,
            'unit_price': 600.0,
            'line_total': 1200.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 15.0,  # $15.00 / kg
            'nominal_weight': 80.0,
        })
        line_id = line['id']

        # 4. Confirm Order -> Reserves stock in PostgreSQL and generates Pick List
        sales_svc.update(order_id, {'status': 'Confirmed'})

        # Verify Order Status
        updated_order = order_repo.get(order_id)
        assert updated_order['status'] == 'Confirmed'

        # Verify Stock Reservation in T0009
        stock_after_reserve = stock_repo.get(stock_record['id'])
        assert float(stock_after_reserve['qty']) == 50.0
        assert float(stock_after_reserve['reserved_qty']) == 2.0

        # Verify Stock Movement logged in T0064
        moves = movement_repo.list(filters={'product_id': prod_id, 'movement_type': 'Reserve'})
        assert len(moves) >= 1
        assert moves[0]['reference_type'] == 'sales_order'
        assert moves[0]['reference_id'] == order_id

        # Verify Pick List generated in T0101
        pick_lists = pl_repo.list(filters={'sales_order_id': order_id})
        assert len(pick_lists) == 1
        pkl = pick_lists[0]
        pkl_id = pkl['id']
        assert pkl['status'] == 'Pending'
        assert pkl['pick_list_number'].startswith('PKL-')

        # Verify Pick List Item created in T0102 with dual UOM attributes
        pl_items = pli_repo.list(filters={'pick_list_id': pkl_id})
        assert len(pl_items) == 1
        pli = pl_items[0]
        assert pli['product_id'] == prod_id
        assert float(pli['qty_ordered']) == 2.0
        assert float(pli['nominal_weight']) == 80.0
        assert float(pli['tolerance_pct']) == 5.0
        assert pli['catch_weight_uom'] == 'kg'
        assert pli['tolerance_status'] == 'Not Applicable'

        # 5. Warehouse Scale Weighing (Picker weighs 78.4 kg on scale)
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=2.0,
            catch_weight_actual=78.4,
            catch_weight_uom='kg',
            pick_list_id=pkl_id,
        )
        assert pick_res['tolerance_status'] == 'Within Tolerance'
        assert float(pick_res['tolerance_variance_pct']) == -2.0
        assert float(pick_res['catch_weight_actual']) == 78.4

        # Direct SQL check on T0102
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT catch_weight_actual, tolerance_variance_pct, tolerance_status FROM "Nova".t0102 WHERE id = %s;', (pli['id'],))
            db_pli = cur.fetchone()
            assert float(db_pli['catch_weight_actual']) == 78.4
            assert float(db_pli['tolerance_variance_pct']) == -2.0
            assert db_pli['tolerance_status'] == 'Within Tolerance'

        # Verify no discrepancies
        discs = pick_svc.check_pick_list_discrepancies(pkl_id)
        assert len(discs) == 0

        # 6. Complete Picking -> Pick List Completed, Order Shipped
        complete_res = pick_svc.complete_picking(pkl_id)
        assert complete_res['status'] == 'Completed'
        assert order_repo.get(order_id)['status'] == 'Shipped'

        # 7. Order Delivery -> Catch-Weight Recalculation & Invoice Creation
        sales_svc.update(order_id, {'status': 'Delivered'})

        # Verify Recalculated Order Totals in T0012
        deliv_order = order_repo.get(order_id)
        assert deliv_order['status'] == 'Delivered'
        # 78.4kg * $15/kg = $1,176.00 subtotal
        assert float(deliv_order['subtotal']) == 1176.0
        assert float(deliv_order['tax']) == 58.80
        assert float(deliv_order['grand_total']) == 1234.80

        # Verify Sales Line Updated in T0013
        db_line = line_repo.get(line_id)
        assert float(db_line['catch_weight_actual']) == 78.4
        assert float(db_line['recalculated_total']) == 1176.0

        # 8. Verify Invoice Created in T0090
        invoices = inv_repo.list(filters={'sales_order_id': order_id})
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv['invoice_number'].startswith('INV-')
        assert inv['is_catch_weight'] is True
        assert float(inv['nominal_total_weight']) == 80.0
        assert float(inv['actual_total_weight']) == 78.4
        assert float(inv['weight_adjustment_amount']) == -24.0
        assert float(inv['total_amount']) == 1234.80
        assert 'Catch-weight adjustment: -24.00' in inv['notes']

        # 9. Verify Customer Balance Updated in T0010 (500.0 initial + 1234.80 = 1734.80)
        updated_cust = customer_repo.get(cust_id)
        assert float(updated_cust['balance']) == 1734.80

        # 10. Verify Stock Deduction
        stock_svc.deduct_stock(prod_id, wh_id, 2.0, reference_type='sales_order', reference_id=order_id)
        final_stock = stock_repo.get(stock_record['id'])
        assert float(final_stock['qty']) == 48.0
        assert float(final_stock['reserved_qty']) == 0.0

        deduct_moves = movement_repo.list(filters={'product_id': prod_id, 'movement_type': 'Deduct'})
        assert len(deduct_moves) >= 1
        assert float(deduct_moves[0]['qty_change']) == -2.0
        assert float(deduct_moves[0]['balance_after']) == 48.0


# ============================================================================
# 3. Negative Scenarios: Discrepancy Gating & Supervisor Approval Workflow
# ============================================================================

class TestRealPostgresCatchWeightDiscrepancyAndApproval:
    """
    Tests out-of-tolerance discrepancy detection, execution gating,
    supervisor approval workflow, and database atomicity in real PostgreSQL.
    """

    def test_real_postgres_out_of_tolerance_blocks_completion_and_delivery(self, isolated_tenant, real_db_conn):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'Cold Storage B', 'location': 'Bay 2', 'is_active': True})
        cust = customer_repo.create({'name': 'Gourmet Market', 'credit_limit': 15000.0, 'balance': 0.0})

        # Dual UOM Gouda with nominal 20kg, 5.0% tolerance, $20/kg
        gouda = product_repo.create({
            'name': 'Gouda Aged Wheel',
            'sku': 'CW-GOUDA-DISC-01',
            'price': 400.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 20.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        prod_id = gouda['id']
        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh['id'], 'qty': 20.0, 'reserved_qty': 0.0})

        # Create Order: 1 wheel, nominal 20.0kg
        order = order_repo.create({
            'order_number': 'SO-CW-DISC-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 400.0,
            'tax': 0.0,
            'grand_total': 400.0,
            'order_date': '2026-08-26',
        })
        order_id = order['id']

        line = line_repo.create({
            'sales_order_id': order_id,
            'product_id': prod_id,
            'product_name': 'Gouda Aged Wheel',
            'qty': 1.0,
            'unit_price': 400.0,
            'line_total': 400.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 20.0,
            'nominal_weight': 20.0,
        })

        # Confirm Order
        sales_svc.update(order_id, {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order_id})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Record out-of-tolerance scale weight: 23.0 kg (+15.0% variance > 5.0% tolerance)
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=1.0,
            catch_weight_actual=23.0,
            catch_weight_uom='kg',
            pick_list_id=pkl['id'],
        )
        assert pick_res['tolerance_status'] == 'Out of Tolerance'
        assert float(pick_res['tolerance_variance_pct']) == 15.0
        assert pick_res['supervisor_approved'] is False

        # Verify discrepancy detected
        discrepancies = pick_svc.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 1
        assert discrepancies[0]['id'] == pli['id']

        # 1. Verification: complete_picking must be blocked
        with pytest.raises(ValueError, match="Unapproved catch-weight tolerance discrepancies exist"):
            pick_svc.complete_picking(pkl['id'])

        # Pick list status must remain Pending/In Progress
        assert pl_repo.get(pkl['id'])['status'] != 'Completed'

        # 2. Verification: order delivery must be blocked
        order_repo.update(order_id, {'status': 'Shipped'})  # simulate edge transition attempt
        with pytest.raises(HTTPException) as exc_info:
            sales_svc.update(order_id, {'status': 'Delivered'})
        assert exc_info.value.status_code == 400
        assert "Unapproved catch-weight tolerance discrepancies exist" in exc_info.value.detail

        # Verify no invoice was created in PostgreSQL
        invoices = inv_repo.list(filters={'sales_order_id': order_id})
        assert len(invoices) == 0

        # 3. Supervisor Approval Workflow
        user_repo = CrudRepository('T0021')
        sup_user = user_repo.create({
            'username': 'sup_user_disc',
            'password_hash': 'hashed_pw',
            'full_name': 'Supervisor Disc',
            'email': 'sup_disc@example.com',
            'role': 'Supervisor',
        })
        sup_id = sup_user['id']

        approval_res = pick_svc.approve_tolerance(
            pick_list_id=pkl['id'],
            item_id=pli['id'],
            supervisor_id=sup_id,
            supervisor_notes="Approved overweight wheel for VIP customer order per Head of Quality",
        )
        assert approval_res['has_discrepancies'] is False
        assert approval_res['discrepancy_count'] == 0

        # Verify PostgreSQL record updated in T0102
        approved_item = pli_repo.get(pli['id'])
        assert approved_item['supervisor_approved'] is True
        assert approved_item['tolerance_status'] == 'Approved'
        assert approved_item['supervisor_approved_by'] == sup_id
        assert "VIP" in approved_item['supervisor_notes']

        # 4. Now complete picking succeeds
        complete_res = pick_svc.complete_picking(pkl['id'])
        assert complete_res['status'] == 'Completed'

        # 5. Now order delivery succeeds
        deliv_res = sales_svc.update(order_id, {'status': 'Delivered'})
        assert deliv_res['status'] == 'Delivered'
        # 23.0kg * $20/kg = $460.00
        assert float(deliv_res['subtotal']) == 460.0
        assert float(deliv_res['grand_total']) == 460.0

        # Verify Invoice Created with +$60.00 adjustment
        inv = inv_repo.list(filters={'sales_order_id': order_id})[0]
        assert float(inv['total_amount']) == 460.0
        assert float(inv['actual_total_weight']) == 23.0
        assert float(inv['weight_adjustment_amount']) == 60.0
        assert 'Catch-weight adjustment: +60.00' in inv['notes']


# ============================================================================
# 4. Complex Multi-Item Mixed Basket Recalculation Test
# ============================================================================

class TestRealPostgresMultiItemMixedRecalculation:
    """
    Tests multi-item orders containing both catch-weight and non-catch-weight items,
    with underweight and overweight adjustments simultaneously.
    """

    def test_real_postgres_mixed_order_net_adjustments(self, isolated_tenant, real_db_conn):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'Central Depot', 'location': 'Main Area', 'is_active': True})
        cust = customer_repo.create({'name': 'Fine Foods Distribution', 'credit_limit': 50000.0, 'balance': 2000.0})

        # Product 1: Catch-Weight Cheddar (20kg nom/case, +/-15% tol, $12/kg -> $240/case)
        p1 = product_repo.create({
            'name': 'Cheddar 20KG Block',
            'sku': 'CW-CHED-20',
            'price': 240.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 20.0,
            'tolerance_pct': 15.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        # Product 2: Catch-Weight Prosciutto (10kg nom/case, +/-10% tol, $25/kg -> $250/case)
        p2 = product_repo.create({
            'name': 'Prosciutto San Daniele',
            'sku': 'CW-PROSC-10',
            'price': 250.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 10.0,
            'tolerance_pct': 10.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        # Product 3: Non-Catch-Weight Olive Oil ($30/unit fixed)
        p3 = product_repo.create({
            'name': 'Extra Virgin Olive Oil 5L',
            'sku': 'FIXED-OIL-5L',
            'price': 30.0,
            'is_catch_weight': False,
            'is_active': True,
        })

        stock_repo.create({'product_id': p1['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p2['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p3['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})

        # Order:
        # Line 1: 2 cases Cheddar (40kg nom = $480.00)
        # Line 2: 1 case Prosciutto (10kg nom = $250.00)
        # Line 3: 4 units Olive Oil ($120.00)
        # Subtotal: $850.00, Tax 10%: $85.00, Grand Total: $935.00
        order = order_repo.create({
            'order_number': 'SO-CW-MIX-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 850.0,
            'tax': 85.0,
            'grand_total': 935.0,
            'order_date': '2026-08-26',
        })
        order_id = order['id']

        line1 = line_repo.create({
            'sales_order_id': order_id,
            'product_id': p1['id'],
            'product_name': 'Cheddar 20KG Block',
            'qty': 2.0,
            'unit_price': 240.0,
            'line_total': 480.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 12.0,
            'nominal_weight': 40.0,
        })
        line2 = line_repo.create({
            'sales_order_id': order_id,
            'product_id': p2['id'],
            'product_name': 'Prosciutto San Daniele',
            'qty': 1.0,
            'unit_price': 250.0,
            'line_total': 250.0,
            'line_number': 2,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 25.0,
            'nominal_weight': 10.0,
        })
        line3 = line_repo.create({
            'sales_order_id': order_id,
            'product_id': p3['id'],
            'product_name': 'Extra Virgin Olive Oil 5L',
            'qty': 4.0,
            'unit_price': 30.0,
            'line_total': 120.0,
            'line_number': 3,
            'is_catch_weight': False,
        })

        # Confirm & Pick
        sales_svc.update(order_id, {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order_id})[0]
        pl_items = pli_repo.list(filters={'pick_list_id': pkl['id']})

        it_ched = next(i for i in pl_items if i['product_id'] == p1['id'])
        it_prosc = next(i for i in pl_items if i['product_id'] == p2['id'])
        it_oil = next(i for i in pl_items if i['product_id'] == p3['id'])

        # Scale weights:
        # Cheddar: 36.0kg (underweight -10.0% within 15% tol) -> 36kg * $12 = $432.00 (-$48.00 adj)
        # Prosciutto: 10.8kg (overweight +8.0% within 10% tol) -> 10.8kg * $25 = $270.00 (+$20.00 adj)
        # Olive Oil: standard 4 units -> $120.00
        pick_svc.pick_item(item_id=it_ched['id'], qty_picked=2.0, catch_weight_actual=36.0, catch_weight_uom='kg')
        pick_svc.pick_item(item_id=it_prosc['id'], qty_picked=1.0, catch_weight_actual=10.8, catch_weight_uom='kg')
        pick_svc.pick_item(item_id=it_oil['id'], qty_picked=4.0)

        pick_svc.complete_picking(pkl['id'])

        # Preview recalculation
        preview = sales_svc.recalculate_order_catch_weight(order_id)
        assert preview['is_catch_weight'] is True
        assert float(preview['original_subtotal']) == 850.0
        # Recalculated subtotal: 432 + 270 + 120 = 822.00
        assert float(preview['recalculated_subtotal']) == 822.0
        assert float(preview['weight_adjustment_amount']) == -28.0
        assert float(preview['nominal_total_weight']) == 50.0
        assert float(preview['actual_total_weight']) == 46.8
        # Proportional tax: 10% of 822.00 = 82.20
        assert float(preview['tax']) == 82.20
        assert float(preview['grand_total']) == 904.20

        # Deliver order
        deliv_res = sales_svc.update(order_id, {'status': 'Delivered'})
        assert float(deliv_res['subtotal']) == 822.0
        assert float(deliv_res['grand_total']) == 904.20

        # Verify Invoice in PostgreSQL
        inv = inv_repo.list(filters={'sales_order_id': order_id})[0]
        assert float(inv['total_amount']) == 904.20
        assert float(inv['weight_adjustment_amount']) == -28.0
        assert float(inv['nominal_total_weight']) == 50.0
        assert float(inv['actual_total_weight']) == 46.8
        assert 'Catch-weight adjustment: -28.00' in inv['notes']


# ============================================================================
# 5. REST API & MCP Tools Integration Tests on Real PostgreSQL
# ============================================================================

class TestRealPostgresCatchWeightRestApiAndMcp:
    """
    Tests HTTP REST API endpoints and MCP server tool handlers directly
    executing against real PostgreSQL tables.
    """

    def test_real_postgres_http_rest_api_workflow(self, isolated_tenant, real_db_conn):
        client = create_real_db_api_client()
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'API Cold Warehouse', 'location': 'Zone C', 'is_active': True})
        cust = customer_repo.create({'name': 'REST API Customer Ltd', 'credit_limit': 30000.0, 'balance': 0.0})

        # 1. POST /api/T0003I (Create Catch-Weight Product)
        prod_resp = client.post('/api/T0003I', json={
            'name': 'Gorgonzola Mountain Wheel',
            'sku': 'CW-GORG-REST-01',
            'price': 180.0,
            'cost_price': 120.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 12.0,
            'tolerance_pct': 5.0,
            'pricing_basis': 'weight',
        })
        assert prod_resp.status_code == 201
        prod = prod_resp.json()
        prod_id = prod['id']
        assert prod['is_catch_weight'] is True

        # Seed Stock
        stock_repo = CrudRepository('T0009')
        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh['id'], 'qty': 40.0, 'reserved_qty': 0.0})

        # 2. POST /api/T0012I/with-lines (Create Order with Lines)
        so_resp = client.post('/api/T0012I/with-lines', json={
            'order': {
                'order_number': 'SO-REST-CW-01',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Pending',
                'order_date': '2026-08-26',
            },
            'lines': [
                {
                    'product_id': prod_id,
                    'product_name': 'Gorgonzola Mountain Wheel',
                    'qty': 2.0,
                    'unit_price': 180.0,
                    'is_catch_weight': True,
                    'pricing_uom_id': uom_map['kg'],
                    'unit_price_pricing_uom': 15.0,
                    'nominal_weight': 24.0,
                    'line_number': 1,
                }
            ]
        })
        assert so_resp.status_code == 201
        order_id = so_resp.json()['id']

        # 3. POST /api/T0012I/{id}/confirm
        confirm_resp = client.post(f'/api/T0012I/{order_id}/confirm')
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()['status'] == 'Confirmed'

        # 4. GET /api/T0101I/{id}/detail
        pl_repo = CrudRepository('T0101')
        pkl = pl_repo.list(filters={'sales_order_id': order_id})[0]
        pkl_id = pkl['id']

        detail_resp = client.get(f'/api/T0101I/{pkl_id}/detail')
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail['items']) == 1
        pli_id = detail['items'][0]['id']

        # 5. POST /api/T0101I/{id}/pick-item/{item_id} (Out of tolerance: 26.4kg on 24.0kg nominal -> +10%)
        pick_resp = client.post(f'/api/T0101I/{pkl_id}/pick-item/{pli_id}', json={
            'qty_picked': 2.0,
            'catch_weight_actual': 26.4,
            'catch_weight_uom': 'kg',
        })
        assert pick_resp.status_code == 200
        assert pick_resp.json()['tolerance_status'] == 'Out of Tolerance'

        # 6. GET /api/T0101I/{id}/discrepancies
        disc_resp = client.get(f'/api/T0101I/{pkl_id}/discrepancies')
        assert disc_resp.status_code == 200
        assert len(disc_resp.json()) == 1

        # 7. Complete is blocked
        blocked_comp = client.post(f'/api/T0101I/{pkl_id}/complete')
        assert blocked_comp.status_code == 400

        # 8. POST /api/T0101I/{id}/approve-tolerance
        user_repo = CrudRepository('T0021')
        sup_user = user_repo.create({
            'username': 'rest_api_supervisor',
            'password_hash': 'hashed_pw',
            'full_name': 'API Supervisor',
            'email': 'api_sup@example.com',
            'role': 'Supervisor',
        })
        appr_resp = client.post(f'/api/T0101I/{pkl_id}/approve-tolerance', json={
            'item_id': pli_id,
            'supervisor_id': sup_user['id'],
            'supervisor_notes': 'Approved by REST API supervisor',
        })
        assert appr_resp.status_code == 200
        assert appr_resp.json()['has_discrepancies'] is False

        # 9. POST /api/T0101I/{id}/complete succeeds
        comp_resp = client.post(f'/api/T0101I/{pkl_id}/complete')
        assert comp_resp.status_code == 200
        assert comp_resp.json()['status'] == 'Completed'

        # 10. GET /api/T0012I/{id}/recalculate-preview
        prev_resp = client.get(f'/api/T0012I/{order_id}/recalculate-preview')
        assert prev_resp.status_code == 200
        assert float(prev_resp.json()['recalculated_subtotal']) == 396.0  # 26.4kg * $15 = $396.00
        assert float(prev_resp.json()['weight_adjustment_amount']) == 36.0

        # 11. POST /api/T0012I/{id}/deliver
        deliv_resp = client.post(f'/api/T0012I/{order_id}/deliver')
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()['status'] == 'Delivered'
        assert float(deliv_resp.json()['subtotal']) == 396.0

        # 12. GET /api/T0090I/{id}/catch-weight-breakdown
        inv_repo = CrudRepository('T0090')
        invoice_id = inv_repo.list(filters={'sales_order_id': order_id})[0]['id']
        inv_bd_resp = client.get(f'/api/T0090I/{invoice_id}/catch-weight-breakdown')
        assert inv_bd_resp.status_code == 200
        inv_bd = inv_bd_resp.json()
        assert inv_bd['is_catch_weight'] is True
        assert float(inv_bd['nominal_total_weight']) == 24.0
        assert float(inv_bd['actual_total_weight']) == 26.4
        assert float(inv_bd['weight_adjustment_amount']) == 36.0

    def test_real_postgres_mcp_servers_tool_calling_workflow(self, isolated_tenant, real_db_conn):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        stock_repo = CrudRepository('T0009')
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'MCP Warehouse', 'location': 'Dock 9', 'is_active': True})
        cust = customer_repo.create({'name': 'MCP AI Customer', 'credit_limit': 10000.0, 'balance': 0.0})

        # 1. Create dual UOM product via inventory_mcp handler
        prod = inv_mcp._create_product(
            name='Manchego Curado Real PG',
            sku='CW-MANCH-MCP-01',
            price=450.0,
            is_catch_weight=True,
            pricing_uom_id=uom_map['kg'],
            nominal_weight=30.0,
            tolerance_pct=5.0,
            pricing_basis='weight',
        )
        prod_id = prod['id']
        assert prod['is_catch_weight'] is True

        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh['id'], 'qty': 30.0, 'reserved_qty': 0.0})

        # 2. Create order via sales_mcp handler
        order = sales_mcp._create_order(
            customer_id=cust['id'],
            warehouse_id=wh['id'],
            subtotal=450.0,
            grand_total=450.0,
        )
        order_id = order['id']

        sales_mcp._create_order_line(
            sales_order_id=order_id,
            product_name='Manchego Curado Real PG',
            product_id=prod_id,
            qty=1.0,
            unit_price=450.0,
            is_catch_weight=True,
            pricing_uom_id=uom_map['kg'],
            unit_price_pricing_uom=15.0,
            nominal_weight=30.0,
        )

        # 3. Confirm order via sales_mcp
        confirm_res = sales_mcp._confirm_order(order_id)
        assert confirm_res['status'] == 'Confirmed'

        # 4. List pick lists via warehouse_mcp
        pkls = wh_mcp._list_pick(sales_order_id=order_id)
        assert len(pkls) == 1
        pkl_id = pkls[0]['id']

        pkl_detail = wh_mcp._get_pick_list(pkl_id)
        pli_id = pkl_detail['items'][0]['id']

        # 5. Pick item with scale weight via warehouse_mcp (28.8kg -> -4.0% variance)
        pick_res = wh_mcp._pick_item(
            item_id=pli_id,
            qty_picked=1.0,
            catch_weight_actual=28.8,
            catch_weight_uom='kg',
            pick_list_id=pkl_id,
        )
        assert pick_res['tolerance_status'] == 'Within Tolerance'

        # 6. Recalculate order via sales_mcp
        recalc = sales_mcp._recalculate_order_catch_weight(order_id)
        assert float(recalc['recalculated_subtotal']) == 432.0  # 28.8kg * $15 = $432.00
        assert float(recalc['weight_adjustment_amount']) == -18.0

        # 7. Query catch_weight orders filter
        cw_orders = sales_mcp._list_orders(is_catch_weight=True)
        assert any(o['id'] == order_id for o in cw_orders)


# ============================================================================
# 6. Zero-Tolerance & Boundary Condition Tests
# ============================================================================

class TestRealPostgresCatchWeightBoundaryConditions:
    """
    Tests edge cases: 0% strict tolerance, exact threshold boundaries,
    and invalid negative values against PostgreSQL constraints.
    """

    def test_real_postgres_zero_tolerance_strict_checking(self, isolated_tenant):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'Strict Warehouse', 'is_active': True})
        cust = customer_repo.create({'name': 'Strict Customer', 'credit_limit': 10000.0, 'balance': 0.0})

        # 0.0% strict tolerance: exact 1.0kg required
        gold_prod = product_repo.create({
            'name': 'Saffron Box High Value',
            'sku': 'CW-SAFFRON-0TOL',
            'price': 1000.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 1.0,
            'tolerance_pct': 0.0,
            'pricing_basis': 'weight',
            'is_active': True,
        })
        stock_repo.create({'product_id': gold_prod['id'], 'warehouse_id': wh['id'], 'qty': 10.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-CW-ZERO-01',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 1000.0,
            'grand_total': 1000.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': gold_prod['id'],
            'product_name': 'Saffron Box High Value',
            'qty': 1.0,
            'unit_price': 1000.0,
            'line_total': 1000.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 1000.0,
            'nominal_weight': 1.0,
        })

        sales_svc.update(order['id'], {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Weighing 1.01 kg (+1.0% variance > 0.0% tolerance) -> Out of Tolerance
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=1.0,
            catch_weight_actual=1.01,
            catch_weight_uom='kg',
            pick_list_id=pkl['id'],
        )
        assert pick_res['tolerance_status'] == 'Out of Tolerance'

        # Exact 1.000 kg -> Within Tolerance
        pick_res_exact = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=1.0,
            catch_weight_actual=1.000,
            catch_weight_uom='kg',
            pick_list_id=pkl['id'],
        )
        assert pick_res_exact['tolerance_status'] == 'Within Tolerance'

    def test_real_postgres_negative_scale_weight_rejection(self, isolated_tenant):
        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        uom_map = _seed_base_uoms(uom_repo)

        wh = wh_repo.create({'name': 'Negative Weight WH', 'is_active': True})
        cust = customer_repo.create({'name': 'Negative Weight Customer', 'credit_limit': 5000.0, 'balance': 0.0})
        prod = product_repo.create({
            'name': 'Sample Cheese',
            'sku': 'CW-SAMPLE-NEG',
            'price': 100.0,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'nominal_weight': 10.0,
            'tolerance_pct': 5.0,
            'is_active': True,
        })
        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 10.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-CW-NEG-01',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 100.0,
            'grand_total': 100.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': 'Sample Cheese',
            'qty': 1.0,
            'unit_price': 100.0,
            'line_total': 100.0,
            'line_number': 1,
            'is_catch_weight': True,
            'pricing_uom_id': uom_map['kg'],
            'unit_price_pricing_uom': 10.0,
            'nominal_weight': 10.0,
        })

        sales_svc.update(order['id'], {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Negative scale weight must raise ValueError
        with pytest.raises(ValueError, match="Catch weight cannot be negative"):
            pick_svc.pick_item(
                item_id=pli['id'],
                qty_picked=1.0,
                catch_weight_actual=-5.0,
                catch_weight_uom='kg',
                pick_list_id=pkl['id'],
            )


# ============================================================================
# 7. Multi-Tenant Isolation for Catch-Weight Operations
# ============================================================================

class TestRealPostgresCatchWeightTenantIsolation:
    """
    Guarantees strict tenant data partitioning in PostgreSQL across dual-UOM
    products, sales orders, pick lists, scale weights, and invoices.
    """

    def test_real_postgres_tenant_data_isolation(self, real_harness, db_cleaner, real_db_conn):
        from packages.database.isolation import isolated_tenant as isolated_tenant_ctx
        from modules.core.context import tenant_context

        uom_repo = CrudRepository('T0001')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        inv_repo = CrudRepository('T0090')

        with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Alpha") as (tenant_a, _):
            uom_map = _seed_base_uoms(uom_repo)
            wh_a = wh_repo.create({'name': 'Tenant A Warehouse', 'is_active': True})
            cust_a = customer_repo.create({'name': 'Tenant A Customer', 'credit_limit': 10000.0, 'balance': 0.0})

            prod_a = product_repo.create({
                'name': 'Tenant A Exclusive Cheese',
                'sku': 'CW-TENANT-A-01',
                'price': 500.0,
                'is_catch_weight': True,
                'pricing_uom_id': uom_map['kg'],
                'nominal_weight': 25.0,
                'tolerance_pct': 5.0,
                'is_active': True,
            })

            order_a = order_repo.create({
                'order_number': 'SO-TENANT-A-01',
                'customer_id': cust_a['id'],
                'warehouse_id': wh_a['id'],
                'status': 'Draft',
                'subtotal': 500.0,
                'grand_total': 500.0,
                'order_date': '2026-08-26',
            })
            line_a = line_repo.create({
                'sales_order_id': order_a['id'],
                'product_id': prod_a['id'],
                'product_name': 'Tenant A Exclusive Cheese',
                'qty': 1.0,
                'unit_price': 500.0,
                'line_total': 500.0,
                'line_number': 1,
                'is_catch_weight': True,
                'nominal_weight': 25.0,
            })

            # Verify Tenant A sees its product and order
            assert product_repo.get(prod_a['id']) is not None
            assert order_repo.get(order_a['id']) is not None

            # Now switch context to Tenant B
            with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Beta") as (tenant_b, _):
                # Tenant B must NOT see Tenant A's product, order, or customer
                assert product_repo.get(prod_a['id']) is None
                assert order_repo.get(order_a['id']) is None
                assert customer_repo.get(cust_a['id']) is None

                # Tenant B listing products/orders should return 0 records
                assert len(product_repo.list(filters={'sku': 'CW-TENANT-A-01'})) == 0
                assert len(order_repo.list(filters={'order_number': 'SO-TENANT-A-01'})) == 0

        # Unscoped SQL query verifies business_id was stored properly in PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT business_id FROM "Nova".t0003 WHERE sku = \'CW-TENANT-A-01\';')
            # After teardown of tenant_a context, records were cleaned up by cleaner
            row = cur.fetchone()
            assert row is None
