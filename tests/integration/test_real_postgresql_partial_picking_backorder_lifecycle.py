"""
Real PostgreSQL End-to-End Integration Test Suite for Partial Picking, Backordering,
Unpicked Item Status Tracking, Unreserved Stock Release Upon Order Cancellation,
and Remaining Allocation Consistency.

This test suite executes directly against the real PostgreSQL container (schema "Nova"),
verifying:
1. Partial picking progress calculations and line-level unpicked item status tracking (T0101, T0102).
2. Strict pick list completion gating preventing closure when unpicked items remain.
3. Incremental multi-step picking across single and multi-batch lines leading to full completion.
4. Partial order fulfillment and backorder splitting lifecycle (fulfilled delivery vs backorder sales order).
5. Field Sales mobile sync conflict resolution with backorder actions.
6. Order cancellation releasing reserved stock from T0009 and logging 'Unreserve' movements in T0064.
7. Concurrent order reservation isolation (cancellation of Order A preserves Order B's reservations).
8. Consistency of batch allocations (T0088) and physical stock during partial picking and cancellation.
9. Guarding against picking or fulfilling already cancelled sales orders.
10. REST API endpoints and MCP server tool calling for partial picking, cancellation, and stock checks.
11. Multi-tenant isolation for partial picking, backordering, and stock cancellation workflows.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from packages.database.sequence import (
    generate_invoice_number,
    generate_pick_list_number,
)
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.sales.services.field_sales_sync_service import FieldSalesSyncService
from modules.sales.models.field_sales import (
    FieldSalesOrderSubmission,
    FieldSalesOrderLine,
    FieldSalesResolveConflictRequest,
    ConflictResolutionItem,
    ResolutionAction,
)
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService

from modules.inventory.controllers.T0003I import router as product_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from modules.warehouse.controllers.T0088I import router as batch_router
from modules.warehouse.controllers.T0008I import router as wh_router
from modules.accounting.controllers.T0090I import router as invoice_router
from modules.crm.controllers.T0010I import router as customer_router
from modules.sales.controllers.field_sales_controller import router as field_sales_router

from packages.auth.deps import get_current_user
import packages.mcp.servers.inventory_mcp as inv_mcp
import packages.mcp.servers.sales_mcp as sales_mcp
import packages.mcp.servers.warehouse_mcp as wh_mcp
from modules.core.context import set_current_tenant, get_current_tenant


pytestmark = [pytest.mark.real_db, pytest.mark.integration]


TEST_ADMIN = {
    'id': 1,
    'username': 'admin',
    'role': 'Admin',
    'permissions': ['*'],
}


def create_real_db_api_client():
    """Create FastAPI test client with warehouse, sales, inventory, and accounting routers."""
    app = FastAPI(title="Nova Real PostgreSQL Partial Picking & Backorder Test Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(batch_router)
    app.include_router(wh_router)
    app.include_router(invoice_router)
    app.include_router(customer_router)
    app.include_router(field_sales_router)
    return TestClient(app)


def _seed_base_uoms(uom_repo):
    """Ensure standard UOMs exist in T0001."""
    existing = uom_repo.list()
    uom_map = {u['uom_code']: u['id'] for u in existing}
    if 'CASE' not in uom_map:
        rec = uom_repo.create({'uom_code': 'CASE', 'uom_name': 'Case / Box', 'is_active': True})
        uom_map['CASE'] = rec['id']
    if 'EA' not in uom_map:
        rec = uom_repo.create({'uom_code': 'EA', 'uom_name': 'Each', 'is_active': True})
        uom_map['EA'] = rec['id']
    if 'kg' not in uom_map:
        rec = uom_repo.create({'uom_code': 'kg', 'uom_name': 'Kilogram', 'is_active': True})
        uom_map['kg'] = rec['id']
    return uom_map


# ============================================================================
# 1. Partial Picking Progress, Status Tracking & Completion Validation
# ============================================================================

class TestRealPostgresPartialPickingStatusTracking:
    """
    Tests partial picking status tracking, line-level unpicked quantity recording,
    progress percentage calculations, and strict completion blocking.
    """

    def test_partial_picking_progress_and_item_status_tracking(self, isolated_tenant, real_db_conn):
        """
        Verify that picking an order with multiple items tracks individual line progress,
        calculates pick list overall progress percentage, and blocks complete_picking
        when unpicked items remain:
        - Line 1: Ordered 10, Picked 10 (100% picked)
        - Line 2: Ordered 20, Picked 12 (60% picked, 8 unpicked)
        - Line 3: Ordered 5, Picked 1 (20% picked, 4 unpicked)
        - Line 4: Ordered 15, Picked 0 (0% picked, 15 unpicked)
        - Total: Ordered 50, Picked 23 -> Progress = 23 / 50 * 100 = 46.0%
        """
        uom_repo = CrudRepository('T0001')
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        uom_map = _seed_base_uoms(uom_repo)
        wh = wh_repo.create({'name': 'Central Picking Warehouse', 'location': 'Aisle 1-4', 'is_active': True})
        wh_id = wh['id']

        cust = cust_repo.create({'name': 'Boutique Grocery Group', 'credit_limit': 50000.0, 'balance': 0.0, 'is_active': True})

        p1 = prod_repo.create({'name': 'Espresso Beans 1kg', 'sku': 'COF-ESP-1K', 'price': 20.0, 'is_active': True})
        p2 = prod_repo.create({'name': 'Colombian Roast 1kg', 'sku': 'COF-COL-1K', 'price': 18.0, 'is_active': True})
        p3 = prod_repo.create({'name': 'French Vanilla Syrup 750ml', 'sku': 'SYR-VAN-750', 'price': 12.0, 'is_active': True})
        p4 = prod_repo.create({'name': 'Caramel Sauce 500g', 'sku': 'SAU-CAR-500', 'price': 8.0, 'is_active': True})

        # Seed physical stock in T0009
        stock_repo.create({'product_id': p1['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p2['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p3['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p4['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})

        # Create Sales Order for 50 items total
        # Subtotal: 10*20 + 20*18 + 5*12 + 15*8 = 200 + 360 + 60 + 120 = 740
        order = order_repo.create({
            'order_number': 'SO-PART-PICK-001',
            'customer_id': cust['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 740.0,
            'tax': 74.0,
            'grand_total': 814.0,
            'order_date': str(date.today()),
        })
        order_id = order['id']

        line_repo.create({'sales_order_id': order_id, 'product_id': p1['id'], 'product_name': 'Espresso Beans 1kg', 'qty': 10.0, 'unit_price': 20.0, 'line_total': 200.0, 'line_number': 1})
        line_repo.create({'sales_order_id': order_id, 'product_id': p2['id'], 'product_name': 'Colombian Roast 1kg', 'qty': 20.0, 'unit_price': 18.0, 'line_total': 360.0, 'line_number': 2})
        line_repo.create({'sales_order_id': order_id, 'product_id': p3['id'], 'product_name': 'French Vanilla Syrup 750ml', 'qty': 5.0, 'unit_price': 12.0, 'line_total': 60.0, 'line_number': 3})
        line_repo.create({'sales_order_id': order_id, 'product_id': p4['id'], 'product_name': 'Caramel Sauce 500g', 'qty': 15.0, 'unit_price': 8.0, 'line_total': 120.0, 'line_number': 4})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # Confirm order -> Generates pick list and reserves stock
        sales_svc.update(order_id, {'status': 'Confirmed'})

        # Retrieve pick list
        pick_lists = pl_repo.list(filters={'sales_order_id': order_id})
        assert len(pick_lists) == 1
        pl = pick_lists[0]
        pl_id = pl['id']

        # Start picking
        pick_svc.start_picking(pl_id)
        assert pl_repo.get(pl_id)['status'] == 'In Progress'

        # Get pick list items
        items = pli_repo.list(filters={'pick_list_id': pl_id}, order_by='line_number')
        assert len(items) == 4

        item1, item2, item3, item4 = items

        # Partial picking execution
        # Item 1: fully pick 10
        pick_svc.pick_item(item1['id'], qty_picked=10.0, pick_list_id=pl_id)
        # Item 2: partially pick 12 of 20
        pick_svc.pick_item(item2['id'], qty_picked=12.0, pick_list_id=pl_id)
        # Item 3: partially pick 1 of 5
        pick_svc.pick_item(item3['id'], qty_picked=1.0, pick_list_id=pl_id)
        # Item 4: left at 0 of 15

        # Query pick list with items and verify progress calculation
        pl_detailed = pick_svc.get_with_items(pl_id)
        assert pl_detailed['status'] == 'In Progress'
        # 23 / 50 = 46.0%
        assert pl_detailed['progress_pct'] == 46.0

        # Verify individual items in PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT id, product_id, qty_ordered, qty_picked FROM "Nova".t0102 WHERE pick_list_id = %s ORDER BY line_number;',
                (pl_id,)
            )
            rows = cur.fetchall()
            assert len(rows) == 4
            assert float(rows[0]['qty_ordered']) == 10.0 and float(rows[0]['qty_picked']) == 10.0
            assert float(rows[1]['qty_ordered']) == 20.0 and float(rows[1]['qty_picked']) == 12.0
            assert float(rows[2]['qty_ordered']) == 5.0 and float(rows[2]['qty_picked']) == 1.0
            assert float(rows[3]['qty_ordered']) == 15.0 and float(rows[3]['qty_picked']) == 0.0

        # Attempt to complete picking while items remain unpicked -> MUST fail
        with pytest.raises(ValueError) as excinfo:
            pick_svc.complete_picking(pl_id)

        err_msg = str(excinfo.value)
        assert "Cannot complete pick list" in err_msg
        assert "Colombian Roast 1kg" in err_msg or str(p2['id']) in err_msg
        assert "French Vanilla Syrup 750ml" in err_msg or str(p3['id']) in err_msg
        assert "Caramel Sauce 500g" in err_msg or str(p4['id']) in err_msg

        # Verify pick list and order statuses remained unchanged in PostgreSQL
        assert pl_repo.get(pl_id)['status'] == 'In Progress'
        assert order_repo.get(order_id)['status'] == 'Confirmed'

    def test_incremental_multi_step_picking_to_full_completion(self, isolated_tenant, real_db_conn):
        """
        Verify picking can occur incrementally over multiple passes until 100% is reached:
        - Pass 1: Item A picked 4/10 -> progress 20.0% -> completion blocked.
        - Pass 2: Item A picked remaining 6/10 -> progress 50.0% -> completion blocked.
        - Pass 3: Item B picked 5/10 -> progress 75.0% -> completion blocked.
        - Pass 4: Item B picked remaining 5/10 -> progress 100.0% -> completion SUCCEEDS.
        - Status transitions to Completed and Shipped.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        wh = wh_repo.create({'name': 'Incremental Pick Hub', 'is_active': True})
        cust = cust_repo.create({'name': 'Incremental Cafe', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})

        p_a = prod_repo.create({'name': 'Organic Tea A', 'sku': 'TEA-A', 'price': 10.0, 'is_active': True})
        p_b = prod_repo.create({'name': 'Organic Tea B', 'sku': 'TEA-B', 'price': 10.0, 'is_active': True})

        stock_repo.create({'product_id': p_a['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p_b['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-INCR-PICK-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 200.0,
            'grand_total': 200.0,
            'order_date': str(date.today()),
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': p_a['id'], 'product_name': 'Organic Tea A', 'qty': 10.0, 'unit_price': 10.0, 'line_total': 100.0, 'line_number': 1})
        line_repo.create({'sales_order_id': order['id'], 'product_id': p_b['id'], 'product_name': 'Organic Tea B', 'qty': 10.0, 'unit_price': 10.0, 'line_total': 100.0, 'line_number': 2})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        sales_svc.update(order['id'], {'status': 'Confirmed'})
        pl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pick_svc.start_picking(pl['id'])

        items = pli_repo.list(filters={'pick_list_id': pl['id']}, order_by='line_number')
        item_a, item_b = items[0], items[1]

        # Pass 1
        pick_svc.pick_item(item_a['id'], qty_picked=4.0, pick_list_id=pl['id'])
        assert pick_svc.get_with_items(pl['id'])['progress_pct'] == 20.0
        with pytest.raises(ValueError):
            pick_svc.complete_picking(pl['id'])

        # Pass 2
        pick_svc.pick_item(item_a['id'], qty_picked=10.0, pick_list_id=pl['id'])
        assert pick_svc.get_with_items(pl['id'])['progress_pct'] == 50.0
        with pytest.raises(ValueError):
            pick_svc.complete_picking(pl['id'])

        # Pass 3
        pick_svc.pick_item(item_b['id'], qty_picked=5.0, pick_list_id=pl['id'])
        assert pick_svc.get_with_items(pl['id'])['progress_pct'] == 75.0
        with pytest.raises(ValueError):
            pick_svc.complete_picking(pl['id'])

        # Pass 4 - fully picked
        pick_svc.pick_item(item_b['id'], qty_picked=10.0, pick_list_id=pl['id'])
        assert pick_svc.get_with_items(pl['id'])['progress_pct'] == 100.0

        # Complete picking succeeds
        completed = pick_svc.complete_picking(pl['id'])
        assert completed['status'] == 'Completed'
        assert order_repo.get(order['id'])['status'] == 'Shipped'


# ============================================================================
# 2. Partial Fulfillment, Backorder Generation & Splitting
# ============================================================================

class TestRealPostgresPartialFulfillmentAndBackorderSplitting:
    """
    Tests partial fulfillment scenarios where unpicked/unfulfilled items
    are split into backorders (Backorder Sales Orders):
    - Original order quantity is fulfilled and shipped/invoiced for the available portion.
    - Backorder is generated for the remaining quantity with status 'Draft'/'Pending'.
    - Financial calculations and customer balances reflect exact fulfilled delivery.
    """

    def test_partial_order_fulfillment_and_backorder_splitting_lifecycle(self, isolated_tenant, real_db_conn):
        """
        Verify end-to-end partial fulfillment with backorder creation:
        - Customer orders 50 units of Prod A and 30 units of Prod B ($1300 total).
        - Warehouse can only fulfill 30 units of Prod A and 20 units of Prod B.
        - Original order is adjusted to fulfilled qty (30 Prod A + 20 Prod B = $800 subtotal).
        - Backorder SO is created for remaining 20 units of Prod A and 10 units of Prod B ($500 subtotal).
        - Fulfilled order progresses: Confirmed -> Picked -> Shipped -> Delivered -> Invoiced.
        - Customer balance is incremented only by $800 + tax (not $1300 + tax).
        - Backorder remains in 'Draft' waiting for restock.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')

        wh = wh_repo.create({'name': 'Backorder WH', 'is_active': True})
        cust = cust_repo.create({'name': 'Retail Supercenter', 'credit_limit': 100000.0, 'balance': 0.0, 'is_active': True})

        prod_a = prod_repo.create({'name': 'Artisanal Pasta 500g', 'sku': 'PASTA-500G', 'price': 20.0, 'is_active': True})
        prod_b = prod_repo.create({'name': 'Tomato Basil Sauce 500ml', 'sku': 'SAUCE-500ML', 'price': 10.0, 'is_active': True})

        # Seed physical stock: Prod A has 30 available, Prod B has 20 available
        stock_a = stock_repo.create({'product_id': prod_a['id'], 'warehouse_id': wh['id'], 'qty': 30.0, 'reserved_qty': 0.0})
        stock_b = stock_repo.create({'product_id': prod_b['id'], 'warehouse_id': wh['id'], 'qty': 20.0, 'reserved_qty': 0.0})

        # 1. Create Initial Sales Order (50 Prod A, 30 Prod B)
        orig_order = order_repo.create({
            'order_number': 'SO-ORIG-FULFILL-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 1300.0,  # 50*20 + 30*10 = 1000 + 300
            'tax': 130.0,
            'grand_total': 1430.0,
            'order_date': str(date.today()),
        })
        line_a = line_repo.create({'sales_order_id': orig_order['id'], 'product_id': prod_a['id'], 'product_name': 'Artisanal Pasta 500g', 'qty': 50.0, 'unit_price': 20.0, 'line_total': 1000.0, 'line_number': 1})
        line_b = line_repo.create({'sales_order_id': orig_order['id'], 'product_id': prod_b['id'], 'product_name': 'Tomato Basil Sauce 500ml', 'qty': 30.0, 'unit_price': 10.0, 'line_total': 300.0, 'line_number': 2})

        # 2. Adjust original order lines to available quantities and generate backorder order
        # Fulfilled part: 30 of Prod A ($600), 20 of Prod B ($200) -> Subtotal $800, Tax $80, Grand Total $880
        line_repo.update(line_a['id'], {'qty': 30.0, 'line_total': 600.0})
        line_repo.update(line_b['id'], {'qty': 20.0, 'line_total': 200.0})
        order_repo.update(orig_order['id'], {'subtotal': 800.0, 'tax': 80.0, 'grand_total': 880.0})

        # Backorder part: 20 of Prod A ($400), 10 of Prod B ($100) -> Subtotal $500, Tax $50, Grand Total $550
        backorder = order_repo.create({
            'order_number': f"{orig_order['order_number']}-BO",
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 500.0,
            'tax': 50.0,
            'grand_total': 550.0,
            'notes': f"Backorder for unfulfilled items from order {orig_order['order_number']}",
            'order_date': str(date.today()),
        })
        line_repo.create({'sales_order_id': backorder['id'], 'product_id': prod_a['id'], 'product_name': 'Artisanal Pasta 500g', 'qty': 20.0, 'unit_price': 20.0, 'line_total': 400.0, 'line_number': 1})
        line_repo.create({'sales_order_id': backorder['id'], 'product_id': prod_b['id'], 'product_name': 'Tomato Basil Sauce 500ml', 'qty': 10.0, 'unit_price': 10.0, 'line_total': 100.0, 'line_number': 2})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # 3. Confirm and fulfill the adjusted original order
        sales_svc.update(orig_order['id'], {'status': 'Confirmed'})

        # Verify stock reservation in T0009 for the fulfilled portion
        assert float(stock_repo.get(stock_a['id'])['reserved_qty']) == 30.0
        assert float(stock_repo.get(stock_b['id'])['reserved_qty']) == 20.0

        # Pick and complete original order
        pl_orig = pl_repo.list(filters={'sales_order_id': orig_order['id']})[0]
        pick_svc.start_picking(pl_orig['id'])
        items = pli_repo.list(filters={'pick_list_id': pl_orig['id']}, order_by='line_number')

        pick_svc.pick_item(items[0]['id'], qty_picked=30.0, pick_list_id=pl_orig['id'])
        pick_svc.pick_item(items[1]['id'], qty_picked=20.0, pick_list_id=pl_orig['id'])
        pick_svc.complete_picking(pl_orig['id'])

        assert order_repo.get(orig_order['id'])['status'] == 'Shipped'

        # Deliver original order -> Invoiced & customer balance updated
        sales_svc.update(orig_order['id'], {'status': 'Delivered'})

        # Verify invoice created for $880
        invoices = inv_repo.list(filters={'sales_order_id': orig_order['id']})
        assert len(invoices) == 1
        assert float(invoices[0]['total_amount']) == 880.0

        # Verify customer balance is exactly $880.0
        cust_after = cust_repo.get(cust['id'])
        assert float(cust_after['balance']) == 880.0

        # 4. Verify Backorder Order in PostgreSQL
        bo_in_db = order_repo.get(backorder['id'])
        assert bo_in_db['status'] == 'Draft'
        assert bo_in_db['order_number'] == 'SO-ORIG-FULFILL-001-BO'
        assert float(bo_in_db['grand_total']) == 550.0

        bo_lines = line_repo.list(filters={'sales_order_id': backorder['id']}, order_by='line_number')
        assert len(bo_lines) == 2
        assert float(bo_lines[0]['qty']) == 20.0
        assert float(bo_lines[1]['qty']) == 10.0

    def test_field_sales_mobile_sync_backorder_action_resolution(self, isolated_tenant, real_db_conn):
        """
        Verify Field Sales mobile sync conflict resolution using ResolutionAction.BACKORDER:
        - Rep submits order for 30 units when only 10 are available.
        - Rep marks item action as 'backorder'.
        - Sync resolves order with [BACKORDER] tag preserved in line notes.
        - Order is persisted in PostgreSQL with client_order_uuid and sync_status='Synced'.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'Field Sync WH', 'is_active': True})
        cust = cust_repo.create({'name': 'Field Customer', 'credit_limit': 20000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'Specialty Olive Tapenade', 'sku': f'TAPENADE-100G-SYNC-{isolated_tenant}', 'price': 15.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 10.0, 'reserved_qty': 0.0})

        sync_svc = FieldSalesSyncService()

        client_uuid = f'uuid-backorder-test-{isolated_tenant}'
        # Order submission with 30 units (10 available)
        submission = FieldSalesOrderSubmission(
            client_order_uuid=client_uuid,
            customer_id=cust['id'],
            warehouse_id=wh['id'],
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=prod['id'],
                    product_name='Specialty Olive Tapenade',
                    qty=30.0,
                    unit_price=15.0,
                    line_total=450.0,
                    notes='Customer specifically requested full batch',
                )
            ],
        )

        # Resolve conflict by choosing BACKORDER action
        resolve_req = FieldSalesResolveConflictRequest(
            client_order_uuid=client_uuid,
            order_data=submission,
            resolutions=[
                ConflictResolutionItem(
                    line_number=1,
                    product_id=prod['id'],
                    action=ResolutionAction.BACKORDER.value,
                )
            ],
        )

        result = sync_svc.resolve_and_sync(resolve_req)
        assert result.status == 'Synced'
        assert result.server_order_id is not None

        # Verify in PostgreSQL
        db_order = order_repo.get(result.server_order_id)
        assert db_order is not None
        assert db_order['client_order_uuid'] == client_uuid

        lines = line_repo.list(filters={'sales_order_id': result.server_order_id})
        assert len(lines) == 1
        assert float(lines[0]['qty']) == 30.0
        # Line notes must contain [BACKORDER] tag
        assert '[BACKORDER]' in lines[0].get('notes', '') or 'BACKORDER' in str(lines[0])


