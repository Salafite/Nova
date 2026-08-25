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


def test_sqlserver_connector_discover_schema_with_filter():
    """Verify discover_schema respects table_filter and returns all schemas."""
    mock_data = {
        "tbl_Products": [{"id": 1, "name": "Item A"}],
        "tbl_Customers": [{"custcode": "C1", "name": "Cust A"}],
        "tbl_Orders": [{"order_id": 101, "total": 50.0}],
    }
    connector = SQLServerConnector(mock_data=mock_data)

    # Discover all
    all_discovery = connector.discover_schema()
    assert all_discovery["success"] is True
    assert all_discovery["tables_count"] == 3
    assert len(all_discovery["schemas"]) == 3
    assert "tbl_Products" in all_discovery["schemas"]

    # Discover filtered
    filtered_discovery = connector.discover_schema(table_filter=["tbl_products", "tbl_orders"])
    assert filtered_discovery["success"] is True
    assert filtered_discovery["tables_count"] == 2
    assert "tbl_Products" in filtered_discovery["schemas"]
    assert "tbl_Orders" in filtered_discovery["schemas"]
    assert "tbl_Customers" not in filtered_discovery["schemas"]


def test_sqlserver_connector_filtering_and_projection():
    """Verify extract_chunks and preview_table support filter conditions and column projection."""
    mock_data = {
        "items": [
            {"id": 1, "sku": "A101", "name": "Item 1", "price": Decimal("10.00"), "category": "Food"},
            {"id": 2, "sku": "A102", "name": "Item 2", "price": Decimal("20.00"), "category": "Drink"},
            {"id": 3, "sku": "A103", "name": "Item 3", "price": Decimal("30.00"), "category": "Food"},
            {"id": 4, "sku": "A104", "name": "Item 4", "price": Decimal("40.00"), "category": "Drink"},
        ]
    }
    connector = SQLServerConnector(mock_data=mock_data)

    # Dict filter
    food_chunks = list(connector.extract_chunks("items", filter_condition={"category": "Food"}, columns=["sku", "price"]))
    assert len(food_chunks) == 1
    assert len(food_chunks[0]) == 2
    assert food_chunks[0][0] == {"sku": "A101", "price": 10.0}
    assert food_chunks[0][1] == {"sku": "A103", "price": 30.0}

    # Callable filter
    expensive_chunks = list(connector.extract_chunks("items", filter_condition=lambda r: r.get("price", 0) > 25))
    assert len(expensive_chunks) == 1
    assert len(expensive_chunks[0]) == 2
    assert expensive_chunks[0][0]["id"] == 3
    assert expensive_chunks[0][1]["id"] == 4

    # Preview with column projection
    preview = connector.preview_table("items", limit=2, columns=["sku", "name"])
    assert len(preview) == 2
    assert list(preview[0].keys()) == ["sku", "name"]
    assert preview[0]["sku"] == "A101"


def test_sqlserver_connector_pymssql_driver_mock():
    """Verify connector fallback to pymssql when pyodbc is not installed."""
    mock_pymssql = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"": "Microsoft SQL Server 2019", "database": "LegacyDB"}
    mock_cursor.fetchall.return_value = [{"TABLE_NAME": "tbl_Items"}]
    mock_conn.cursor.return_value = mock_cursor
    mock_pymssql.connect.return_value = mock_conn

    with patch.dict("sys.modules", {"pyodbc": None, "pymssql": mock_pymssql}):
        connector = SQLServerConnector(
            host="sql.local",
            database="LegacyDB",
            user="sa",
            password="pwd",
        )
        res = connector.test_connection()
        assert res.success is True
        assert res.details.get("driver") == "pymssql"
        assert "tbl_Items" in res.tables


def test_sqlserver_connector_foreign_key_discovery():
    """Verify foreign key relationships are captured in TableSchema."""
    mock_schemas = {
        "order_items": TableSchema(
            table_name="order_items",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnSchema(
                    name="order_id",
                    data_type="INTEGER",
                    is_foreign_key=True,
                    foreign_table="orders",
                    foreign_column="id",
                ),
                ColumnSchema(
                    name="product_id",
                    data_type="INTEGER",
                    is_foreign_key=True,
                    foreign_table="products",
                    foreign_column="id",
                ),
            ],
            primary_key=["id"],
            foreign_keys=[
                {"from_column": "order_id", "to_table": "orders", "to_column": "id"},
                {"from_column": "product_id", "to_table": "products", "to_column": "id"},
            ],
            row_count_estimate=50,
        )
    }

    connector = SQLServerConnector(
        database="StoreDB",
        mock_schemas=mock_schemas,
    )

    schema = connector.get_table_schema("order_items")
    assert schema.table_name == "order_items"
    assert len(schema.foreign_keys) == 2
    assert schema.get_column("order_id").is_foreign_key is True
    assert schema.get_column("order_id").foreign_table == "orders"
    assert schema.get_column("product_id").foreign_column == "id"

