import os
import re
import json
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch
import pytest

import httpx
from fastapi import FastAPI, Depends

from packages.database.sequence import (
    get_next_sequence_value,
    generate_document_number,
    generate_invoice_number,
    generate_pick_list_number,
    DOCUMENT_SEQUENCES,
    DOCUMENT_PREFIXES,
)
from modules.core.repositories.base import CrudRepository
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.accounting.services.invoice_service import InvoiceService
from modules.inventory.services.stock_movement import StockMovementService
import modules.core.controllers
from modules.sales.controllers.T0012I import router as sales_router
from modules.accounting.controllers.T0090I import router as invoice_router
from modules.warehouse.controllers.T0101I import router as pick_list_router
from packages.auth.deps import get_current_user


# ============================================================================
# Thread-Safe In-Memory Mock Database Infrastructure
# ============================================================================

class ThreadSafeAtomicSequenceManager:
    """Simulates atomic PostgreSQL sequences under high concurrency."""
    def __init__(self):
        self.sequences = {}
        self.lock = threading.Lock()

    def nextval(self, seq_name: str) -> int:
        with self.lock:
            val = self.sequences.get(seq_name, 0) + 1
            self.sequences[seq_name] = val
            return val

    def setval(self, seq_name: str, val: int, is_called: bool = True) -> int:
        with self.lock:
            self.sequences[seq_name] = val
            return val

    def get_last(self, seq_name: str) -> int:
        with self.lock:
            return self.sequences.get(seq_name, 0)

    def reset(self):
        with self.lock:
            self.sequences.clear()


class ThreadSafeTableStore:
    """
    Thread-safe in-memory table storage simulating PostgreSQL tables with
    strict primary key indexing and unique constraint enforcement.
    """
    def __init__(self):
        self.tables = {}
        self.lock = threading.RLock()
        self.unique_constraints = {
            't0090': ['invoice_number'],
            't0101': ['pick_list_number'],
        }

    def reset(self):
        with self.lock:
            self.tables.clear()

    def _get_table(self, table_name: str):
        tbl = table_name.lower().replace('"', '')
        if '.' in tbl:
            tbl = tbl.split('.')[-1]
        with self.lock:
            if tbl not in self.tables:
                self.tables[tbl] = {
                    'data': {},
                    'counter': 0,
                    'uniques': self.unique_constraints.get(tbl, []),
                }
            return self.tables[tbl]

    def create(self, table_name: str, payload: dict, pk: str = 'id') -> dict:
        with self.lock:
            tbl_info = self._get_table(table_name)
            data = tbl_info['data']
            uniques = tbl_info['uniques']

            # Check unique constraint violations
            for col in uniques:
                val = payload.get(col)
                if val is not None and str(val).strip():
                    for existing_item in data.values():
                        if existing_item.get(col) == val:
                            raise ValueError(
                                f"Unique constraint violation on {table_name}.{col}: "
                                f"duplicate value '{val}' already exists!"
                            )

            tbl_info['counter'] += 1
            record_id = payload.get(pk, tbl_info['counter'])
            if record_id in data:
                tbl_info['counter'] += 1
                record_id = tbl_info['counter']

            record = dict(payload)
            record[pk] = record_id
            data[record_id] = record
            return dict(record)

    def get(self, table_name: str, id_val, pk: str = 'id') -> dict:
        with self.lock:
            tbl_info = self._get_table(table_name)
            record = tbl_info['data'].get(id_val)
            return dict(record) if record else None

    def update(self, table_name: str, id_val, payload: dict, pk: str = 'id') -> dict:
        with self.lock:
            tbl_info = self._get_table(table_name)
            data = tbl_info['data']
            if id_val not in data:
                return None

            uniques = tbl_info['uniques']
            for col in uniques:
                val = payload.get(col)
                if val is not None and str(val).strip():
                    for k, existing_item in data.items():
                        if k != id_val and existing_item.get(col) == val:
                            raise ValueError(
                                f"Unique constraint violation on {table_name}.{col}: "
                                f"duplicate value '{val}' already exists!"
                            )

            data[id_val].update(payload)
            return dict(data[id_val])

    def list(self, table_name: str, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None) -> list:
        with self.lock:
            tbl_info = self._get_table(table_name)
            data = tbl_info['data']
            results = []
            for row in data.values():
                match = True
                if filters:
                    for k, v in filters.items():
                        if row.get(k) != v:
                            match = False
                            break
                if match:
                    results.append(dict(row))

            if order_by:
                results.sort(key=lambda r: r.get(order_by, 0))
            if offset:
                results = results[offset:]
            if limit:
                results = results[:limit]
            return results

    def count(self, table_name: str, filters: dict = None) -> int:
        with self.lock:
            return len(self.list(table_name, filters=filters))

    def delete(self, table_name: str, id_val, pk: str = 'id') -> bool:
        with self.lock:
            tbl_info = self._get_table(table_name)
            data = tbl_info['data']
            if id_val in data:
                del data[id_val]
                return True
            return False


