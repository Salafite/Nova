import re
import logging
from unittest.mock import MagicMock, patch
import pytest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from packages.database.sequence import (
    generate_invoice_number,
    generate_pick_list_number,
)
from modules.core.repositories.base import CrudRepository
from modules.sales.services.sales_service import SalesOrderService
from modules.warehouse.services.pick_list_service import PickListService
from modules.inventory.services.stock_movement import StockMovementService
import modules.core.controllers
from modules.sales.controllers.T0012I import router as sales_router
from packages.auth.deps import get_current_user


# ============================================================================
# Transactional Mock Storage & Connection Infrastructure
# ============================================================================

class TransactionalTableStore:
    """
    In-memory mock table store supporting atomic transactional staging,
    commits, and rollbacks on a per-connection basis.
    """
    def __init__(self):
        self.committed_data = {}
        self.table_counters = {}
        # conn_id -> {'creates': {table: {id: record}}, 'updates': {table: {id: record}}, 'deletes': {table: set(ids)}}
        self.transactions = {}

    def reset(self):
        self.committed_data.clear()
        self.table_counters.clear()
        self.transactions.clear()

    def _normalize_table(self, table_name: str) -> str:
        tbl = table_name.lower().replace('"', '')
        if '.' in tbl:
            tbl = tbl.split('.')[-1]
        return tbl

    def _get_table_data(self, tbl: str):
        if tbl not in self.committed_data:
            self.committed_data[tbl] = {}
            self.table_counters[tbl] = 0
        return self.committed_data[tbl]

    def _get_next_id(self, tbl: str, explicit_id=None):
        self._get_table_data(tbl)
        if explicit_id is not None:
            if explicit_id > self.table_counters[tbl]:
                self.table_counters[tbl] = explicit_id
            return explicit_id
        self.table_counters[tbl] += 1
        return self.table_counters[tbl]

    def start_transaction(self, conn_id):
        self.transactions[conn_id] = {
            'creates': {},
            'updates': {},
            'deletes': {},
        }

    def commit_transaction(self, conn_id):
        if conn_id not in self.transactions:
            return
        tx = self.transactions[conn_id]
        # Apply creates
        for tbl, records in tx['creates'].items():
            t_data = self._get_table_data(tbl)
            for rec_id, rec in records.items():
                t_data[rec_id] = dict(rec)
        # Apply updates
        for tbl, records in tx['updates'].items():
            t_data = self._get_table_data(tbl)
            for rec_id, rec in records.items():
                if rec_id in t_data:
                    t_data[rec_id].update(rec)
                else:
                    t_data[rec_id] = dict(rec)
        # Apply deletes
        for tbl, ids in tx['deletes'].items():
            t_data = self._get_table_data(tbl)
            for rec_id in ids:
                t_data.pop(rec_id, None)
        del self.transactions[conn_id]

    def rollback_transaction(self, conn_id):
        # Discard all uncommitted staging for this connection
        if conn_id in self.transactions:
            del self.transactions[conn_id]

    def create(self, table_name: str, payload: dict, pk: str = 'id', conn=None) -> dict:
        tbl = self._normalize_table(table_name)
        record_id = self._get_next_id(tbl, payload.get(pk))
        record = dict(payload)
        record[pk] = record_id

        conn_id = getattr(conn, 'conn_id', None)
        if conn_id is not None and conn_id in self.transactions:
            tx = self.transactions[conn_id]
            if tbl not in tx['creates']:
                tx['creates'][tbl] = {}
            tx['creates'][tbl][record_id] = dict(record)
        else:
            t_data = self._get_table_data(tbl)
            t_data[record_id] = dict(record)
        return dict(record)

    def get(self, table_name: str, id_val, pk: str = 'id', conn=None) -> dict:
        tbl = self._normalize_table(table_name)
        conn_id = getattr(conn, 'conn_id', None)
        if conn_id is not None and conn_id in self.transactions:
            tx = self.transactions[conn_id]
            # Check deletes
            if tbl in tx['deletes'] and id_val in tx['deletes'][tbl]:
                return None
            # Check updates
            if tbl in tx['updates'] and id_val in tx['updates'][tbl]:
                return dict(tx['updates'][tbl][id_val])
            # Check creates
            if tbl in tx['creates'] and id_val in tx['creates'][tbl]:
                return dict(tx['creates'][tbl][id_val])

        t_data = self._get_table_data(tbl)
        rec = t_data.get(id_val)
        return dict(rec) if rec else None

    def update(self, table_name: str, id_val, payload: dict, pk: str = 'id', conn=None) -> dict:
        tbl = self._normalize_table(table_name)
        existing = self.get(table_name, id_val, pk=pk, conn=conn)
        if not existing:
            return None

        updated = dict(existing)
        updated.update(payload)

        conn_id = getattr(conn, 'conn_id', None)
        if conn_id is not None and conn_id in self.transactions:
            tx = self.transactions[conn_id]
            if tbl not in tx['updates']:
                tx['updates'][tbl] = {}
            tx['updates'][tbl][id_val] = dict(updated)
        else:
            t_data = self._get_table_data(tbl)
            if id_val in t_data:
                t_data[id_val].update(payload)
                updated = dict(t_data[id_val])
        return dict(updated)

    def list(self, table_name: str, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None) -> list:
        tbl = self._normalize_table(table_name)
        t_data = self._get_table_data(tbl)

        records_map = {k: dict(v) for k, v in t_data.items()}

        conn_id = getattr(conn, 'conn_id', None)
        if conn_id is not None and conn_id in self.transactions:
            tx = self.transactions[conn_id]
            # Overlay creates
            if tbl in tx['creates']:
                for k, v in tx['creates'][tbl].items():
                    records_map[k] = dict(v)
            # Overlay updates
            if tbl in tx['updates']:
                for k, v in tx['updates'][tbl].items():
                    records_map[k] = dict(v)
            # Exclude deletes
            if tbl in tx['deletes']:
                for k in tx['deletes'][tbl]:
                    records_map.pop(k, None)

        results = []
        for row in records_map.values():
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

    def delete(self, table_name: str, id_val, pk: str = 'id', conn=None) -> bool:
        tbl = self._normalize_table(table_name)
        conn_id = getattr(conn, 'conn_id', None)
        if conn_id is not None and conn_id in self.transactions:
            tx = self.transactions[conn_id]
            if tbl not in tx['deletes']:
                tx['deletes'][tbl] = set()
            tx['deletes'][tbl].add(id_val)
            if tbl in tx['creates'] and id_val in tx['creates'][tbl]:
                del tx['creates'][tbl][id_val]
            if tbl in tx['updates'] and id_val in tx['updates'][tbl]:
                del tx['updates'][tbl][id_val]
            return True
        else:
            t_data = self._get_table_data(tbl)
            if id_val in t_data:
                del t_data[id_val]
                return True
            return False


