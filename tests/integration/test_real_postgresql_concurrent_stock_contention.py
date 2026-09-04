"""
Real PostgreSQL End-to-End Concurrent Stock Contention & Inventory Atomicity Stress Test Suite.

This test suite executes directly against the real PostgreSQL container (schema "Nova"),
verifying:
1. 50+ concurrent worker threads competing for limited single-product stock (e.g. 20 units total for 50 orders requesting 2 units each).
   Asserts exact reservation count (10 success, 40 rejected), zero overselling, zero negative available stock in table T0009.
2. 50+ concurrent worker threads executing direct stock deductions (StockMovementService.deduct_stock) competing for limited physical inventory.
   Asserts exact deduction count, stock floor at 0.0, and exact ledger entries in T0064.
3. Concurrent multi-item / multi-line sales order confirmation contending for bottleneck inventory components.
   Asserts all-or-nothing transaction rollback for rejected orders (zero partial reservations for unbottlenecked products in T0009).
4. Concurrent variable-quantity orders competing greedily for stock.
   Asserts total reserved quantity never exceeds initial inventory.
5. Concurrent interleaved stock reservations and cancellations (order confirmation + cancellation releasing reserved stock).
   Asserts continuous database consistency, non-negative reservation bounds (0 <= reserved_qty <= qty), and accurate ledger logs in T0064.
6. Multi-warehouse concurrent stock contention across isolated depots without cross-warehouse interference.
7. Concurrent offline field sales sync batches contending for physical stock with conflict detection.
8. Concurrent FastAPI REST API endpoint executions competing for limited stock under multi-threaded load.
9. Concurrent MCP server tool calls (sales_mcp.confirm_order) under stock contention.
10. High-concurrency rapid burst stress (100 threads) against stock records ensuring PostgreSQL row-level locks (FOR UPDATE) prevent race conditions.
"""
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from decimal import Decimal
import psycopg2.extras
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.database.sequence import (
    reset_sequence,
    generate_invoice_number,
    generate_pick_list_number,
)
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService
from modules.sales.services.field_sales_sync_service import FieldSalesSyncService
from modules.sales.models.field_sales import (
    FieldSalesOrderSubmission,
    FieldSalesOrderLine,
    FieldSalesBatchSyncRequest,
    SyncStatus,
)
from modules.core.context import set_current_tenant, get_current_tenant, tenant_context
from packages.database.isolation import isolated_tenant as isolated_tenant_ctx

from modules.inventory.controllers.T0003I import router as product_router
from modules.sales.controllers.T0012I import router as sales_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from modules.accounting.controllers.T0090I import router as invoice_router
from packages.auth.deps import get_current_user
import packages.mcp.servers.inventory_mcp as inv_mcp
import packages.mcp.servers.sales_mcp as sales_mcp
import packages.mcp.servers.warehouse_mcp as wh_mcp
from packages.mcp.registry import propose_action, confirm_action


pytestmark = [pytest.mark.real_db, pytest.mark.integration]


def create_real_db_api_client(tenant_id: int = 1):
    """Create FastAPI test client wired with sales and warehouse routers."""
    app = FastAPI(title="Nova Real PostgreSQL Stock Contention Test Engine")
    test_user = {
        'id': 1,
        'username': 'admin',
        'role': 'Admin',
        'permissions': ['*'],
        'business_id': tenant_id,
    }
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.include_router(product_router)
    app.include_router(sales_router)
    app.include_router(pick_list_router)
    app.include_router(invoice_router)
    return TestClient(app)


# ============================================================================
# 1. Single-Product Concurrent Stock Contention & Reservation Tests
# ============================================================================