# Global test database instances
seq_mgr = ThreadSafeAtomicSequenceManager()
tbl_store = ThreadSafeTableStore()


class MockThreadSafeConnection:
    """Thread-safe mock connection routing cursor and sequence calls."""
    def __init__(self):
        self.is_closed = False
        self._is_mock = True

    def cursor(self, cursor_factory=None):
        return MockThreadSafeCursor()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.is_closed = True


class MockThreadSafeCursor:
    def __init__(self):
        self._last_result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, sql, params=None):
        sql_str = str(sql).strip()
        params = params or ()

        # 1. SELECT nextval(%s)
        if 'nextval' in sql_str.lower():
            seq_name = params[0] if params else 'default_seq'
            val = seq_mgr.nextval(seq_name)
            self._last_result = (val,)
            return

        # 2. SELECT setval(%s, %s, %s)
        if 'setval' in sql_str.lower():
            seq_name = params[0]
            val = params[1]
            is_called = params[2] if len(params) > 2 else True
            res = seq_mgr.setval(seq_name, val, is_called)
            self._last_result = (res,)
            return

        # 3. SELECT last_value FROM ...
        if 'last_value' in sql_str.lower():
            seq_name = sql_str.split('FROM')[-1].strip().strip(';').strip('"')
            val = seq_mgr.get_last(seq_name)
            self._last_result = (val,)
            return

        self._last_result = None

    def fetchone(self):
        return self._last_result

    def fetchall(self):
        return [self._last_result] if self._last_result else []


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def setup_mock_environment():
    """Reset sequence counters, table store, and wire thread-safe CRUD hooks."""
    seq_mgr.reset()
    tbl_store.reset()

    # Pre-seed foundational records for sales / warehouse operations
    tbl_store.create('T0008', {'id': 1, 'name': 'Main Warehouse', 'is_active': True})
    tbl_store.create('T0010', {'id': 1, 'name': 'Acme Enterprise', 'credit_limit': 10000000.0, 'balance': 0.0})
    tbl_store.create('T0009', {'id': 1, 'product_id': 1, 'warehouse_id': 1, 'qty': 1000000, 'reserved_qty': 0})

    mock_conn = MockThreadSafeConnection()

    def mock_get_conn():
        return mock_conn

    def mock_rel_conn(c):
        pass

    # Patch CrudRepository methods to route to ThreadSafeTableStore
    def repo_create(self, payload: dict, conn=None):
        return tbl_store.create(self.qualified, payload, pk=self.pk)

    def repo_get(self, id_val, conn=None):
        return tbl_store.get(self.qualified, id_val, pk=self.pk)

    def repo_update(self, id_val, payload: dict, conn=None):
        return tbl_store.update(self.qualified, id_val, payload, pk=self.pk)

    def repo_list(self, filters=None, order_by=None, limit=None, offset=None, conn=None):
        return tbl_store.list(self.qualified, filters=filters, order_by=order_by, limit=limit, offset=offset)

    def repo_count(self, filters=None, conn=None):
        return tbl_store.count(self.qualified, filters=filters)

    def repo_delete(self, id_val, conn=None):
        return tbl_store.delete(self.qualified, id_val, pk=self.pk)

    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    mock_pool.putconn.return_value = None

    with patch('packages.database.connection._pool', mock_pool), \
         patch('packages.database.connection.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.connection.release_connection', side_effect=mock_rel_conn), \
         patch('modules.sales.services.sales_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.sales.services.sales_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.sales.services.enhanced_sales_order_service.get_connection', side_effect=mock_get_conn), \
         patch('modules.sales.services.enhanced_sales_order_service.release_connection', side_effect=mock_rel_conn), \
         patch('modules.core.repositories.base.get_connection', side_effect=mock_get_conn), \
         patch('modules.core.repositories.base.release_connection', side_effect=mock_rel_conn), \
         patch('packages.database.sequence.get_connection', side_effect=mock_get_conn), \
         patch('packages.database.sequence.release_connection', side_effect=mock_rel_conn), \
         patch.object(CrudRepository, 'create', repo_create), \
         patch.object(CrudRepository, 'get', repo_get), \
         patch.object(CrudRepository, 'update', repo_update), \
         patch.object(CrudRepository, 'list', repo_list), \
         patch.object(CrudRepository, 'count', repo_count), \
         patch.object(CrudRepository, 'delete', repo_delete):
        yield


