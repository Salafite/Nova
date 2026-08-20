import pytest
from unittest.mock import patch, MagicMock
from packages.mcp.servers.database_mcp import (
    _list_tables, _describe_table, _execute_read_query, _get_schema, register_tools,
)


MOCK_ROWS = [{"table_name": "T0001", "table_type": "BASE TABLE"}]
MOCK_COLS = [{"column_name": "id", "data_type": "integer", "is_nullable": "NO",
              "character_maximum_length": None, "ordinal_position": 1}]


@pytest.fixture
def mock_db():
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = MOCK_ROWS
    cur.fetchmany.return_value = MOCK_COLS
    conn.cursor.return_value.__enter__.return_value = cur
    with patch("packages.mcp.servers.database_mcp.get_connection", return_value=conn):
        with patch("packages.mcp.servers.database_mcp.release_connection"):
            yield conn, cur


class TestListTables:
    def test_returns_tables_from_db(self, mock_db):
        conn, cur = mock_db
        result = _list_tables()
        assert result == MOCK_ROWS
        call_sql = cur.execute.call_args[0][0]
        assert "information_schema.tables" in call_sql

    def test_releases_connection(self, mock_db):
        conn, cur = mock_db
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            _list_tables()
            release.assert_called_once_with(conn)


class TestDescribeTable:
    def test_returns_columns(self, mock_db):
        conn, cur = mock_db
        cur.fetchall.return_value = MOCK_COLS
        result = _describe_table("T0001")
        assert result == MOCK_COLS
        assert cur.execute.call_args[0][1] == ("Nova", "t0001")

    def test_returns_error_on_unknown_table(self, mock_db):
        conn, cur = mock_db
        cur.fetchall.return_value = []
        result = _describe_table("UNKNOWN")
        assert "error" in result

    def test_releases_connection(self, mock_db):
        conn, cur = mock_db
        cur.fetchall.return_value = MOCK_COLS
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            _describe_table("T0001")
            release.assert_called_once_with(conn)


class TestExecuteReadQuery:
    def test_select_query_returns_results(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 1, "name": "test"}]
        result = _execute_read_query("SELECT * FROM products", limit=100)
        assert result == [{"id": 1, "name": "test"}]

    def test_sandboxed_transaction_setup(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 1}]
        _execute_read_query("SELECT 1")
        executed_calls = [call[0][0] for call in cur.execute.call_args_list]
        assert "SET TRANSACTION READ ONLY" in executed_calls
        assert "SET LOCAL ROLE nova_readonly" in executed_calls
        assert "SET LOCAL statement_timeout = '5s'" in executed_calls
        assert "SELECT 1" in executed_calls
        conn.commit.assert_called_once()

    def test_rejects_non_select(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("DROP TABLE products")

    def test_rejects_insert(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("INSERT INTO products VALUES (1)")

    def test_rejects_update(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("UPDATE products SET name='x'")

    def test_rejects_delete(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("DELETE FROM products")

    def test_rejects_create(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("CREATE TABLE x (id int)")

    def test_rejects_alter(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("ALTER TABLE products ADD COLUMN x int")

    def test_rejects_truncate(self, mock_db):
        conn, cur = mock_db
        with pytest.raises(ValueError, match="Only SELECT"):
            _execute_read_query("TRUNCATE products")

    def test_allows_queries_with_update_and_write_keywords_in_columns(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 1, "update_number": 2, "updated_at": "2026-01-01"}]
        result = _execute_read_query("SELECT id, update_number, updated_at FROM t0021 WHERE updated_by = 1")
        assert result == [{"id": 1, "update_number": 2, "updated_at": "2026-01-01"}]

    def test_allows_queries_with_keywords_in_string_literals(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 5, "description": "Need to update stock and create new order"}]
        result = _execute_read_query("SELECT id, description FROM products WHERE description LIKE '%update%'")
        assert result == [{"id": 5, "description": "Need to update stock and create new order"}]

    def test_allows_with_cte_and_explain_queries(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"total": 42}]
        result = _execute_read_query("WITH cte AS (SELECT count(*) as total FROM t0001) SELECT total FROM cte")
        assert result == [{"total": 42}]

        explain_result = _execute_read_query("EXPLAIN SELECT * FROM t0001")
        assert explain_result == [{"total": 42}]

    def test_insufficient_privilege_error_handling(self, mock_db):
        conn, cur = mock_db
        from psycopg2 import errors
        cur.execute.side_effect = [None, None, None, errors.InsufficientPrivilege("permission denied for column password_hash")]
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            result = _execute_read_query("SELECT password_hash FROM t0021")
            assert "error" in result
            assert "Permission denied" in result["error"]
            conn.rollback.assert_called()
            release.assert_called_once_with(conn)

    def test_readonly_transaction_error_handling(self, mock_db):
        conn, cur = mock_db
        from psycopg2 import errors
        cur.execute.side_effect = [None, None, None, errors.ReadOnlySqlTransaction("cannot execute INSERT in a read-only transaction")]
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            result = _execute_read_query("SELECT * FROM products")
            assert "error" in result
            assert "Read-only transaction violation" in result["error"]
            conn.rollback.assert_called()
            release.assert_called_once_with(conn)

    def test_query_canceled_timeout_error_handling(self, mock_db):
        conn, cur = mock_db
        from psycopg2 import errors
        cur.execute.side_effect = [None, None, None, errors.QueryCanceled("canceling statement due to statement timeout")]
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            result = _execute_read_query("SELECT pg_sleep(10)")
            assert "error" in result
            assert "Query canceled" in result["error"]
            conn.rollback.assert_called()
            release.assert_called_once_with(conn)

    def test_generic_database_error_handling(self, mock_db):
        conn, cur = mock_db
        import psycopg2
        cur.execute.side_effect = [None, None, None, psycopg2.DatabaseError("syntax error at or near 'FORM'")]
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            result = _execute_read_query("SELECT * FORM products")
            assert "error" in result
            assert "Database error" in result["error"]
            conn.rollback.assert_called()
            release.assert_called_once_with(conn)

    def test_releases_connection(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 1}]
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            _execute_read_query("SELECT 1")
            release.assert_called_once_with(conn)


class TestGetSchema:
    def test_returns_all_columns(self, mock_db):
        conn, cur = mock_db
        cur.fetchall.return_value = [
            {"table_name": "T0001", "column_name": "id", "data_type": "integer",
             "is_nullable": "NO", "character_maximum_length": None, "ordinal_position": 1}
        ]
        result = _get_schema()
        assert len(result) == 1
        assert result[0]["table_name"] == "T0001"

    def test_releases_connection(self, mock_db):
        conn, cur = mock_db
        with patch("packages.mcp.servers.database_mcp.release_connection") as release:
            _get_schema()
            release.assert_called_once_with(conn)


class TestRegisterTools:
    def test_register_tools_clears_and_registers(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()
        register_tools()
        tool_names = [t.name for t in registry.get_tools()]
        assert "list_tables" in tool_names
        assert "describe_table" in tool_names
        assert "execute_read_query" in tool_names
        resource_uris = [r.uri for r in registry.list_resources()]
        assert "nova://schema" in resource_uris
