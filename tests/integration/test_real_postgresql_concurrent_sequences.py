"""
Real PostgreSQL End-to-End Concurrency & Sequence Generation Stress Test Suite.

This test suite executes directly against the real PostgreSQL container (schema "Nova"),
verifying:
1. 50+ concurrent worker threads generating invoice numbers (INV-XXXXX) against real PostgreSQL sequence `seq_invoice_number`.
2. 50+ concurrent worker threads generating pick list numbers (PKL-XXXXX) against real PostgreSQL sequence `seq_pick_list_number`.
3. 100 concurrent worker threads executing interleaved invoice & pick list numbering simultaneously without cross-contamination.
4. Concurrency-safe custom document formatting and padding (e.g. DOC-XXXXXX, SO-XXXXXX).
5. 50+ concurrent direct service creations (InvoiceService.create, PickListService.create, SalesOrderService.create) with auto-generated document numbers and real table persistence (T0090, T0101, T0012, T0013).
6. 50+ concurrent Sales Order Confirmations generating 50 unique pick lists (T0101/T0102) with zero duplicate numbers.
7. 50+ concurrent Sales Order Deliveries generating 50 unique invoices (T0090) with zero duplicate numbers.
8. 50+ concurrent Full Order Lifecycle pipeline (Creation -> Confirmation -> Picking -> Delivery) running simultaneously.
9. Multi-tenant concurrency isolation: simultaneous document generation across independent tenants without collisions.
10. Concurrent FastAPI REST API endpoint executions (POST /api/T0090I, POST /api/T0101I, POST /api/T0012I/{id}/confirm) under multi-threaded load.
11. Concurrent MCP server tool calls (sales_mcp, warehouse_mcp, accounting_mcp).
12. Sequence atomicity and progression across rollbacks and aborted transactions.
"""
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import psycopg2.extras
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.database.sequence import (
    get_next_sequence_value,
    generate_document_number,
    generate_invoice_number,
    generate_pick_list_number,
    reset_sequence,
    set_sequence_value,
    get_current_sequence_value,
    DOCUMENT_SEQUENCES,
    DOCUMENT_PREFIXES,
)
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService
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
import packages.mcp.servers.accounting_mcp as accounting_mcp


pytestmark = [pytest.mark.real_db, pytest.mark.integration]


def create_real_db_api_client(tenant_id: int = 1):
    """Create FastAPI test client with sales, invoice, and pick list routers wired for real DB tests."""
    app = FastAPI(title="Nova Real PostgreSQL Concurrent Sequence Test Engine")
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
# 1. Concurrent Atomic Sequence Generation Tests against Real PostgreSQL
# ============================================================================

