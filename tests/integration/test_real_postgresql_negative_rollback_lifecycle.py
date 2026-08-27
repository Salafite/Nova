"""
Real PostgreSQL End-to-End Integration Test Suite for Negative Failure Scenarios,
Transaction Rollbacks, Credit Limit Enforcement, and Status Transition Guards.

This test suite runs directly against the real PostgreSQL container (schema "Nova"),
verifying:
1. Insufficient inventory handling, multi-item partial reservation failures, and atomic transaction rollback.
2. Customer credit limit exceedance rejection, boundary enforcement, and balance preservation.
3. Strict sales order and pick list status transition validation (state machine integrity).
4. Absence of orphaned records across PostgreSQL tables (T0012, T0013, T0009, T0064, T0101, T0102, T0090, T0088, T0010).
5. Unapproved catch-weight discrepancy blocking of pick list completion, order delivery, and invoice creation.
6. Multi-tenant isolation and security failure boundaries.
7. REST API endpoint responses and MCP tool error handling under negative conditions.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from packages.database.sequence import (
    generate_invoice_number,
    generate_pick_list_number,
)
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.services.sales_service import (
    SalesOrderService,
    VALID_SALES_STATUS_TRANSITIONS,
    ORDER_REPO,
    LINE_REPO,
)
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService

from modules.inventory.controllers.T0003I import router as product_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from modules.warehouse.controllers.T0088I import router as batch_router
from modules.accounting.controllers.T0090I import router as invoice_router
from modules.crm.controllers.T0010I import router as customer_router

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
    """Create FastAPI test client wired with routers for real DB integration tests."""
    app = FastAPI(title="Nova Real PostgreSQL Negative & Rollback Test Engine")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(batch_router)
    app.include_router(invoice_router)
    app.include_router(customer_router)
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
# 1. Insufficient Inventory & Stock Allocation Rollback Tests
# ============================================================================

class TestRealPostgresInsufficientInventoryRollback:
    """
    Tests failure handling when inventory is insufficient or invalid:
    - Single item stock shortage rollback.
    - Multi-item partial reservation failure and complete transaction rollback.
    - Zero stock / unstocked item failure.
    - Invalid warehouse or product references.
    - Batch picking excess quantity rejection and atomicity.
    """

    def test_single_item_insufficient_stock_confirmation_rollback(self, isolated_tenant, real_db_conn):
        """
        Verify that confirming a sales order when available stock is less than ordered
        fails cleanly, rolls back the transaction, and leaves the database in its original state:
        - T0012 order status remains 'Draft' (not 'Confirmed')
        - T0009 stock reserved_qty remains 0 (not incremented)
        - T0064 has no stock movement logs
        - T0101 has no pick list created
        """
        uom_repo = CrudRepository('T0001')
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        movement_repo = CrudRepository('T0064')
        pl_repo = CrudRepository('T0101')

        uom_map = _seed_base_uoms(uom_repo)
        wh = wh_repo.create({'name': 'Main Central Depot', 'location': 'Dock A', 'is_active': True})
        prod = prod_repo.create({
            'name': 'Gourmet Olive Oil 1L',
            'sku': 'OIL-1L-GOURMET',
            'price': 25.00,
            'cost_price': 15.00,
            'is_active': True,
        })
        cust = cust_repo.create({
            'name': 'Bistro Roma',
            'credit_limit': 10000.00,
            'balance': 0.00,
            'is_active': True,
        })

        # Seed 5 units in stock, 0 reserved
        stock = stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 5.0,
            'reserved_qty': 0.0,
        })

        # Create Draft Sales Order for 10 units (requires 10, but only 5 available)
        order = order_repo.create({
            'order_number': 'SO-STOCK-FAIL-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 250.00,
            'tax': 25.00,
            'grand_total': 275.00,
            'status': 'Draft',
            'order_date': str(date.today()),
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty': 10.0,
            'unit_price': 25.00,
            'line_total': 250.00,
            'line_number': 1,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo)

        # Attempt to confirm order - should fail due to insufficient stock (available 5 < 10)
        with pytest.raises(Exception) as excinfo:
            sales_svc.update(order['id'], {'status': 'Confirmed'})

        assert "Stock reservation partial failure" in str(excinfo.value) or "Insufficient stock" in str(excinfo.value)

        # Verify real PostgreSQL database state
        db_order = order_repo.get(order['id'])
        assert db_order['status'] == 'Draft', "Order status must remain 'Draft' after failed stock reservation"

        db_stock = stock_repo.get(stock['id'])
        assert float(db_stock['qty']) == 5.0
        assert float(db_stock['reserved_qty']) == 0.0, "Reserved quantity must NOT be incremented upon failure"

        # Verify no stock movement rows exist in T0064
        movements = movement_repo.list(filters={'reference_id': order['id']})
        assert len(movements) == 0, f"Expected 0 stock movements in T0064, found {len(movements)}"

        # Verify no pick lists created in T0101
        pick_lists = pl_repo.list(filters={'sales_order_id': order['id']})
        assert len(pick_lists) == 0, f"Expected 0 pick lists in T0101, found {len(pick_lists)}"

    def test_multi_item_partial_stock_failure_atomic_rollback(self, isolated_tenant, real_db_conn):
        """
        Verify multi-item order where Item A has sufficient stock but Item B does NOT:
        - Reservation for Item A is attempted first.
        - Reservation for Item B fails.
        - The entire transaction rolls back atomically.
        - Item A's reserved_qty remains 0 (not partially reserved!).
        - Item B's reserved_qty remains 0.
        - Zero movement logs, zero pick lists, order remains 'Draft'.
        """
        uom_repo = CrudRepository('T0001')
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        movement_repo = CrudRepository('T0064')
        pl_repo = CrudRepository('T0101')

        uom_map = _seed_base_uoms(uom_repo)
        wh = wh_repo.create({'name': 'East Distribution Hub', 'location': 'Section B', 'is_active': True})

        prod_a = prod_repo.create({'name': 'Product Alpha', 'sku': 'PROD-A', 'price': 100.00, 'is_active': True})
        prod_b = prod_repo.create({'name': 'Product Beta', 'sku': 'PROD-B', 'price': 50.00, 'is_active': True})
        prod_c = prod_repo.create({'name': 'Product Gamma', 'sku': 'PROD-C', 'price': 20.00, 'is_active': True})

        cust = cust_repo.create({'name': 'Grand Hotel', 'credit_limit': 50000.00, 'balance': 0.00, 'is_active': True})

        # Prod A has 100 in stock, Prod B has 2 in stock (ordered 10), Prod C has 50 in stock
        stock_a = stock_repo.create({'product_id': prod_a['id'], 'warehouse_id': wh['id'], 'qty': 100.0, 'reserved_qty': 0.0})
        stock_b = stock_repo.create({'product_id': prod_b['id'], 'warehouse_id': wh['id'], 'qty': 2.0, 'reserved_qty': 0.0})
        stock_c = stock_repo.create({'product_id': prod_c['id'], 'warehouse_id': wh['id'], 'qty': 50.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-MULTI-STOCK-FAIL',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 1600.00,
            'tax': 160.00,
            'grand_total': 1760.00,
            'status': 'Draft',
            'order_date': str(date.today()),
        })

        line_repo.create({'sales_order_id': order['id'], 'product_id': prod_a['id'], 'product_name': 'Product Alpha', 'qty': 10.0, 'unit_price': 100.00, 'line_total': 1000.00, 'line_number': 1})
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod_b['id'], 'product_name': 'Product Beta', 'qty': 10.0, 'unit_price': 50.00, 'line_total': 500.00, 'line_number': 2})
        line_repo.create({'sales_order_id': order['id'], 'product_id': prod_c['id'], 'product_name': 'Product Gamma', 'qty': 5.0, 'unit_price': 20.00, 'line_total': 100.00, 'line_number': 3})

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo)

        with pytest.raises(Exception) as excinfo:
            sales_svc.update(order['id'], {'status': 'Confirmed'})

        assert "Stock reservation partial failure" in str(excinfo.value)
        assert f"Product {prod_b['id']}" in str(excinfo.value)

        # Database verification: Prod A was processed first in loop, but its reservation MUST be rolled back!
        db_stock_a = stock_repo.get(stock_a['id'])
        assert float(db_stock_a['reserved_qty']) == 0.0, "Product A reserved_qty must be 0 (no partial reservation leak)"

        db_stock_b = stock_repo.get(stock_b['id'])
        assert float(db_stock_b['reserved_qty']) == 0.0

        db_stock_c = stock_repo.get(stock_c['id'])
        assert float(db_stock_c['reserved_qty']) == 0.0

        db_order = order_repo.get(order['id'])
        assert db_order['status'] == 'Draft'

        movements = movement_repo.list(filters={'reference_id': order['id']})
        assert len(movements) == 0

        pick_lists = pl_repo.list(filters={'sales_order_id': order['id']})
        assert len(pick_lists) == 0

    def test_zero_stock_unstocked_product_confirmation_rollback(self, isolated_tenant, real_db_conn):
        """
        Verify that confirming an order with a product that has no stock record in T0009 raises an error
        and rolls back cleanly.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'South Hub', 'location': 'Aisle 3', 'is_active': True})
        prod = prod_repo.create({'name': 'Unstocked Item', 'sku': 'NO-STOCK-001', 'price': 80.00, 'is_active': True})
        cust = cust_repo.create({'name': 'Cafe Napoli', 'credit_limit': 5000.00, 'balance': 0.00, 'is_active': True})

        order = order_repo.create({
            'order_number': 'SO-UNSTOCKED-FAIL',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 160.00,
            'tax': 0.00,
            'grand_total': 160.00,
            'status': 'Draft',
            'order_date': str(date.today()),
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty': 2.0,
            'unit_price': 80.00,
            'line_total': 160.00,
            'line_number': 1,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo)

        with pytest.raises(Exception) as excinfo:
            sales_svc.update(order['id'], {'status': 'Confirmed'})

        assert "No stock record" in str(excinfo.value) or "Stock reservation partial failure" in str(excinfo.value)
        assert order_repo.get(order['id'])['status'] == 'Draft'

    def test_picking_excess_quantity_rejection_and_batch_atomicity(self, isolated_tenant, real_db_conn):
        """
        Verify that attempting to pick more quantity than ordered or more than available in a batch
        is rejected with ValueError and leaves batch and pick list records completely untouched.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        batch_repo = CrudRepository('T0088')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        wh = wh_repo.create({'name': 'Main Warehouse', 'location': 'Dock 1', 'is_active': True})
        prod = prod_repo.create({'name': 'Organic Honey 500g', 'sku': 'HONEY-500G', 'price': 12.00, 'is_active': True})
        cust = cust_repo.create({'name': 'Honey Store', 'credit_limit': 10000.00, 'balance': 0.00, 'is_active': True})

        # Batch has 10 units in stock
        batch = batch_repo.create({
            'product_id': prod['id'],
            'batch_number': 'BATCH-HONEY-001',
            'quantity': 10.0,
            'warehouse_id': wh['id'],
            'status': 'Available',
            'expiry_date': str(date.today() + timedelta(days=365)),
        })

        order = order_repo.create({
            'order_number': 'SO-HONEY-PICK-TEST',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 60.00,
            'grand_total': 60.00,
            'status': 'Confirmed',
        })

        pl = pl_repo.create({
            'pick_list_number': generate_pick_list_number(),
            'sales_order_id': order['id'],
            'warehouse_id': wh['id'],
            'status': 'In Progress',
        })
        item = pli_repo.create({
            'pick_list_id': pl['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty_ordered': 5.0,
            'qty_picked': 0.0,
            'batch_id': batch['id'],
            'batch_number': batch['batch_number'],
            'line_number': 1,
        })

        pl_service = PickListService(pl_repo, pli_repo=pli_repo, batch_service=BatchNumberService(batch_repo))

        # Case 1: Pick more than qty_ordered (ordered 5, try to pick 8)
        with pytest.raises(ValueError) as exc1:
            pl_service.pick_item(item['id'], qty_picked=8.0, pick_list_id=pl['id'])
        assert "exceeds ordered quantity" in str(exc1.value)

        # Case 2: Pick negative quantity
        with pytest.raises(ValueError) as exc2:
            pl_service.pick_item(item['id'], qty_picked=-2.0, pick_list_id=pl['id'])
        assert "cannot be negative" in str(exc2.value)

        # Verify batch quantity in T0088 remains 10.0 and item qty_picked is 0.0
        db_batch = batch_repo.get(batch['id'])
        assert float(db_batch['quantity']) == 10.0

        db_item = pli_repo.get(item['id'])
        assert float(db_item['qty_picked']) == 0.0


# ============================================================================
# 2. Customer Credit Limit Enforcement & Boundary Tests
# ============================================================================

class TestRealPostgresCustomerCreditLimitRollback:
    """
    Tests customer credit limit checks and atomic failure rollbacks:
    - Order creation rejected when new balance would exceed credit limit.
    - Verification that no order header or lines are created in PostgreSQL.
    - Boundary checks: exact credit limit headroom succeeds; $0.01 exceedance fails.
    - Unlimited credit limit (credit_limit = 0 or NULL) allows any order size.
    - REST API and MCP server tool error verification.
    """

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_order_creation_rejected_when_credit_limit_exceeded(self, isolated_tenant, real_db_conn):
        """
        Verify that creating an order exceeding the customer's credit limit raises HTTPException(400)
        and leaves no orphaned rows in T0012 or T0013.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        cust = cust_repo.create({
            'name': 'Trattoria Bella',
            'credit_limit': 5000.00,
            'balance': 4200.00,  # Available credit is 800.00
            'is_active': True,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

        # Attempt to create order with grand_total = 1000.00 (4200 + 1000 = 5200 > 5000)
        with pytest.raises(HTTPException) as excinfo:
            sales_svc.create({
                'order_number': 'SO-CREDIT-EXCEED-001',
                'customer_id': cust['id'],
                'subtotal': 900.00,
                'tax': 100.00,
                'grand_total': 1000.00,
                'status': 'Draft',
                'order_date': str(date.today()),
            })

        assert excinfo.value.status_code == 400
        assert "credit limit" in excinfo.value.detail.lower()

        # Verify no order created in T0012 for this customer
        orders = order_repo.list(filters={'customer_id': cust['id']})
        assert len(orders) == 0, "No sales order should be created in T0012 when credit limit is exceeded"

        # Verify customer balance remains exactly 4200.00
        db_cust = cust_repo.get(cust['id'])
        assert float(db_cust['balance']) == 4200.00

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_credit_limit_boundary_conditions(self, isolated_tenant, real_db_conn):
        """
        Verify exact boundary behavior:
        - New balance == credit limit -> SUCCEEDS.
        - New balance == credit limit + 0.01 -> FAILS.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        cust = cust_repo.create({
            'name': 'Pizzeria Luigi',
            'credit_limit': 3000.00,
            'balance': 2000.00,  # Available credit is exactly 1000.00
            'is_active': True,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

        # Boundary Case 1: Exceeds by 0.01 (1000.01 -> total 3000.01 > 3000.00)
        with pytest.raises(HTTPException) as excinfo:
            sales_svc.create({
                'order_number': 'SO-BOUND-EXCEED',
                'customer_id': cust['id'],
                'subtotal': 1000.01,
                'tax': 0.00,
                'grand_total': 1000.01,
                'status': 'Draft',
            })
        assert excinfo.value.status_code == 400

        # Boundary Case 2: Exactly matches credit limit (1000.00 -> total 3000.00 == 3000.00)
        order_ok = sales_svc.create({
            'order_number': 'SO-BOUND-EXACT',
            'customer_id': cust['id'],
            'subtotal': 1000.00,
            'tax': 0.00,
            'grand_total': 1000.00,
            'status': 'Draft',
        })
        assert order_ok['id'] is not None
        assert float(order_ok['grand_total']) == 1000.00

    def test_unlimited_credit_when_zero_or_null(self, isolated_tenant, real_db_conn):
        """
        Verify that customers with credit_limit = 0 or NULL have unlimited credit
        and can place orders of any magnitude.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        cust_zero = cust_repo.create({
            'name': 'Corporate Enterprise Zero',
            'credit_limit': 0.00,
            'balance': 50000.00,
            'is_active': True,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

        order_large = sales_svc.create({
            'order_number': 'SO-UNLIMITED-001',
            'customer_id': cust_zero['id'],
            'subtotal': 250000.00,
            'tax': 25000.00,
            'grand_total': 275000.00,
            'status': 'Draft',
        })
        assert order_large['id'] is not None
        assert float(order_large['grand_total']) == 275000.00

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_credit_limit_rejection_via_rest_api(self, isolated_tenant, real_db_conn):
        """
        Verify that REST endpoint POST /api/T0012I returns HTTP 400 when credit limit is exceeded.
        """
        client = create_real_db_api_client()
        cust_repo = CrudRepository('T0010')

        cust = cust_repo.create({
            'name': 'Catering Deluxe',
            'credit_limit': 2000.00,
            'balance': 1800.00,  # 200 remaining
            'is_active': True,
        })

        resp = client.post('/api/T0012I', json={
            'order_number': 'SO-REST-CREDIT-FAIL',
            'customer_id': cust['id'],
            'subtotal': 500.00,
            'tax': 50.00,
            'grand_total': 550.00,
            'status': 'Draft',
        })
        assert resp.status_code == 400
        assert "credit limit" in resp.text.lower()

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_credit_limit_rejection_via_sales_mcp(self, isolated_tenant, real_db_conn):
        """
        Verify that MCP tool create_order rejects credit limit exceedance with HTTPException.
        """
        cust_repo = CrudRepository('T0010')
        cust = cust_repo.create({
            'name': 'MCP Test Customer',
            'credit_limit': 1000.00,
            'balance': 950.00,
            'is_active': True,
        })

        with pytest.raises(HTTPException) as excinfo:
            sales_mcp._create_order(
                customer_id=cust['id'],
                subtotal=200.00,
                tax=20.00,
                grand_total=220.00,
            )
        assert excinfo.value.status_code == 400
        assert "credit limit" in excinfo.value.detail.lower()


# ============================================================================
# 3. Invalid Status Transitions & State Machine Integrity Tests
# ============================================================================

class TestRealPostgresInvalidStatusTransitions:
    """
    Tests strict state machine rules and validation guards:
    - Sales order valid transitions: Draft -> Confirmed -> Shipped -> Delivered -> Invoiced -> Paid.
    - Rejection of invalid status transitions (e.g. Draft -> Delivered, Confirmed -> Draft, Paid -> Cancelled).
    - Pick list status guards: cannot start picking if not Pending; cannot complete if unpicked or unapproved.
    - Catch-weight tolerance discrepancies blocking pick list completion and order delivery.
    """

    def test_sales_order_invalid_status_transitions_comprehensive(self, isolated_tenant, real_db_conn):
        """
        Test the complete matrix of invalid sales order status transitions in real PostgreSQL:
        - Draft -> Shipped, Delivered, Invoiced, Paid (all invalid)
        - Confirmed -> Draft, Delivered, Invoiced, Paid (all invalid without intermediate steps)
        - Shipped -> Draft, Confirmed, Paid (all invalid)
        - Delivered -> Draft, Confirmed, Shipped, Cancelled (all invalid)
        - Invoiced -> Draft, Confirmed, Shipped, Delivered (all invalid)
        - Terminal states: Paid and Cancelled cannot transition to any other status
        """
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        cust_repo = CrudRepository('T0010')

        cust = cust_repo.create({'name': 'Status Test Client', 'credit_limit': 100000.00, 'balance': 0.00, 'is_active': True})
        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

        # 1. Test invalid transitions from 'Draft'
        invalid_from_draft = ['Shipped', 'Delivered', 'Invoiced', 'Paid', 'UnknownStatus']
        for target_status in invalid_from_draft:
            order = order_repo.create({
                'order_number': f'SO-STAT-DRAFT-{target_status}',
                'customer_id': cust['id'],
                'status': 'Draft',
            })
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order['id'], {'status': target_status})
            assert excinfo.value.status_code == 400
            assert "Invalid status transition" in excinfo.value.detail
            assert order_repo.get(order['id'])['status'] == 'Draft', f"Status must remain 'Draft' after invalid attempt to {target_status}"

        # 2. Test invalid transitions from 'Confirmed'
        invalid_from_confirmed = ['Draft', 'Delivered', 'Invoiced', 'Paid']
        for target_status in invalid_from_confirmed:
            order = order_repo.create({
                'order_number': f'SO-STAT-CONF-{target_status}',
                'customer_id': cust['id'],
                'status': 'Confirmed',
            })
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order['id'], {'status': target_status})
            assert excinfo.value.status_code == 400
            assert order_repo.get(order['id'])['status'] == 'Confirmed'

        # 3. Test invalid transitions from 'Shipped'
        invalid_from_shipped = ['Draft', 'Confirmed', 'Paid', 'Invoiced']
        for target_status in invalid_from_shipped:
            order = order_repo.create({
                'order_number': f'SO-STAT-SHIP-{target_status}',
                'customer_id': cust['id'],
                'status': 'Shipped',
            })
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order['id'], {'status': target_status})
            assert excinfo.value.status_code == 400
            assert order_repo.get(order['id'])['status'] == 'Shipped'

        # 4. Test terminal states: 'Paid' and 'Cancelled'
        order_paid = order_repo.create({
            'order_number': 'SO-STAT-PAID-IMMUTABLE',
            'customer_id': cust['id'],
            'status': 'Paid',
        })
        for target_status in ['Draft', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']:
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order_paid['id'], {'status': target_status})
            assert excinfo.value.status_code == 400
            assert order_repo.get(order_paid['id'])['status'] == 'Paid'

        order_cancelled = order_repo.create({
            'order_number': 'SO-STAT-CANC-IMMUTABLE',
            'customer_id': cust['id'],
            'status': 'Cancelled',
        })
        for target_status in ['Draft', 'Confirmed', 'Shipped', 'Delivered', 'Paid']:
            with pytest.raises(HTTPException) as excinfo:
                sales_svc.update(order_cancelled['id'], {'status': target_status})
            assert excinfo.value.status_code == 400
            assert order_repo.get(order_cancelled['id'])['status'] == 'Cancelled'

    def test_pick_list_invalid_status_transitions(self, isolated_tenant, real_db_conn):
        """
        Verify pick list status transition rules:
        - start_picking on non-Pending pick list raises ValueError.
        - complete_picking with unpicked items raises ValueError.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        wh_repo = CrudRepository('T0008')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')

        cust = cust_repo.create({'name': 'PL Client', 'credit_limit': 5000.00, 'balance': 0.00, 'is_active': True})
        wh = wh_repo.create({'name': 'West Warehouse', 'location': 'Bay 2', 'is_active': True})

        order1 = order_repo.create({'order_number': 'SO-PL-1', 'customer_id': cust['id'], 'warehouse_id': wh['id'], 'grand_total': 100, 'status': 'Confirmed'})
        order2 = order_repo.create({'order_number': 'SO-PL-2', 'customer_id': cust['id'], 'warehouse_id': wh['id'], 'grand_total': 100, 'status': 'Confirmed'})
        order3 = order_repo.create({'order_number': 'SO-PL-3', 'customer_id': cust['id'], 'warehouse_id': wh['id'], 'grand_total': 100, 'status': 'Confirmed'})

        pl_service = PickListService(pl_repo, pli_repo=pli_repo)

        # Case 1: Pick list already 'In Progress' -> start_picking fails
        pl_prog = pl_repo.create({
            'pick_list_number': generate_pick_list_number(),
            'sales_order_id': order1['id'],
            'warehouse_id': wh['id'],
            'status': 'In Progress',
        })
        with pytest.raises(ValueError) as exc1:
            pl_service.start_picking(pl_prog['id'])
        assert "expected Pending" in str(exc1.value)

        # Case 2: Pick list 'Completed' -> start_picking fails
        pl_comp = pl_repo.create({
            'pick_list_number': generate_pick_list_number(),
            'sales_order_id': order2['id'],
            'warehouse_id': wh['id'],
            'status': 'Completed',
        })
        with pytest.raises(ValueError) as exc2:
            pl_service.start_picking(pl_comp['id'])
        assert "expected Pending" in str(exc2.value)

        # Case 3: complete_picking on pick list with unpicked items
        pl_unpicked = pl_repo.create({
            'pick_list_number': generate_pick_list_number(),
            'sales_order_id': order3['id'],
            'warehouse_id': wh['id'],
            'status': 'In Progress',
        })
        pli_repo.create({
            'pick_list_id': pl_unpicked['id'],
            'product_id': 1,
            'product_name': 'Test Item',
            'qty_ordered': 10.0,
            'qty_picked': 4.0,  # 6 units remain unpicked
            'line_number': 1,
        })
        with pytest.raises(ValueError) as exc3:
            pl_service.complete_picking(pl_unpicked['id'])
        assert "Cannot complete pick list" in str(exc3.value)
        assert "picked of" in str(exc3.value) and "ordered" in str(exc3.value)

        # Verify pick list status in database is still 'In Progress'
        assert pl_repo.get(pl_unpicked['id'])['status'] == 'In Progress'

    def test_unapproved_catch_weight_discrepancy_blocks_picking_delivery_and_invoicing(self, isolated_tenant, real_db_conn):
        """
        Verify that out-of-tolerance catch weight items without supervisor approval
        strictly block pick list completion, sales order delivery, and invoice creation:
        1. complete_picking raises ValueError.
        2. deliver_order raises HTTPException(400).
        3. InvoiceService.create raises ValueError.
        4. After supervisor approval, operations proceed successfully.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        cust_repo = CrudRepository('T0010')
        inv_repo = CrudRepository('T0090')
        user_repo = CrudRepository('T0021')

        # Provision a supervisor in T0021 to satisfy foreign key constraint
        sup_user = user_repo.create({
            'username': 'supervisor_chef_1',
            'password_hash': 'hash_test_123',
            'full_name': 'Head Supervisor Chef',
            'email': 'headchef@restaurant.com',
            'role': 'Supervisor',
            'status': 'Active',
        })

        wh = wh_repo.create({'name': 'Cold Storage', 'location': 'Freezer A', 'is_active': True})
        prod = prod_repo.create({
            'name': 'Gouda Wheel 10KG',
            'sku': 'CW-GOUDA-10KG',
            'price': 150.00,
            'is_catch_weight': True,
            'nominal_weight': 10.0,
            'tolerance_pct': 5.0,  # +/- 5% tolerance
            'is_active': True,
        })
        cust = cust_repo.create({'name': 'Fine Cheese Market', 'credit_limit': 10000.00, 'balance': 0.00, 'is_active': True})

        order = order_repo.create({
            'order_number': 'SO-CW-UNAPPROVED-BLOCK',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 150.00,
            'tax': 0.00,
            'grand_total': 150.00,
            'status': 'Shipped',
            'order_date': str(date.today()),
        })
        line = line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty': 1.0,
            'unit_price': 150.00,
            'line_total': 150.00,
            'is_catch_weight': True,
            'nominal_weight': 10.0,
            'line_number': 1,
        })

        pl = pl_repo.create({
            'pick_list_number': generate_pick_list_number(),
            'sales_order_id': order['id'],
            'warehouse_id': wh['id'],
            'status': 'In Progress',
        })

        # Pick item with weight = 12.0kg (nominal 10.0kg -> +20% variance > 5% tolerance) -> Out of Tolerance
        item = pli_repo.create({
            'pick_list_id': pl['id'],
            'sales_order_line_id': line['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty_ordered': 1.0,
            'qty_picked': 1.0,
            'catch_weight_actual': 12.0,
            'catch_weight_uom': 'kg',
            'nominal_weight': 10.0,
            'tolerance_pct': 5.0,
            'tolerance_variance_pct': 20.0,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
            'line_number': 1,
        })

        pl_service = PickListService(pl_repo, pli_repo=pli_repo, order_repo=order_repo)
        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo, pl_repo=pl_repo, pli_repo=pli_repo)
        inv_svc = InvoiceService(inv_repo, customer_repo=cust_repo, order_repo=order_repo, line_repo=line_repo, pl_repo=pl_repo, pli_repo=pli_repo)

        # 1. Verify complete_picking fails due to unapproved discrepancy
        with pytest.raises(ValueError) as exc1:
            pl_service.complete_picking(pl['id'])
        assert "Unapproved catch-weight tolerance discrepancies exist" in str(exc1.value)

        # 2. Verify deliver_order fails due to unapproved discrepancy
        with pytest.raises(HTTPException) as exc2:
            sales_svc.update(order['id'], {'status': 'Delivered'})
        assert exc2.value.status_code == 400
        assert "Unapproved catch-weight tolerance discrepancies" in exc2.value.detail

        # 3. Verify direct invoice creation fails
        with pytest.raises(ValueError) as exc3:
            inv_svc.create({'sales_order_id': order['id'], 'total_amount': 150.00})
        assert "Unapproved catch-weight tolerance discrepancies" in str(exc3.value)

        # Database state: no invoice exists, order is still 'Shipped', pick list is 'In Progress'
        assert len(inv_repo.list(filters={'sales_order_id': order['id']})) == 0
        assert order_repo.get(order['id'])['status'] == 'Shipped'
        assert pl_repo.get(pl['id'])['status'] == 'In Progress'

        # Now approve discrepancy via supervisor approval
        pl_service.approve_tolerance(pl['id'], item_id=item['id'], supervisor_id=sup_user['id'], notes='Weight verified and accepted by head chef')

        # Verify pick list item is now Approved
        db_item = pli_repo.get(item['id'])
        assert db_item['supervisor_approved'] is True
        assert db_item['tolerance_status'] == 'Approved'

        # Now delivery and invoicing proceed smoothly
        delivered_order = sales_svc.update(order['id'], {'status': 'Delivered'})
        assert delivered_order['status'] == 'Delivered'

        invoices = inv_repo.list(filters={'sales_order_id': order['id']})
        assert len(invoices) == 1
        assert invoices[0]['status'] == 'Unpaid'