class MockTransactionalConnection:
    """Mock connection with transaction state tracking and store integration."""
    _counter = 0

    def __init__(self, store: TransactionalTableStore):
        MockTransactionalConnection._counter += 1
        self.conn_id = MockTransactionalConnection._counter
        self.store = store
        self.store.start_transaction(self.conn_id)
        self.commit_count = 0
        self.rollback_count = 0
        self.is_released = False
        self.fail_rollback_on_purpose = False
        self._is_mock = True

    def commit(self):
        self.commit_count += 1
        self.store.commit_transaction(self.conn_id)

    def rollback(self):
        self.rollback_count += 1
        if self.fail_rollback_on_purpose:
            raise RuntimeError("Database connection reset during rollback")
        self.store.rollback_transaction(self.conn_id)

    def close(self):
        self.is_released = True

    def cursor(self, cursor_factory=None):
        return MagicMock()


# Global test store instance
test_store = TransactionalTableStore()
active_connections = []


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def setup_mock_db():
    test_store.reset()
    active_connections.clear()

    # Pre-seed base data
    test_store.create('T0008', {'id': 1, 'name': 'Main Warehouse', 'is_active': True})
    test_store.create('T0010', {'id': 1, 'name': 'Acme Global', 'credit_limit': 50000.0, 'balance': 0.0})
    test_store.create('T0009', {'id': 1, 'product_id': 1, 'warehouse_id': 1, 'qty': 1000, 'reserved_qty': 0})

    def mock_get_conn():
        conn = MockTransactionalConnection(test_store)
        active_connections.append(conn)
        return conn

    def mock_rel_conn(c):
        if c:
            c.is_released = True

    def repo_create(self, payload: dict, conn=None, *args, **kwargs):
        return test_store.create(self.qualified, payload, pk=self.pk, conn=conn)

    def repo_get(self, id_val, conn=None, *args, **kwargs):
        return test_store.get(self.qualified, id_val, pk=self.pk, conn=conn)

    def repo_update(self, id_val, payload: dict, conn=None, *args, **kwargs):
        return test_store.update(self.qualified, id_val, payload, pk=self.pk, conn=conn)

    def repo_list(self, filters=None, order_by=None, limit=None, offset=None, conn=None, *args, **kwargs):
        return test_store.list(self.qualified, filters=filters, order_by=order_by, limit=limit, offset=offset, conn=conn)

    def repo_delete(self, id_val, conn=None, *args, **kwargs):
        return test_store.delete(self.qualified, id_val, pk=self.pk, conn=conn)

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
         patch.object(CrudRepository, 'delete', repo_delete):
        yield