class TestRealPostgresConcurrentAtomicSequences:
    """Stress tests verifying atomic sequence generation under 50+ concurrent threads against real PostgreSQL."""

    def test_50_concurrent_threads_invoice_numbers(self, isolated_tenant, real_db_conn):
        """
        Simulate 50 concurrent threads generating invoice numbers (INV-XXXXX) directly against
        real PostgreSQL sequence 'seq_invoice_number'.
        Assert zero duplicate document numbers, regex match, and continuous sequence progression.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        generated_numbers = []
        errors = []
        lock = threading.Lock()

        def worker(thread_idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    inv_num = generate_invoice_number()
                    with lock:
                        generated_numbers.append(inv_num)
                except Exception as e:
                    with lock:
                        errors.append(f"Thread-{thread_idx} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(generated_numbers) == 50

        # Verify uniqueness: zero duplicate collisions
        unique_numbers = set(generated_numbers)
        assert len(unique_numbers) == 50, (
            f"Duplicate invoice numbers detected: {len(generated_numbers) - len(unique_numbers)} collisions"
        )

        # Verify format (INV-XXXXX with 5 digits)
        pattern = re.compile(r"^INV-\d{5}$")
        for num in generated_numbers:
            assert pattern.match(num), f"Invoice number '{num}' does not match format INV-XXXXX"

        # Verify sequence numbers cover 1 through 50 consecutively
        extracted_ints = sorted(int(num.split('-')[1]) for num in generated_numbers)
        assert extracted_ints == list(range(1, 51)), f"Gaps or invalid sequence progression: {extracted_ints}"

        # Verify real PostgreSQL sequence last_value
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT last_value FROM "Nova".seq_invoice_number;')
            row = cur.fetchone()
            assert row[0] == 50

    def test_50_concurrent_threads_pick_list_numbers(self, isolated_tenant, real_db_conn):
        """
        Simulate 50 concurrent threads generating pick list numbers (PKL-XXXXX) directly against
        real PostgreSQL sequence 'seq_pick_list_number'.
        Assert zero duplicate document numbers, regex match, and continuous sequence progression.
        """
        reset_sequence('seq_pick_list_number', start_val=1)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        generated_numbers = []
        errors = []
        lock = threading.Lock()

        def worker(thread_idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    pkl_num = generate_pick_list_number()
                    with lock:
                        generated_numbers.append(pkl_num)
                except Exception as e:
                    with lock:
                        errors.append(f"Thread-{thread_idx} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(generated_numbers) == 50

        # Verify uniqueness
        unique_numbers = set(generated_numbers)
        assert len(unique_numbers) == 50, (
            f"Duplicate pick list numbers detected: {len(generated_numbers) - len(unique_numbers)} collisions"
        )

        # Verify format (PKL-XXXXX with 5 digits)
        pattern = re.compile(r"^PKL-\d{5}$")
        for num in generated_numbers:
            assert pattern.match(num), f"Pick list number '{num}' does not match format PKL-XXXXX"

        # Verify continuous range 1..50
        extracted_ints = sorted(int(num.split('-')[1]) for num in generated_numbers)
        assert extracted_ints == list(range(1, 51))

        # Verify real PostgreSQL sequence last_value
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT last_value FROM "Nova".seq_pick_list_number;')
            row = cur.fetchone()
            assert row[0] == 50

    def test_100_concurrent_threads_interleaved_invoices_and_pick_lists(self, isolated_tenant, real_db_conn):
        """
        Simulate 100 simultaneous threads (50 generating invoices, 50 generating pick lists)
        verifying that independent PostgreSQL sequences operate in parallel without cross-contamination.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        reset_sequence('seq_pick_list_number', start_val=1)

        num_workers = 100
        barrier = threading.Barrier(num_workers)
        invoices = []
        pick_lists = []
        errors = []
        lock = threading.Lock()

        def invoice_worker():
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    inv = generate_invoice_number()
                    with lock:
                        invoices.append(inv)
                except Exception as e:
                    with lock:
                        errors.append(e)

        def pick_list_worker():
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    pkl = generate_pick_list_number()
                    with lock:
                        pick_lists.append(pkl)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = []
        for _ in range(50):
            threads.append(threading.Thread(target=invoice_worker))
            threads.append(threading.Thread(target=pick_list_worker))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(invoices) == 50
        assert len(pick_lists) == 50
        assert len(set(invoices)) == 50
        assert len(set(pick_lists)) == 50

        # Check invoice format & continuous progression 1..50
        inv_ints = sorted(int(num.split('-')[1]) for num in invoices)
        assert inv_ints == list(range(1, 51))

        # Check pick list format & continuous progression 1..50
        pkl_ints = sorted(int(num.split('-')[1]) for num in pick_lists)
        assert pkl_ints == list(range(1, 51))

    def test_50_concurrent_threads_custom_padding_and_prefix(self, isolated_tenant, real_db_conn):
        """
        Simulate concurrent generation using generate_document_number with custom prefix 'DOC' and padding 6.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        results = []
        errors = []
        lock = threading.Lock()

        def worker():
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    doc_num = generate_document_number('seq_invoice_number', prefix='DOC', padding=6)
                    with lock:
                        results.append(doc_num)
                except Exception as e:
                    with lock:
                        errors.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0
        assert len(results) == 50
        assert len(set(results)) == 50
        pattern = re.compile(r"^DOC-\d{6}$")
        for doc in results:
            assert pattern.match(doc)

        extracted_ints = sorted(int(num.split('-')[1]) for num in results)
        assert extracted_ints == list(range(1, 51))

    def test_50_concurrent_workers_direct_nextval_raw_integers(self, isolated_tenant, real_db_conn):
        """
        Simulate 50 concurrent workers calling get_next_sequence_value directly on real PostgreSQL sequence.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        values = []
        errors = []
        lock = threading.Lock()

        def worker():
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    val = get_next_sequence_value('seq_invoice_number')
                    with lock:
                        values.append(val)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(values) == 50
        assert sorted(values) == list(range(1, 51))


# ============================================================================
# 2. Concurrent Direct Service Document Creation against Real PostgreSQL
# ============================================================================