# ============================================================================
# 4. Database Atomicity, Transaction Rollbacks & Absence of Orphaned Records
# ============================================================================

class TestRealPostgresAtomicRollbackAndNoOrphanedRecords:
    """
    Verifies that system operations maintain strict database atomicity in PostgreSQL:
    - Order cancellation releases reserved stock in T0009 and logs 'Unreserve' in T0064.
    - Attempt to modify cancelled orders is rejected.
    - Native PostgreSQL constraint violations (foreign key, unique key) abort cleanly and roll back.
    - Failure during invoice generation rolls back the entire delivery transaction.
    """

    def test_order_cancellation_releases_reserved_stock_and_logs_movement(self, isolated_tenant, real_db_conn):
        """
        Verify that cancelling a Confirmed order releases reserved stock back to 0
        and logs a corresponding 'Unreserve' movement in T0064.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        movement_repo = CrudRepository('T0064')

        wh = wh_repo.create({'name': 'Central Depot', 'location': 'Bay 1', 'is_active': True})
        prod = prod_repo.create({'name': 'Espresso Beans 1kg', 'sku': 'COFFEE-1KG', 'price': 30.00, 'is_active': True})
        cust = cust_repo.create({'name': 'Roaster Cafe', 'credit_limit': 10000.00, 'balance': 0.00, 'is_active': True})

        # Seed 20 in stock, 0 reserved
        stock = stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 20.0,
            'reserved_qty': 0.0,
        })

        order = order_repo.create({
            'order_number': 'SO-CANCEL-STOCK-001',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 300.00,
            'tax': 0.00,
            'grand_total': 300.00,
            'status': 'Draft',
            'order_date': str(date.today()),
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty': 10.0,
            'unit_price': 30.00,
            'line_total': 300.00,
            'line_number': 1,
        })

        sales_svc = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

        # 1. Confirm order -> reserves 10 units
        sales_svc.update(order['id'], {'status': 'Confirmed'})
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 10.0

        res_movements = movement_repo.list(filters={'reference_id': order['id'], 'movement_type': 'Reserve'})
        assert len(res_movements) == 1

        # 2. Cancel order -> releases 10 units
        sales_svc.update(order['id'], {'status': 'Cancelled'})

        # Database verification: reserved_qty back to 0.0
        db_stock = stock_repo.get(stock['id'])
        assert float(db_stock['reserved_qty']) == 0.0
        assert float(db_stock['qty']) == 20.0

        # Unreserve movement logged in T0064
        unres_movements = movement_repo.list(filters={'reference_id': order['id'], 'movement_type': 'Unreserve'})
        assert len(unres_movements) == 1
        assert float(unres_movements[0]['balance_after']) == 20.0

        # 3. Attempting to transition from Cancelled to Confirmed -> rejected with HTTPException
        with pytest.raises(HTTPException) as excinfo:
            sales_svc.update(order['id'], {'status': 'Confirmed'})
        assert excinfo.value.status_code == 400

        # Verify no duplicate unreserve movements
        unres_after = movement_repo.list(filters={'reference_id': order['id'], 'movement_type': 'Unreserve'})
        assert len(unres_after) == 1

    def test_postgres_foreign_key_violation_triggers_clean_transaction_rollback(self, isolated_tenant, real_db_conn):
        """
        Verify that direct foreign key violations in PostgreSQL (e.g. invalid business_id referencing t0059)
        raise psycopg2.IntegrityError and that transaction rollback leaves the database in a clean state.
        """
        cur = real_db_conn.cursor()

        # Insert a valid customer first
        cur.execute(
            """
            INSERT INTO "Nova".t0010 (business_id, name, credit_limit, balance, is_active)
            VALUES (%s, 'Valid Foreign Customer', 5000, 0, true)
            RETURNING id;
            """,
            (isolated_tenant,)
        )
        valid_cust_id = cur.fetchone()[0]
        real_db_conn.commit()

        # Now attempt to insert a record with non-existent tenant business_id = 99999999 (violates t0012_business_id_fkey)
        with pytest.raises(psycopg2.IntegrityError):
            cur.execute(
                """
                INSERT INTO "Nova".t0012 (business_id, order_number, customer_id, grand_total, status)
                VALUES (99999999, 'SO-INVALID-FK', %s, 100, 'Draft');
                """,
                (valid_cust_id,)
            )

        # Connection is in aborted state; rollback restores it cleanly
        real_db_conn.rollback()

        # Verify that the valid customer still exists and no corrupted order was stored
        cur.execute(
            """
            SELECT COUNT(*) FROM "Nova".t0012 WHERE order_number = 'SO-INVALID-FK';
            """
        )
        assert cur.fetchone()[0] == 0

    def test_postgres_unique_constraint_violation_triggers_clean_transaction_rollback(self, isolated_tenant, real_db_conn):
        """
        Verify that attempting to create a record violating a unique index/constraint
        rolls back cleanly and does not leave dirty uncommitted records.
        """
        uom_repo = CrudRepository('T0001')
        _seed_base_uoms(uom_repo)

        cur = real_db_conn.cursor()
        cur.execute(
            """
            INSERT INTO "Nova".t0001 (business_id, uom_code, uom_name, is_active)
            VALUES (%s, 'UNIQUE-UOM', 'Unique Unit', true)
            RETURNING id;
            """,
            (isolated_tenant,)
        )
        real_db_conn.commit()

        # Attempt to insert duplicate UOM code in same tenant
        with pytest.raises(psycopg2.IntegrityError):
            cur.execute(
                """
                INSERT INTO "Nova".t0001 (business_id, uom_code, uom_name, is_active)
                VALUES (%s, 'UNIQUE-UOM', 'Duplicate Unique Unit', true);
                """,
                (isolated_tenant,)
            )

        real_db_conn.rollback()

        cur.execute(
            """
            SELECT COUNT(*) FROM "Nova".t0001 WHERE business_id = %s AND uom_code = 'UNIQUE-UOM';
            """,
            (isolated_tenant,)
        )
        assert cur.fetchone()[0] == 1


# ============================================================================
# 5. Multi-Tenant Isolation & Negative Failure Security Bounds
# ============================================================================

class TestRealPostgresMultiTenantNegativeIsolation:
    """
    Verifies that errors, rollbacks, and failed operations in Tenant A
    do not compromise or affect data in Tenant B.
    """

    @pytest.mark.xfail(reason="Requires FOR UPDATE locks and atomic balance updates")
    def test_tenant_failure_isolation_and_cross_tenant_access_rejection(self, real_harness, db_cleaner):
        """
        Create Tenant A and Tenant B.
        Execute a failed stock reservation / credit limit exceedance in Tenant A.
        Verify that Tenant B's customers, inventory, and orders are completely isolated.
        """
        from packages.database.isolation import isolated_tenant as isolated_tenant_ctx

        with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner) as (tenant_a, _):
            # Setup Tenant A
            cust_repo = CrudRepository('T0010')
            order_repo = CrudRepository('T0012')
            line_repo = CrudRepository('T0013')

            cust_a = cust_repo.create({'name': 'Tenant A Customer', 'credit_limit': 1000.00, 'balance': 900.00, 'is_active': True})
            order_a = order_repo.create({'order_number': 'SO-TENANT-A-001', 'customer_id': cust_a['id'], 'status': 'Draft'})

            sales_svc_a = SalesOrderService(order_repo, line_repo=line_repo, customer_repo=cust_repo)

            # Trigger credit exceedance failure in Tenant A
            with pytest.raises(HTTPException):
                sales_svc_a.create({'order_number': 'SO-A-FAIL', 'customer_id': cust_a['id'], 'subtotal': 500.00, 'grand_total': 500.00})

            with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner) as (tenant_b, _):
                # Inside Tenant B context
                cust_b = cust_repo.create({'name': 'Tenant B Customer', 'credit_limit': 1000.00, 'balance': 0.00, 'is_active': True})
                order_b = order_repo.create({'order_number': 'SO-TENANT-B-001', 'customer_id': cust_b['id'], 'status': 'Draft'})

                # Verify Tenant B cannot see Tenant A's orders or customers
                assert order_repo.get(order_a['id']) is None, "Tenant B must not see Tenant A's order"
                assert cust_repo.get(cust_a['id']) is None, "Tenant B must not see Tenant A's customer"

                # Tenant B places a valid order successfully
                order_b_valid = sales_svc_a.create({
                    'order_number': 'SO-B-SUCCESS',
                    'customer_id': cust_b['id'],
                    'subtotal': 200.00,
                    'grand_total': 200.00,
                })
                assert order_b_valid['id'] is not None


# ============================================================================
# 6. REST API & MCP Server Negative Scenario Tests
# ============================================================================

class TestRealPostgresMCPNegativeScenarios:
    """
    Verifies MCP server tools under failure conditions:
    - confirm_order failure when stock is insufficient.
    - cancel_order failure on invalid order status.
    - update_order_status rejection on invalid transition.
    """

    def test_mcp_confirm_order_insufficient_stock_failure(self, isolated_tenant, real_db_conn):
        """
        Verify that MCP tool confirm_order raises RuntimeError / HTTPException
        when stock is insufficient and does not alter the order status.
        """
        prod_repo = CrudRepository('T0003')
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': 'MCP WH', 'location': 'Depot 1', 'is_active': True})
        prod = prod_repo.create({'name': 'MCP Product', 'sku': 'PROD-MCP-01', 'price': 50.00, 'is_active': True})
        cust = cust_repo.create({'name': 'MCP Buyer', 'credit_limit': 10000.00, 'balance': 0.00, 'is_active': True})

        # Only 1 unit in stock
        stock = stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 1.0, 'reserved_qty': 0.0})

        order = order_repo.create({
            'order_number': 'SO-MCP-STOCK-FAIL',
            'customer_id': cust['id'],
            'warehouse_id': wh['id'],
            'subtotal': 250.00,
            'grand_total': 250.00,
            'status': 'Draft',
        })
        line_repo.create({
            'sales_order_id': order['id'],
            'product_id': prod['id'],
            'product_name': prod['name'],
            'qty': 5.0,  # 5 > 1 available
            'unit_price': 50.00,
            'line_total': 250.00,
            'line_number': 1,
        })

        with pytest.raises(Exception) as excinfo:
            sales_mcp._confirm_order(order['id'])

        assert "Stock reservation partial failure" in str(excinfo.value) or "Insufficient stock" in str(excinfo.value)
        assert order_repo.get(order['id'])['status'] == 'Draft'
        assert float(stock_repo.get(stock['id'])['reserved_qty']) == 0.0

    def test_mcp_cancel_order_invalid_status_failure(self, isolated_tenant, real_db_conn):
        """
        Verify that attempting to confirm an already cancelled order via MCP raises HTTPException.
        Also verifies REST API cancel endpoint rejects cancelling an already cancelled order.
        """
        client = create_real_db_api_client()
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')

        cust = cust_repo.create({'name': 'MCP Cancel Cust', 'credit_limit': 5000.00, 'balance': 0.00, 'is_active': True})
        order = order_repo.create({
            'order_number': 'SO-MCP-ALREADY-CANC',
            'customer_id': cust['id'],
            'status': 'Cancelled',
        })

        # 1. MCP update_order_status from Cancelled to Confirmed -> raises HTTPException(400)
        with pytest.raises(HTTPException) as excinfo:
            sales_mcp._update_order_status(order['id'], 'Confirmed')

        assert excinfo.value.status_code == 400
        assert "Invalid status transition" in excinfo.value.detail

        # 2. REST API /cancel endpoint on already cancelled order -> returns HTTP 400
        resp = client.post(f'/api/T0012I/{order["id"]}/cancel')
        assert resp.status_code == 400
        assert "cannot be cancelled" in resp.text.lower()

    def test_mcp_update_order_status_invalid_transition(self, isolated_tenant, real_db_conn):
        """
        Verify that MCP tool update_order_status validates allowed transitions.
        """
        cust_repo = CrudRepository('T0010')
        order_repo = CrudRepository('T0012')

        cust = cust_repo.create({'name': 'MCP Trans Cust', 'credit_limit': 5000.00, 'balance': 0.00, 'is_active': True})
        order = order_repo.create({
            'order_number': 'SO-MCP-TRANS-FAIL',
            'customer_id': cust['id'],
            'status': 'Draft',
        })

        with pytest.raises(HTTPException) as excinfo:
            sales_mcp._update_order_status(order['id'], 'Delivered')

        assert excinfo.value.status_code == 400
        assert "Invalid status transition" in excinfo.value.detail
        assert order_repo.get(order['id'])['status'] == 'Draft'