TEST_ADMIN_USER = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}


def create_test_app():
    app = FastAPI(title="Test Rollback App")
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN_USER
    app.include_router(sales_router)
    return app


def unittest_mock_any():
    from unittest.mock import ANY
    return ANY


# ============================================================================
# 1. Transaction Infrastructure & Rollback Mechanics Tests
# ============================================================================

class TestTransactionRollbackInfrastructure:
    """Verifies low-level connection commit, rollback, and cleanup behavior."""

    def test_connection_commit_called_on_successful_update(self):
        """Successful status update commits transaction and releases connection."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 1, 'order_number': 'SO-00001', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        service = SalesOrderService(order_repo)

        with patch.object(service, '_reserve_order_stock') as mock_reserve:
            updated = service.update(1, {'status': 'Confirmed'})
            assert updated['status'] == 'Confirmed'
            assert mock_reserve.called

        assert len(active_connections) >= 1
        last_conn = active_connections[-1]
        assert last_conn.commit_count == 1
        assert last_conn.rollback_count == 0
        assert last_conn.is_released is True

        # Committed change visible
        assert order_repo.get(1)['status'] == 'Confirmed'

    def test_connection_rollback_called_on_exception(self, caplog):
        """Exception during status update triggers rollback and releases connection."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 1, 'order_number': 'SO-00001', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.INFO):
            with patch.object(service, '_reserve_order_stock', side_effect=RuntimeError("Pick list creation failed")):
                with pytest.raises(RuntimeError, match="Pick list creation failed"):
                    service.update(1, {'status': 'Confirmed'})

        assert len(active_connections) >= 1
        last_conn = active_connections[-1]
        assert last_conn.commit_count == 0
        assert last_conn.rollback_count == 1
        assert last_conn.is_released is True

        # Order remains in original Draft status
        assert order_repo.get(1)['status'] == 'Draft'
        # Structured log emitted
        assert any("Transaction rolled back for sales order 1 update" in r.message for r in caplog.records)

    def test_connection_released_even_when_rollback_itself_raises(self, caplog):
        """If conn.rollback() itself raises, connection is still released in finally block."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 1, 'order_number': 'SO-00001', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        service = SalesOrderService(order_repo)

        # Configure connection to throw on rollback
        def failing_get_conn():
            conn = MockTransactionalConnection(test_store)
            conn.fail_rollback_on_purpose = True
            active_connections.append(conn)
            return conn

        with patch('modules.sales.services.sales_service.get_connection', side_effect=failing_get_conn):
            with caplog.at_level(logging.ERROR):
                with patch.object(service, '_reserve_order_stock', side_effect=RuntimeError("Original error")):
                    with pytest.raises(RuntimeError, match="Original error"):
                        service.update(1, {'status': 'Confirmed'})

        last_conn = active_connections[-1]
        assert last_conn.is_released is True
        # Rollback error logged
        assert any("Error during transaction rollback for sales order 1" in r.message for r in caplog.records)

    def test_caller_provided_connection_not_committed_or_released_by_service(self):
        """When conn is passed by caller, service participates in transaction without committing/closing."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 1, 'order_number': 'SO-00001', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        service = SalesOrderService(order_repo)

        external_conn = MockTransactionalConnection(test_store)

        with patch.object(service, '_reserve_order_stock'):
            updated = service.update(1, {'status': 'Confirmed'}, conn=external_conn)
            assert updated['status'] == 'Confirmed'

        # Service did not commit or release external connection
        assert external_conn.commit_count == 0
        assert external_conn.rollback_count == 0
        assert external_conn.is_released is False

        # Caller commits
        external_conn.commit()
        assert order_repo.get(1)['status'] == 'Confirmed'


# ============================================================================
# 2. Order Confirmation Rollback on Document & Stock Failures
# ============================================================================