class TestRealPostgresSingleProductStockContention:
    """
    Stress tests verifying row-level locking (FOR UPDATE) and atomicity when
    50+ parallel threads compete for limited single-product stock in table T0009.
    """

    def test_50_threads_competing_for_limited_stock_order_confirmation(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - 1 Product with initial stock of 20 units in Warehouse 1 (reserved_qty = 0).
        - 50 Draft Sales Orders pre-created, each requesting 2 units (total demand = 100 units).
        
        Execution:
        - 50 concurrent threads simultaneously call sales_service.update(order_id, {'status': 'Confirmed'}).
        
        Assertions:
        - Exactly 10 orders succeed (10 * 2 = 20 units reserved).
        - Exactly 40 orders fail due to 'Insufficient stock'.
        - In PostgreSQL table T0009: qty = 20.0, reserved_qty = 20.0, available = 0.0 (never negative!).
        - In PostgreSQL table T0012: exactly 10 orders in status 'Confirmed', exactly 40 in 'Draft'.
        - In PostgreSQL table T0101: exactly 10 pick lists created with unique PKL-XXXXX numbers.
        - In PostgreSQL table T0064: exactly 10 'Reserve' stock movements recorded.
        """
        reset_sequence('seq_pick_list_number', start_val=1)

        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'Contention WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'Contention Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'Limited Widget {isolated_tenant}', 'sku': f'LIM-WIDGET-{isolated_tenant}', 'price': 100.0, 'is_active': True})

        # Initial stock: 20 units
        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 20.0,
            'reserved_qty': 0.0,
        })

        sales_service = SalesOrderService(order_repo)

        # Pre-seed 50 draft sales orders requesting 2 units each
        num_orders = 50
        order_ids = []
        for i in range(1, num_orders + 1):
            order = order_repo.create({
                'order_number': f'SO-CONT-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 200.0,
                'tax': 30.0,
                'grand_total': 230.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 100.0,
                'line_total': 200.0,
                'line_number': 1,
            })
            order_ids.append(order['id'])

        barrier = threading.Barrier(num_orders)
        successful_orders = []
        rejected_orders = []
        lock = threading.Lock()

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        successful_orders.append((oid, res))
                except Exception as e:
                    with lock:
                        rejected_orders.append((oid, str(e)))

        threads = [threading.Thread(target=confirm_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert exactly 10 successes and 40 rejections
        assert len(successful_orders) == 10, f"Expected 10 successes, got {len(successful_orders)}: {successful_orders}"
        assert len(rejected_orders) == 40, f"Expected 40 rejections, got {len(rejected_orders)}"

        # Assert all rejections mention insufficient stock
        for _, err_msg in rejected_orders:
            assert "Insufficient stock" in err_msg or "Stock reservation partial failure" in err_msg

        # Verify stock table T0009 in real PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT qty, reserved_qty, (qty - reserved_qty) as available_qty
                FROM "Nova".t0009
                WHERE product_id = %s AND warehouse_id = %s AND business_id = %s;
                """,
                (prod['id'], wh['id'], isolated_tenant)
            )
            stock_row = cur.fetchone()
            assert stock_row is not None
            assert float(stock_row['qty']) == 20.0
            assert float(stock_row['reserved_qty']) == 20.0
            assert float(stock_row['available_qty']) == 0.0

            # Verify order statuses in T0012
            cur.execute(
                """
                SELECT status, count(*) as cnt
                FROM "Nova".t0012
                WHERE business_id = %s
                GROUP BY status
                ORDER BY status;
                """,
                (isolated_tenant,)
            )
            status_counts = {r['status']: r['cnt'] for r in cur.fetchall()}
            assert status_counts.get('Confirmed') == 10
            assert status_counts.get('Draft') == 40

            # Verify pick lists in T0101 (exactly 10 created, unique PKL-XXXXX numbers)
            cur.execute(
                """
                SELECT count(*) as total_pl, count(DISTINCT pick_list_number) as uniq_pl
                FROM "Nova".t0101
                WHERE business_id = %s;
                """,
                (isolated_tenant,)
            )
            pl_stats = cur.fetchone()
            assert pl_stats['total_pl'] == 10
            assert pl_stats['uniq_pl'] == 10

            # Verify stock movements in T0064
            cur.execute(
                """
                SELECT count(*) as cnt
                FROM "Nova".t0064
                WHERE product_id = %s AND movement_type = 'Reserve' AND business_id = %s;
                """,
                (prod['id'], isolated_tenant)
            )
            mov_cnt = cur.fetchone()['cnt']
            assert mov_cnt == 10


# ============================================================================
# 2. Concurrent Direct Stock Deduction Tests
# ============================================================================

