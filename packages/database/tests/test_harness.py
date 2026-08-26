"""
Unit and functional tests for real PostgreSQL DatabaseHarness and mock bypass mechanism.
"""
import os
import threading
from unittest.mock import MagicMock, patch
import pytest

from packages.database.harness import (
    DatabaseHarness,
    get_db_config,
    is_postgres_available,
    get_direct_connection,
    bypass_db_mocks,
    get_shared_harness,
    close_shared_harness,
)
import packages.database.connection as db_conn_module
from packages.database.connection import get_connection, release_connection, db_connection


class TestDatabaseConfig:
    def test_get_db_config_defaults(self, monkeypatch):
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        monkeypatch.delenv("DB_NAME", raising=False)
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        monkeypatch.delenv("DB_SCHEMA", raising=False)
        monkeypatch.delenv("DB_SSLMODE", raising=False)

        cfg = get_db_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 5432
        assert cfg["dbname"] == "nova_erp"
        assert cfg["user"] == "nova"
        assert cfg["password"] == "nova_secret"
        assert cfg["schema"] == "Nova"
        assert cfg["sslmode"] == "prefer"

    def test_get_db_config_custom_env(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "custom-pg-host")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "custom_db")
        monkeypatch.setenv("DB_USER", "custom_user")
        monkeypatch.setenv("DB_PASSWORD", "custom_pass")
        monkeypatch.setenv("DB_SCHEMA", "CustomSchema")
        monkeypatch.setenv("DB_SSLMODE", "require")

        cfg = get_db_config()
        assert cfg["host"] == "custom-pg-host"
        assert cfg["port"] == 5433
        assert cfg["dbname"] == "custom_db"
        assert cfg["user"] == "custom_user"
        assert cfg["password"] == "custom_pass"
        assert cfg["schema"] == "CustomSchema"
        assert cfg["sslmode"] == "require"


class TestPostgresAvailability:
    def test_is_postgres_available_true_when_connects(self):
        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            available = is_postgres_available({"host": "h", "port": 5432, "dbname": "db", "user": "u", "password": "p", "sslmode": "prefer"})
            assert available is True
            mock_connect.assert_called_once()

    def test_is_postgres_available_false_on_connection_error(self):
        with patch("psycopg2.connect", side_effect=Exception("Connection refused")):
            available = is_postgres_available({"host": "invalid-host", "port": 9999, "dbname": "db", "user": "u", "password": "p", "sslmode": "prefer"})
            assert available is False


class TestDatabaseHarnessCore:
    def test_harness_bypass_mocks_restores_mock_pool(self):
        original_pool = db_conn_module._pool
        mock_real_pool = MagicMock(name="real_pool")

        with patch("packages.database.harness.ThreadedConnectionPool", return_value=mock_real_pool):
            harness = DatabaseHarness(config={"host": "localhost", "port": 5432, "dbname": "db", "user": "u", "password": "p", "schema": "Nova", "sslmode": "prefer"})

            assert db_conn_module._pool is original_pool

            with harness.bypass_mocks():
                assert db_conn_module._pool is mock_real_pool

            assert db_conn_module._pool is original_pool

    def test_harness_connection_checkout_and_release(self):
        mock_real_pool = MagicMock(name="real_pool")
        mock_conn = MagicMock(name="conn")
        mock_cursor = MagicMock(name="cursor")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_real_pool.getconn.return_value = mock_conn

        with patch("packages.database.harness.ThreadedConnectionPool", return_value=mock_real_pool):
            harness = DatabaseHarness(config={"host": "localhost", "port": 5432, "dbname": "db", "user": "u", "password": "p", "schema": "Nova", "sslmode": "prefer"})

            with harness.connection() as conn:
                assert conn is mock_conn
                mock_cursor.execute.assert_called_once_with('SET search_path TO "Nova", public;')

            mock_real_pool.putconn.assert_called_once_with(mock_conn, close=False)

    def test_harness_cursor_context_manager_commit_and_rollback(self):
        mock_real_pool = MagicMock(name="real_pool")
        mock_conn = MagicMock(name="conn")
        mock_cursor = MagicMock(name="cursor")
        mock_conn.cursor.return_value = mock_cursor
        mock_real_pool.getconn.return_value = mock_conn

        with patch("packages.database.harness.ThreadedConnectionPool", return_value=mock_real_pool):
            harness = DatabaseHarness(config={"host": "localhost", "port": 5432, "dbname": "db", "user": "u", "password": "p", "schema": "Nova", "sslmode": "prefer"})

            # Successful block commits
            with harness.cursor() as cur:
                assert cur is mock_cursor
            mock_conn.commit.assert_called_once()
            mock_conn.rollback.assert_not_called()

            # Exception block rolls back
            mock_conn.reset_mock()
            with pytest.raises(ValueError, match="query failed"):
                with harness.cursor() as cur:
                    raise ValueError("query failed")
            mock_conn.rollback.assert_called_once()
            mock_conn.commit.assert_not_called()

    def test_harness_execute_query_fetch_variants(self):
        mock_real_pool = MagicMock(name="real_pool")
        mock_conn = MagicMock(name="conn")
        mock_cursor = MagicMock(name="cursor")
        mock_conn.cursor.return_value = mock_cursor
        mock_real_pool.getconn.return_value = mock_conn

        mock_cursor.fetchall.return_value = [("row1",), ("row2",)]
        mock_cursor.fetchone.return_value = ("row1",)
        mock_cursor.rowcount = 42

        with patch("packages.database.harness.ThreadedConnectionPool", return_value=mock_real_pool):
            harness = DatabaseHarness(config={"host": "localhost", "port": 5432, "dbname": "db", "user": "u", "password": "p", "schema": "Nova", "sslmode": "prefer"})

            res_all = harness.execute_query("SELECT * FROM test", fetch="all")
            assert res_all == [("row1",), ("row2",)]

            res_one = harness.execute_query("SELECT * FROM test WHERE id=1", fetch="one")
            assert res_one == ("row1",)

            res_none = harness.execute_query("UPDATE test SET x=1", fetch="none")
            assert res_none == 42


@pytest.mark.integration
@pytest.mark.real_db
class TestDatabaseHarnessRealPostgres:
    """
    Live integration tests executing against real PostgreSQL instance.
    """

    def test_real_postgres_connection_and_search_path(self, real_harness):
        with real_harness.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user, 1 + 1;")
                row = cur.fetchone()
                assert row is not None
                assert row[2] == 2

    def test_real_postgres_mock_bypass_with_global_functions(self, real_harness):
        # Verify that get_connection() inside bypass_mocks returns real connection
        with real_harness.bypass_mocks():
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 40 + 2;")
                    result = cur.fetchone()
                    assert result[0] == 42
            finally:
                release_connection(conn)

    def test_real_postgres_db_connection_context_manager(self, real_harness):
        with real_harness.bypass_mocks():
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 'harness_working' AS status;")
                    res = cur.fetchone()
                    assert res[0] == "harness_working"

    def test_real_postgres_concurrent_threads_pool_safety(self, real_harness):
        results = []
        errors = []

        def worker(thread_id):
            try:
                with real_harness.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT %s, pg_backend_pid();", (thread_id,))
                        row = cur.fetchone()
                        results.append((thread_id, row[0]))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(results) == 20
        assert sorted([r[0] for r in results]) == list(range(20))
