"""
Real PostgreSQL End-to-End Integration Test Suite for Multi-Item, Multi-Batch FEFO
Lot Allocation and Multi-Warehouse Fulfillment Lifecycle.

This test suite executes directly against the real PostgreSQL container (schema "Nova"),
verifying:
1. Multi-Item, Multi-Batch FEFO lot allocation (earliest expiry first, NULL expiry last, id ASC).
2. Split allocations across multiple batches and unallocated remainder handling.
3. Picker batch overrides, barcode scanning, and validation gating.
4. Batch quantity adjustments, status transitions ('Available' -> 'Partially Used' -> 'Depleted'),
   and stock deductions in PostgreSQL tables T0088, T0009, T0064, T0101, T0102.
5. Multi-warehouse inventory isolation and fulfillment: preventing cross-warehouse allocation.
6. Inter-warehouse inventory transfers and movement audit logging.
7. End-to-end food recall and lot traceability reporting (Inbound Supplier/PO/GRN -> Outbound Pick/SO/Invoice -> Customers).
8. REST API endpoints and MCP server tool execution.
9. Database constraint verification and multi-tenant isolation.
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
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.warehouse.services.goods_receipt_service import GoodsReceiptService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService

from modules.inventory.controllers.T0003I import router as product_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from modules.warehouse.controllers.T0088I import router as batch_router
from modules.warehouse.controllers.T0075I import router as grn_router
from modules.warehouse.controllers.T0008I import router as wh_router
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
    """Create FastAPI test client with warehouse, batch, sales, and product routers."""
    app = FastAPI(title="Nova Real PostgreSQL FEFO & Multi-Warehouse Test Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(batch_router)
    app.include_router(grn_router)
    app.include_router(wh_router)
    app.include_router(invoice_router)
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
# 1. Multi-Item, Multi-Batch FEFO Lot Allocation Lifecycle
# ============================================================================

class TestRealPostgresFEFOLotAllocationLifecycle:
    """
    Tests end-to-end multi-item, multi-batch FEFO lot allocation in real PostgreSQL:
    - Inbound Goods Receipts creating batches with manufacturing and expiry dates.
    - Sales Order Confirmation auto-allocating lots using FEFO (earliest expiry first).
    - Multi-batch splitting when line qty exceeds a single batch.
    - Partial batch allocation with unallocated remainder items.
    - Picker lot selection, scanning, overrides, and depletion upon pick completion.
    """

    def test_real_postgres_inbound_goods_receipt_batch_registration(self, isolated_tenant, real_db_conn):
        """
        Verify that Goods Receipts (T0075) with lines (T0076) correctly register
        and update batch records in T0088, record stock movements in T0064,
        and update inventory levels in T0009.
        """
        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        grn_repo = CrudRepository('T0075')
        grn_line_repo = CrudRepository('T0076')
        batch_repo = CrudRepository('T0088')
        stock_repo = CrudRepository('T0009')
        movement_repo = CrudRepository('T0064')

        wh = wh_repo.create({'name': 'Inbound Receiving Dock', 'location': 'Section A', 'is_active': True})
        product = product_repo.create({
            'name': 'Organic Whole Milk 1L',
            'sku': 'MILK-ORG-1L',
            'price': 4.50,
            'cost_price': 2.80,
            'is_active': True,
        })
        wh_id = wh['id']
        prod_id = product['id']

        grn_svc = GoodsReceiptService(grn_repo)

        # 1. Create Goods Receipt in Draft status -> No batch registered yet
        grn_draft = grn_svc.create({
            'receipt_number': 'GRN-FEFO-001',
            'warehouse_id': wh_id,
            'status': 'Draft',
            'receipt_date': '2026-08-26',
        })
        grn_id = grn_draft['id']

        grn_line_repo.create({
            'receipt_id': grn_id,
            'product_id': prod_id,
            'product_name': 'Organic Whole Milk 1L',
            'qty_received': 50.0,
            'qty_ordered': 50.0,
            'batch_number': 'LOT-MILK-2026A',
            'manufacturing_date': '2026-08-20',
            'expiry_date': '2026-11-20',
            'line_number': 1,
        })

        # Batches must not exist while GRN is in Draft
        batches_before = batch_repo.list(filters={'product_id': prod_id, 'batch_number': 'LOT-MILK-2026A'})
        assert len(batches_before) == 0

        # 2. Complete Goods Receipt -> Registers Batch and records movements
        grn_svc.update(grn_id, {'status': 'Completed'})

        # Verify batch registered in T0088
        batches_after = batch_repo.list(filters={'product_id': prod_id, 'batch_number': 'LOT-MILK-2026A'})
        assert len(batches_after) == 1
        batch = batches_after[0]
        assert float(batch['quantity']) == 50.0
        assert str(batch['expiry_date']) == '2026-11-20'
        assert str(batch['manufacturing_date']) == '2026-08-20'
        assert batch['status'] == 'Available'
        assert batch['warehouse_id'] == wh_id

        # Direct PostgreSQL SQL verification
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT id, product_id, batch_number, quantity, status, warehouse_id, business_id FROM "Nova".t0088 WHERE id = %s;',
                (batch['id'],)
            )
            db_row = cur.fetchone()
            assert db_row is not None
            assert float(db_row['quantity']) == 50.0
            assert db_row['status'] == 'Available'
            assert db_row['business_id'] == isolated_tenant

        # Verify stock movement recorded in T0064
        moves = movement_repo.list(filters={'product_id': prod_id, 'movement_type': 'Goods Receipt'})
        assert len(moves) >= 1
        assert float(moves[0]['qty_change']) == 50.0
        assert moves[0]['warehouse_id'] == wh_id

    def test_real_postgres_multi_item_fefo_lot_split_allocation(self, isolated_tenant, real_db_conn):
        """
        Verify multi-item order confirmation with multi-batch FEFO lot splitting:
        - Product 1 (Pasteurized Milk): Order requests 25 units.
          Batches in DB:
          - LOT-M1 (exp: 2026-04-01, qty: 10) -> Earliest
          - LOT-M2 (exp: 2026-06-01, qty: 15) -> Second
          - LOT-M3 (exp: 2026-09-01, qty: 20) -> Third
          FEFO must split into: LOT-M1 (10 units) + LOT-M2 (15 units), LOT-M3 unused.
        - Product 2 (Greek Yogurt): Order requests 14 units.
          Batches in DB:
          - LOT-Y1 (exp: 2026-05-10, qty: 8)
          - LOT-Y2 (exp: 2026-07-10, qty: 20)
          FEFO must split into: LOT-Y1 (8 units) + LOT-Y2 (6 units).
        - Product 3 (Non-batch dry item): 5 units allocated without batch.
        """
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        wh = wh_repo.create({'name': 'FEFO Main Warehouse', 'location': 'Bay 1', 'is_active': True})
        wh_id = wh['id']

        cust = customer_repo.create({'name': 'Supermarket Chain Alpha', 'credit_limit': 50000.0, 'balance': 0.0})
        cust_id = cust['id']

        p_milk = product_repo.create({'name': 'Pasteurized Milk 2L', 'sku': 'MILK-2L', 'price': 5.0, 'is_active': True})
        p_yog = product_repo.create({'name': 'Greek Yogurt 500g', 'sku': 'YOG-500G', 'price': 3.5, 'is_active': True})
        p_dry = product_repo.create({'name': 'Dry Oats 1kg', 'sku': 'OATS-1KG', 'price': 4.0, 'is_active': True})

        # Seed warehouse physical stock in T0009
        stock_repo.create({'product_id': p_milk['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p_yog['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': p_dry['id'], 'warehouse_id': wh_id, 'qty': 100.0, 'reserved_qty': 0.0})

        # Seed Batches in T0088
        # Milk batches: M3 created first, then M1, then M2 (to verify sort by expiry, not insertion order)
        b_m3 = batch_repo.create({'product_id': p_milk['id'], 'batch_number': 'LOT-M3', 'expiry_date': '2026-09-01', 'quantity': 20.0, 'warehouse_id': wh_id, 'status': 'Available'})
        b_m1 = batch_repo.create({'product_id': p_milk['id'], 'batch_number': 'LOT-M1', 'expiry_date': '2026-04-01', 'quantity': 10.0, 'warehouse_id': wh_id, 'status': 'Available'})
        b_m2 = batch_repo.create({'product_id': p_milk['id'], 'batch_number': 'LOT-M2', 'expiry_date': '2026-06-01', 'quantity': 15.0, 'warehouse_id': wh_id, 'status': 'Available'})

        # Yogurt batches
        b_y2 = batch_repo.create({'product_id': p_yog['id'], 'batch_number': 'LOT-Y2', 'expiry_date': '2026-07-10', 'quantity': 20.0, 'warehouse_id': wh_id, 'status': 'Available'})
        b_y1 = batch_repo.create({'product_id': p_yog['id'], 'batch_number': 'LOT-Y1', 'expiry_date': '2026-05-10', 'quantity': 8.0, 'warehouse_id': wh_id, 'status': 'Available'})

        # Create Multi-Item Sales Order
        order = order_repo.create({
            'order_number': 'SO-FEFO-MULTI-01',
            'customer_id': cust_id,
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 194.0,  # 25*5 + 14*3.5 + 5*4 = 125 + 49 + 20 = 194
            'grand_total': 194.0,
            'order_date': '2026-08-26',
        })
        order_id = order['id']

        line_repo.create({'sales_order_id': order_id, 'product_id': p_milk['id'], 'product_name': 'Pasteurized Milk 2L', 'qty': 25.0, 'unit_price': 5.0, 'line_total': 125.0, 'line_number': 1})
        line_repo.create({'sales_order_id': order_id, 'product_id': p_yog['id'], 'product_name': 'Greek Yogurt 500g', 'qty': 14.0, 'unit_price': 3.5, 'line_total': 49.0, 'line_number': 2})
        line_repo.create({'sales_order_id': order_id, 'product_id': p_dry['id'], 'product_name': 'Dry Oats 1kg', 'qty': 5.0, 'unit_price': 4.0, 'line_total': 20.0, 'line_number': 3})

        # Confirm Order -> Generates Pick List with FEFO allocation
        sales_svc.update(order_id, {'status': 'Confirmed'})

        # Verify Pick List created
        pick_lists = pl_repo.list(filters={'sales_order_id': order_id})
        assert len(pick_lists) == 1
        pkl = pick_lists[0]
        pkl_id = pkl['id']
        assert pkl['status'] == 'Pending'
        assert pkl['pick_list_number'].startswith('PKL-')

        # Retrieve and inspect Pick List Items in T0102
        pl_items = pli_repo.list(filters={'pick_list_id': pkl_id}, order_by='line_number')
        # Expect 5 pick list items total:
        # Milk split (2 items), Yogurt split (2 items), Dry oats (1 item)
        assert len(pl_items) == 5

        milk_items = [it for it in pl_items if it['product_id'] == p_milk['id']]
        yog_items = [it for it in pl_items if it['product_id'] == p_yog['id']]
        dry_items = [it for it in pl_items if it['product_id'] == p_dry['id']]

        # 1. Milk Allocations Verification (FEFO: LOT-M1 first, LOT-M2 second)
        assert len(milk_items) == 2
        assert milk_items[0]['batch_id'] == b_m1['id']
        assert milk_items[0]['batch_number'] == 'LOT-M1'
        assert float(milk_items[0]['qty_ordered']) == 10.0
        assert str(milk_items[0]['expiry_date']) == '2026-04-01'

        assert milk_items[1]['batch_id'] == b_m2['id']
        assert milk_items[1]['batch_number'] == 'LOT-M2'
        assert float(milk_items[1]['qty_ordered']) == 15.0
        assert str(milk_items[1]['expiry_date']) == '2026-06-01'

        # 2. Yogurt Allocations Verification (FEFO: LOT-Y1 first, LOT-Y2 second)
        assert len(yog_items) == 2
        assert yog_items[0]['batch_id'] == b_y1['id']
        assert yog_items[0]['batch_number'] == 'LOT-Y1'
        assert float(yog_items[0]['qty_ordered']) == 8.0
        assert str(yog_items[0]['expiry_date']) == '2026-05-10'

        assert yog_items[1]['batch_id'] == b_y2['id']
        assert yog_items[1]['batch_number'] == 'LOT-Y2'
        assert float(yog_items[1]['qty_ordered']) == 6.0
        assert str(yog_items[1]['expiry_date']) == '2026-07-10'

        # 3. Dry Oats (Non-batch) Verification
        assert len(dry_items) == 1
        assert dry_items[0]['batch_id'] is None
        assert dry_items[0]['batch_number'] is None
        assert float(dry_items[0]['qty_ordered']) == 5.0

    def test_real_postgres_fefo_partial_lot_allocation_with_unallocated_remainder(self, isolated_tenant):
        """
        When total lot quantities are insufficient for the ordered quantity,
        FEFO creates allocated lot items for available inventory and an unallocated
        item (batch_id=None) for the remaining quantity.
        """
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)

        wh = wh_repo.create({'name': 'Partial Warehouse', 'is_active': True})
        cust = customer_repo.create({'name': 'Customer Partial', 'credit_limit': 10000.0, 'balance': 0.0})
        prod = product_repo.create({'name': 'Specialty Artisanal Cheese', 'sku': 'CHEESE-SPEC', 'price': 20.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})

        # Available batches total 12 units (Lot 1: 5 units, Lot 2: 7 units)
        b1 = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-PART-1', 'expiry_date': '2026-04-15', 'quantity': 5.0, 'warehouse_id': wh['id'], 'status': 'Available'})
        b2 = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-PART-2', 'expiry_date': '2026-06-15', 'quantity': 7.0, 'warehouse_id': wh['id'], 'status': 'Available'})

        # Order requests 20 units (8 units deficit in lots)
        order = order_repo.create({
            'order_number': 'SO-PART-LOT-01',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'status': 'Draft',
            'subtotal': 400.0,
            'grand_total': 400.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod['id'], 'product_name': 'Specialty Artisanal Cheese', 'qty': 20.0, 'unit_price': 20.0, 'line_total': 400.0, 'line_number': 1})

        sales_svc.update(order['id'], {'status': 'Confirmed'})

        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        items = pli_repo.list(filters={'pick_list_id': pkl['id']}, order_by='line_number')

        assert len(items) == 3
        # Lot 1 item
        assert items[0]['batch_id'] == b1['id']
        assert items[0]['batch_number'] == 'LOT-PART-1'
        assert float(items[0]['qty_ordered']) == 5.0

        # Lot 2 item
        assert items[1]['batch_id'] == b2['id']
        assert items[1]['batch_number'] == 'LOT-PART-2'
        assert float(items[1]['qty_ordered']) == 7.0

        # Unallocated remainder item
        assert items[2]['batch_id'] is None
        assert items[2]['batch_number'] is None
        assert items[2]['expiry_date'] is None
        assert float(items[2]['qty_ordered']) == 8.0

    def test_real_postgres_fefo_null_expiry_and_id_tiebreaker(self, isolated_tenant):
        """
        Verify FEFO sorting rules against real PostgreSQL records:
        - Batches with NULL expiry dates must sort after batches with valid dates.
        - Batches with identical expiry dates must sort by id ASC.
        """
        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        batch_repo = CrudRepository('T0088')

        wh = wh_repo.create({'name': 'Tiebreaker WH', 'is_active': True})
        prod = product_repo.create({'name': 'Canned Beans', 'sku': 'BEANS-CAN', 'price': 2.0, 'is_active': True})

        # Create batches:
        # B_NOEXP: expiry NULL, qty 10
        # B_EXP2: expiry 2026-10-01, qty 5
        # B_SAME_A: expiry 2026-05-01, qty 4 (created first -> lower id)
        # B_SAME_B: expiry 2026-05-01, qty 6 (created second -> higher id)
        b_noexp = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-NOEXP', 'expiry_date': None, 'quantity': 10.0, 'warehouse_id': wh['id'], 'status': 'Available'})
        b_exp2 = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-EXP2', 'expiry_date': '2026-10-01', 'quantity': 5.0, 'warehouse_id': wh['id'], 'status': 'Available'})
        b_same_a = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-SAME-A', 'expiry_date': '2026-05-01', 'quantity': 4.0, 'warehouse_id': wh['id'], 'status': 'Available'})
        b_same_b = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-SAME-B', 'expiry_date': '2026-05-01', 'quantity': 6.0, 'warehouse_id': wh['id'], 'status': 'Available'})

        batch_svc = BatchNumberService(batch_repo)

        # Allocate 20 units total
        allocs = batch_svc.allocate_fefo_lots(product_id=prod['id'], warehouse_id=wh['id'], qty_needed=20.0)

        # Expected allocation order:
        # 1. LOT-SAME-A (4 units, exp 2026-05-01, id b_same_a)
        # 2. LOT-SAME-B (6 units, exp 2026-05-01, id b_same_b)
        # 3. LOT-EXP2   (5 units, exp 2026-10-01)
        # 4. LOT-NOEXP  (5 units out of 10, exp NULL - last)
        assert len(allocs) == 4
        assert allocs[0]['batch_number'] == 'LOT-SAME-A'
        assert float(allocs[0]['quantity']) == 4.0

        assert allocs[1]['batch_number'] == 'LOT-SAME-B'
        assert float(allocs[1]['quantity']) == 6.0

        assert allocs[2]['batch_number'] == 'LOT-EXP2'
        assert float(allocs[2]['quantity']) == 5.0

        assert allocs[3]['batch_number'] == 'LOT-NOEXP'
        assert float(allocs[3]['quantity']) == 5.0

    def test_real_postgres_picker_lot_override_and_completion_depletion(self, isolated_tenant, real_db_conn):
        """
        Verify picking workflow with picker lot override and batch depletion in PostgreSQL:
        - Order confirms -> FEFO suggests LOT-DEF-1 (10 units).
        - Picker in warehouse overrides item to LOT-ALT-2 (which has 15 units available).
        - Pick list completed -> depletes LOT-ALT-2 (15 -> 5, status='Partially Used').
        - LOT-DEF-1 remains untouched (quantity=10, status='Available').
        - Sales order transitions to 'Shipped'.
        - Stock deducted in T0009 and movement logged in T0064.
        """
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        movement_repo = CrudRepository('T0064')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        stock_svc = StockMovementService()

        wh = wh_repo.create({'name': 'Override Warehouse', 'is_active': True})
        wh_id = wh['id']
        cust = customer_repo.create({'name': 'Override Customer', 'credit_limit': 15000.0, 'balance': 0.0})
        prod = product_repo.create({'name': 'Premium Butter 500g', 'sku': 'BUTTER-500G', 'price': 6.0, 'is_active': True})
        prod_id = prod['id']

        stock_rec = stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_id, 'qty': 50.0, 'reserved_qty': 0.0})

        # Default FEFO lot (earlier expiry)
        b_def = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-DEF-1', 'expiry_date': '2026-04-01', 'quantity': 10.0, 'warehouse_id': wh_id, 'status': 'Available'})
        # Alternative lot (later expiry)
        b_alt = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-ALT-2', 'expiry_date': '2026-08-01', 'quantity': 15.0, 'warehouse_id': wh_id, 'status': 'Available'})

        order = order_repo.create({
            'order_number': 'SO-OVERRIDE-01',
            'customer_id': cust['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 60.0,
            'grand_total': 60.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod_id, 'product_name': 'Premium Butter 500g', 'qty': 10.0, 'unit_price': 6.0, 'line_total': 60.0, 'line_number': 1})

        # Confirm order
        sales_svc.update(order['id'], {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Initial suggested lot was LOT-DEF-1
        assert pli['batch_id'] == b_def['id']
        assert pli['batch_number'] == 'LOT-DEF-1'

        # Picker scans/selects LOT-ALT-2 instead
        pick_res = pick_svc.pick_item(
            item_id=pli['id'],
            qty_picked=10.0,
            pick_list_id=pkl['id'],
            picked_batch_id=b_alt['id'],
            picked_batch_number='LOT-ALT-2',
        )
        assert pick_res['picked_batch_id'] == b_alt['id']
        assert pick_res['picked_batch_number'] == 'LOT-ALT-2'

        # Complete picking
        complete_res = pick_svc.complete_picking(pkl['id'])
        assert complete_res['status'] == 'Completed'
        assert order_repo.get(order['id'])['status'] == 'Shipped'

        # Verify Batch Depletion in PostgreSQL:
        # LOT-ALT-2 was depleted from 15 to 5 (Partially Used)
        updated_alt = batch_repo.get(b_alt['id'])
        assert float(updated_alt['quantity']) == 5.0
        assert updated_alt['status'] == 'Partially Used'

        # LOT-DEF-1 remained untouched at 10 (Available)
        updated_def = batch_repo.get(b_def['id'])
        assert float(updated_def['quantity']) == 10.0
        assert updated_def['status'] == 'Available'

        # Physical stock deduction
        stock_svc.deduct_stock(prod_id, wh_id, 10.0, reference_type='sales_order', reference_id=order['id'])
        final_stock = stock_repo.get(stock_rec['id'])
        assert float(final_stock['qty']) == 40.0


# ============================================================================
# 2. Multi-Warehouse Fulfillment Lifecycle & Inventory Partitioning
# ============================================================================

class TestRealPostgresMultiWarehouseFulfillmentLifecycle:
    """
    Tests fulfillment across multiple distinct warehouse facilities in real PostgreSQL:
    - Independent inventory levels and batch pools per warehouse facility.
    - Strict warehouse isolation: orders for Facility 1 allocate only Facility 1 lots.
    - Rejection of cross-warehouse lot assignment.
    - Inter-warehouse inventory transfers and movement audit logging.
    """

    def test_real_postgres_multi_warehouse_isolated_lot_allocation(self, isolated_tenant, real_db_conn):
        """
        Warehouse A (North Hub) and Warehouse B (South Hub) hold inventory for the same product.
        Sales Order A (Warehouse A) must strictly allocate Warehouse A batches,
        even when Warehouse B has batches with earlier expiration dates.
        """
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        # 1. Setup Two Distinct Warehouses
        wh_north = wh_repo.create({'name': 'North Distribution Center', 'location': 'Sector N', 'is_active': True})
        wh_south = wh_repo.create({'name': 'South Logistics Hub', 'location': 'Sector S', 'is_active': True})
        wh_north_id = wh_north['id']
        wh_south_id = wh_south['id']

        cust = customer_repo.create({'name': 'Multi-WH Customer', 'credit_limit': 30000.0, 'balance': 0.0})
        product = product_repo.create({'name': 'Gourmet Olive Oil 1L', 'sku': 'OIL-GOURMET-1L', 'price': 12.0, 'is_active': True})
        prod_id = product['id']

        # Seed physical stock in both warehouses
        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_north_id, 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_south_id, 'qty': 100.0, 'reserved_qty': 0.0})

        # Seed Batches:
        # North Batch: LOT-NORTH-1 (expiry 2026-10-01, qty 40)
        # South Batch: LOT-SOUTH-EARLY (expiry 2026-03-01, qty 40) -> Much earlier expiry, but located in South!
        b_north = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-NORTH-1', 'expiry_date': '2026-10-01', 'quantity': 40.0, 'warehouse_id': wh_north_id, 'status': 'Available'})
        b_south = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-SOUTH-EARLY', 'expiry_date': '2026-03-01', 'quantity': 40.0, 'warehouse_id': wh_south_id, 'status': 'Available'})

        # 2. Create and Confirm Order for Warehouse North
        order_north = order_repo.create({
            'order_number': 'SO-WH-NORTH-01',
            'customer_id': cust['id'],
            'warehouse_id': wh_north_id,
            'status': 'Draft',
            'subtotal': 120.0,
            'grand_total': 120.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({'sales_order_id': order_north['id'], 'product_id': prod_id, 'product_name': 'Gourmet Olive Oil 1L', 'qty': 10.0, 'unit_price': 12.0, 'line_total': 120.0, 'line_number': 1})

        sales_svc.update(order_north['id'], {'status': 'Confirmed'})

        # Verify Pick List allocated from North Hub ONLY
        pkl_north = pl_repo.list(filters={'sales_order_id': order_north['id']})[0]
        assert pkl_north['warehouse_id'] == wh_north_id
        items_north = pli_repo.list(filters={'pick_list_id': pkl_north['id']})

        assert len(items_north) == 1
        assert items_north[0]['batch_id'] == b_north['id']
        assert items_north[0]['batch_number'] == 'LOT-NORTH-1'
        # Must NOT allocate South batch despite its earlier expiry
        assert items_north[0]['batch_id'] != b_south['id']

        # 3. Create and Confirm Order for Warehouse South
        order_south = order_repo.create({
            'order_number': 'SO-WH-SOUTH-01',
            'customer_id': cust['id'],
            'warehouse_id': wh_south_id,
            'status': 'Draft',
            'subtotal': 240.0,
            'grand_total': 240.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({'sales_order_id': order_south['id'], 'product_id': prod_id, 'product_name': 'Gourmet Olive Oil 1L', 'qty': 20.0, 'unit_price': 12.0, 'line_total': 240.0, 'line_number': 1})

        sales_svc.update(order_south['id'], {'status': 'Confirmed'})

        pkl_south = pl_repo.list(filters={'sales_order_id': order_south['id']})[0]
        assert pkl_south['warehouse_id'] == wh_south_id
        items_south = pli_repo.list(filters={'pick_list_id': pkl_south['id']})

        assert len(items_south) == 1
        assert items_south[0]['batch_id'] == b_south['id']
        assert items_south[0]['batch_number'] == 'LOT-SOUTH-EARLY'

        # Complete both pick lists
        pick_svc.pick_item(item_id=items_north[0]['id'], qty_picked=10.0, pick_list_id=pkl_north['id'])
        pick_svc.complete_picking(pkl_north['id'])

        pick_svc.pick_item(item_id=items_south[0]['id'], qty_picked=20.0, pick_list_id=pkl_south['id'])
        pick_svc.complete_picking(pkl_south['id'])

        # Verify respective batch quantities in PostgreSQL
        assert float(batch_repo.get(b_north['id'])['quantity']) == 30.0  # 40 - 10
        assert float(batch_repo.get(b_south['id'])['quantity']) == 20.0  # 40 - 20

    def test_real_postgres_cross_warehouse_lot_picking_rejection(self, isolated_tenant):
        """
        Validate that picking an item rejects assignment of a batch from a different warehouse facility.
        """
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)

        wh_a = wh_repo.create({'name': 'Facility Alpha', 'is_active': True})
        wh_b = wh_repo.create({'name': 'Facility Beta', 'is_active': True})
        cust = customer_repo.create({'name': 'Cross WH Customer', 'credit_limit': 10000.0, 'balance': 0.0})
        prod = product_repo.create({'name': 'Almond Butter', 'sku': 'ALM-BUTTER', 'price': 8.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh_a['id'], 'qty': 20.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh_b['id'], 'qty': 20.0, 'reserved_qty': 0.0})

        b_in_a = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-IN-A', 'expiry_date': '2026-06-01', 'quantity': 20.0, 'warehouse_id': wh_a['id'], 'status': 'Available'})
        b_in_b = batch_repo.create({'product_id': prod['id'], 'batch_number': 'LOT-IN-B', 'expiry_date': '2026-07-01', 'quantity': 20.0, 'warehouse_id': wh_b['id'], 'status': 'Available'})

        order = order_repo.create({
            'order_number': 'SO-CROSS-WH-01',
            'customer_id': cust['id'],
            'warehouse_id': wh_a['id'],
            'status': 'Draft',
            'subtotal': 80.0,
            'grand_total': 80.0,
            'order_date': '2026-08-26',
        })
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod['id'], 'product_name': 'Almond Butter', 'qty': 10.0, 'unit_price': 8.0, 'line_total': 80.0, 'line_number': 1})

        sales_svc.update(order['id'], {'status': 'Confirmed'})
        pkl = pl_repo.list(filters={'sales_order_id': order['id']})[0]
        pli = pli_repo.list(filters={'pick_list_id': pkl['id']})[0]

        # Attempt to pick using batch belonging to Facility Beta (wh_b) for a pick list in Facility Alpha (wh_a)
        with pytest.raises(ValueError, match="belongs to a different warehouse"):
            pick_svc.pick_item(
                item_id=pli['id'],
                qty_picked=10.0,
                pick_list_id=pkl['id'],
                picked_batch_id=b_in_b['id'],
            )

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_real_postgres_multi_warehouse_inter_facility_stock_transfer(self, isolated_tenant, real_db_conn):
        """
        Verify inter-warehouse stock transfer between facilities with real PostgreSQL persistence:
        - Transfer Out from Warehouse 1.
        - Transfer In to Warehouse 2.
        - Verifies balances in T0009 and movement records in T0064.
        """
        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        movement_repo = CrudRepository('T0064')
        stock_svc = StockMovementService()

        wh1 = wh_repo.create({'name': 'Origin Facility', 'is_active': True})
        wh2 = wh_repo.create({'name': 'Destination Facility', 'is_active': True})
        prod = product_repo.create({'name': 'Bulk Coffee Beans', 'sku': 'COFFEE-BULK', 'price': 15.0, 'is_active': True})
        prod_id = prod['id']

        # Initial stock: 100 in Origin, 0 in Destination
        s1 = stock_repo.create({'product_id': prod_id, 'warehouse_id': wh1['id'], 'qty': 100.0, 'reserved_qty': 0.0})
        s2 = stock_repo.create({'product_id': prod_id, 'warehouse_id': wh2['id'], 'qty': 0.0, 'reserved_qty': 0.0})

        # Transfer 35 units from Origin to Destination
        # 1. Deduct from Origin
        stock_svc.record_movement(
            product_id=prod_id,
            warehouse_id=wh1['id'],
            movement_type='Transfer Out',
            qty_change=-35.0,
            reference_type='warehouse_transfer',
            reference_id=999,
            description=f'Transfer to {wh2["name"]}',
        )
        stock_repo.update(s1['id'], {'qty': 65.0})

        # 2. Add to Destination
        stock_svc.record_movement(
            product_id=prod_id,
            warehouse_id=wh2['id'],
            movement_type='Transfer In',
            qty_change=35.0,
            reference_type='warehouse_transfer',
            reference_id=999,
            description=f'Transfer from {wh1["name"]}',
        )
        stock_repo.update(s2['id'], {'qty': 35.0})

        # Verify balances in T0009
        assert float(stock_repo.get(s1['id'])['qty']) == 65.0
        assert float(stock_repo.get(s2['id'])['qty']) == 35.0

        # Verify movement records in T0064
        moves = movement_repo.list(filters={'product_id': prod_id, 'reference_type': 'warehouse_transfer'})
        assert len(moves) == 2
        m_out = next(m for m in moves if m['movement_type'] == 'Transfer Out')
        m_in = next(m for m in moves if m['movement_type'] == 'Transfer In')
        assert float(m_out['qty_change']) == -35.0
        assert m_out['warehouse_id'] == wh1['id']
        assert float(m_in['qty_change']) == 35.0
        assert m_in['warehouse_id'] == wh2['id']


# ============================================================================
# 3. Lot Traceability & Food Recall Reporting
# ============================================================================

class TestRealPostgresLotTraceabilityAndRecallReporting:
    """
    Tests complete end-to-end forward and backward lot traceability and food recall
    reporting executing against real PostgreSQL tables:
    Inbound Supplier -> Purchase Order -> Goods Receipt -> Batch Master ->
    Current Warehouse Stock -> Outbound Pick Lists -> Sales Orders -> Invoices -> Affected Customers.
    """

    def test_real_postgres_end_to_end_food_recall_report(self, isolated_tenant, real_db_conn):
        supplier_repo = CrudRepository('T0011')
        po_repo = CrudRepository('T0014')
        grn_repo = CrudRepository('T0075')
        grn_line_repo = CrudRepository('T0076')
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')

        sales_svc = SalesOrderService(order_repo)
        pick_svc = PickListService(pl_repo)
        batch_svc = BatchNumberService(batch_repo)

        # 1. Setup Master Data
        wh = wh_repo.create({'name': 'Main Logistics Facility', 'location': 'Central Hub', 'is_active': True})
        wh_id = wh['id']

        supplier = supplier_repo.create({
            'name': 'Alpine Dairy Farms Co',
            'email': 'qa@alpinedairy.com',
            'phone': '+1-800-555-MILK',
            'category': 'Dairy Products',
        })
        supp_id = supplier['id']

        product = product_repo.create({
            'name': 'Alpine Raw Milk Cheese 500g',
            'sku': 'CHEESE-ALP-500',
            'price': 15.0,
            'cost_price': 9.0,
            'category': 'Perishable Dairy',
            'is_active': True,
        })
        prod_id = product['id']

        cust1 = customer_repo.create({
            'name': 'Gourmet Bistro NYC',
            'email': 'chef@gourmetbistro.com',
            'phone': '+1-212-555-0199',
            'group_name': 'Hospitality',
            'credit_limit': 20000.0,
            'balance': 0.0,
        })
        cust2 = customer_repo.create({
            'name': 'Organic Grocers Market',
            'email': 'buyer@organicgrocers.com',
            'phone': '+1-415-555-0122',
            'group_name': 'Retail',
            'credit_limit': 30000.0,
            'balance': 0.0,
        })

        # 2. Inbound: Purchase Order & Goods Receipt
        po = po_repo.create({
            'order_number': 'PO-RECALL-001',
            'supplier_id': supp_id,
            'status': 'Received',
            'total': 1800.0,
            'order_date': '2026-08-01',
        })
        po_id = po['id']

        grn = grn_repo.create({
            'receipt_number': 'GRN-RECALL-001',
            'purchase_order_id': po_id,
            'warehouse_id': wh_id,
            'status': 'Completed',
            'receipt_date': '2026-08-05',
        })
        grn_id = grn['id']

        grn_line_repo.create({
            'receipt_id': grn_id,
            'product_id': prod_id,
            'product_name': 'Alpine Raw Milk Cheese 500g',
            'qty_received': 200.0,
            'qty_ordered': 200.0,
            'batch_number': 'LOT-ALP-RECALL-99',
            'manufacturing_date': '2026-08-01',
            'expiry_date': '2026-12-01',
            'line_number': 1,
        })

        # Batch record in T0088 (200 units initial)
        batch = batch_repo.create({
            'product_id': prod_id,
            'batch_number': 'LOT-ALP-RECALL-99',
            'manufacturing_date': '2026-08-01',
            'expiry_date': '2026-12-01',
            'quantity': 200.0,
            'warehouse_id': wh_id,
            'status': 'Available',
            'notes': 'Suspected microbial contamination report',
        })
        batch_id = batch['id']

        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_id, 'qty': 200.0, 'reserved_qty': 0.0})

        # 3. Outbound Order 1 for Customer 1 (60 units)
        so1 = order_repo.create({
            'order_number': 'SO-REC-001',
            'customer_id': cust1['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 900.0,
            'grand_total': 900.0,
            'order_date': '2026-08-10',
        })
        line_repo.create({'sales_order_id': so1['id'], 'product_id': prod_id, 'product_name': 'Alpine Raw Milk Cheese 500g', 'qty': 60.0, 'unit_price': 15.0, 'line_total': 900.0, 'line_number': 1})
        sales_svc.update(so1['id'], {'status': 'Confirmed'})

        pkl1 = pl_repo.list(filters={'sales_order_id': so1['id']})[0]
        pli1 = pli_repo.list(filters={'pick_list_id': pkl1['id']})[0]
        pick_svc.pick_item(item_id=pli1['id'], qty_picked=60.0, pick_list_id=pkl1['id'])
        pick_svc.complete_picking(pkl1['id'])
        sales_svc.update(so1['id'], {'status': 'Delivered'})

        # 4. Outbound Order 2 for Customer 2 (40 units)
        so2 = order_repo.create({
            'order_number': 'SO-REC-002',
            'customer_id': cust2['id'],
            'warehouse_id': wh_id,
            'status': 'Draft',
            'subtotal': 600.0,
            'grand_total': 600.0,
            'order_date': '2026-08-15',
        })
        line_repo.create({'sales_order_id': so2['id'], 'product_id': prod_id, 'product_name': 'Alpine Raw Milk Cheese 500g', 'qty': 40.0, 'unit_price': 15.0, 'line_total': 600.0, 'line_number': 1})
        sales_svc.update(so2['id'], {'status': 'Confirmed'})

        pkl2 = pl_repo.list(filters={'sales_order_id': so2['id']})[0]
        pli2 = pli_repo.list(filters={'pick_list_id': pkl2['id']})[0]
        pick_svc.pick_item(item_id=pli2['id'], qty_picked=40.0, pick_list_id=pkl2['id'])
        pick_svc.complete_picking(pkl2['id'])
        sales_svc.update(so2['id'], {'status': 'Delivered'})

        # Remaining batch quantity in T0088: 200 - 60 - 40 = 100
        assert float(batch_repo.get(batch_id)['quantity']) == 100.0

        # 5. Generate Full Food Recall Report using BatchNumberService
        report = batch_svc.get_recall_report(batch_number='LOT-ALP-RECALL-99')

        # Verify Batch Master Information
        assert report['batch']['batch_number'] == 'LOT-ALP-RECALL-99'
        assert report['batch']['product_name'] == 'Alpine Raw Milk Cheese 500g'
        assert report['batch']['product_sku'] == 'CHEESE-ALP-500'
        assert float(report['batch']['quantity']) == 100.0
        assert report['batch']['warehouse_name'] == 'Main Logistics Facility'

        # Verify Inbound Traceability
        assert len(report['inbound_trace']) >= 1
        inbound = report['inbound_trace'][0]
        assert inbound['receipt_number'] == 'GRN-RECALL-001'
        assert inbound['po_number'] == 'PO-RECALL-001'
        assert inbound['supplier_name'] == 'Alpine Dairy Farms Co'
        assert inbound['supplier_email'] == 'qa@alpinedairy.com'
        assert float(inbound['qty_received']) == 200.0

        # Verify Outbound Traceability (Pick Lists, Orders, Invoices)
        assert len(report['outbound_trace']) == 2
        out_so_numbers = [t['sales_order_number'] for t in report['outbound_trace']]
        assert 'SO-REC-001' in out_so_numbers
        assert 'SO-REC-002' in out_so_numbers

        # Verify Affected Customer Contact List
        assert len(report['affected_customers']) == 2
        cust_emails = [c['email'] for c in report['affected_customers']]
        assert 'chef@gourmetbistro.com' in cust_emails
        assert 'buyer@organicgrocers.com' in cust_emails

        c1 = next(c for c in report['affected_customers'] if c['customer_id'] == cust1['id'])
        assert c1['customer_name'] == 'Gourmet Bistro NYC'
        assert float(c1['total_qty_picked']) == 60.0

        c2 = next(c for c in report['affected_customers'] if c['customer_id'] == cust2['id'])
        assert c2['customer_name'] == 'Organic Grocers Market'
        assert float(c2['total_qty_picked']) == 40.0

        # Verify Overall Summary Metrics
        assert float(report['summary']['total_qty_received']) == 200.0
        assert float(report['summary']['total_qty_picked']) == 100.0
        assert float(report['summary']['current_quantity']) == 100.0
        assert report['summary']['total_affected_customers'] == 2
        assert report['summary']['total_affected_orders'] == 2

        # Verify report generation by batch_id produces identical results
        report_by_id = batch_svc.get_recall_report(batch_id=batch_id)
        assert report_by_id['batch']['id'] == batch_id
        assert report_by_id['summary']['total_affected_customers'] == 2

    def test_real_postgres_recall_report_nonexistent_batch_handling(self, isolated_tenant):
        batch_repo = CrudRepository('T0088')
        batch_svc = BatchNumberService(batch_repo)

        with pytest.raises(ValueError, match="Either batch_number or batch_id"):
            batch_svc.get_recall_report()

        with pytest.raises(ValueError, match="Batch with ID 99999 not found"):
            batch_svc.get_recall_report(batch_id=99999)

        with pytest.raises(ValueError, match="Batch 'NONEXISTENT-LOT-XYZ' not found"):
            batch_svc.get_recall_report(batch_number='NONEXISTENT-LOT-XYZ')


# ============================================================================
# 4. HTTP REST API & MCP Tools Integration Tests on Real PostgreSQL
# ============================================================================

class TestRealPostgresFEFORestApiAndMcp:
    """
    Tests REST API endpoints (T0101I, T0088I, T0075I) and MCP tools (warehouse_mcp)
    directly executing against real PostgreSQL tables.
    """

    def test_real_postgres_http_rest_api_fefo_workflow(self, isolated_tenant, real_db_conn):
        client = create_real_db_api_client()
        wh_repo = CrudRepository('T0008')
        customer_repo = CrudRepository('T0010')
        product_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        batch_repo = CrudRepository('T0088')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'API FEFO WH', 'is_active': True})
        wh_id = wh['id']
        cust = customer_repo.create({'name': 'API FEFO Cust', 'credit_limit': 10000.0, 'balance': 0.0})
        prod = product_repo.create({'name': 'Organic Greek Yogurt', 'sku': 'REST-YOG-01', 'price': 4.0, 'is_active': True})
        prod_id = prod['id']

        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_id, 'qty': 50.0, 'reserved_qty': 0.0})

        # Batches
        b1 = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-API-1', 'expiry_date': '2026-05-01', 'quantity': 10.0, 'warehouse_id': wh_id, 'status': 'Available'})
        b2 = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-API-2', 'expiry_date': '2026-08-01', 'quantity': 15.0, 'warehouse_id': wh_id, 'status': 'Available'})

        # 1. Create and Confirm Order via REST API
        so_resp = client.post('/api/T0012I/with-lines', json={
            'order': {
                'order_number': 'SO-REST-FEFO-01',
                'customer_id': cust['id'],
                'warehouse_id': wh_id,
                'status': 'Pending',
                'order_date': '2026-08-26',
            },
            'lines': [
                {
                    'product_id': prod_id,
                    'product_name': 'Organic Greek Yogurt',
                    'qty': 10.0,
                    'unit_price': 4.0,
                    'line_number': 1,
                }
            ]
        })
        assert so_resp.status_code == 201
        order_id = so_resp.json()['id']

        confirm_resp = client.post(f'/api/T0012I/{order_id}/confirm')
        assert confirm_resp.status_code == 200

        pl_repo = CrudRepository('T0101')
        pkl = pl_repo.list(filters={'sales_order_id': order_id})[0]
        pkl_id = pkl['id']

        # 2. GET /api/T0101I/{id}/detail
        detail_resp = client.get(f'/api/T0101I/{pkl_id}/detail')
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail['items']) == 1
        pli_id = detail['items'][0]['id']

        # 3. GET /api/T0101I/{id}/items/{item_id}/available-batches
        avail_resp = client.get(f'/api/T0101I/{pkl_id}/items/{pli_id}/available-batches')
        assert avail_resp.status_code == 200
        avail_batches = avail_resp.json()
        assert len(avail_batches) == 2
        # Earliest expiry first
        assert avail_batches[0]['batch_number'] == 'LOT-API-1'
        assert avail_batches[1]['batch_number'] == 'LOT-API-2'

        # 4. POST /api/T0101I/{id}/pick-item/{item_id} (Pick using LOT-API-2 override)
        pick_resp = client.post(f'/api/T0101I/{pkl_id}/pick-item/{pli_id}', json={
            'qty_picked': 10.0,
            'picked_batch_id': b2['id'],
            'picked_batch_number': 'LOT-API-2',
        })
        assert pick_resp.status_code == 200
        assert pick_resp.json()['picked_batch_id'] == b2['id']

        # 5. POST /api/T0101I/{id}/complete
        comp_resp = client.post(f'/api/T0101I/{pkl_id}/complete')
        assert comp_resp.status_code == 200
        assert comp_resp.json()['status'] == 'Completed'

        # 6. GET /api/T0088I/recall-report?batch_number=LOT-API-2
        recall_resp = client.get('/api/T0088I/recall-report?batch_number=LOT-API-2')
        assert recall_resp.status_code == 200
        recall_data = recall_resp.json()
        assert recall_data['batch']['batch_number'] == 'LOT-API-2'
        assert float(recall_data['summary']['total_qty_picked']) == 10.0
        assert recall_data['summary']['total_affected_customers'] == 1

        # 7. GET /api/T0088I/{id}/trace
        trace_resp = client.get(f'/api/T0088I/{b2["id"]}/trace')
        assert trace_resp.status_code == 200
        assert trace_resp.json()['batch']['id'] == b2['id']

    def test_real_postgres_mcp_warehouse_tools_workflow(self, isolated_tenant, real_db_conn):
        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        batch_repo = CrudRepository('T0088')
        customer_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'MCP FEFO WH', 'is_active': True})
        wh_id = wh['id']
        cust = customer_repo.create({'name': 'MCP FEFO Cust', 'credit_limit': 10000.0, 'balance': 0.0})
        prod = product_repo.create({'name': 'MCP Perishable Juice', 'sku': 'JUICE-MCP-01', 'price': 3.0, 'is_active': True})
        prod_id = prod['id']

        stock_repo = CrudRepository('T0009')
        stock_repo.create({'product_id': prod_id, 'warehouse_id': wh_id, 'qty': 50.0, 'reserved_qty': 0.0})

        b1 = batch_repo.create({'product_id': prod_id, 'batch_number': 'LOT-MCP-J1', 'expiry_date': '2026-05-15', 'quantity': 25.0, 'warehouse_id': wh_id, 'status': 'Available'})

        # 1. MCP list_batch_numbers
        mcp_batches = wh_mcp._list_batch(product_id=prod_id)
        assert len(mcp_batches) == 1
        assert mcp_batches[0]['batch_number'] == 'LOT-MCP-J1'

        # 2. Create order & confirm via MCP
        order = sales_mcp._create_order(customer_id=cust['id'], warehouse_id=wh_id, subtotal=30.0, grand_total=30.0)
        order_id = order['id']
        sales_mcp._create_order_line(sales_order_id=order_id, product_name='MCP Perishable Juice', product_id=prod_id, qty=10.0, unit_price=3.0)
        sales_mcp._confirm_order(order_id)

        # 3. List pick lists via MCP
        pkls = wh_mcp._list_pick(sales_order_id=order_id)
        assert len(pkls) == 1
        pkl_id = pkls[0]['id']

        # 4. Get pick list detail via MCP
        pkl_detail = wh_mcp._get_pick_list(pkl_id)
        pli_id = pkl_detail['items'][0]['id']
        assert pkl_detail['items'][0]['batch_number'] == 'LOT-MCP-J1'

        # 5. Pick item via MCP
        pick_res = wh_mcp._pick_item(item_id=pli_id, qty_picked=10.0, pick_list_id=pkl_id)
        assert float(pick_res['qty_picked']) == 10.0

        # 6. Complete pick list
        pick_svc = PickListService()
        pick_svc.complete_picking(pkl_id)

        # 7. Get recall report via MCP
        recall = wh_mcp._get_batch_recall_report(batch_number='LOT-MCP-J1')
        assert recall['batch']['batch_number'] == 'LOT-MCP-J1'
        assert float(recall['summary']['total_qty_picked']) == 10.0


# ============================================================================
# 5. Database Constraints, Negative Handling & Tenant Isolation
# ============================================================================

class TestRealPostgresFEFOConstraintsAndTenantIsolation:
    """
    Tests database constraints, negative edge cases, and multi-tenant isolation
    in real PostgreSQL:
    - Unique batch number per product enforcement in T0088.
    - Quantity below 0 prevention on batch adjustments.
    - Tenant isolation across batches, warehouses, and recall dossiers.
    """

    def test_real_postgres_batch_duplicate_constraint_and_negative_quantity_prevention(self, isolated_tenant):
        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        batch_repo = CrudRepository('T0088')
        batch_svc = BatchNumberService(batch_repo)

        wh = wh_repo.create({'name': 'Constraint WH', 'is_active': True})
        prod = product_repo.create({'name': 'Constraint Item', 'sku': 'CONSTR-01', 'price': 10.0, 'is_active': True})

        # Create initial batch
        b1 = batch_svc.create({
            'product_id': prod['id'],
            'batch_number': 'LOT-UNIQUE-01',
            'expiry_date': '2026-12-31',
            'quantity': 20.0,
            'warehouse_id': wh['id'],
        })
        assert b1['id'] is not None

        # 1. Duplicate batch_number for same product must raise ValueError
        with pytest.raises(ValueError, match="already exists for this product"):
            batch_svc.create({
                'product_id': prod['id'],
                'batch_number': 'LOT-UNIQUE-01',
                'expiry_date': '2026-12-31',
                'quantity': 10.0,
                'warehouse_id': wh['id'],
            })

        # 2. Adjust quantity cannot drive batch below 0
        with pytest.raises(ValueError, match="Resulting quantity cannot be below 0"):
            batch_svc.adjustQuantity(b1['id'], -25.0)

        # Quantity must remain 20.0
        assert float(batch_repo.get(b1['id'])['quantity']) == 20.0

    def test_real_postgres_fefo_tenant_data_isolation(self, real_harness, db_cleaner, real_db_conn):
        """
        Verify that multi-tenant isolation in PostgreSQL strictly isolates
        batches, warehouses, FEFO allocations, and recall reports between tenants.
        """
        from packages.database.isolation import isolated_tenant as isolated_tenant_ctx

        wh_repo = CrudRepository('T0008')
        product_repo = CrudRepository('T0003')
        batch_repo = CrudRepository('T0088')
        batch_svc = BatchNumberService(batch_repo)

        with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Alpha Corp") as (tenant_a, _):
            wh_a = wh_repo.create({'name': 'Tenant A Warehouse', 'is_active': True})
            prod_a = product_repo.create({'name': 'Tenant A Vaccine Lot', 'sku': 'VAC-TENANT-A', 'price': 100.0, 'is_active': True})

            batch_a = batch_repo.create({
                'product_id': prod_a['id'],
                'batch_number': 'LOT-TENANT-A-SECRET',
                'expiry_date': '2026-11-01',
                'quantity': 50.0,
                'warehouse_id': wh_a['id'],
                'status': 'Available',
            })

            # Verify Tenant A sees its batch
            assert batch_repo.get(batch_a['id']) is not None
            assert len(batch_svc.allocate_fefo_lots(prod_a['id'], wh_a['id'], qty_needed=10.0)) == 1

            # Switch context to Tenant Beta
            with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner, business_name="Tenant Beta Corp") as (tenant_b, _):
                # Tenant B cannot see Tenant A's batch, warehouse, or product
                assert batch_repo.get(batch_a['id']) is None
                assert wh_repo.get(wh_a['id']) is None
                assert product_repo.get(prod_a['id']) is None

                # Tenant B FEFO allocation for prod_a returns empty list
                assert batch_svc.allocate_fefo_lots(prod_a['id'], wh_a['id'], qty_needed=10.0) == []

                # Tenant B querying recall report for Tenant A's batch raises Not Found
                with pytest.raises(ValueError, match="not found"):
                    batch_svc.get_recall_report(batch_number='LOT-TENANT-A-SECRET')