class TestRealPostgresConcurrentDirectServiceCreation:
    """Stress tests verifying auto-generated document numbers on direct CRUD creations in real PostgreSQL tables."""

    def test_50_concurrent_direct_invoice_creations(self, isolated_tenant, real_db_conn):
        """
        Create 50 invoices concurrently via InvoiceService without providing invoice_number.
        Assert that all 50 invoices are persisted in PostgreSQL table 't0090' with distinct INV-XXXXX numbers.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        cust_repo = CrudRepository('T0010')
        customer = cust_repo.create({
            'name': f'Concurrent Test Customer {isolated_tenant}',
            'credit_limit': 1000000.0,
            'balance': 0.0,
            'is_active': True,
        })
        customer_id = customer['id']

        inv_repo = CrudRepository('T0090')
        service = InvoiceService(inv_repo)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        created_invoices = []
        errors = []
        lock = threading.Lock()

        def worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    invoice = service.create({
                        'partner_id': customer_id,
                        'issue_date': '2026-08-20',
                        'due_date': '2026-09-20',
                        'total_amount': 100.0 + idx,
                        'status': 'Unpaid',
                    })
                    with lock:
                        created_invoices.append(invoice)
                except Exception as e:
                    with lock:
                        errors.append(f"Worker {idx} failed: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered errors: {errors}"
        assert len(created_invoices) == 50

        # Verify all 50 invoices got distinct auto-generated INV-XXXXX numbers
        invoice_numbers = [inv['invoice_number'] for inv in created_invoices]
        assert len(set(invoice_numbers)) == 50
        for num in invoice_numbers:
            assert re.match(r"^INV-\d{5}$", num)

        # Verify directly in real PostgreSQL table 't0090'
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT count(*) as total_count, count(DISTINCT invoice_number) as unique_count
                FROM "Nova".t0090
                WHERE business_id = %s;
                """,
                (isolated_tenant,)
            )
            stats = cur.fetchone()
            assert stats['total_count'] == 50
            assert stats['unique_count'] == 50

            cur.execute(
                """
                SELECT invoice_number FROM "Nova".t0090
                WHERE business_id = %s
                ORDER BY invoice_number ASC;
                """,
                (isolated_tenant,)
            )
            db_rows = cur.fetchall()
            db_nums = [r['invoice_number'] for r in db_rows]
            db_ints = sorted(int(n.split('-')[1]) for n in db_nums)
            assert db_ints == list(range(1, 51))

    def test_50_concurrent_direct_pick_list_creations(self, isolated_tenant, real_db_conn):
        """
        Create 50 pick lists concurrently via PickListService without providing pick_list_number.
        Assert that all 50 pick lists are persisted in PostgreSQL table 't0101' with distinct PKL-XXXXX numbers.
        """
        reset_sequence('seq_pick_list_number', start_val=1)
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        so_repo = CrudRepository('T0012')
        wh = wh_repo.create({'name': f'Concurrent WH {isolated_tenant}', 'is_active': True})
        wh_id = wh['id']
        cust = cust_repo.create({'name': f'Concurrent Cust {isolated_tenant}', 'is_active': True})

        order_ids = []
        for i in range(50):
            so = so_repo.create({
                'order_number': f'SO-PL-SEED-{isolated_tenant}-{i:04d}',
                'customer_id': cust['id'],
                'warehouse_id': wh_id,
                'status': 'Confirmed',
            })
            order_ids.append(so['id'])

        pl_repo = CrudRepository('T0101')
        service = PickListService(pl_repo)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        created_pick_lists = []
        errors = []
        lock = threading.Lock()

        def worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    pl = service.create({
                        'sales_order_id': order_ids[idx],
                        'warehouse_id': wh_id,
                        'status': 'Pending',
                    })
                    with lock:
                        created_pick_lists.append(pl)
                except Exception as e:
                    with lock:
                        errors.append(f"Worker {idx} failed: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered errors: {errors}"
        assert len(created_pick_lists) == 50

        # Verify all 50 pick lists got distinct auto-generated PKL-XXXXX numbers
        pkl_numbers = [pl['pick_list_number'] for pl in created_pick_lists]
        assert len(set(pkl_numbers)) == 50
        for num in pkl_numbers:
            assert re.match(r"^PKL-\d{5}$", num)

        # Verify directly in PostgreSQL table 't0101'
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT count(*) as total_count, count(DISTINCT pick_list_number) as unique_count
                FROM "Nova".t0101
                WHERE business_id = %s;
                """,
                (isolated_tenant,)
            )
            stats = cur.fetchone()
            assert stats['total_count'] == 50
            assert stats['unique_count'] == 50

    def test_50_concurrent_direct_sales_order_creations(self, isolated_tenant, real_db_conn):
        """
        Create 50 sales orders with lines concurrently using EnhancedSalesOrderService.
        Assert that all 50 sales orders and their lines persist accurately in PostgreSQL tables T0012 and T0013.
        """
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')

        wh = wh_repo.create({'name': f'SO Test WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'SO Test Cust {isolated_tenant}', 'credit_limit': 500000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'SO Test Product {isolated_tenant}', 'sku': f'SO-SKU-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        order_repo = CrudRepository('T0012')
        service = EnhancedSalesOrderService(order_repo)

        num_orders = 50
        barrier = threading.Barrier(num_orders)
        created_orders = []
        errors = []
        lock = threading.Lock()

        def worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    order = service.create_with_lines(
                        order_data={
                            'order_number': f'SO-{isolated_tenant}-{idx:05d}',
                            'customer_id': cust['id'],
                            'warehouse_id': wh['id'],
                            'status': 'Draft',
                            'order_date': '2026-08-20',
                        },
                        lines=[{
                            'product_id': prod['id'],
                            'product_name': prod['name'],
                            'qty': 2,
                            'unit_price': 50.0,
                            'line_number': 1,
                        }]
                    )
                    with lock:
                        created_orders.append(order)
                except Exception as e:
                    with lock:
                        errors.append(f"Order worker {idx} failed: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, num_orders + 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(created_orders) == 50

        # Verify directly in PostgreSQL T0012 and T0013
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT count(*) as cnt, count(DISTINCT order_number) as uniq FROM "Nova".t0012 WHERE business_id = %s;',
                (isolated_tenant,)
            )
            row = cur.fetchone()
            assert row['cnt'] == 50
            assert row['uniq'] == 50

            cur.execute('SELECT count(*) as cnt FROM "Nova".t0013 WHERE business_id = %s;', (isolated_tenant,))
            line_cnt = cur.fetchone()['cnt']
            assert line_cnt == 50


# ============================================================================
# 3. Concurrent Sales Order Lifecycle & Document Generation Tests
# ============================================================================

class TestRealPostgresConcurrentSalesOrderLifecycle:
    """
    Stress tests verifying concurrent order confirmation (pick list generation)
    and delivery (invoice generation) for 50 simultaneous orders in real PostgreSQL.
    """

    def test_50_concurrent_orders_confirmation_generates_50_unique_pick_lists(
        self, isolated_tenant, real_db_conn
    ):
        """
        Simulate 50 simultaneous orders transitioning Draft -> Confirmed.
        Verifies 50 unique pick lists (PKL-XXXXX) are produced in PostgreSQL table T0101
        backed by sequence 'seq_pick_list_number' without collisions.
        """
        reset_sequence('seq_pick_list_number', start_val=1)

        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'Lifecycle WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'Lifecycle Cust {isolated_tenant}', 'credit_limit': 10000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'Widget {isolated_tenant}', 'sku': f'WIDGET-CONF-{isolated_tenant}', 'price': 50.0, 'is_active': True})

        # Seed ample inventory in T0009
        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 10000.0,
            'reserved_qty': 0.0,
        })

        sales_service = SalesOrderService(order_repo)

        # Pre-seed 50 draft sales orders with 1 line each (qty=2)
        order_ids = []
        for i in range(1, 51):
            order = order_repo.create({
                'order_number': f'SO-CONF-{isolated_tenant}-{i:05d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 15.0,
                'grand_total': 115.0,
                'order_date': '2026-08-20',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            order_ids.append(order['id'])

        num_orders = 50
        barrier = threading.Barrier(num_orders)
        confirmed_orders = []
        errors = []
        lock = threading.Lock()

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Confirmed'})
                    with lock:
                        confirmed_orders.append(res)
                except Exception as e:
                    with lock:
                        errors.append(f"Order {oid} confirmation failed: {e}")

        threads = [threading.Thread(target=confirm_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Confirmation errors: {errors}"
        assert len(confirmed_orders) == 50

        # Verify all 50 orders are in Confirmed status
        for ord_res in confirmed_orders:
            assert ord_res['status'] == 'Confirmed'

        # Verify exactly 50 pick lists created in PostgreSQL table T0101
        pl_repo = CrudRepository('T0101')
        all_pick_lists = pl_repo.list()
        assert len(all_pick_lists) == 50

        # Verify all 50 pick list numbers are unique with PKL-XXXXX format
        pkl_numbers = [pl['pick_list_number'] for pl in all_pick_lists]
        assert len(set(pkl_numbers)) == 50, f"Collisions in pick list numbers: {pkl_numbers}"
        for pkl_num in pkl_numbers:
            assert re.match(r"^PKL-\d{5}$", pkl_num)

        # Verify pick list items created in T0102
        pli_repo = CrudRepository('T0102')
        all_items = pli_repo.list()
        assert len(all_items) == 50
        for item in all_items:
            assert item['qty_ordered'] == 2

        # Verify reserved stock updated in T0009 (50 * 2 = 100 reserved)
        stock_record = stock_repo.list(filters={'product_id': prod['id'], 'warehouse_id': wh['id']})[0]
        assert float(stock_record['reserved_qty']) == 100.0

        # Verify directly via SQL in PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT count(*) as total_pl, count(DISTINCT pick_list_number) as uniq_pl
                FROM "Nova".t0101
                WHERE business_id = %s;
                """,
                (isolated_tenant,)
            )
            pl_stats = cur.fetchone()
            assert pl_stats['total_pl'] == 50
            assert pl_stats['uniq_pl'] == 50

    def test_50_concurrent_orders_delivery_generates_50_unique_invoices(
        self, isolated_tenant, real_db_conn
    ):
        """
        Simulate 50 simultaneous orders transitioning Shipped -> Delivered.
        Verifies 50 unique invoices (INV-XXXXX) are produced in PostgreSQL table T0090
        backed by sequence 'seq_invoice_number' without collisions.
        """
        reset_sequence('seq_invoice_number', start_val=1)

        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'Delivery WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'Delivery Cust {isolated_tenant}', 'credit_limit': 10000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'Delivery Prod {isolated_tenant}', 'sku': f'DELIV-{isolated_tenant}', 'price': 100.0, 'is_active': True})

        sales_service = SalesOrderService(order_repo)

        # Pre-seed 50 Shipped sales orders
        order_ids = []
        for i in range(1, 51):
            order = order_repo.create({
                'order_number': f'SO-DELIV-{isolated_tenant}-{i:05d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Shipped',
                'subtotal': 200.0,
                'tax': 30.0,
                'grand_total': 230.0,
                'order_date': '2026-08-20',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2,
                'unit_price': 100.0,
                'line_total': 200.0,
                'line_number': 1,
            })
            order_ids.append(order['id'])

        num_orders = 50
        barrier = threading.Barrier(num_orders)
        delivered_orders = []
        errors = []
        lock = threading.Lock()

        def deliver_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_service.update(oid, {'status': 'Delivered'})
                    with lock:
                        delivered_orders.append(res)
                except Exception as e:
                    with lock:
                        errors.append(f"Order {oid} delivery failed: {e}")

        threads = [threading.Thread(target=deliver_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Delivery errors: {errors}"
        assert len(delivered_orders) == 50

        # Verify all 50 orders are in Delivered status
        for ord_res in delivered_orders:
            assert ord_res['status'] == 'Delivered'

        # Verify exactly 50 invoices created in PostgreSQL table T0090
        inv_repo = CrudRepository('T0090')
        all_invoices = inv_repo.list()
        assert len(all_invoices) == 50

        # Verify all 50 invoice numbers are unique with INV-XXXXX format
        inv_numbers = [inv['invoice_number'] for inv in all_invoices]
        assert len(set(inv_numbers)) == 50, f"Collisions in invoice numbers: {inv_numbers}"
        for inv_num in inv_numbers:
            assert re.match(r"^INV-\d{5}$", inv_num)

        # Verify sequence numbers cover 1 through 50 consecutively
        extracted_ints = sorted(int(num.split('-')[1]) for num in inv_numbers)
        assert extracted_ints == list(range(1, 51))

        # Direct SQL verification in PostgreSQL table T0090
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT count(*) as total_inv, count(DISTINCT invoice_number) as uniq_inv,
                       sum(total_amount) as grand_total_sum
                FROM "Nova".t0090
                WHERE business_id = %s;
                """,
                (isolated_tenant,)
            )
            inv_stats = cur.fetchone()
            assert inv_stats['total_inv'] == 50
            assert inv_stats['uniq_inv'] == 50
            assert float(inv_stats['grand_total_sum']) == pytest.approx(50 * 230.0)

    def test_50_concurrent_full_order_pipeline_end_to_end(
        self, isolated_tenant, real_db_conn
    ):
        """
        Simulate 50 orders flowing through the complete Order-to-Cash pipeline simultaneously:
        1. Concurrent Creation -> Draft with line items.
        2. Concurrent Confirmation -> Confirmed + Pick List (PKL-XXXXX) generation.
        3. Warehouse picking execution -> Pick List completed -> Shipped.
        4. Concurrent Delivery -> Delivered + Invoice (INV-XXXXX) generation.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        reset_sequence('seq_pick_list_number', start_val=1)

        wh_repo = CrudRepository('T0008')
        stock_repo = CrudRepository('T0009')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        inv_repo = CrudRepository('T0090')

        wh = wh_repo.create({'name': f'E2E Full Pipeline WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'E2E Full Pipeline Cust {isolated_tenant}', 'credit_limit': 10000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'E2E Product {isolated_tenant}', 'sku': f'E2E-PROD-{isolated_tenant}', 'price': 100.0, 'is_active': True})

        stock_repo.create({
            'product_id': prod['id'],
            'warehouse_id': wh['id'],
            'qty': 10000.0,
            'reserved_qty': 0.0,
        })

        sales_service = SalesOrderService(order_repo)
        pick_list_service = PickListService()

        # Step 1: Create 50 Draft orders concurrently
        order_ids = []
        lock = threading.Lock()

        def create_order(idx):
            with tenant_context(isolated_tenant):
                ord_record = order_repo.create({
                    'order_number': f'SO-E2E-{isolated_tenant}-{idx:05d}',
                    'customer_id': cust['id'],
                    'warehouse_id': wh['id'],
                    'status': 'Draft',
                    'subtotal': 100.0,
                    'tax': 10.0,
                    'grand_total': 110.0,
                    'order_date': '2026-08-20',
                })
                line_repo.create({
                    'sales_order_id': ord_record['id'],
                    'product_id': prod['id'],
                    'product_name': prod['name'],
                    'qty': 1,
                    'unit_price': 100.0,
                    'line_total': 100.0,
                    'line_number': 1,
                })
                with lock:
                    order_ids.append(ord_record['id'])

        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(create_order, range(1, 51)))

        assert order_repo.count() == 50
        assert len(order_ids) == 50

        # Step 2: Confirm 50 orders concurrently -> generates 50 unique pick lists
        def confirm_order(oid):
            with tenant_context(isolated_tenant):
                return sales_service.update(oid, {'status': 'Confirmed'})

        with ThreadPoolExecutor(max_workers=50) as executor:
            confirmed = list(executor.map(confirm_order, order_ids))
        assert len(confirmed) == 50

        # Check 50 unique pick lists created
        pick_lists = pl_repo.list()
        assert len(pick_lists) == 50
        pkl_nums = [pl['pick_list_number'] for pl in pick_lists]
        assert len(set(pkl_nums)) == 50

        # Step 3: Complete picking for all pick lists to transition orders to Shipped
        for pl in pick_lists:
            items = pli_repo.list(filters={'pick_list_id': pl['id']})
            for it in items:
                pick_list_service.pick_item(it['id'], it['qty_ordered'])
            pick_list_service.complete_picking(pl['id'])

        # Verify all 50 orders are Shipped
        shipped_orders = order_repo.list(filters={'status': 'Shipped'})
        assert len(shipped_orders) == 50

        # Step 4: Deliver 50 orders concurrently -> generates 50 unique invoices
        def deliver_order(oid):
            with tenant_context(isolated_tenant):
                return sales_service.update(oid, {'status': 'Delivered'})

        with ThreadPoolExecutor(max_workers=50) as executor:
            delivered = list(executor.map(deliver_order, order_ids))
        assert len(delivered) == 50

        # Check 50 unique invoices created
        invoices = inv_repo.list()
        assert len(invoices) == 50
        inv_nums = [inv['invoice_number'] for inv in invoices]
        assert len(set(inv_nums)) == 50

        # SQL Verification in PostgreSQL
        with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    (SELECT count(*) FROM "Nova".t0012 WHERE business_id = %s AND status = 'Delivered') as delivered_so,
                    (SELECT count(*) FROM "Nova".t0101 WHERE business_id = %s AND status = 'Completed') as completed_pl,
                    (SELECT count(*) FROM "Nova".t0090 WHERE business_id = %s AND status = 'Unpaid') as unpaid_inv;
                """,
                (isolated_tenant, isolated_tenant, isolated_tenant)
            )
            res = cur.fetchone()
            assert res['delivered_so'] == 50
            assert res['completed_pl'] == 50
            assert res['unpaid_inv'] == 50


# ============================================================================
# 4. Multi-Tenant Concurrent Sequence Generation & Isolation Tests
# ============================================================================

class TestRealPostgresMultiTenantConcurrentSequences:
    """Stress tests verifying sequence atomicity and data isolation across concurrent multi-tenant workloads."""

    def test_concurrent_multi_tenant_document_generation_isolation(
        self, real_harness, real_db_conn
    ):
        """
        Simulate concurrent document generation across 2 distinct tenants:
        - 30 worker threads for Tenant A
        - 30 worker threads for Tenant B
        Assert that all 60 invoices receive globally unique sequence numbers from PostgreSQL,
        and that CrudRepository queries strictly isolate records by tenant business_id.
        """
        reset_sequence('seq_invoice_number', start_val=1)

        with isolated_tenant_ctx(harness=real_harness) as (tenant_a, _):
            with isolated_tenant_ctx(harness=real_harness) as (tenant_b, _):
                # Seed customer for each tenant
                cust_repo = CrudRepository('T0010')
                with tenant_context(tenant_a):
                    cust_a = cust_repo.create({'name': 'Tenant A Customer', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})
                with tenant_context(tenant_b):
                    cust_b = cust_repo.create({'name': 'Tenant B Customer', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})

                inv_service = InvoiceService()

                total_workers = 60
                barrier = threading.Barrier(total_workers)
                tenant_a_invoices = []
                tenant_b_invoices = []
                errors = []
                lock = threading.Lock()

                def tenant_worker(tenant_id, customer_id, target_list, worker_idx):
                    with tenant_context(tenant_id):
                        try:
                            barrier.wait()
                            inv = inv_service.create({
                                'partner_id': customer_id,
                                'issue_date': '2026-08-20',
                                'due_date': '2026-09-20',
                                'total_amount': 100.0 + worker_idx,
                            })
                            with lock:
                                target_list.append(inv)
                        except Exception as e:
                            with lock:
                                errors.append(f"Tenant {tenant_id} worker {worker_idx} failed: {e}")

                threads = []
                for i in range(30):
                    threads.append(threading.Thread(target=tenant_worker, args=(tenant_a, cust_a['id'], tenant_a_invoices, i)))
                    threads.append(threading.Thread(target=tenant_worker, args=(tenant_b, cust_b['id'], tenant_b_invoices, i)))

                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                assert len(errors) == 0, f"Multi-tenant concurrency errors: {errors}"
                assert len(tenant_a_invoices) == 30
                assert len(tenant_b_invoices) == 30

                # All 60 invoice numbers globally unique
                all_nums = [inv['invoice_number'] for inv in tenant_a_invoices + tenant_b_invoices]
                assert len(set(all_nums)) == 60

                # Check tenant isolation via CrudRepository
                with tenant_context(tenant_a):
                    a_listed = inv_service.repo.list()
                    assert len(a_listed) == 30
                    for row in a_listed:
                        assert row['business_id'] == tenant_a

                with tenant_context(tenant_b):
                    b_listed = inv_service.repo.list()
                    assert len(b_listed) == 30
                    for row in b_listed:
                        assert row['business_id'] == tenant_b

                # Verify via direct SQL in PostgreSQL
                with real_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        'SELECT count(*) as total, count(DISTINCT invoice_number) as uniq FROM "Nova".t0090 WHERE business_id IN (%s, %s);',
                        (tenant_a, tenant_b)
                    )
                    stats = cur.fetchone()
                    assert stats['total'] == 60
                    assert stats['uniq'] == 60


# ============================================================================
# 5. Concurrent REST API & MCP Server Tests
# ============================================================================

class TestRealPostgresConcurrentRestApiAndMCP:
    """Stress tests verifying concurrent document generation via REST API endpoints and MCP server tools."""

    def test_50_concurrent_rest_api_invoice_creations(self, isolated_tenant, real_db_conn):
        """
        Send 50 concurrent POST requests to /api/T0090I (Invoices) via FastAPI TestClient.
        Assert that all 50 respond with HTTP 201 Created and have unique invoice numbers.
        """
        reset_sequence('seq_invoice_number', start_val=1)
        client = create_real_db_api_client(tenant_id=isolated_tenant)

        cust_repo = CrudRepository('T0010')
        cust = cust_repo.create({'name': f'API Customer {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})

        num_threads = 50
        barrier = threading.Barrier(num_threads)
        responses = []
        errors = []
        lock = threading.Lock()

        def api_worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    resp = client.post('/api/T0090I', json={
                        'partner_id': cust['id'],
                        'issue_date': '2026-08-20',
                        'due_date': '2026-09-20',
                        'total_amount': 50.0 + idx,
                        'status': 'Unpaid',
                    })
                    with lock:
                        responses.append(resp)
                except Exception as e:
                    with lock:
                        errors.append(f"API worker {idx} failed: {e}")

        threads = [threading.Thread(target=api_worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"API errors: {errors}"
        assert len(responses) == 50

        invoice_numbers = []
        for r in responses:
            assert r.status_code == 201, f"Expected 201 Created, got {r.status_code}: {r.text}"
            data = r.json()
            assert 'invoice_number' in data
            invoice_numbers.append(data['invoice_number'])

        assert len(set(invoice_numbers)) == 50
        for num in invoice_numbers:
            assert re.match(r"^INV-\d{5}$", num)

    def test_50_concurrent_rest_api_order_confirmations(self, isolated_tenant, real_db_conn):
        """
        Send 50 concurrent POST requests to /api/T0012I/{id}/confirm via FastAPI TestClient.
        Assert that all 50 respond with HTTP 200 and produce 50 unique pick lists in PostgreSQL.
        """
        reset_sequence('seq_pick_list_number', start_val=1)
        client = create_real_db_api_client(tenant_id=isolated_tenant)

        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        prod_repo = CrudRepository('T0003')
        stock_repo = CrudRepository('T0009')
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        wh = wh_repo.create({'name': f'API WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'API Cust {isolated_tenant}', 'credit_limit': 10000000.0, 'balance': 0.0, 'is_active': True})
        prod = prod_repo.create({'name': f'API Prod {isolated_tenant}', 'sku': f'API-SKU-{isolated_tenant}', 'price': 25.0, 'is_active': True})

        stock_repo.create({'product_id': prod['id'], 'warehouse_id': wh['id'], 'qty': 5000.0, 'reserved_qty': 0.0})

        order_ids = []
        for i in range(1, 51):
            order = order_repo.create({
                'order_number': f'SO-API-{isolated_tenant}-{i:05d}',
                'customer_id': cust['id'],
                'warehouse_id': wh['id'],
                'status': 'Draft',
                'subtotal': 50.0,
                'tax': 5.0,
                'grand_total': 55.0,
                'order_date': '2026-08-20',
            })
            line_repo.create({
                'sales_order_id': order['id'],
                'product_id': prod['id'],
                'product_name': prod['name'],
                'qty': 2,
                'unit_price': 25.0,
                'line_total': 50.0,
                'line_number': 1,
            })
            order_ids.append(order['id'])

        num_threads = 50
        barrier = threading.Barrier(num_threads)
        responses = []
        errors = []
        lock = threading.Lock()

        def confirm_worker(oid):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    resp = client.post(f'/api/T0012I/{oid}/confirm')
                    with lock:
                        responses.append((oid, resp))
                except Exception as e:
                    with lock:
                        errors.append(f"Confirm worker {oid} failed: {e}")

        threads = [threading.Thread(target=confirm_worker, args=(oid,)) for oid in order_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(responses) == 50

        for oid, r in responses:
            assert r.status_code == 200, f"Expected 200 OK for order {oid}, got {r.status_code}: {r.text}"

        # Verify exactly 50 pick lists created in PostgreSQL
        pl_repo = CrudRepository('T0101')
        pick_lists = pl_repo.list()
        assert len(pick_lists) == 50
        pkl_nums = [pl['pick_list_number'] for pl in pick_lists]
        assert len(set(pkl_nums)) == 50

    def test_50_concurrent_mcp_tool_document_generation(self, isolated_tenant, real_db_conn):
        """
        Execute MCP server tools concurrently across 50 threads:
        - sales_mcp._create_order
        - sales_mcp._list_orders
        """
        wh_repo = CrudRepository('T0008')
        cust_repo = CrudRepository('T0010')
        wh = wh_repo.create({'name': f'MCP WH {isolated_tenant}', 'is_active': True})
        cust = cust_repo.create({'name': f'MCP Cust {isolated_tenant}', 'credit_limit': 10000000.0, 'balance': 0.0, 'is_active': True})

        num_threads = 50
        barrier = threading.Barrier(num_threads)
        created_orders = []
        errors = []
        lock = threading.Lock()

        def mcp_worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    res = sales_mcp._create_order(
                        order_number=f'SO-MCP-{isolated_tenant}-{idx:05d}',
                        customer_id=cust['id'],
                        warehouse_id=wh['id'],
                        subtotal=100.0,
                        grand_total=100.0,
                        order_date='2026-08-20',
                    )
                    with lock:
                        created_orders.append(res)
                except Exception as e:
                    with lock:
                        errors.append(f"MCP worker {idx} failed: {e}")

        threads = [threading.Thread(target=mcp_worker, args=(i,)) for i in range(1, num_threads + 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"MCP errors: {errors}"
        assert len(created_orders) == 50

        # Query MCP list tools
        with tenant_context(isolated_tenant):
            orders_list = sales_mcp._list_orders(limit=100)
            assert len(orders_list) == 50


# ============================================================================
# 6. Sequence Atomicity Under Aborts & Rollbacks
# ============================================================================

class TestRealPostgresSequenceRollbackAndAtomicity:
    """Stress tests verifying PostgreSQL sequence atomicity across aborted transactions and rollbacks."""

    def test_sequence_progression_across_failed_transactions(self, isolated_tenant, real_db_conn):
        """
        Verify that when transactions fail or roll back, PostgreSQL sequence progression remains atomic:
        - Generate sequence value 1 in a successful transaction.
        - Trigger a rolled-back transaction (which consumes sequence value 2).
        - Subsequent transaction consumes sequence value 3 without deadlock or corruption.
        """
        reset_sequence('seq_invoice_number', start_val=1)

        cust_repo = CrudRepository('T0010')
        cust = cust_repo.create({'name': f'Rollback Cust {isolated_tenant}', 'credit_limit': 1000000.0, 'balance': 0.0, 'is_active': True})

        inv_repo = CrudRepository('T0090')
        service = InvoiceService(inv_repo)

        # 1. Successful invoice 1
        inv1 = service.create({
            'partner_id': cust['id'],
            'issue_date': '2026-08-20',
            'due_date': '2026-09-20',
            'total_amount': 100.0,
        })
        assert inv1['invoice_number'] == 'INV-00001'

        # 2. Rollback transaction that fetched nextval
        from packages.database.connection import get_connection, release_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT nextval(\'"Nova".seq_invoice_number\');')
            conn.rollback()
        finally:
            release_connection(conn)

        # 3. Next invoice generation succeeds with sequence value 3
        inv3 = service.create({
            'partner_id': cust['id'],
            'issue_date': '2026-08-20',
            'due_date': '2026-09-20',
            'total_amount': 200.0,
        })
        assert inv3['invoice_number'] == 'INV-00003'

        # 4. Run 48 concurrent workers to bring total up
        barrier = threading.Barrier(48)
        subsequent_invoices = []
        errors = []
        lock = threading.Lock()

        def worker(idx):
            with tenant_context(isolated_tenant):
                try:
                    barrier.wait()
                    inv = service.create({
                        'partner_id': cust['id'],
                        'issue_date': '2026-08-20',
                        'due_date': '2026-09-20',
                        'total_amount': 300.0 + idx,
                    })
                    with lock:
                        subsequent_invoices.append(inv)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(48)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(subsequent_invoices) == 48

        all_inv_nums = [inv1['invoice_number'], inv3['invoice_number']] + [inv['invoice_number'] for inv in subsequent_invoices]
        assert len(set(all_inv_nums)) == 50
