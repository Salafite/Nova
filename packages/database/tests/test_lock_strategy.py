"""
Unit tests for packages.database.lock_strategy module.
"""
from unittest.mock import MagicMock, patch
import pytest
from packages.database.lock_strategy import (
    sort_lock_keys,
    lock_rows_by_ids,
    lock_rows_by_composite_keys,
)
from modules.core.context import tenant_context


class TestSortLockKeys:
    def test_empty_or_none_input(self):
        assert sort_lock_keys([]) == []
        assert sort_lock_keys(None) == []

    def test_integer_ids_sorted_and_deduplicated(self):
        result = sort_lock_keys([10, 2, 5, 2, 10, 1])
        assert result == [1, 2, 5, 10]

    def test_string_keys_sorted_and_deduplicated(self):
        result = sort_lock_keys(['sku_c', 'sku_a', 'sku_b', 'sku_a'])
        assert result == ['sku_a', 'sku_b', 'sku_c']

    def test_composite_tuples_sorted_and_deduplicated(self):
        tuples = [(10, 2), (5, 1), (10, 1), (5, 1)]
        result = sort_lock_keys(tuples)
        assert result == [(5, 1), (10, 1), (10, 2)]


class TestLockRowsByIds:
    def test_empty_ids_returns_empty_list(self):
        mock_conn = MagicMock()
        assert lock_rows_by_ids(mock_conn, 't0003', 'id', []) == []

    def test_invalid_table_or_pk_identifier_raises_value_error(self):
        mock_conn = MagicMock()
        with pytest.raises(ValueError, match="Invalid table or column identifier"):
            lock_rows_by_ids(mock_conn, 't0003; DROP TABLE t0003;', 'id', [1, 2])

        with pytest.raises(ValueError, match="Invalid table or column identifier"):
            lock_rows_by_ids(mock_conn, 't0003', 'id" OR "1"="1', [1, 2])

    def test_locks_rows_in_sorted_pk_asc_order_without_tenant(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1}, {'id': 5}, {'id': 10}]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        res = lock_rows_by_ids(mock_conn, 't0003', 'id', [10, 1, 5, 1])

        assert res == [{'id': 1}, {'id': 5}, {'id': 10}]
        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        assert 'SELECT * FROM "Nova"."t0003"' in sql
        assert 'WHERE "id" IN (%s, %s, %s)' in sql
        assert 'ORDER BY "id" ASC FOR UPDATE' in sql
        assert params == (1, 5, 10)

    def test_locks_rows_with_active_tenant_context(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 2, 'business_id': 42}]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with tenant_context(42):
            res = lock_rows_by_ids(mock_conn, 't0003', 'id', [2])

        sql, params = mock_cursor.execute.call_args[0]
        assert '"business_id" = %s' in sql
        assert 'ORDER BY "id" ASC FOR UPDATE' in sql
        assert params == (2, 42)


class TestLockRowsByCompositeKeys:
    def test_empty_key_tuples_returns_empty_list(self):
        mock_conn = MagicMock()
        assert lock_rows_by_composite_keys(mock_conn, 't0009', ('product_id', 'warehouse_id'), []) == []

    def test_invalid_composite_column_identifier_raises_value_error(self):
        mock_conn = MagicMock()
        with pytest.raises(ValueError, match="Invalid column identifier"):
            lock_rows_by_composite_keys(
                mock_conn, 't0009', ('product_id', 'bad col;'), [(1, 1)]
            )

    def test_locks_composite_rows_in_sorted_order(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'product_id': 5, 'warehouse_id': 1}]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        tuples = [(10, 2), (5, 1), (10, 1)]
        res = lock_rows_by_composite_keys(mock_conn, 't0009', ('product_id', 'warehouse_id'), tuples)

        sql, params = mock_cursor.execute.call_args[0]
        assert 'WHERE ("product_id", "warehouse_id") IN ((%s, %s), (%s, %s), (%s, %s))' in sql
        assert 'ORDER BY "product_id" ASC, "warehouse_id" ASC FOR UPDATE' in sql
        # Sorted tuples: (5, 1), (10, 1), (10, 2)
        assert params == [5, 1, 10, 1, 10, 2]
