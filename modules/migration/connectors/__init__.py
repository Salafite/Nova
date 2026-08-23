"""Connector modules for legacy ERP data sources and databases."""

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
)
from modules.migration.connectors.sqlserver import (
    MockSQLServerEngine,
    SQLServerConnector,
)
from modules.migration.connectors.csv_dump import (
    CsvDumpConnector,
    SQLDumpTableParser,
    coerce_value,
    detect_delimiter,
    detect_encoding,
    detect_header,
    infer_column_type,
)
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

__all__ = [
    "BaseConnector",
    "ColumnSchema",
    "ConnectionTestResult",
    "TableSchema",
    "SQLServerConnector",
    "MockSQLServerEngine",
    "CsvDumpConnector",
    "SQLDumpTableParser",
    "coerce_value",
    "detect_delimiter",
    "detect_encoding",
    "detect_header",
    "infer_column_type",
    "ConnectorRegistration",
    "register_connector",
    "unregister_connector",
    "normalize_source_type",
    "is_supported_connector",
    "get_connector_class",
    "list_supported_connectors",
    "validate_connection_params",
    "get_connector",
    "create_connector_from_config",
]