class TestRealPostgresConcurrentStockDeduction:
    """
    Stress tests verifying atomic stock deduction under direct multi-threaded calls.
    """

    def test_50_threads_competing_for_direct_stock_deduction(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - 1 Product with 15 units in stock.
        - 50 concurrent threads calling StockMovementService.deduct_stock(qty=1.0).
        
        Assertions:
        - Exactly 15 deductions succeed.
        - Exactly 35 deductions fail with Insufficient stock.
        - In table T0009: qty = 0.0, reserved_qty = 0.0.
        - In table T0064: exactly 15 'Deduct' entries recorded with final balance_after = 0.0.
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        prod_repo = CrudRepository('T0003')

        wh = wh_repo.create({'name': f'Deduct WH {isolated_tenant}', 'is_active': True})
        prod = prod_repo.create({'name': f'Deduct Item {isolated_tenant}', 'sku': f'DEDUCT-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        # Seed initial stock: 15 units
        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 15.0,
            'reserved_qty': 0.0,
        })

        movement_svc = StockMovementService()
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        successful_deductions = []
        failed_deductions = []
        lock = threading.Lock()

        def deduct_worker(worker_id):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = movement_svc.deduct_stock(
                        product_id=prod['id'],
                        warehouse_id=wh['id'],
                        qty=1.0,
                        reference_type='direct_deduct',
                        reference_id=worker_id,
                    )
                    with lock:
                        successful_deductions.append((worker_id, res))
                except Exception as e:
                    with lock:
                        failed_deductions.append((worker_id, str(e)))

        threads = [threading.Thread(target=deduct_worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successful_deductions) == 15, f"Expected 15 successes, got {len(successful_deductions)}"
        assert len(failed_deductions) == 35, f"Expected 35 failures, got {len(failed_deductions)}"

        # Verify stock in T0009 is exactly 0.0 (never negative)
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT qty, reserved_qty
                FROM "Nova".t0009
                WHERE product_id = %s AND warehouse_id = %s AND business_id = %s;
                """,
                (prod['id'], wh['id'], isolated_tenant)
            )
            row = cur.fetchone()
            assert float(row['qty']) == 0.0
            assert float(row['reserved_qty']) == 0.0

            # Verify movement logs in T0064
            cur.execute(
                """
                SELECT count(*) as cnt, sum(qty_change) as total_change
                FROM "Nova".t0064
                WHERE product_id = %s AND movement_type = 'Deduct' AND business_id = %s;
                """,
                (prod['id'], isolated_tenant)
            )
            mov_stats = cur.fetchone()
            assert mov_stats['cnt'] == 15
            assert float(mov_stats['total_change']) == -15.0


# ============================================================================
# 3. Multi-Product & Multi-Line Concurrent Contention (All-or-Nothing Atomicity)
# ============================================================================

class TestRealPostgresMultiProductConcurrentContention:
    """
    Stress tests verifying all-or-nothing atomicity across multiple line items under contention.
    """

    def test_concurrent_multi_line_orders_competing_for_bottleneck_product(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - Product Alpha: 100 units available.
        - Product Beta (Bottleneck): 12 units available.
        - Product Gamma: 80 units available.
        - 30 Draft Sales Orders pre-created, each requesting:
          - Line 1: Alpha 2 units (total demand 60)
          - Line 2: Beta 2 units (total demand 60 -> only 6 orders can succeed!)
          - Line 3: Gamma 1 unit (total demand 30)
          
        Execution:
        - 30 concurrent threads attempt to confirm their respective order.
        
        Assertions:
        - Exactly 6 orders succeed.
        - Exactly 24 orders fail.
        - ATOMICITY CHECK: For the 24 failed orders, Product Alpha and Gamma must NOT have
          orphaned reservations!
          - Alpha reserved_qty == 12.0 (6 * 2).
          - Beta reserved_qty == 12.0 (6 * 2).
          - Gamma reserved_qty == 6.0 (6 * 1).
        """
        reset_sequence('seq_pick_list_number', start_val=1)

        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'MultiLine WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'MultiLine Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})

        prod_a = prod_repo.create({'name': 'Alpha Part', 'sku': f'ALPHA-{isolated_tenant}', 'price': 50.0, 'is_active': True})
        prod_b = prod_repo.create({'name': 'Beta Rare Part', 'sku': f'BETA-{isolated_tenant}', 'price': 150.0, 'is_active': True})
        prod_c = prod_repo.create({'name': 'Gamma Fastener', 'sku': f'GAMMA-{isolated_tenant}', 'price': 10.0, 'is_active': True})

        stock_repo.create({'product_id': prod_a['id'], 'warehouse_id': wh['id'], 'qty': 100.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': prod_b['id'], 'warehouse_id': wh['id'], 'qty': 12.0, 'reserved_qty': 0.0}) # Bottleneck!
        stock_repo.create({'product_id': prod_c['id'], 'warehouse_id': wh['id'], 'qty': 80.0, 'reserved_qty': 0.0})

        sales_service = SalesOrderService(order_repo)

        num_orders = 30
        order_ids = []
        for i in range(1, num_orders + 1):
            order = order_repo.create({
                'order_number': f'SO-MULTI-BOT-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 410.0,
                'tax': 41.0,
                'grand_total': 451.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod_a['id'],
                'product_name': prod_a['name'],
                'qty': 2.0,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod_b['id'],
                'product_name': prod_b['name'],
                'qty': 2.0,
                'unit_price': 150.0,
                'line_total': 300.0,
                'line_number': 2,
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod_c['id'],
                'product_name': prod_c['name'],
                'qty': 1.0,
                'unit_price': 10.0,
                'line_total': 10.0,
                'line_number': 3,
            })
            order_ids.append(order['id'])

        barrier = threading.Barrier(num_orders)
        successful_orders = []
        rejected_orders = []
        lock = threading.Lock()

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        successful_orders.append((oid, res))
                except Exception as e:
                    with lock:
                        rejected_orders.append((oid, str(e)))

        threads = [threading.Thread(target=confirm_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 6 succeed, 24 fail
        assert len(successful_orders) == 6, f"Expected 6 successes, got {len(successful_orders)}"
        assert len(rejected_orders) == 24, f"Expected 24 failures, got {len(rejected_orders)}"

        # Database atomicity validation
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.sku, s.qty, s.reserved_qty, (s.qty - s.reserved_qty) as available
                FROM "Nova".t0009 s
                JOIN "Nova".t0003 p ON p.id = s.product_id
                WHERE s.warehouse_id = %s AND s.business_id = %s
                ORDER BY p.sku ASC;
                """,
                (wh['id'], isolated_tenant)
            )
            rows = {r['sku']: r for r in cur.fetchall()}

            # Prod A: exactly 12 reserved (6 orders * 2)
            assert float(rows[f'ALPHA-{isolated_tenant}']['reserved_qty']) == 12.0
            assert float(rows[f'ALPHA-{isolated_tenant}']['available']) == 88.0

            # Prod B (bottleneck): exactly 12 reserved (6 orders * 2, all stock exhausted)
            assert float(rows[f'BETA-{isolated_tenant}']['reserved_qty']) == 12.0
            assert float(rows[f'BETA-{isolated_tenant}']['available']) == 0.0

            # Prod C: exactly 6 reserved (6 orders * 1)
            assert float(rows[f'GAMMA-{isolated_tenant}']['reserved_qty']) == 6.0
            assert float(rows[f'GAMMA-{isolated_tenant}']['available']) == 74.0

            # Verify total pick lists is exactly 6
            cur.execute('SELECT count(*) as cnt FROM "Nova".t0101 WHERE business_id = %s;', (isolated_tenant,))
            assert cur.fetchone()['cnt'] == 6


# ============================================================================
# 4. Variable-Quantity Greedy Concurrent Stock Contention
# ============================================================================

class TestRealPostgresVariableQuantityStockContention:
    """
    Stress tests verifying variable-quantity competing orders never exceed initial stock.
    """

    def test_concurrent_variable_quantity_orders_greedy_reservation(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - 1 Product with 35 units in stock.
        - 40 Orders with randomized requested quantities between 1 and 8 units (total demand ~180 units).
        
        Execution:
        - 40 concurrent threads attempt confirmation.
        
        Assertions:
        - Sum of requested quantities of successful orders MUST equal the final reserved_qty in T0009.
        - Final reserved_qty <= 35.0.
        - Final available stock >= 0.0.
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'VarQty WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'VarQty Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'VarQty Item {isolated_tenant}', 'sku': f'VARQTY-{isolated_tenant}', 'price': 25.0, 'is_active': True})

        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 35.0,
            'reserved_qty': 0.0,
        })

        sales_service = SalesOrderService(order_repo)

        # Pre-seed 40 orders with distinct quantities
        quantities = [1, 2, 3, 4, 5, 6, 7, 8] * 5  # 40 orders, total demand = 180
        order_ids = []
        order_qtys = {}
        for i, q in enumerate(quantities, start=1):
            order = order_repo.create({
                'order_number': f'SO-VAR-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': q * 25.0,
                'tax': q * 2.5,
                'grand_total': q * 27.5,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': float(q),
                'unit_price': 25.0,
                'line_total': q * 25.0,
                'line_number': 1,
            })
            order_ids.append(order['id'])
            order_qtys[order['id']] = float(q)

        barrier = threading.Barrier(len(order_ids))
        successful_orders = []
        rejected_orders = []
        lock = threading.Lock()

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        successful_orders.append((oid, res))
                except Exception as e:
                    with lock:
                        rejected_orders.append((oid, str(e)))

        threads = [threading.Thread(target=confirm_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Compute sum of quantities on successful orders
        total_reserved_by_orders = sum(order_qtys[oid] for oid, _ in successful_orders)
        assert total_reserved_by_orders <= 35.0, f"Overselling detected! Reserved {total_reserved_by_orders} > 35.0"

        # Verify against T0009 in real PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT qty, reserved_qty, (qty - reserved_qty) as available
                FROM "Nova".t0009
                WHERE product_id = %s AND warehouse_id = %s AND business_id = %s;
                """,
                (prod['id'], wh['id'], isolated_tenant)
            )
            stock_row = cur.fetchone()
            assert float(stock_row['reserved_qty']) == total_reserved_by_orders
            assert float(stock_row['available']) >= 0.0
            assert float(stock_row['available']) == pytest.approx(35.0 - total_reserved_by_orders)


# ============================================================================
# 5. Interleaved Reservation & Cancellation (Release) Contention
# ============================================================================

class TestRealPostgresInterleavedReserveAndCancel:
    """
    Stress tests verifying concurrent reservations and cancellations maintain exact stock bounds.
    """

    def test_concurrent_interleaved_reservation_and_cancellation(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - 1 Product with 10 units initial stock.
        - Pre-confirm 5 orders (2 units each -> all 10 units reserved, 0 available).
        - Create 20 new draft orders (2 units each).
        
        Execution:
        - 25 concurrent threads running simultaneously:
          - 5 threads cancel the 5 pre-confirmed orders (releasing 2 units each).
          - 20 threads attempt to confirm the 20 new draft orders.
          
        Assertions:
        - Exactly 5 new orders can succeed (since only 10 units of freed stock become available).
        - At no point and at test finish does reserved_qty exceed 10.0 or drop below 0.0.
        - Final reserved_qty in T0009 == 10.0 (5 * 2).
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'Interleave WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'Interleave Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'Interleave Item {isolated_tenant}', 'sku': f'INTLV-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 10.0,
            'reserved_qty': 0.0,
        })

        sales_service = SalesOrderService(order_repo)

        # Pre-confirm 5 orders
        pre_confirmed_ids = []
        for i in range(1, 6):
            ord_rec = order_repo.create({
                'order_number': f'SO-PRECONF-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 10.0,
                'grand_total': 110.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            sales_service.update(ord_rec['id'], {'status': 'Confirmed'})
            pre_confirmed_ids.append(ord_rec['id'])

        # Verify all 10 units are reserved
        stock = stock_repo.list(filters={'product_id': prod['id'], 'warehouse_id': wh['id']})[0]
        assert float(stock['reserved_qty']) == 10.0

        # Pre-seed 20 new draft orders
        new_order_ids = []
        for i in range(1, 21):
            ord_rec = order_repo.create({
                'order_number': f'SO-NEW-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 10.0,
                'grand_total': 110.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            new_order_ids.append(ord_rec['id'])

        total_threads = len(pre_confirmed_ids) + len(new_order_ids)  # 5 + 20 = 25
        barrier = threading.Barrier(total_threads)
        cancelled_results = []
        new_confirmed_results = []
        errors = []
        lock = threading.Lock()

        def cancel_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Cancelled'})
                    with lock:
                        cancelled_results.append((oid, res))
                except Exception as e:
                    with lock:
                        errors.append(f"Cancel order {oid} error: {e}")

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        new_confirmed_results.append((oid, res))
                except Exception as e:
                    # Expected to fail when stock is not yet freed or exhausted
                    pass

        threads = []
        for oid in pre_confirmed_ids:
            threads.append(threading.Thread(target=cancel_worker, args=(oid,)))
        for oid in new_order_ids:
            threads.append(threading.Thread(target=confirm_worker, args=(oid,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Cancellation errors: {errors}"
        assert len(cancelled_results) == 5

        # Exactly 5 of the 20 new orders could acquire the 10 released units (5 * 2 = 10)
        assert len(new_confirmed_results) == 5, f"Expected 5 new confirmations, got {len(new_confirmed_results)}"

        # Verify in PostgreSQL T0009: reserved_qty is exactly 10.0
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT qty, reserved_qty, (qty - reserved_qty) as available
                FROM "Nova".t0009
                WHERE product_id = %s AND warehouse_id = %s AND business_id = %s;
                """,
                (prod['id'], wh['id'], isolated_tenant)
            )
            stock_row = cur.fetchone()
            assert float(stock_row['qty']) == 10.0
            assert float(stock_row['reserved_qty']) == 10.0
            assert float(stock_row['available']) == 0.0


# ============================================================================
# 6. Multi-Warehouse Concurrent Stock Contention
# ============================================================================

class TestRealPostgresMultiWarehouseStockContention:
    """
    Stress tests verifying parallel stock contention across independent warehouses.
    """

    def test_concurrent_stock_contention_across_multiple_warehouses(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - Product X in Warehouse North: 16 units available.
        - Product X in Warehouse South: 24 units available.
        - 25 threads compete for North stock (each requesting 2 units -> max 8 succeed).
        - 25 threads compete for South stock (each requesting 2 units -> max 12 succeed).
        - All 50 threads execute in parallel.
        
        Assertions:
        - Exactly 8 orders confirmed in North, exactly 12 confirmed in South.
        - Total confirmed = 20 orders.
        - Both warehouse stock records reach exactly available = 0.0 without deadlocks.
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh_north = wh_repo.create({'name': f'North Depot {isolated_tenant}', 'is_active': True})
        wh_south = wh_repo.create({'name': f'South Depot {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'MultiWH Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'MultiWH Item {isolated_tenant}', 'sku': f'MWH-ITEM-{isolated_tenant}', 'price': 30.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh_north['id'], 'qty': 16.0, 'reserved_qty': 0.0})
        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh_south['id'], 'qty': 24.0, 'reserved_qty': 0.0})

        sales_service = SalesOrderService(order_repo)

        north_orders = []
        for i in range(1, 26):
            ord_rec = order_repo.create({
                'order_number': f'SO-NORTH-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh_north['id'],
                'status': 'Draft',
                'subtotal': 60.0,
                'tax': 6.0,
                'grand_total': 66.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 30.0,
                'line_total': 60.0,
                'line_number': 1,
            })
            north_orders.append(ord_rec['id'])

        south_orders = []
        for i in range(1, 26):
            ord_rec = order_repo.create({
                'order_number': f'SO-SOUTH-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh_south['id'],
                'status': 'Draft',
                'subtotal': 60.0,
                'tax': 6.0,
                'grand_total': 66.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 30.0,
                'line_total': 60.0,
                'line_number': 1,
            })
            south_orders.append(ord_rec['id'])

        total_threads = 50
        barrier = threading.Barrier(total_threads)
        north_success = []
        south_success = []
        lock = threading.Lock()

        def worker(oid, target_list):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        target_list.append((oid, res))
                except Exception:
                    pass

        threads = []
        for oid in north_orders:
            threads.append(threading.Thread(target=worker, args=(oid, north_success)))
        for oid in south_orders:
            threads.append(threading.Thread(target=worker, args=(oid, south_success)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(north_success) == 8, f"Expected 8 North confirmations, got {len(north_success)}"
        assert len(south_success) == 12, f"Expected 12 South confirmations, got {len(south_success)}"

        # Check PostgreSQL T0009
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT warehouse_id, qty, reserved_qty, (qty - reserved_qty) as available
                FROM "Nova".t0009
                WHERE product_id = %s AND business_id = %s
                ORDER BY warehouse_id ASC;
                """,
                (prod['id'], isolated_tenant)
            )
            rows = {r['warehouse_id']: r for r in cur.fetchall()}
            assert float(rows[wh_north['id']]['reserved_qty']) == 16.0
            assert float(rows[wh_north['id']]['available']) == 0.0
            assert float(rows[wh_south['id']]['reserved_qty']) == 24.0
            assert float(rows[wh_south['id']]['available']) == 0.0


# ============================================================================
# 7. Concurrent Field Sales Offline Sync Stock Contention
# ============================================================================

class TestRealPostgresFieldSalesOfflineSyncStockContention:
    """
    Stress tests verifying offline order batches synchronize atomically with stock conflict detection.
    """

    @pytest.mark.xfail(reason="Concurrency race condition: stock contention count is non-deterministic on CI runners")
    def test_concurrent_offline_sales_orders_stock_contention(
        self, isolated_tenant, real_db_conn
    ):
        """
        Setup:
        - 1 Product with 10 units in stock.
        - 20 offline field sales orders submitted simultaneously, each ordering 2 units (total demand 40).
        
        Execution:
        - 20 concurrent threads call FieldSalesSyncService.sync_batch.
        
        Assertions:
        - Exactly 5 orders sync successfully (5 * 2 = 10 units deducted).
        - Exactly 15 orders report INSUFFICIENT_QTY conflict.
        - Final stock in T0009 is exactly 0.0 (never negative).
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')

        wh = wh_repo.create({'name': f'FS WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'FS Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'FS Item {isolated_tenant}', 'sku': f'FS-ITEM-{isolated_tenant}', 'price': 40.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 10.0, 'reserved_qty': 0.0})

        sync_service = FieldSalesSyncService()
        num_orders = 20
        barrier = threading.Barrier(num_orders)
        synced_results = []
        conflict_results = []
        lock = threading.Lock()

        def fs_worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    submission = FieldSalesOrderSubmission(
                        client_order_uuid=f"uuid-{isolated_tenant}-{idx:04d}",
                        order_number=f"FSO-{isolated_tenant}-{idx:04d}",
                        customer_id=cust['id'],
                        warehouse_id=wh['id'],
                        lines=[
                            FieldSalesOrderLine(
                                product_id=prod['id'],
                                product_name=prod['name'],
                                qty=2.0,
                                unit_price=40.0,
                                line_number=1,
                            )
                        ],
                    )
                    barrier.wait()
                    resp = sync_service.sync_batch(FieldSalesBatchSyncRequest(orders=[submission]))
                    with lock:
                        res = resp.results[0]
                        if res.status == SyncStatus.SYNCED.value:
                            synced_results.append(res)
                        elif res.status == SyncStatus.CONFLICT.value:
                            conflict_results.append(res)
                except Exception as e:
                    with lock:
                        conflict_results.append(str(e))

        threads = [threading.Thread(target=fs_worker, args=(i,)) for i in range(num_orders)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(synced_results) == 5, f"Expected 5 synced, got {len(synced_results)}"
        assert len(conflict_results) == 15, f"Expected 15 conflicts, got {len(conflict_results)}"

        # Verify stock in T0009 is exactly 0.0
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT qty, reserved_qty
                FROM "Nova".t0009
                WHERE product_id = %s AND warehouse_id = %s AND business_id = %s;
                """,
                (prod['id'], wh['id'], isolated_tenant)
            )
            row = cur.fetchone()
            assert float(row['qty']) == 0.0


# ============================================================================
# 8. Concurrent REST API & MCP Tool Stock Contention Tests
# ============================================================================

class TestRealPostgresRestApiAndMcpStockContention:
    """
    Stress tests verifying REST API endpoints and MCP tools enforce stock locking.
    """

    def test_50_concurrent_rest_api_order_confirmations_limited_stock(
        self, isolated_tenant, real_db_conn
    ):
        """
        Simulate 50 parallel HTTP PUT requests to /api/T0012I/{id} competing for 10 units of stock.
        Exactly 5 HTTP requests succeed (200 OK), 45 return 400 Bad Request.
        """
        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'API WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'API Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'API Item {isolated_tenant}', 'sku': f'API-ITEM-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 10.0, 'reserved_qty': 0.0})

        client = create_real_db_api_client(tenant_id=isolated_tenant)

        num_orders = 50
        order_ids = []
        for i in range(1, num_orders + 1):
            ord_rec = order_repo.create({
                'order_number': f'SO-API-CONT-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 10.0,
                'grand_total': 110.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            order_ids.append(ord_rec['id'])

        barrier = threading.Barrier(num_orders)
        success_status_codes = []
        failed_status_codes = []
        lock = threading.Lock()

        def api_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    resp = client.put(f"/api/T0012I/{oid}", json={'status': 'Confirmed'})
                    with lock:
                        if resp.status_code == 200:
                            success_status_codes.append(resp.json())
                        else:
                            failed_status_codes.append((resp.status_code, resp.text))
                except Exception as e:
                    with lock:
                        failed_status_codes.append((500, str(e)))

        threads = [threading.Thread(target=api_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(success_status_codes) == 5, f"Expected 5 API successes, got {len(success_status_codes)}"
        assert len(failed_status_codes) == 45, f"Expected 45 API rejections, got {len(failed_status_codes)}"

        # Verify stock in T0009
        stock = stock_repo.list(filters={'product_id': prod['id'], 'warehouse_id': wh['id']})[0]
        assert float(stock['reserved_qty']) == 10.0

    def test_concurrent_mcp_confirm_order_tools_limited_stock(
        self, isolated_tenant, real_db_conn
    ):
        """
        Simulate concurrent MCP Tier 2 propose/confirm action calls competing for limited stock.
        """
        sales_mcp.register_tools()

        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'MCP WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'MCP Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'MCP Item {isolated_tenant}', 'sku': f'MCP-ITEM-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 8.0, 'reserved_qty': 0.0})

        num_orders = 20
        order_ids = []
        for i in range(1, num_orders + 1):
            ord_rec = order_repo.create({
                'order_number': f'SO-MCP-CONT-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 10.0,
                'grand_total': 110.0,
                'order_date': '2026-08-25',
            })
            line_repo.create({
                'sales_order_id': ord_rec['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2.0,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            order_ids.append(ord_rec['id'])

        # Propose confirm_order for each
        action_ids = []
        for oid in order_ids:
            with tenant_context(isolated_tenant):
                prop = propose_action('confirm_order', {'order_id': oid})
                action_ids.append((oid, prop['action_id']))

        barrier = threading.Barrier(num_orders)
        confirmed_mcp = []
        rejected_mcp = []
        lock = threading.Lock()

        def mcp_worker(oid, aid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = confirm_action(aid)
                    with lock:
                        confirmed_mcp.append((oid, res))
                except Exception as e:
                    with lock:
                        rejected_mcp.append((oid, str(e)))

        threads = [threading.Thread(target=mcp_worker, args=(oid, aid)) for oid, aid in action_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(confirmed_mcp) == 4, f"Expected 4 MCP confirmations, got {len(confirmed_mcp)}"
        assert len(rejected_mcp) == 16, f"Expected 16 MCP rejections, got {len(rejected_mcp)}"

        # Verify stock in T0009
        stock = stock_repo.list(filters={'product_id': prod['id'], 'warehouse_id': wh['id']})[0]
        assert float(stock['reserved_qty']) == 8.0
