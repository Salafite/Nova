import re
import psycopg2
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


SCHEMA = "Nova"


def register_tools():
    register_tool(
        Tool(name="list_tables", description="List all tables in the Nova schema", input_schema={
            "type": "object",
            "properties": {},
        }),
        _list_tables,
    )
    register_tool(
        Tool(name="describe_table", description="Get column information for a table", input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name (e.g., T0001, T0001I, products)"},
            },
            "required": ["table_name"],
        }),
        _describe_table,
    )
    register_tool(
        Tool(name="execute_read_query", description="Execute a read-only SQL query (SELECT only)", input_schema={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT SQL query to execute"},
                "limit": {"type": "integer", "description": "Max rows to return (default 100)"},
            },
            "required": ["sql"],
        }),
        _execute_read_query,
    )
    register_resource(
        Resource(uri="nova://schema", name="Full Schema", description="All tables and columns in the Nova schema"),
        _get_schema,
    )


def _list_tables():
    conn = get_connection()
    try:
        sql = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (SCHEMA,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def _describe_table(table_name: str):
    conn = get_connection()
    try:
        sql = """
            SELECT column_name, data_type, is_nullable, character_maximum_length,
                   column_default, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (SCHEMA, table_name.lower()))
            rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                return {"error": f"Table '{table_name}' not found in schema '{SCHEMA}'"}
            return rows
    finally:
        release_connection(conn)


def _execute_read_query(sql: str, limit: int = 100):
    sanitized = sql.strip().lower()
    if not sanitized.startswith("select") or "insert" in sanitized or "update" in sanitized or "delete" in sanitized or "drop" in sanitized or "alter" in sanitized or "create" in sanitized or "truncate" in sanitized or "grant" in sanitized:
        raise ValueError("Only SELECT queries are allowed")
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET LOCAL statement_timeout = '10s'")
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchmany(limit)]
            return rows
    finally:
        release_connection(conn)


def _get_schema():
    conn = get_connection()
    try:
        sql = """
            SELECT c.table_name, c.column_name, c.data_type, c.is_nullable,
                   c.character_maximum_length, c.ordinal_position
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            WHERE t.table_schema = %s
            ORDER BY c.table_name, c.ordinal_position
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (SCHEMA,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    server = McpServer(name="database-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()
