"""Unit tests for SQLServerConnector.

Tests connection testing, schema discovery, chunk extraction,
type normalization, and driver fallback / mock capabilities.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
)
from modules.migration.connectors.sqlserver import (
    MockSQLServerEngine,
    SQLServerConnector,
    normalize_sql_type,
)
from modules.migration.models.migration import SQLServerConnectionConfig


def test_normalize_sql_type():
    """Verify raw SQL Server types normalize to standard uppercase types."""
    assert normalize_sql_type("nvarchar(255)") == "VARCHAR"
    assert normalize_sql_type("varchar(max)") == "VARCHAR"
    assert normalize_sql_type("int") == "INTEGER"
    assert normalize_sql_type("tinyint") == "INTEGER"
    assert normalize_sql_type("bigint") == "BIGINT"
    assert normalize_sql_type("bit") == "BOOLEAN"
    assert normalize_sql_type("decimal(18,4)") == "DECIMAL"
    assert normalize_sql_type("money") == "DECIMAL"
    assert normalize_sql_type("datetime2(7)") == "DATETIME"
    assert normalize_sql_type("date") == "DATE"
    assert normalize_sql_type("varbinary(max)") == "BINARY"
    assert normalize_sql_type("uniqueidentifier") == "UUID"
    assert normalize_sql_type("") == "VARCHAR"


def test_sqlserver_connector_init_with_config():
    """Verify connector initializes properly with Pydantic model and dict configs."""
    pydantic_cfg = SQLServerConnectionConfig(
        host="192.168.1.100",
        port=14333,
        database="LegacyFoodPOS",
        user="db_user",
        password="secret_password",
        trust_server_certificate=True,
        schema_name="dbo",
        timeout=15,
    )
    connector = SQLServerConnector(config=pydantic_cfg)
    assert connector.host == "192.168.1.100"
    assert connector.port == 14333
    assert connector.database == "LegacyFoodPOS"
    assert connector.user == "db_user"
    assert connector.password == "secret_password"
    assert connector.trust_server_certificate is True
    assert connector.schema_name == "dbo"
    assert connector.timeout == 15

    # Dict config
    dict_cfg = {
        "host": "localhost",
        "port": 1433,
        "database": "TestDB",
        "user": "sa",
        "password": "pwd",
        "schema_name": "custom_schema",
    }
    connector2 = SQLServerConnector(config=dict_cfg)
    assert connector2.host == "localhost"
    assert connector2.database == "TestDB"
    assert connector2.schema_name == "custom_schema"


def test_sqlserver_connector_odbc_conn_str():
    """Verify ODBC connection string generation."""
    connector = SQLServerConnector(
        host="sql.example.com",
        port=1433,
        database="ERP_2015",
        user="sa",
        password="StrongPassword123!",
        trust_server_certificate=True,
        driver="ODBC Driver 18 for SQL Server",
        timeout=45,
    )
    conn_str = connector._build_odbc_conn_str()
    assert "DRIVER={ODBC Driver 18 for SQL Server}" in conn_str
    assert "SERVER=sql.example.com,1433" in conn_str
    assert "DATABASE=ERP_2015" in conn_str
    assert "UID=sa" in conn_str
    assert "PWD=StrongPassword123!" in conn_str
    assert "TrustServerCertificate=yes" in conn_str
    assert "Connection Timeout=45" in conn_str


def test_sqlserver_connector_mock_engine_testing():
    """Verify connection testing and metadata discovery using MockSQLServerEngine."""
    mock_data = {
        "tbl_Products": [
            {
                "id": 1,
                "code": "PRD-001",
                "name": "Shawarma Sandwich",
                "price": Decimal("15.50"),
                "cost": Decimal("8.00"),
                "is_active": True,
                "created_at": datetime(2023, 1, 1, 10, 0, 0),
            },
            {
                "id": 2,
                "code": "PRD-002",
                "name": "Falafel Plate",
                "price": Decimal("10.00"),
                "cost": Decimal("4.50"),
                "is_active": True,
                "created_at": datetime(2023, 1, 2, 11, 0, 0),
            },
        ],
        "tbl_Customers": [
            {
                "custcode": "CUST-001",
                "name": "Ahmed Ali",
                "phone": "0501234567",
                "balance": Decimal("150.00"),
            },
        ],
    }

    connector = SQLServerConnector(
        database="LegacyRestaurantDB",
        mock_data=mock_data,
    )

    # 1. Test connection
    res = connector.test_connection()
    assert res.success is True
    assert "Successfully connected" in res.message
    assert res.tables_count == 2
    assert "tbl_Products" in res.tables
    assert "tbl_Customers" in res.tables
    assert res.database_name == "LegacyRestaurantDB"

    # 2. Get tables
    tables = connector.get_tables()
    assert len(tables) == 2
    assert "tbl_Products" in tables

    # 3. Get table schema
    schema = connector.get_table_schema("tbl_Products")
    assert schema.table_name == "tbl_Products"
    assert schema.row_count_estimate == 2
    assert "id" in schema.primary_key
    assert len(schema.columns) == 7

    col_names = schema.column_names
    assert "code" in col_names
    assert "price" in col_names

    price_col = schema.get_column("price")
    assert price_col is not None
    assert price_col.data_type == "DECIMAL"

    is_active_col = schema.get_column("is_active")
    assert is_active_col is not None
    assert is_active_col.data_type == "BOOLEAN"

    # 4. Preview table
    preview = connector.preview_table("tbl_Products", limit=1)
    assert len(preview) == 1
    assert preview[0]["code"] == "PRD-001"
    assert preview[0]["price"] == 15.5  # serialized from Decimal to float

    # 5. Extract chunks
    chunks = list(connector.extract_chunks("tbl_Products", chunk_size=1))
    assert len(chunks) == 2
    assert len(chunks[0]) == 1
    assert chunks[0][0]["name"] == "Shawarma Sandwich"
    assert chunks[1][0]["name"] == "Falafel Plate"

    # 6. Extract all
    all_records = connector.extract_all("tbl_Products")
    assert len(all_records) == 2

    # 7. Get row count
    cnt = connector.get_row_count("tbl_Products")
    assert cnt == 2


def test_sqlserver_connector_no_driver_error():
    """Verify that attempting to connect without driver and without mock returns clean error in test_connection."""
    connector = SQLServerConnector(
        host="non-existent-host.local",
        database="NoDriverDB",
    )
    # test_connection should catch and report error gracefully
    res = connector.test_connection()
    assert res.success is False
    assert res.error is not None
    assert "driver" in res.error.lower() or "connect" in res.error.lower()


def test_sqlserver_connector_with_mocked_pyodbc():
    """Verify live query logic and schema discovery when pyodbc driver is mocked."""
    mock_cursor = MagicMock()
    mock_cursor.description = [
        ("id", 1, None, None, None, None, None),
        ("product_name", 2, None, None, None, None, None),
        ("price", 3, None, None, None, None, None),
    ]

    # Mock responses for queries
    def execute_side_effect(sql, params=None):
        sql_str = str(sql).upper()
        if "@@VERSION" in sql_str:
            mock_cursor.fetchone.return_value = ("Microsoft SQL Server 2022", "TestProdDB")
        elif "INFORMATION_SCHEMA.TABLES" in sql_str:
            mock_cursor.fetchall.return_value = [("Items",), ("Orders",)]
        elif "INFORMATION_SCHEMA.COLUMNS" in sql_str:
            mock_cursor.fetchall.return_value = [
                ("id", "int", "NO", None, 10, 0, None, 1),
                ("product_name", "nvarchar", "YES", 200, None, None, None, 2),
                ("price", "money", "YES", None, 19, 4, "0.0", 3),
            ]
        elif "TABLE_CONSTRAINTS" in sql_str:
            mock_cursor.fetchall.return_value = [("id",)]
        elif "REFERENTIAL_CONSTRAINTS" in sql_str:
            mock_cursor.fetchall.return_value = []
        elif "COUNT(*)" in sql_str:
            mock_cursor.fetchone.return_value = (42,)
        elif "SELECT TOP" in sql_str:
            mock_cursor.fetchall.return_value = [
                (1, "Espresso", Decimal("12.00")),
                (2, "Latte", Decimal("16.00")),
            ]
        elif "SELECT *" in sql_str or "SELECT " in sql_str:
            # fetchmany side effect
            mock_cursor.fetchmany.side_effect = [
                [(1, "Espresso", Decimal("12.00")), (2, "Latte", Decimal("16.00"))],
                [],
            ]

    mock_cursor.execute.side_effect = execute_side_effect

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    connector = SQLServerConnector(
        host="localhost",
        database="TestProdDB",
    )
    connector._conn = mock_conn
    connector._is_connected = True
    connector._active_driver = "pyodbc"

    # Test connection
    res = connector.test_connection()
    assert res.success is True
    assert res.database_name == "TestProdDB"
    assert res.tables_count == 2
    assert "Items" in res.tables

    # Test schema discovery
    schema = connector.get_table_schema("Items")
    assert schema.table_name == "Items"
    assert schema.primary_key == ["id"]
    assert len(schema.columns) == 3

    id_col = schema.get_column("id")
    assert id_col is not None
    assert id_col.is_primary_key is True
    assert id_col.data_type == "INTEGER"

    price_col = schema.get_column("price")
    assert price_col is not None
    assert price_col.data_type == "DECIMAL"
    assert price_col.raw_type == "money"

    # Test row count
    cnt = connector.get_row_count("Items")
    assert cnt == 42

    # Test preview
    preview = connector.preview_table("Items", limit=2)
    assert len(preview) == 2
    assert preview[0]["product_name"] == "Espresso"
    assert preview[0]["price"] == 12.0

    # Test chunk streaming
    chunks = list(connector.extract_chunks("Items", chunk_size=2))
    assert len(chunks) == 1
    assert len(chunks[0]) == 2
    assert chunks[0][0]["id"] == 1
    assert chunks[0][1]["id"] == 2


def test_sqlserver_connector_context_manager():
    """Verify connector functions as a context manager."""
    mock_engine = MockSQLServerEngine(
        tables_data={"demo": [{"id": 1, "val": "abc"}]},
    )
    with SQLServerConnector(mock_engine=mock_engine) as conn:
        assert conn.is_connected is True
        tables = conn.get_tables()
        assert "demo" in tables
    assert conn.is_connected is False