# Helper for test admin auth
TEST_ADMIN_USER = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}


def create_test_fastapi_app():
    """Create test FastAPI application with sales, invoice, and picklist routes."""
    app = FastAPI(title="Concurrency Test ERP")

    # Dependency overrides to bypass auth in integration testing
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN_USER

    app.include_router(sales_router)
    app.include_router(invoice_router)
    app.include_router(pick_list_router)

    return app


# ============================================================================
# 1. Concurrent Atomic Sequence Generation Tests
# ============================================================================

class TestConcurrentAtomicSequences:
    """Stress tests verifying atomic sequence generation under 50+ concurrent threads."""

    def test_50_concurrent_threads_invoice_numbers(self):
        """Simulate 50 concurrent threads generating invoice numbers (INV-XXXXX)."""
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        generated_numbers = []
        errors = []

        def worker(thread_idx):
            try:
                # Synchronize thread starts for maximum concurrency stress
                barrier.wait()
                invoice_num = generate_invoice_number()
                generated_numbers.append(invoice_num)
            except Exception as e:
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
        assert len(unique_numbers) == 50, f"Duplicate invoice numbers detected: {len(generated_numbers) - len(unique_numbers)} collisions"

        # Verify format (INV-XXXXX with 5 digits)
        pattern = re.compile(r"^INV-\d{5}$")
        for num in generated_numbers:
            assert pattern.match(num), f"Invoice number '{num}' does not match format INV-XXXXX"

        # Verify sequence numbers cover 1 through 50 consecutively
        extracted_ints = sorted(int(num.split('-')[1]) for num in generated_numbers)
        assert extracted_ints == list(range(1, 51))

    def test_50_concurrent_threads_pick_list_numbers(self):
        """Simulate 50 concurrent threads generating pick list numbers (PKL-XXXXX)."""
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        generated_numbers = []
        errors = []

        def worker(thread_idx):
            try:
                barrier.wait()
                pkl_num = generate_pick_list_number()
                generated_numbers.append(pkl_num)
            except Exception as e:
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
        assert len(unique_numbers) == 50, f"Duplicate pick list numbers detected: {len(generated_numbers) - len(unique_numbers)} collisions"

        # Verify format (PKL-XXXXX with 5 digits)
        pattern = re.compile(r"^PKL-\d{5}$")
        for num in generated_numbers:
            assert pattern.match(num), f"Pick list number '{num}' does not match format PKL-XXXXX"

        # Verify continuous range 1..50
        extracted_ints = sorted(int(num.split('-')[1]) for num in generated_numbers)
        assert extracted_ints == list(range(1, 51))

    def test_100_concurrent_threads_interleaved_invoices_and_pick_lists(self):
        """
        Simulate 100 simultaneous threads (50 generating invoices, 50 generating pick lists)
        verifying that independent sequences operate in parallel without cross-contamination.
        """
        num_workers = 100
        barrier = threading.Barrier(num_workers)
        invoices = []
        pick_lists = []
        errors = []

        def invoice_worker():
            try:
                barrier.wait()
                inv = generate_invoice_number()
                invoices.append(inv)
            except Exception as e:
                errors.append(e)

        def pick_list_worker():
            try:
                barrier.wait()
                pkl = generate_pick_list_number()
                pick_lists.append(pkl)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            threads.append(threading.Thread(target=invoice_worker))
            threads.append(threading.Thread(target=pick_list_worker))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(invoices) == 50
        assert len(pick_lists) == 50
        assert len(set(invoices)) == 50
        assert len(set(pick_lists)) == 50

        # Check invoice format
        for inv in invoices:
            assert inv.startswith('INV-')
        # Check pick list format
        for pkl in pick_lists:
            assert pkl.startswith('PKL-')

    def test_50_concurrent_threads_custom_padding_and_prefix(self):
        """Simulate concurrent generation with custom document prefix and padding."""
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        results = []

        def worker():
            barrier.wait()
            doc_num = generate_document_number('seq_custom_doc', prefix='DOC', padding=6)
            results.append(doc_num)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        assert len(results) == 50
        assert len(set(results)) == 50
        pattern = re.compile(r"^DOC-\d{6}$")
        for doc in results:
            assert pattern.match(doc)


