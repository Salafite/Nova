"""Unit tests for Connector Factory and Registry (modules/migration/connectors/factory.py)."""

from typing import Any, Dict, Iterator, List, Optional
import pytest
from pydantic import BaseModel

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
)
from modules.migration.connectors.csv_dump import CsvDumpConnector
from modules.migration.connectors.factory import (
    ConnectorRegistration,
    create_connector_from_config,
    get_connector,
    get_connector_class,
    is_supported_connector,
    list_supported_connectors,
    normalize_source_type,
    register_connector,
    unregister_connector,
    validate_connection_params,
)
from modules.migration.connectors.sqlserver import (
    MockSQLServerEngine,
    SQLServerConnector,
)
from modules.migration.models.migration import (
    ConnectorConfig,
    CsvDumpConnectionConfig,
    SQLServerConnectionConfig,
)


class CustomTestConnector(BaseConnector):
    """Custom connector for testing dynamic registration in the factory registry."""

    def __init__(self, endpoint_url: str = "http://localhost:8000", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.endpoint_url = endpoint_url

    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(
            success=True,
            message="Connected to Custom Test Endpoint",
            database_name="CustomDB",
        )

    def get_tables(self) -> List[str]:
        return ["custom_items", "custom_orders"]

    def get_table_schema(self, table_name: str) -> TableSchema:
        return TableSchema(
            table_name=table_name,
            columns=[
                ColumnSchema(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnSchema(name="name", data_type="VARCHAR"),
            ],
            primary_key=["id"],
        )

    def get_row_count(self, table_name: str, filter_condition: Optional[Any] = None) -> int:
        return 10

    def preview_table(
        self, table_name: str, limit: int = 100, columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        return [{"id": 1, "name": "Item 1"}]

    def extract_chunks(
        self,
        table_name: str,
        chunk_size: int = 1000,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
        order_by: Optional[str] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        yield [{"id": 1, "name": "Item 1"}]


class CustomTestConfig(BaseModel):
    endpoint_url: str = "http://localhost:8000"
    api_key: Optional[str] = None


def test_list_supported_connectors():
    """Verify default registered connectors are returned with complete metadata."""
    connectors = list_supported_connectors()
    assert len(connectors) >= 2

    source_types = [c["source_type"] for c in connectors]
    assert "sqlserver" in source_types
    assert "csv_dump" in source_types

    sqlserver_info = next(c for c in connectors if c["source_type"] == "sqlserver")
    assert sqlserver_info["is_database"] is True
    assert "mssql" in sqlserver_info["aliases"]
    assert "database" in sqlserver_info["required_params"]
    assert sqlserver_info["default_port"] == 1433

    csv_info = next(c for c in connectors if c["source_type"] == "csv_dump")
    assert csv_info["is_database"] is False
    assert "csv" in csv_info["aliases"]
    assert "zip" in csv_info["aliases"]


def test_normalize_source_type_and_aliases():
    """Verify alias normalization and case/whitespace tolerance."""
    assert normalize_source_type("sqlserver") == "sqlserver"
    assert normalize_source_type("SQLSERVER") == "sqlserver"
    assert normalize_source_type(" mssql ") == "sqlserver"
    assert normalize_source_type("sql_server") == "sqlserver"
    assert normalize_source_type("ms_sql") == "sqlserver"

    assert normalize_source_type("csv_dump") == "csv_dump"
    assert normalize_source_type("CSV") == "csv_dump"
    assert normalize_source_type("dump") == "csv_dump"
    assert normalize_source_type("zip") == "csv_dump"
    assert normalize_source_type("csv_directory") == "csv_dump"

    assert normalize_source_type("unknown_db") == "unknown_db"
    assert normalize_source_type("") == ""


def test_is_supported_connector():
    """Verify support check for built-in and alias identifiers."""
    assert is_supported_connector("sqlserver") is True
    assert is_supported_connector("mssql") is True
    assert is_supported_connector("csv_dump") is True
    assert is_supported_connector("csv") is True
    assert is_supported_connector("non_existent_type") is False
    assert is_supported_connector("") is False


def test_get_connector_class():
    """Verify retrieving connector class by source type and aliases."""
    assert get_connector_class("sqlserver") is SQLServerConnector
    assert get_connector_class("mssql") is SQLServerConnector
    assert get_connector_class("csv_dump") is CsvDumpConnector
    assert get_connector_class("csv") is CsvDumpConnector

    with pytest.raises(ValueError, match="Unsupported connector source_type"):
        get_connector_class("oracle_erp")


def test_get_connector_sqlserver_instantiation():
    """Verify instantiating SQLServerConnector with various config shapes."""
    # 1. Direct kwargs
    conn1 = get_connector("sqlserver", database="LegacyDB", host="db.local", port=1433)
    assert isinstance(conn1, SQLServerConnector)
    assert conn1.database == "LegacyDB"
    assert conn1.host == "db.local"

    # 2. Using alias
    conn2 = get_connector("mssql", database="AliasDB")
    assert isinstance(conn2, SQLServerConnector)
    assert conn2.database == "AliasDB"

    # 3. Using SQLServerConnectionConfig model
    pydantic_cfg = SQLServerConnectionConfig(
        host="192.168.1.50",
        port=14330,
        database="ProductionLegacy",
        user="db_user",
        password="secret_password",
    )
    conn3 = get_connector("sqlserver", config=pydantic_cfg)
    assert isinstance(conn3, SQLServerConnector)
    assert conn3.host == "192.168.1.50"
    assert conn3.port == 14330
    assert conn3.database == "ProductionLegacy"
    assert conn3.user == "db_user"

    # 4. Using generic ConnectorConfig model
    wrapper_cfg = ConnectorConfig(
        source_type="sqlserver",
        sqlserver=SQLServerConnectionConfig(database="WrappedDB", host="db.wrapped"),
    )
    conn4 = get_connector(config=wrapper_cfg)
    assert isinstance(conn4, SQLServerConnector)
    assert conn4.database == "WrappedDB"
    assert conn4.host == "db.wrapped"


def test_get_connector_csv_dump_instantiation():
    """Verify instantiating CsvDumpConnector with in-memory files and Pydantic configs."""
    # 1. In-memory files via kwargs
    in_memory = {"products.csv": "id,name,price\n1,Burger,9.99\n"}
    conn1 = get_connector("csv_dump", in_memory_files=in_memory)
    assert isinstance(conn1, CsvDumpConnector)
    tables = conn1.get_tables()
    assert "products" in tables

    # 2. Using alias
    conn2 = get_connector("csv", in_memory_files=in_memory)
    assert isinstance(conn2, CsvDumpConnector)
    assert "products" in conn2.get_tables()

    # 3. Using CsvDumpConnectionConfig model
    cfg = CsvDumpConnectionConfig(dump_path="/data/csv_exports", delimiter=";")
    conn3 = get_connector("csv_dump", config=cfg)
    assert isinstance(conn3, CsvDumpConnector)
    assert conn3.dump_path == "/data/csv_exports"
    assert conn3.delimiter == ";"

    # 4. Using generic ConnectorConfig model
    wrapper = ConnectorConfig(
        source_type="csv_dump",
        csv_dump=CsvDumpConnectionConfig(delimiter="\t", encoding="utf-8"),
    )
    conn4 = get_connector(config=wrapper)
    assert isinstance(conn4, CsvDumpConnector)
    assert conn4.delimiter == "\t"
    assert conn4.encoding == "utf-8"


def test_get_connector_error_handling():
    """Verify missing or invalid source_type raises descriptive ValueError."""
    with pytest.raises(ValueError, match="source_type is required"):
        get_connector()

    with pytest.raises(ValueError, match="Unsupported connector source_type"):
        get_connector("invalid_source_123")


def test_create_connector_from_config():
    """Verify create_connector_from_config helper function."""
    # From ConnectorConfig
    cfg = ConnectorConfig(
        source_type="sqlserver",
        sqlserver=SQLServerConnectionConfig(database="FromConfigDB"),
    )
    conn1 = create_connector_from_config(cfg)
    assert isinstance(conn1, SQLServerConnector)
    assert conn1.database == "FromConfigDB"

    # From dictionary
    dict_cfg = {"source_type": "csv_dump", "delimiter": "|"}
    conn2 = create_connector_from_config(dict_cfg)
    assert isinstance(conn2, CsvDumpConnector)
    assert conn2.delimiter == "|"

    # Invalid input
    with pytest.raises(TypeError, match="Expected ConnectorConfig or dict"):
        create_connector_from_config(12345)  # type: ignore


def test_validate_connection_params():
    """Verify validation of connection parameters for various connector types."""
    # 1. Valid SQL Server params
    res_sql_valid = validate_connection_params(
        "sqlserver",
        {"host": "localhost", "port": 1433, "database": "LegacyDB", "user": "sa"},
    )
    assert res_sql_valid["valid"] is True
    assert len(res_sql_valid["errors"]) == 0
    assert res_sql_valid["cleaned_params"]["database"] == "LegacyDB"

    # 2. Invalid SQL Server params (missing database)
    res_sql_invalid = validate_connection_params("sqlserver", {"host": "localhost", "port": 1433})
    assert res_sql_invalid["valid"] is False
    assert any("database" in err.lower() for err in res_sql_invalid["errors"])

    # 3. Invalid SQL Server params (invalid port range)
    res_sql_port = validate_connection_params(
        "sqlserver", {"database": "DB", "port": 999999}
    )
    assert res_sql_port["valid"] is False
    assert any("port" in err.lower() for err in res_sql_port["errors"])

    # 4. raise_on_error behavior
    with pytest.raises(ValueError, match="Connection parameter validation failed"):
        validate_connection_params("sqlserver", {"host": "localhost"}, raise_on_error=True)

    # 5. Unsupported connector validation
    res_unsupported = validate_connection_params("unsupported_source", {})
    assert res_unsupported["valid"] is False
    assert "Unsupported connector source_type" in res_unsupported["errors"][0]

    with pytest.raises(ValueError, match="Unsupported connector source_type"):
        validate_connection_params("unsupported_source", {}, raise_on_error=True)

    # 6. Valid CSV Dump params
    res_csv = validate_connection_params(
        "csv_dump", {"dump_path": "/tmp/exports", "delimiter": ","}
    )
    assert res_csv["valid"] is True


def test_dynamic_connector_registration_and_unregistration():
    """Verify registering a third-party custom connector dynamically and unregistering it."""
    test_type = "custom_test"
    register_connector(
        source_type=test_type,
        connector_class=CustomTestConnector,
        display_name="Custom Test Data Connector",
        config_model=CustomTestConfig,
        description="Connects to custom legacy REST endpoints",
        aliases=["custom_api", "test_api"],
        is_database=False,
        required_params=["endpoint_url"],
    )

    try:
        # Verify registered
        assert is_supported_connector(test_type) is True
        assert is_supported_connector("custom_api") is True
        assert is_supported_connector("test_api") is True

        cls = get_connector_class("custom_api")
        assert cls is CustomTestConnector

        # Instantiation via factory
        conn = get_connector("custom_api", endpoint_url="http://legacy.internal:9000")
        assert isinstance(conn, CustomTestConnector)
        assert conn.endpoint_url == "http://legacy.internal:9000"

        # Test connection execution
        test_res = conn.test_connection()
        assert test_res.success is True
        assert "Custom Test Endpoint" in test_res.message
        assert conn.get_tables() == ["custom_items", "custom_orders"]

        # Validate params
        val_res = validate_connection_params("custom_api", {"endpoint_url": "http://api.local"})
        assert val_res["valid"] is True

    finally:
        # Cleanup
        removed = unregister_connector(test_type)
        assert removed is True
        assert is_supported_connector(test_type) is False
        assert is_supported_connector("custom_api") is False