class TestOrderConfirmationRollback:
    """Verifies atomicity and rollback during Draft -> Confirmed transition."""

    def test_rollback_on_pick_list_sequence_generation_failure(self, caplog):
        """
        When sequence generator fails during pick list creation on order confirmation:
        - Traceable RuntimeError is raised
        - Transaction is rolled back
        - Order status remains Draft
        - No pick list or items exist in database
        - Structured error and rollback logs are emitted
        """
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        order_repo.create({
            'id': 100,
            'order_number': 'SO-00100',
            'status': 'Draft',
            'customer_id': 1,
            'warehouse_id': 1,
            'subtotal': 500.0,
            'tax': 75.0,
            'grand_total': 575.0,
        })
        line_repo.create({
            'id': 1,
            'sales_order_id': 100,
            'product_id': 1,
            'product_name': 'Component Alpha',
            'qty': 5,
            'unit_price': 100.0,
            'line_total': 500.0,
            'line_number': 1,
        })
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.INFO):
            with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', side_effect=RuntimeError("Sequence seq_pick_list_number unavailable")):
                with pytest.raises(RuntimeError, match="Failed to create pick list for sales order 100"):
                    service.update(100, {'status': 'Confirmed'})

        # 1. Order status remained Draft (not stranded in Confirmed)
        order_after = order_repo.get(100)
        assert order_after['status'] == 'Draft'

        # 2. No pick list was created in T0101
        pl_repo = CrudRepository('T0101')
        pick_lists = pl_repo.list(filters={'sales_order_id': 100})
        assert len(pick_lists) == 0

        # 3. No pick list items were created in T0102
        pli_repo = CrudRepository('T0102')
        items = pli_repo.list()
        assert len(items) == 0

        # 4. Stock reservation rolled back
        inv_repo = CrudRepository('T0009')
        inv = inv_repo.get(1)
        assert inv['reserved_qty'] == 0

        # 5. Structured logs verified
        assert any("Failed to create pick list for sales order 100" in r.message and r.levelno == logging.ERROR for r in caplog.records)
        assert any("Transaction rolled back for sales order 100" in r.message and r.levelno == logging.INFO for r in caplog.records)

    def test_rollback_on_pick_list_header_creation_failure(self, caplog):
        """Failure during pick list header creation rolls back entire confirmation."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 101, 'order_number': 'SO-00101', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            with patch.object(PickListService, 'create', side_effect=Exception("Database lock timeout on T0101")):
                with pytest.raises(RuntimeError, match="Failed to create pick list header for sales order 101"):
                    service.update(101, {'status': 'Confirmed'})

        assert order_repo.get(101)['status'] == 'Draft'
        assert any("Failed to create pick list header for sales order 101" in r.message for r in caplog.records)

    def test_rollback_on_pick_list_item_creation_failure(self, caplog):
        """Failure during item insertion in T0102 rolls back order and pick list header."""
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        order_repo.create({'id': 102, 'order_number': 'SO-00102', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        line_repo.create({'id': 20, 'sales_order_id': 102, 'product_id': 1, 'product_name': 'Item 1', 'qty': 2, 'line_number': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            with patch.object(CrudRepository, 'create') as mock_create:
                # Let pick list header create succeed, but fail on line items
                def side_effect(payload, conn=None):
                    if payload.get('sales_order_line_id'):
                        raise RuntimeError("Disk full writing T0102")
                    return test_store.create('T0101', payload, pk='id', conn=conn)

                mock_create.side_effect = side_effect
                with pytest.raises(RuntimeError, match="Failed to create pick list item for sales order line 20"):
                    service.update(102, {'status': 'Confirmed'})

        assert order_repo.get(102)['status'] == 'Draft'
        pl_repo = CrudRepository('T0101')
        assert len(pl_repo.list(filters={'sales_order_id': 102})) == 0

    def test_rollback_on_missing_warehouse(self, caplog):
        """When order has no warehouse and no active warehouse exists, rejection is cleanly handled."""
        order_repo = CrudRepository('T0012')
        wh_repo = CrudRepository('T0008')
        # Deactivate all warehouses
        wh_repo.update(1, {'is_active': False})

        order_repo.create({'id': 103, 'order_number': 'SO-00103', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': None})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(HTTPException) as exc_info:
                service.update(103, {'status': 'Confirmed'})
            assert exc_info.value.status_code == 400
            assert "No active warehouse found" in exc_info.value.detail

        assert order_repo.get(103)['status'] == 'Draft'
        assert any("Cannot reserve stock for sales order 103: No active warehouse found" in r.message for r in caplog.records)

    def test_rollback_on_stock_reservation_failure(self, caplog):
        """Stock reservation partial failure rolls back order and pick list creation."""
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        order_repo.create({'id': 104, 'order_number': 'SO-00104', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})
        line_repo.create({'id': 30, 'sales_order_id': 104, 'product_id': 999, 'product_name': 'Out of Stock Widget', 'qty': 100, 'line_number': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            with patch.object(StockMovementService, 'reserve_stock', side_effect=ValueError("Product 999 not found in warehouse 1")):
                with pytest.raises(RuntimeError, match="Stock reservation partial failure"):
                    service.update(104, {'status': 'Confirmed'})

        assert order_repo.get(104)['status'] == 'Draft'
        assert any("Sales order 104 stock reservation failed" in r.message for r in caplog.records)


# ============================================================================
# 3. Order Delivery Rollback on Invoice Failures
# ============================================================================

class TestOrderDeliveryRollback:
    """Verifies atomicity and rollback during Shipped -> Delivered transition."""

    def test_rollback_on_invoice_sequence_generation_failure(self, caplog):
        """
        When invoice sequence generation fails during order delivery:
        - Traceable RuntimeError is raised
        - Transaction is rolled back
        - Order status remains Shipped (not stuck in Delivered)
        - No invoice is created in T0090
        - Customer balance is unchanged
        - Structured logs are emitted
        """
        order_repo = CrudRepository('T0012')
        customer_repo = CrudRepository('T0010')
        order_repo.create({
            'id': 200,
            'order_number': 'SO-00200',
            'status': 'Shipped',
            'customer_id': 1,
            'warehouse_id': 1,
            'grand_total': 1500.0,
            'order_date': '2026-08-20',
        })
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.INFO):
            with patch('modules.sales.services.sales_service.generate_invoice_number', side_effect=RuntimeError("Sequence seq_invoice_number exhausted")):
                with pytest.raises(RuntimeError, match="Failed to create invoice for sales order 200"):
                    service.update(200, {'status': 'Delivered'})

        # 1. Order status remained Shipped
        order_after = order_repo.get(200)
        assert order_after['status'] == 'Shipped'

        # 2. No invoice was created
        inv_repo = CrudRepository('T0090')
        invoices = inv_repo.list(filters={'sales_order_id': 200})
        assert len(invoices) == 0

        # 3. Customer balance unchanged (remains 0.0)
        customer = customer_repo.get(1)
        assert customer['balance'] == 0.0

        # 4. Structured logs verified
        assert any("Failed to create invoice for sales order 200" in r.message and r.levelno == logging.ERROR for r in caplog.records)
        assert any("Transaction rolled back for sales order 200" in r.message and r.levelno == logging.INFO for r in caplog.records)

    def test_rollback_on_invoice_header_creation_failure(self, caplog):
        """Database error inserting invoice in T0090 rolls back delivery."""
        order_repo = CrudRepository('T0012')
        order_repo.create({
            'id': 201,
            'order_number': 'SO-00201',
            'status': 'Shipped',
            'customer_id': 1,
            'warehouse_id': 1,
            'grand_total': 750.0,
            'order_date': '2026-08-20',
        })
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            with patch.object(CrudRepository, 'create', side_effect=Exception("Unique constraint violation on invoice_number")):
                with pytest.raises(RuntimeError, match="Failed to create invoice for sales order 201"):
                    service.update(201, {'status': 'Delivered'})

        assert order_repo.get(201)['status'] == 'Shipped'
        assert any("Failed to create invoice for sales order 201" in r.message for r in caplog.records)

    def test_rollback_on_customer_balance_update_failure(self, caplog):
        """Failure updating customer balance rolls back both invoice creation and order delivery."""
        order_repo = CrudRepository('T0012')
        customer_repo = CrudRepository('T0010')
        order_repo.create({
            'id': 202,
            'order_number': 'SO-00202',
            'status': 'Shipped',
            'customer_id': 1,
            'warehouse_id': 1,
            'grand_total': 300.0,
            'order_date': '2026-08-20',
        })
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.ERROR):
            orig_update = test_store.update

            def failing_update(table_name, id_val, payload, pk='id', conn=None):
                if 't0010' in table_name.lower():
                    raise Exception("Database lock error on T0010")
                return orig_update(table_name, id_val, payload, pk=pk, conn=conn)

            with patch.object(test_store, 'update', side_effect=failing_update):
                with pytest.raises(RuntimeError, match="Failed to update customer balance for customer 1"):
                    service.update(202, {'status': 'Delivered'})

        # Order remains Shipped
        assert order_repo.get(202)['status'] == 'Shipped'
        # Invoice rolled back
        inv_repo = CrudRepository('T0090')
        assert len(inv_repo.list(filters={'sales_order_id': 202})) == 0
        # Customer balance unchanged
        assert customer_repo.get(1)['balance'] == 0.0


# ============================================================================
# 4. Pick List Service Error Handling & Structured Logging Tests
# ============================================================================

class TestPickListServiceExplicitErrorsAndLogging:
    """Tests explicit exceptions and structured logging in PickListService."""

    def test_create_pick_list_sequence_failure_raises_and_logs(self, caplog):
        """Direct creation raises RuntimeError with context when sequence generation fails."""
        pl_repo = CrudRepository('T0101')
        service = PickListService(pl_repo)

        with caplog.at_level(logging.ERROR):
            with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', side_effect=Exception("DB pool timeout")):
                with pytest.raises(RuntimeError, match="Failed to generate pick list number: DB pool timeout"):
                    service.create({'sales_order_id': 5, 'warehouse_id': 1})

        assert any("Failed to generate pick list sequence number: DB pool timeout" in r.message for r in caplog.records)

    def test_create_from_order_nonexistent_order_raises_and_logs(self, caplog):
        """create_from_order raises ValueError when sales order does not exist."""
        service = PickListService()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="Sales order 9999 not found"):
                service.create_from_order(9999)

        assert any("Cannot create pick list: Sales order 9999 not found" in r.message for r in caplog.records)

    def test_create_from_order_no_active_warehouse_raises_and_logs(self, caplog):
        """create_from_order raises ValueError when no warehouse ID provided and no active warehouse exists."""
        order_repo = CrudRepository('T0012')
        wh_repo = CrudRepository('T0008')
        wh_repo.update(1, {'is_active': False})
        order_repo.create({'id': 301, 'order_number': 'SO-00301', 'warehouse_id': None})
        service = PickListService()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="No active warehouse found"):
                service.create_from_order(301)

        assert any("Cannot create pick list for sales order 301: No active warehouse found" in r.message for r in caplog.records)

    def test_create_from_order_empty_lines_logs_warning(self, caplog):
        """create_from_order logs warning when sales order has no lines."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 302, 'order_number': 'SO-00302', 'warehouse_id': 1})
        service = PickListService()

        with caplog.at_level(logging.WARNING):
            with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00302'):
                pl = service.create_from_order(302)
                assert pl['pick_list_number'] == 'PKL-00302'

        assert any("Sales order 302 has no order lines when generating pick list" in r.message for r in caplog.records)

    def test_pick_item_nonexistent_item_raises_and_logs(self, caplog):
        """pick_item raises ValueError if item is not found."""
        service = PickListService()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="Pick list item 9999 not found"):
                service.pick_item(9999, 5)

        assert any("Cannot pick item: Pick list item 9999 not found" in r.message for r in caplog.records)

    def test_pick_item_negative_quantity_raises_and_logs(self, caplog):
        """pick_item raises ValueError on negative picked quantity."""
        pli_repo = CrudRepository('T0102')
        pli_repo.create({'id': 1, 'pick_list_id': 1, 'qty_ordered': 10, 'qty_picked': 0})
        service = PickListService()

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError, match="Quantity picked cannot be negative: -2"):
                service.pick_item(1, -2)

        assert any("Invalid picked quantity -2 for item 1" in r.message for r in caplog.records)

    def test_start_picking_nonexistent_raises_and_logs(self, caplog):
        """start_picking raises ValueError on nonexistent pick list."""
        service = PickListService()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="Pick list 8888 not found"):
                service.start_picking(8888)

        assert any("Cannot start picking: Pick list 8888 not found" in r.message for r in caplog.records)

    def test_start_picking_invalid_status_raises_and_logs(self, caplog):
        """start_picking raises ValueError if status is not Pending."""
        pl_repo = CrudRepository('T0101')
        pl_repo.create({'id': 50, 'pick_list_number': 'PKL-00050', 'status': 'Completed'})
        service = PickListService(pl_repo)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError, match="Pick list status is Completed, expected Pending"):
                service.start_picking(50)

        assert any("Cannot start picking: Pick list 50 status is Completed, expected Pending" in r.message for r in caplog.records)

    @patch('modules.warehouse.services.pick_list_service.release_connection')
    @patch('modules.warehouse.services.pick_list_service.get_connection')
    def test_complete_picking_nonexistent_raises_and_logs(self, mock_get_conn, mock_release, caplog):
        """complete_picking raises ValueError on nonexistent pick list."""
        mock_get_conn.return_value = MagicMock()
        service = PickListService()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="Pick list 7777 not found"):
                service.complete_picking(7777)

        assert any("Cannot complete picking: Pick list 7777 not found" in r.message for r in caplog.records)

    @patch('modules.warehouse.services.pick_list_service.release_connection')
    @patch('modules.warehouse.services.pick_list_service.get_connection')
    def test_complete_picking_unpicked_items_raises_actionable_summary(self, mock_get_conn, mock_release, caplog):
        """complete_picking raises detailed ValueError summarizing all unpicked items."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        pl_repo = CrudRepository('T0101')
        pli_repo = CrudRepository('T0102')
        pl_repo.create({'id': 60, 'pick_list_number': 'PKL-00060', 'status': 'In Progress', 'sales_order_id': 1})
        pli_repo.create({'id': 601, 'pick_list_id': 60, 'product_id': 10, 'product_name': 'Steel Rod', 'qty_ordered': 10, 'qty_picked': 4})
        pli_repo.create({'id': 602, 'pick_list_id': 60, 'product_id': 11, 'product_name': 'Brass Fitting', 'qty_ordered': 5, 'qty_picked': 0})
        service = PickListService(pl_repo)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError) as exc_info:
                service.complete_picking(60)
            err_msg = str(exc_info.value)
            assert "Cannot complete pick list 60" in err_msg
            assert "Item Steel Rod has 4 picked of 10 ordered" in err_msg
            assert "Item Brass Fitting has 0 picked of 5 ordered" in err_msg

        assert any("Cannot complete pick list 60" in r.message for r in caplog.records)

    @patch('modules.warehouse.services.pick_list_service.release_connection')
    @patch('modules.warehouse.services.pick_list_service.get_connection')
    def test_complete_picking_rollback_on_batch_adjust_failure(self, mock_get_conn, mock_release):
        """complete_picking rolls back all changes when a batch adjustment fails mid-transaction."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        pl_repo = CrudRepository('T0101')
        pl_repo.create({'id': 70, 'pick_list_number': 'PKL-00070', 'status': 'In Progress', 'sales_order_id': 1})
        pli_repo = CrudRepository('T0102')
        pli_repo.create({'id': 701, 'pick_list_id': 70, 'product_id': 10, 'product_name': 'Steel Rod',
                         'qty_ordered': 10, 'qty_picked': 10, 'picked_batch_id': 101})
        pli_repo.create({'id': 702, 'pick_list_id': 70, 'product_id': 11, 'product_name': 'Brass Fitting',
                         'qty_ordered': 5, 'qty_picked': 5, 'picked_batch_id': 102})
        service = PickListService(pl_repo)
        adjust_calls = []

        def tracking_adjust(batch_id, qty, conn=None):
            adjust_calls.append(batch_id)
            if len(adjust_calls) == 2:
                raise RuntimeError("Simulated batch adjustment failure")

        service.batch_service.adjustQuantity = tracking_adjust

        with pytest.raises(RuntimeError, match="Simulated batch adjustment failure"):
            service.complete_picking(70)

        assert adjust_calls == [101, 102]
        pl = pl_repo.get(70)
        assert pl['status'] == 'In Progress'
        mock_conn.rollback.assert_called_once_with()
        mock_release.assert_called_once_with(mock_conn)