# ============================================================================
# 2. Concurrent Direct Service Creation Tests
# ============================================================================

class TestConcurrentDirectServiceCreation:
    """Stress tests verifying auto-generated document numbers on direct CRUD creations."""

    def test_50_concurrent_direct_invoice_creations(self):
        """Create 50 invoices concurrently without providing invoice_number."""
        inv_repo = CrudRepository('T0090')
        service = InvoiceService(inv_repo)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        created_invoices = []
        errors = []

        def worker(idx):
            try:
                barrier.wait()
                invoice = service.create({
                    'partner_id': 1,
                    'issue_date': '2026-08-20',
                    'due_date': '2026-09-20',
                    'total_amount': 100.0 + idx,
                })
                created_invoices.append(invoice)
            except Exception as e:
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

    def test_50_concurrent_direct_pick_list_creations(self):
        """Create 50 pick lists concurrently without providing pick_list_number."""
        pl_repo = CrudRepository('T0101')
        service = PickListService(pl_repo)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        created_pick_lists = []
        errors = []

        def worker(idx):
            try:
                barrier.wait()
                pl = service.create({
                    'sales_order_id': idx,
                    'warehouse_id': 1,
                    'status': 'Pending',
                })
                created_pick_lists.append(pl)
            except Exception as e:
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


# ============================================================================
# 3. Concurrent Sales Order Lifecycle & Document Generation Tests
# ============================================================================