# ============================================================================
# 3. Stock Reservation & Unreserved Stock Release Upon Order Cancellation
# ============================================================================

class TestRealPostgresStockReservationAndCancellationRelease:
    """
    Tests stock reservation mechanics in T0009 and unreserved stock release upon
    order cancellation, verifying exact stock level preservation and movement audit logs.
    """

    def test_order_cancellation_releases_stock_reservations_cleanly(self, isolated_tenant, real_db_conn):
        """
        Verify that confirming an order increases reserved_qty in T0009 and logs 'Reserve' in T0064,
        and cancelling the order reduces reserved_qty back to initial state and logs 'Unreserve' in T0064:
        - Product 1: Stock=100, Order Qty=25 -> Reserved goes 0 -> 25 -> 0.
        - Product 2: Stock=80, Order Qty=30 -> Reserved goes 0 -> 30 -> 0.
        - T0064 logs exact reference_type='sales_order' and reference_id=order_id.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        movement_repo = CrudRepository('T0064')

        wh = wh_repo.create({'name': 'Cancel Release WH', 'is_active': True})
        wh_id = wh['id']
        cust = cust_repo.create({'name': 'Cancel Test Client', 'credit_limit': 50000.0, 'balance': 0.0, 'is_active': True})

        p1 = prod_repo.create({'name': 'Item Cancel Alpha', 'sku': 'ITEM-CANC-A', 'price': 10.0, 'is_active': True})
        p2 = prod_repo.create({'name': 'Item Cancel Beta', 'sku': 'ITEM-CANC-B', 'price': 20.0, 'is_active': True})

        s1 = stock_repo.create({'product_id': p1['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        s2 = stock_repo.create({'product_id': p2['id'], 'warehouse_id': wh_id, 'qty': 80.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-CANC-RELEASE-001',
            'customer_id': cust['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 850.0,  # 25*10 + 30*20 = 250 + 600
            'grand_total': 850.0,
            'order_date': str(date.today()),
        })
        order_id = order['id']

        line_repo.create({'sales_order_id': order_id, 'product_id': p1['id'], 'product_name': 'Item Cancel Alpha', 'qty': 25.0, 'unit_price': 10.0, 'line_total': 250.0, 'line_number': 1})
        line_repo.create({'sales_order_id': order_id, 'product_id': p2['id'], 'product_name': 'Item Cancel Beta', 'qty': 30.0, 'unit_price': 20.0, 'line_total': 600.0, 'line_number': 2})

        sales_svc = SalesOrderService(order_repo)

        # 1. Confirm Order -> Reserves Stock
        sales_svc.update(order_id, {'status': 'Confirmed'})

        # Verify reservations
        db_s1 = stock_repo.get(s1['id'])
        db_s2 = stock_repo.get(s2['id'])
        assert float(db_s1['qty']) == 100.0
        assert float(db_s1['reserved_qty']) == 25.0
        assert float(db_s2['qty']) == 80.0
        assert float(db_s2['reserved_qty']) == 30.0

        # Verify Reserve movements in T0064
        reserve_moves = movement_repo.list(filters={'reference_id': order_id, 'movement_type': 'Reserve'})
        assert len(reserve_moves) == 2

        # 2. Cancel Order -> Unreserves Stock
        sales_svc.update(order_id, {'status': 'Cancelled'})

        # Verify unreserved stock in PostgreSQL
        db_s1_after = stock_repo.get(s1['id'])
        db_s2_after = stock_repo.get(s2['id'])
        assert float(db_s1_after['qty']) == 100.0
        assert float(db_s1_after['reserved_qty']) == 0.0, "Reserved quantity for Product 1 must be reset to 0"
        assert float(db_s2_after['qty']) == 80.0
        assert float(db_s2_after['reserved_qty']) == 0.0, "Reserved quantity for Product 2 must be reset to 0"

        # Verify Unreserve movements in T0064
        unreserve_moves = movement_repo.list(filters={'reference_id': order_id, 'movement_type': 'Unreserve'})
        assert len(unreserve_moves) == 2
        for move in unreserve_moves:
            assert move['reference_type'] == 'sales_order'
            assert float(move['qty_change']) == 0.0

        # Verify order status is 'Cancelled'
        assert order_repo.get(order_id)['status'] == 'Cancelled'

    def test_concurrent_order_isolation_on_single_order_cancellation(self, isolated_tenant, real_db_conn):
        """
        Verify that cancelling one order does not affect the reservations or status of another active confirmed order:
        - Stock = 100
        - Order 1 requests 20 units -> reserved = 20
        - Order 2 requests 35 units -> reserved = 55
        - Order 1 is cancelled -> reserved drops to 35 (Order 2's 35 remains reserved!)
        - Order 2 can be fulfilled and shipped successfully.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        wh = wh_repo.create({'name': 'Shared Stock WH', 'is_active': True})
        wh_id = wh['id']
        cust1 = cust_repo.create({'name': 'Client 1', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
        cust2 = cust_repo.create({'name': 'Client 2', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})

        prod = prod_repo.create({'name': 'Shared Product Widget', 'sku': 'WIDGET-SH-01', 'price': 10.0, 'is_active': True})
        stock = stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})

        # Order 1 (20 units)
        so1 = order_repo.create({'order_number': 'SO-CONC-ISO-01', 'customer_id': cust1['id'], 'warehouse_id': wh_id, 'status': 'Draft', 'grand_total': 200.0})
        line_repo.create({'sales_order_id': so1['id'], 'product_id': prod['id'], 'product_name': 'Shared Product Widget', 'qty': 20.0, 'unit_price': 10.0, 'line_total': 200.0, 'line_number': 1})

        # Order 2 (35 units)
        so2 = order_repo.create({'order_number': 'SO-CONC-ISO-02', 'customer_id': cust2['id'], 'warehouse_id': wh_id, 'status': 'Draft', 'grand_total': 350.0})
        line_repo.create({'sales_order_id': so2['id'], 'product_id': prod['id'], 'product_name': 'Shared Product Widget', 'qty': 35.0, 'unit_price': 10.0, 'line_total': 350.0, 'line_number': 1})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # Confirm both orders
        sales_svc.update(so1['id'], {'status': 'Confirmed'})
        sales_svc.update(so2['id'], {'status': 'Confirmed'})

        # Total reserved = 55
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 55.0

        # Cancel Order 1
        sales_svc.update(so1['id'], {'status': 'Cancelled'})

        # Reserved drops to exactly 35 (Order 2's reservation)
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 35.0
        assert order_repo.get(so1['id'])['status'] == 'Cancelled'
        assert order_repo.get(so2['id'])['status'] == 'Confirmed'

        # Fulfill Order 2 completely
        pl2 = pl_repo.list(filters={'sales_order_id': so2['id']})[0]
        pick_svc.start_picking(pl2['id'])
        pli2 = pli_repo.list(filters={'pick_list_id': pl2['id']})[0]
        pick_svc.pick_item(pli2['id'], qty_picked=35.0, pick_list_id=pl2['id'])
        pick_svc.complete_picking(pl2['id'])

        assert order_repo.get(so2['id'])['status'] == 'Shipped'

    def test_partial_picking_cancellation_and_unreserved_stock_release(self, isolated_tenant, real_db_conn):
        """
        Verify that if an order has been partially picked (e.g. 15 of 40 picked)
        and the order is subsequently cancelled before completion:
        - All 40 units of reserved stock are cleanly released.
        - Physical quantity in T0009 remains 100.0.
        - Reserved quantity in T0009 returns to 0.0.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        wh = wh_repo.create({'name': 'Partial Cancel WH', 'is_active': True})
        cust = cust_repo.create({'name': 'Partial Cancel Client', 'credit_limit': 20000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'Specialty Olive Oil 500ml', 'sku': 'OIL-500ML', 'price': 15.0, 'is_active': True})

        stock = stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 100.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-PART-CANC-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 600.0,
            'grand_total': 600.0,
            'order_date': str(date.today()),
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod['id'], 'product_name': 'Specialty Olive Oil 500ml', 'qty': 40.0, 'unit_price': 15.0, 'line_total': 600.0, 'line_number': 1})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        sales_svc.update(order['id'], {'status': 'Confirmed'})
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 40.0

        # Start picking and partially pick 15 units
        pl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pick_svc.start_picking(pl['id'])
        pli = pli_repo.list(filters={'pick_list_id': pl['id']})[0]
        pick_svc.pick_item(pli['id'], qty_picked=15.0, pick_list_id=pl['id'])

        # Customer calls to cancel the order
        sales_svc.update(order['id'], {'status': 'Cancelled'})

        # Verify reservations are 100% released in PostgreSQL
        db_stock = stock_repo.get(stock['id'])
        assert float(db_stock['qty']) == 100.0
        assert float(db_stock['reserved_qty']) == 0.0
        assert order_repo.get(order['id'])['status'] == 'Cancelled'


# ============================================================================
# 4. Remaining Allocation Consistency & Batch Invariants
# ============================================================================

class TestRealPostgresRemainingAllocationConsistencyAndBatchInvariants:
    """
    Tests consistency of batch quantities (T0088), physical stock (T0009),
    and pick list allocations during partial picks, overrides, and cancellations.
    """

    def test_batch_allocation_consistency_during_partial_picks_and_cancellation(self, isolated_tenant, real_db_conn):
        """
        Verify multi-batch FEFO lot allocation integrity:
        - Lot A (10 units, exp 2026-04-01), Lot B (15 units, exp 2026-06-01).
        - Order for 20 units confirmed -> FEFO allocates Lot A (10) and Lot B (10).
        - Picker picks Lot A (10 units) and Lot B (5 units) -> 5 units unpicked.
        - Batch records in T0088 remain untouched (10 and 15) until pick list is completed.
        - When order is cancelled:
          - Both batches in T0088 remain intact (10 and 15).
          - Reserved stock in T0009 is released (20 -> 0).
          - No batch corruption occurs.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        wh = wh_repo.create({'name': 'Batch Invariant WH', 'is_active': True})
        wh_id = wh['id']
        cust = cust_repo.create({'name': 'Batch Cust', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'Cheddar Block 1kg', 'sku': 'CHED-1KG', 'price': 12.0, 'is_active': True})
        prod_id = prod['id']

        stock = stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_id, 'qty': 25.0, 'reserved_qty': 0.0})

        # Seed Batches in T0088
        b_a = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-CHED-A', 'expiry_date': '2026-04-01', 'quantity': 10.0, 'warehouse_id': wh_id, 'status': 'Available'})
        b_b = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-CHED-B', 'expiry_date': '2026-06-01', 'quantity': 15.0, 'warehouse_id': wh_id, 'status': 'Available'})

        order = order_repo.create({
            'order_number': 'SO-BATCH-CONSIST-01',
            'customer_id': cust['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 240.0,
            'grand_total': 240.0,
            'order_date': str(date.today()),
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod_id, 'product_name': 'Cheddar Block 1kg', 'qty': 20.0, 'unit_price': 12.0, 'line_total': 240.0, 'line_number': 1})

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # Confirm order
        sales_svc.update(order['id'], {'status': 'Confirmed'})

        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        items = pli_repo.list(filters={'pick_list_id': pkl['id']}, order_by='line_number')
        assert len(items) == 2

        # Start picking
        pick_svc.start_picking(pkl['id'])
        # Pick 10 of Lot A, 5 of Lot B
        pick_svc.pick_item(items[0]['id'], qty_picked=10.0, pick_list_id=pkl['id'])
        pick_svc.pick_item(items[1]['id'], qty_picked=5.0, pick_list_id=pkl['id'])

        # Verify batch quantities in T0088 are NOT yet depleted (completion required)
        assert float(batch_repo.get(b_a['id'])['quantity']) == 10.0
        assert float(batch_repo.get(b_b['id'])['quantity']) == 15.0

        # Cancel order
        sales_svc.update(order['id'], {'status': 'Cancelled'})

        # Verify batch quantities in PostgreSQL remain exactly 10 and 15
        assert float(batch_repo.get(b_a['id'])['quantity']) == 10.0
        assert float(batch_repo.get(b_b['id'])['quantity']) == 15.0
        assert batch_repo.get(b_a['id'])['status'] == 'Available'
        assert batch_repo.get(b_b['id'])['status'] == 'Available'

        # Verify stock reservation in T0009 is released
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 0.0
        assert float(stock_repo.get(stock['id'])['qty']) == 25.0

    def test_cancelled_order_blocks_subsequent_fulfillment_and_invoicing(self, isolated_tenant, real_db_conn):
        """
        Verify that once an order is Cancelled, attempting to transition to Shipped, Delivered, or Invoiced
        is strictly rejected by status machine validation.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'Terminal State WH', 'is_active': True})
        cust = cust_repo.create({'name': 'Terminal State Cust', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'Widget X', 'sku': 'WID-X', 'price': 10.0, 'is_active': True})

        order = order_repo.create({
            'order_number': 'SO-TERMINAL-CANC-01',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Cancelled',
            'subtotal': 100.0,
            'grand_total': 100.0,
        })

        sales_svc = SalesOrderService(order_repo)

        # Attempt to transition cancelled order to Shipped, Delivered, Invoiced -> All must fail with 400
        for target in ['Confirmed', 'Shipped', 'Delivered', 'Invoiced', 'Paid']:
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order['id'], {'status': target})
            assert excinfo.value.status_code == 400
            assert "Invalid status transition" in excinfo.value.detail


# ============================================================================
# 5. REST API & MCP Server Tooling for Partial Picking & Cancellation
# ============================================================================

class TestRealPostgresPartialPickingRestApiAndMcp:
    """
    Tests REST API endpoints and MCP server tool executions for partial picking,
    pick list progress inspection, and order cancellation.
    """

    def test_rest_api_partial_picking_and_cancellation_flow(self, isolated_tenant, real_db_conn):
        """
        Verify REST API workflow:
        1. POST /api/T0012I -> Create Draft order.
        2. PUT /api/T0012I/{id} -> Confirm order (creates pick list & reserves stock).
        3. GET /api/T0101I -> Query pick lists.
        4. PUT /api/T0102I/{id} -> Partially pick item.
        5. PUT /api/T0012I/{id} -> Cancel order (releases reserved stock).
        """
        client = create_real_db_api_client()
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'REST WH', 'is_active': True})
        cust = cust_repo.create({'name': 'REST Customer', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'REST Product 1', 'sku': 'REST-PROD-1', 'price': 25.0, 'is_active': True})

        stock = stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})

        # 1. Create order
        resp_create = client.post('/api/T0012I', json={
            'order_number': 'SO-REST-PART-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 250.0,
            'grand_total': 250.0,
            'status': 'Draft',
        })
        assert resp_create.status_code in (200, 201)
        order_id = resp_create.json()['id']

        # Add line
        line_repo.create({'sales_order_id': order_id, 'product_id': prod['id'], 'product_name': 'REST Product 1', 'qty': 10.0, 'unit_price': 25.0, 'line_total': 250.0, 'line_number': 1})

        # 2. Confirm order
        resp_conf = client.put(f'/api/T0012I/{order_id}', json={'status': 'Confirmed'})
        assert resp_conf.status_code == 200
        assert resp_conf.json()['status'] == 'Confirmed'

        # Verify stock reserved
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 10.0

        # 3. Query pick list and start picking
        resp_pl = client.get('/api/T0101I', params={'sales_order_id': order_id})
        assert resp_pl.status_code == 200
        pick_lists = resp_pl.json()
        assert len(pick_lists) >= 1
        pl_id = pick_lists[0]['id']

        resp_start = client.post(f'/api/T0101I/{pl_id}/start')
        assert resp_start.status_code == 200
        assert resp_start.json()['status'] == 'In Progress'

        # Query pick list items via detail endpoint
        resp_detail = client.get(f'/api/T0101I/{pl_id}/detail')
        assert resp_detail.status_code == 200
        items = resp_detail.json().get('items', [])
        assert len(items) == 1
        pli_id = items[0]['id']

        # 4. Partially pick item (4 of 10)
        resp_pick = client.post(f'/api/T0101I/{pl_id}/pick-item/{pli_id}', json={'qty_picked': 4.0})
        assert resp_pick.status_code == 200
        assert float(resp_pick.json()['qty_picked']) == 4.0

        # Query detail again to check progress
        resp_detail2 = client.get(f'/api/T0101I/{pl_id}/detail')
        assert resp_detail2.json()['progress_pct'] == 40.0

        # 5. Cancel order via REST API
        resp_cancel = client.put(f'/api/T0012I/{order_id}', json={'status': 'Cancelled'})
        assert resp_cancel.status_code == 200
        assert resp_cancel.json()['status'] == 'Cancelled'

        # Verify stock reservation released
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 0.0

    def test_mcp_servers_partial_picking_and_cancellation(self, isolated_tenant, real_db_conn):
        """
        Verify MCP server tool executions:
        - sales_mcp._confirm_order
        - inv_mcp._check_stock
        - wh_mcp._list_pick_lists
        - sales_mcp._cancel_order
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'MCP Pick WH', 'is_active': True})
        cust = cust_repo.create({'name': 'MCP Pick Customer', 'credit_limit': 15000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': 'MCP Almond Milk', 'sku': 'ALM-MILK-1L', 'price': 5.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 40.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-MCP-PART-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 50.0,
            'grand_total': 50.0,
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod['id'], 'product_name': 'MCP Almond Milk', 'qty': 10.0, 'unit_price': 5.0, 'line_total': 50.0, 'line_number': 1})

        # Confirm via sales MCP
        conf_res = sales_mcp._confirm_order(order['id'])
        assert conf_res['status'] == 'Confirmed'

        # Check stock via inventory MCP
        stock_info = inv_mcp._check_stock(prod['id'], warehouse_id=wh['id'])
        assert len(stock_info) == 1
        assert float(stock_info[0]['qty']) == 40.0
        assert float(stock_info[0]['reserved_qty']) == 10.0
        assert float(stock_info[0]['available_qty']) == 30.0

        # Query pick lists via warehouse MCP
        pls = wh_mcp._list_pick_lists(sales_order_id=order['id'])
        assert len(pls) >= 1
        assert pls[0]['sales_order_id'] == order['id']

        # Cancel order via sales MCP
        cancel_res = sales_mcp._cancel_order(order['id'])
        assert cancel_res['status'] == 'Cancelled'

        # Check stock again via inventory MCP -> reserved should be 0, available 40
        stock_info_after = inv_mcp._check_stock(prod['id'], warehouse_id=wh['id'])
        assert len(stock_info_after) == 1
        assert float(stock_info_after[0]['reserved_qty']) == 0.0
        assert float(stock_info_after[0]['available_qty']) == 40.0


