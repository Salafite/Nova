import os
from unittest.mock import MagicMock, patch
import pytest
from psycopg2.pool import PoolError

import packages.database.connection as db_conn_module
from packages.database.connection import (
    get_connection,
    release_connection,
    db_connection,
)


@pytest.fixture
def mock_pool():
    with patch.object(db_conn_module, "_pool") as mock:
        yield mock


class TestGetConnection:
    def test_get_connection_success(self, mock_pool):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        conn = get_connection()

        assert conn is mock_conn
        mock_pool.getconn.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SET search_path TO Nova")
        mock_pool.putconn.assert_not_called()

    def test_get_connection_with_custom_schema(self, mock_pool, monkeypatch):
        monkeypatch.setenv("DB_SCHEMA", "CustomTenant")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        conn = get_connection()

        assert conn is mock_conn
        mock_cursor.execute.assert_called_once_with("SET search_path TO CustomTenant")

    def test_failed_search_path_releases_connection_back_to_pool(self, mock_pool):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("syntax error in search_path")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        with pytest.raises(Exception, match="syntax error in search_path"):
            get_connection()

        mock_pool.getconn.assert_called_once()
        # Ensure connection was safely returned to pool despite error
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch("time.sleep", return_value=None)
    def test_transient_error_retries_and_puts_back_intermediate_connections(
        self, mock_sleep, mock_pool
    ):
        conn1 = MagicMock(name="conn1")
        cursor1 = MagicMock()
        cursor1.execute.side_effect = Exception("server closed unexpectedly during init")
        conn1.cursor.return_value.__enter__.return_value = cursor1

        conn2 = MagicMock(name="conn2")
        cursor2 = MagicMock()
        cursor2.execute.side_effect = Exception("connection timeout error")
        conn2.cursor.return_value.__enter__.return_value = cursor2

        conn3 = MagicMock(name="conn3")
        cursor3 = MagicMock()
        conn3.cursor.return_value.__enter__.return_value = cursor3

        mock_pool.getconn.side_effect = [conn1, conn2, conn3]

        result_conn = get_connection()

        assert result_conn is conn3
        assert mock_pool.getconn.call_count == 3
        # Both failing intermediate connections must be returned to pool
        assert mock_pool.putconn.call_count == 2
        mock_pool.putconn.assert_any_call(conn1)
        mock_pool.putconn.assert_any_call(conn2)
        assert mock_sleep.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_transient_error_exhausts_retries_and_releases_all(
        self, mock_sleep, mock_pool
    ):
        conns = [MagicMock(name=f"conn{i}") for i in range(10)]
        for conn in conns:
            cursor = MagicMock()
            cursor.execute.side_effect = Exception("connection closed unexpectedly")
            conn.cursor.return_value.__enter__.return_value = cursor

        mock_pool.getconn.side_effect = conns

        with pytest.raises(Exception, match="closed unexpectedly"):
            get_connection()

        assert mock_pool.getconn.call_count == 10
        assert mock_pool.putconn.call_count == 10
        for conn in conns:
            mock_pool.putconn.assert_any_call(conn)

    def test_pool_exhaustion_raises_pool_error(self, mock_pool):
        mock_pool.getconn.side_effect = PoolError("connection pool exhausted")

        with pytest.raises(PoolError, match="connection pool exhausted"):
            get_connection()

        mock_pool.putconn.assert_not_called()


class TestReleaseConnection:
    def test_release_valid_connection(self, mock_pool):
        mock_conn = MagicMock()
        release_connection(mock_conn)
        mock_pool.putconn.assert_called_once_with(mock_conn, close=False)

    def test_release_none_connection(self, mock_pool):
        release_connection(None)
        mock_pool.putconn.assert_not_called()

    def test_release_with_close_discards_connection(self, mock_pool):
        mock_conn = MagicMock()
        release_connection(mock_conn, close=True)
        mock_pool.putconn.assert_called_once_with(mock_conn, close=True)


class TestDbConnectionContextManager:
    def test_db_connection_success(self, mock_pool):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        with db_connection() as conn:
            assert conn is mock_conn
            mock_pool.putconn.assert_not_called()

        mock_pool.putconn.assert_called_once_with(mock_conn, close=False)

    def test_db_connection_exception_in_context(self, mock_pool):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn

        with pytest.raises(RuntimeError, match="error during query execution"):
            with db_connection() as conn:
                assert conn is mock_conn
                raise RuntimeError("error during query execution")

        mock_pool.putconn.assert_called_once_with(mock_conn, close=False)