# ============================================================================
# 5. Sales Service State Transitions & Validation Tests
# ============================================================================

class TestSalesServiceStateTransitionsAndValidation:
    """Tests status transition safety, stock releases, and credit limits."""

    def test_invalid_status_transition_raises_http_400_and_logs_warning(self, caplog):
        """Invalid transition (Draft -> Delivered) raises HTTP 400 and logs warning."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 400, 'order_number': 'SO-00400', 'status': 'Draft', 'customer_id': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(HTTPException) as exc_info:
                service.update(400, {'status': 'Delivered'})
            assert exc_info.value.status_code == 400
            assert "Invalid status transition: Draft -> Delivered" in exc_info.value.detail

        assert order_repo.get(400)['status'] == 'Draft'
        assert any("Invalid status transition attempted for sales order 400: Draft -> Delivered" in r.message for r in caplog.records)

    def test_cancelling_confirmed_order_releases_stock(self, caplog):
        """Cancelling Confirmed order triggers _release_order_stock."""
        order_repo = CrudRepository('T0012')
        line_repo = CrudRepository('T0013')
        order_repo.create({'id': 401, 'order_number': 'SO-00401', 'status': 'Confirmed', 'customer_id': 1, 'warehouse_id': 1})
        line_repo.create({'id': 1, 'sales_order_id': 401, 'product_id': 1, 'qty': 10, 'line_number': 1})
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.INFO):
            with patch.object(StockMovementService, 'release_stock') as mock_release:
                updated = service.update(401, {'status': 'Cancelled'})
                assert updated['status'] == 'Cancelled'
                assert mock_release.called
                mock_release.assert_called_once_with(1, 1, 10, 'sales_order', 401, conn=unittest_mock_any())

        assert order_repo.get(401)['status'] == 'Cancelled'

    def test_order_creation_credit_limit_exceeded_places_on_credit_hold_and_logs(self, caplog):
        """Order creation exceeding customer credit limit is placed on Credit Hold status with reason logged."""
        customer_repo = CrudRepository('T0010')
        customer_repo.update(1, {'credit_limit': 1000.0, 'balance': 800.0})

        order_repo = CrudRepository('T0012')
        service = SalesOrderService(order_repo)

        with caplog.at_level(logging.WARNING):
            order = service.create({
                'customer_id': 1,
                'subtotal': 300.0,
                'tax': 0.0,
                'grand_total': 300.0,
            })
            assert order['status'] == 'Credit Hold'
            assert 'Customer credit limit exceeded' in order['hold_reason']

        assert any("Order creation placed on Credit Hold for customer Acme Global" in r.message for r in caplog.records)


# ============================================================================
# 6. FastAPI HTTP Endpoint Error Propagation & Rollback Integration
# ============================================================================

class TestFastAPIHttpEndpointRollback:
    """Verifies that HTTP endpoints return proper 400/404 errors on document generation failure and rollback."""

    def test_http_confirm_endpoint_rolls_back_and_returns_500_on_document_failure(self):
        """
        POST /api/T0012I/{id}/confirm returns HTTP 500 when document generation fails,
        leaving order in Draft status in database.
        """
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 500, 'order_number': 'SO-00500', 'status': 'Draft', 'customer_id': 1, 'warehouse_id': 1})

        app = create_test_app()
        client = TestClient(app)

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', side_effect=RuntimeError("Sequence lock error")):
            resp = client.post('/api/T0012I/500/confirm')
            assert resp.status_code == 500

        # Order must remain Draft in database
        assert order_repo.get(500)['status'] == 'Draft'

    def test_http_deliver_endpoint_rolls_back_and_returns_500_on_document_failure(self):
        """
        POST /api/T0012I/{id}/deliver returns HTTP 500 when invoice generation fails,
        leaving order in Shipped status in database.
        """
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 501, 'order_number': 'SO-00501', 'status': 'Shipped', 'customer_id': 1, 'warehouse_id': 1, 'grand_total': 250.0})

        app = create_test_app()
        client = TestClient(app)

        with patch('modules.sales.services.sales_service.generate_invoice_number', side_effect=RuntimeError("Sequence seq_invoice_number failed")):
            resp = client.post('/api/T0012I/501/deliver')
            assert resp.status_code == 500

        # Order must remain Shipped in database
        assert order_repo.get(501)['status'] == 'Shipped'

    def test_http_confirm_invalid_status_returns_400(self):
        """Confirming an already Delivered order returns HTTP 400."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 502, 'order_number': 'SO-00502', 'status': 'Delivered'})

        app = create_test_app()
        client = TestClient(app)

        resp = client.post('/api/T0012I/502/confirm')
        assert resp.status_code == 400
        assert "Only Draft or Pending orders can be confirmed" in resp.json()['detail']

    def test_http_deliver_invalid_status_returns_400(self):
        """Delivering a Draft order returns HTTP 400."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 503, 'order_number': 'SO-00503', 'status': 'Draft'})

        app = create_test_app()
        client = TestClient(app)

        resp = client.post('/api/T0012I/503/deliver')
        assert resp.status_code == 400
        assert "Only Shipped orders can be marked as delivered" in resp.json()['detail']

    def test_http_cancel_paid_or_cancelled_returns_400(self):
        """Cancelling a Paid order returns HTTP 400."""
        order_repo = CrudRepository('T0012')
        order_repo.create({'id': 504, 'order_number': 'SO-00504', 'status': 'Paid'})

        app = create_test_app()
        client = TestClient(app)

        resp = client.post('/api/T0012I/504/cancel')
        assert resp.status_code == 400
        assert "Order cannot be cancelled" in resp.json()['detail']

    def test_http_endpoints_order_not_found_returns_404(self):
        """Nonexistent order ID returns HTTP 404 across confirm, deliver, cancel."""
        app = create_test_app()
        client = TestClient(app)

        for endpoint in ['confirm', 'deliver', 'cancel']:
            resp = client.post(f'/api/T0012I/99999/{endpoint}')
            assert resp.status_code == 404
            assert resp.json()['detail'] == 'Order not found'
