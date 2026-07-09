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

    def test_sets_statement_timeout(self, mock_db):
        conn, cur = mock_db
        cur.fetchmany.return_value = [{"id": 1}]
        _execute_read_query("SELECT 1")
        timeout_call = cur.execute.call_args_list[0]
        assert "statement_timeout" in timeout_call[0][0]

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