class TestConcurrentSalesOrderLifecycle:
    """
    Stress tests verifying concurrent order creation, confirmation (pick list generation),
    and delivery (invoice generation) for 50 simultaneous orders.
    """

    def test_50_concurrent_orders_confirmation_generates_50_unique_pick_lists(self):
        """
        Simulate 50 simultaneous orders transitioning Draft -> Confirmed.
        Verifies 50 unique pick lists (PKL-XXXXX) are produced without collisions.
        """
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        service = SalesOrderService(order_repo)

        # Seed 50 draft sales orders with lines
        for i in range(1, 51):
            order_repo.create({
                'id': i,
                'order_number': f'SO-{i:05d}',
                'customer_id': 1,
                'warehouse_id': 1,
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 15.0,
                'grand_total': 115.0,
            })
            line_repo.create({
                'sales_order_id': i,
                'product_id': 1,
                'product_name': 'Standard Widget',
                'qty': 2,
                'unit_price': 50.0,
                'line_total': 100.0,
                'line_number': 1,
            })

        num_orders = 50
        barrier = threading.Barrier(num_orders)
        confirmed_orders = []
        errors = []

        def confirm_worker(order_id):
            try:
                barrier.wait()
                result = service.update(order_id, {'status': 'Confirmed'})
                confirmed_orders.append(result)
            except Exception as e:
                errors.append(f"Order {order_id} confirmation failed: {e}")

        threads = [threading.Thread(target=confirm_worker, args=(i,)) for i in range(1, 51)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Confirmation errors: {errors}"
        assert len(confirmed_orders) == 50

        # Verify all 50 orders are in Confirmed status
        for ord_res in confirmed_orders:
            assert ord_res['status'] == 'Confirmed'

        # Verify exactly 50 pick lists created in T0101
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

    def test_50_concurrent_orders_delivery_generates_50_unique_invoices(self):
        """
        Simulate 50 simultaneous orders transitioning Shipped -> Delivered.
        Verifies 50 unique invoices (INV-XXXXX) are produced without duplicate crashes.
        """
        order_repo = CrudRepository('T0012')
        service = SalesOrderService(order_repo)

        # Seed 50 shipped sales orders
        for i in range(1, 51):
            order_repo.create({
                'id': i,
                'order_number': f'SO-{i:05d}',
                'customer_id': 1,
                'warehouse_id': 1,
                'status': 'Shipped',
                'subtotal': 200.0,
                'tax': 30.0,
                'grand_total': 230.0,
                'order_date': '2026-08-20',
            })

        num_orders = 50
        barrier = threading.Barrier(num_orders)
        delivered_orders = []
        errors = []

        def deliver_worker(order_id):
            try:
                barrier.wait()
                result = service.update(order_id, {'status': 'Delivered'})
                delivered_orders.append(result)
            except Exception as e:
                errors.append(f"Order {order_id} delivery failed: {e}")

        threads = [threading.Thread(target=deliver_worker, args=(i,)) for i in range(1, 51)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Delivery errors: {errors}"
        assert len(delivered_orders) == 50

        # Verify all 50 orders are in Delivered status
        for ord_res in delivered_orders:
            assert ord_res['status'] == 'Delivered'

        # Verify exactly 50 invoices created in T0090
        inv_repo = CrudRepository('T0090')
        all_invoices = inv_repo.list()
        assert len(all_invoices) == 50

        # Verify all 50 invoice numbers are unique with INV-XXXXX format
        inv_numbers = [inv['invoice_number'] for inv in all_invoices]
        assert len(set(inv_numbers)) == 50, f"Collisions in invoice numbers: {inv_numbers}"
        for inv_num in inv_numbers:
            assert re.match(r"^INV-\d{5}$", inv_num)

    def test_50_concurrent_full_order_pipeline_end_to_end(self):
        """
        Simulate 50 orders flowing through the complete lifecycle simultaneously:
        1. Concurrent Creation -> Draft
        2. Concurrent Confirmation -> Confirmed + Pick List (PKL-XXXXX)
        3. Picking completion -> Shipped
        4. Concurrent Delivery -> Delivered + Invoice (INV-XXXXX)
        """
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        sales_service = SalesOrderService(order_repo)
        pick_list_service = PickListService()

        # Step 1: Create 50 Draft orders concurrently
        def create_order(idx):
            ord_record = order_repo.create({
                'id': idx,
                'order_number': f'SO-{idx:05d}',
                'customer_id': 1,
                'warehouse_id': 1,
                'status': 'Draft',
                'subtotal': 100.0,
                'tax': 10.0,
                'grand_total': 110.0,
                'order_date': '2026-08-20',
            })
            line_repo.create({
                'sales_order_id': idx,
                'product_id': 1,
                'product_name': 'Standard Widget',
                'qty': 1,
                'unit_price': 100.0,
                'line_total': 100.0,
                'line_number': 1,
            })
            return ord_record

        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(create_order, range(1, 51)))

        assert order_repo.count() == 50

        # Step 2: Confirm 50 orders concurrently
        def confirm_order(idx):
            return sales_service.update(idx, {'status': 'Confirmed'})

        with ThreadPoolExecutor(max_workers=50) as executor:
            confirmed = list(executor.map(confirm_order, range(1, 51)))
        assert len(confirmed) == 50

        # Check 50 unique pick lists created
        pl_repo = CrudRepository('T0101')
        pick_lists = pl_repo.list()
        assert len(pick_lists) == 50
        pkl_nums = [pl['pick_list_number'] for pl in pick_lists]
        assert len(set(pkl_nums)) == 50

        # Step 3: Complete picking for all pick lists to transition orders to Shipped
        for pl in pick_lists:
            items = pick_list_service.pli_repo.list(filters={'pick_list_id': pl['id']})
            for it in items:
                pick_list_service.pick_item(it['id'], it['qty_ordered'])
            pick_list_service.complete_picking(pl['id'])

        # Verify all 50 orders are Shipped
        shipped_orders = order_repo.list(filters={'status': 'Shipped'})
        assert len(shipped_orders) == 50

        # Step 4: Deliver 50 orders concurrently
        def deliver_order(idx):
            return sales_service.update(idx, {'status': 'Delivered'})

        with ThreadPoolExecutor(max_workers=50) as executor:
            delivered = list(executor.map(deliver_order, range(1, 51)))
        assert len(delivered) == 50

        # Check 50 unique invoices created
        inv_repo = CrudRepository('T0090')
        invoices = inv_repo.list()
        assert len(invoices) == 50
        inv_nums = [inv['invoice_number'] for inv in invoices]
        assert len(set(inv_nums)) == 50
        for num in inv_nums:
            assert re.match(r"^INV-\d{5}$", num)


# ============================================================================
# 4. Concurrent FastAPI HTTP Endpoints Stress Tests
# ============================================================================

class TestConcurrentFastAPIHttpEndpoints:
    """Stress tests verifying zero HTTP 500 errors under concurrent HTTP requests."""

    async def test_50_concurrent_http_order_confirmations(self):
        """Simulate 50 concurrent HTTP POST requests to /api/T0012I/{id}/confirm."""
        app = create_test_fastapi_app()

        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')

        for i in range(1, 51):
            order_repo.create({
                'id': i,
                'order_number': f'SO-HTTP-{i:05d}',
                'customer_id': 1,
                'warehouse_id': 1,
                'status': 'Draft',
                'subtotal': 50.0,
                'tax': 5.0,
                'grand_total': 55.0,
            })
            line_repo.create({
                'sales_order_id': i,
                'product_id': 1,
                'product_name': 'Widget',
                'qty': 1,
                'unit_price': 50.0,
                'line_total': 50.0,
                'line_number': 1,
            })

        async def confirm_order(order_id, client):
            return await client.post(f"/api/T0012I/{order_id}/confirm")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(
                *(confirm_order(i, client) for i in range(1, 51))
            )

        assert len(responses) == 50

        # Verify zero HTTP 500 internal server errors
        for resp in responses:
            assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"

        # Verify pick lists created without collisions
        pl_repo = CrudRepository('T0101')
        pls = pl_repo.list()
        assert len(pls) == 50
        nums = [p['pick_list_number'] for p in pls]
        assert len(set(nums)) == 50

    async def test_50_concurrent_http_order_deliveries(self):
        """Simulate 50 concurrent HTTP POST requests to /api/T0012I/{id}/deliver."""
        app = create_test_fastapi_app()

        order_repo = CrudRepository('T0012')

        for i in range(1, 51):
            order_repo.create({
                'id': i,
                'order_number': f'SO-DELIV-{i:05d}',
                'customer_id': 1,
                'warehouse_id': 1,
                'status': 'Shipped',
                'subtotal': 75.0,
                'tax': 7.5,
                'grand_total': 82.5,
                'order_date': '2026-08-20',
            })

        async def deliver_order(order_id, client):
            return await client.post(f"/api/T0012I/{order_id}/deliver")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(
                *(deliver_order(i, client) for i in range(1, 51))
            )

        assert len(responses) == 50

        # Verify zero HTTP 500 errors
        for resp in responses:
            assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"

        # Verify invoices created without collisions
        inv_repo = CrudRepository('T0090')
        invoices = inv_repo.list()
        assert len(invoices) == 50
        nums = [inv['invoice_number'] for inv in invoices]
        assert len(set(nums)) == 50

    async def test_50_concurrent_http_direct_document_creations(self):
        """
        Simulate 25 concurrent POST requests to /api/T0090I/ and 25 to /api/T0101I/
        without passing document numbers.
        """
        app = create_test_fastapi_app()

        async def create_invoice(idx, client):
            return await client.post("/api/T0090I/", json={
                'partner_id': 1,
                'issue_date': '2026-08-20',
                'due_date': '2026-09-20',
                'total_amount': 50.0 + idx,
            })

        async def create_pick_list(idx, client):
            return await client.post("/api/T0101I/", json={
                'sales_order_id': idx,
                'warehouse_id': 1,
                'status': 'Pending',
            })

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            inv_responses = await asyncio.gather(
                *(create_invoice(i, client) for i in range(25))
            )
            pkl_responses = await asyncio.gather(
                *(create_pick_list(i, client) for i in range(25))
            )

        assert len(inv_responses) == 25
        assert len(pkl_responses) == 25

        # All must be 201 Created with zero 500 internal errors
        for r in inv_responses:
            assert r.status_code == 201, f"Invoice creation failed: {r.text}"
            data = r.json()
            assert re.match(r"^INV-\d{5}$", data['invoice_number'])

        for r in pkl_responses:
            assert r.status_code == 201, f"Pick list creation failed: {r.text}"
            data = r.json()
            assert re.match(r"^PKL-\d{5}$", data['pick_list_number'])

        # Unique document numbers across responses
        inv_nums = [r.json()['invoice_number'] for r in inv_responses]
        pkl_nums = [r.json()['pick_list_number'] for r in pkl_responses]
        assert len(set(inv_nums)) == 25
        assert len(set(pkl_nums)) == 25


# ============================================================================
# 5. Asyncio Concurrent Document Generation Tests
# ============================================================================

class TestAsyncioConcurrentDocumentNumbering:
    """Stress tests verifying async coroutine concurrency using asyncio.gather."""

    @pytest.mark.asyncio
    async def test_50_concurrent_asyncio_invoice_numbering(self):
        """Simulate 50 concurrent async tasks calling generate_invoice_number."""
        async def async_gen_invoice():
            await asyncio.sleep(0.001)
            return generate_invoice_number()

        tasks = [asyncio.create_task(async_gen_invoice()) for _ in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50
        assert len(set(results)) == 50
        for num in results:
            assert re.match(r"^INV-\d{5}$", num)

    @pytest.mark.asyncio
    async def test_50_concurrent_asyncio_pick_list_numbering(self):
        """Simulate 50 concurrent async tasks calling generate_pick_list_number."""
        async def async_gen_pick_list():
            await asyncio.sleep(0.001)
            return generate_pick_list_number()

        tasks = [asyncio.create_task(async_gen_pick_list()) for _ in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50
        assert len(set(results)) == 50
        for num in results:
            assert re.match(r"^PKL-\d{5}$", num)
