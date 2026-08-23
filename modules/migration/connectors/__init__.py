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
]