# ============================================================================
# 6. Multi-Tenant Isolation for Partial Picking & Backorders
# ============================================================================

class TestRealPostgresMultiTenantPartialPickingIsolation:
    """
    Verifies multi-tenant isolation ensuring partial picking, backordering, and stock cancellation
    in Tenant A do not leak, affect, or expose records to Tenant B.
    """

    def test_multi_tenant_partial_picking_and_cancellation_isolation(self, real_db, real_harness, db_cleaner, real_db_conn):
        """
        Create two isolated tenants:
        - Tenant A creates Order A for Product A, picks partially, and cancels.
        - Tenant B creates Order B for Product B, confirms and holds stock reservation.
        - Actions in Tenant A must NOT alter Tenant B's reservations or pick lists.
        """
        from packages.database.isolation import isolated_tenant as isolated_tenant_ctx

        with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Alpha Corp") as (tenant_a_id, _):
            # Tenant A Setup
            prod_repo_a = CrudRepository('T0003')
            wh_repo_a = CrudRepository('T0008')
            stock_repo_a = CrudRepository('T0009')
            cust_repo_a = CrudRepository('T0010')
            order_repo_a = CrudRepository('T0012')
            line_repo_a = CrudRepository('T0013')
            pl_repo_a = CrudRepository('T0101')
            pli_repo_a = CrudRepository('T0102')

            wh_a = wh_repo_a.create({'name': 'Tenant A WH', 'is_active': True})
            cust_a = cust_repo_a.create({'name': 'Tenant A Customer', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
            prod_a = prod_repo_a.create({'name': 'Tenant A Product', 'sku': 'TEN-A-PROD', 'price': 10.0, 'is_active': True})
            stock_a = stock_repo_a.create({'product_id': prod_a['id'], 'warehouse_id': wh_a['id'], 'qty': 50.0, 'reserved_qty': 0.0})

            order_a = order_repo_a.create({'order_number': 'SO-TENANT-A-01', 'customer_id': cust_a['id'], 'warehouse_id': wh_a['id'], 'status': 'Draft', 'grand_total': 100.0})
            line_repo_a.create({'sales_order_id': order_a['id'], 'product_id': prod_a['id'], 'product_name': 'Tenant A Product', 'qty': 10.0, 'unit_price': 10.0, 'line_total': 100.0, 'line_number': 1})

            sales_svc_a = SalesOrderService(order_repo_a)
            sales_svc_a.update(order_a['id'], {'status': 'Confirmed'})
            assert float(stock_repo_a.get(stock_a['id'])['reserved_qty']) == 10.0

            # Switch to Tenant B
            with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Beta Corp") as (tenant_b_id, _):
                prod_repo_b = CrudRepository('T0003')
                wh_repo_b = CrudRepository('T0008')
                stock_repo_b = CrudRepository('T0009')
                cust_repo_b = CrudRepository('T0010')
                order_repo_b = CrudRepository('T0012')
                line_repo_b = CrudRepository('T0013')
                pl_repo_b = CrudRepository('T0101')

                # Tenant B cannot see Tenant A's records
                assert prod_repo_b.get(prod_a['id']) is None
                assert wh_repo_b.get(wh_a['id']) is None
                assert order_repo_b.get(order_a['id']) is None
                assert len(order_repo_b.list(filters={'id': order_a['id']})) == 0
                assert len(pl_repo_b.list(filters={'sales_order_id': order_a['id']})) == 0

                # Create Tenant B entities
                wh_b = wh_repo_b.create({'name': 'Tenant B WH', 'is_active': True})
                cust_b = cust_repo_b.create({'name': 'Tenant B Customer', 'credit_limit': 10000.0, 'balance': 0.0, 'is_active': True})
                prod_b = prod_repo_b.create({'name': 'Tenant B Product', 'sku': 'TEN-B-PROD', 'price': 20.0, 'is_active': True})
                stock_b = stock_repo_b.create({'product_id': prod_b['id'], 'warehouse_id': wh_b['id'], 'qty': 80.0, 'reserved_qty': 0.0})

                order_b = order_repo_b.create({'order_number': 'SO-TENANT-B-01', 'customer_id': cust_b['id'], 'warehouse_id': wh_b['id'], 'status': 'Draft', 'grand_total': 300.0})
                line_repo_b.create({'sales_order_id': order_b['id'], 'product_id': prod_b['id'], 'product_name': 'Tenant B Product', 'qty': 15.0, 'unit_price': 20.0, 'line_total': 300.0, 'line_number': 1})

                sales_svc_b = SalesOrderService(order_repo_b)
                sales_svc_b.update(order_b['id'], {'status': 'Confirmed'})

                # Verify Tenant B stock reservation
                assert float(stock_repo_b.get(stock_b['id'])['reserved_qty']) == 15.0

                # Cancel Order B in Tenant B
                sales_svc_b.update(order_b['id'], {'status': 'Cancelled'})
                assert float(stock_repo_b.get(stock_b['id'])['reserved_qty']) == 0.0

            # Back in Tenant A context -> Tenant A's stock reservation MUST still be 10.0 intact!
            assert float(stock_repo_a.get(stock_a['id'])['reserved_qty']) == 10.0
            assert order_repo_a.get(order_a['id'])['status'] == 'Confirmed'

            # Now cancel Order A
            sales_svc_a.update(order_a['id'], {'status': 'Cancelled'})
            assert float(stock_repo_a.get(stock_a['id'])['reserved_qty']) == 0.0
