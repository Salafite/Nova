from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Iterator, List, Optional, Union
import time


@dataclass
class ColumnSchema:
    """Schema metadata for a single column in a legacy table."""
    name: str
    data_type: str = "VARCHAR"
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    default_value: Optional[str] = None
    ordinal_position: Optional[int] = None
    raw_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "is_nullable": self.is_nullable,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "foreign_table": self.foreign_table,
            "foreign_column": self.foreign_column,
            "max_length": self.max_length,
            "precision": self.precision,
            "scale": self.scale,
            "default_value": self.default_value,
            "ordinal_position": self.ordinal_position,
            "raw_type": self.raw_type or self.data_type,
        }


@dataclass
class TableSchema:
    """Schema metadata for a table or dataset in a legacy source."""
    table_name: str
    columns: List[ColumnSchema] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    row_count_estimate: Optional[int] = None
    description: Optional[str] = None

    @property
    def column_names(self) -> List[str]:
        return [col.name for col in self.columns]

    def get_column(self, name: str) -> Optional[ColumnSchema]:
        name_lower = name.lower()
        for col in self.columns:
            if col.name.lower() == name_lower:
                return col
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "columns": [col.to_dict() for col in self.columns],
            "column_names": self.column_names,
            "primary_key": self.primary_key,
            "foreign_keys": self.foreign_keys,
            "row_count_estimate": self.row_count_estimate,
            "description": self.description,
        }


@dataclass
class ConnectionTestResult:
    """Result of a connection test against a legacy source."""
    success: bool
    message: str
    latency_ms: float = 0.0
    server_version: Optional[str] = None
    database_name: Optional[str] = None
    tables_count: Optional[int] = None
    tables: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "server_version": self.server_version,
            "database_name": self.database_name,
            "tables_count": self.tables_count if self.tables_count is not None else len(self.tables),
            "tables": self.tables,
            "details": self.details,
            "error": self.error,
        }


class BaseConnector(ABC):
    """Abstract base connector for legacy database systems and bulk file dumps.
    
    Provides standardized methods for connection validation, schema discovery,
    row count inspection, preview retrieval, and memory-safe chunked streaming extraction.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self) -> None:
        """Establish connection or initialize resource handles."""
        self._is_connected = True

    def disconnect(self) -> None:
        """Close connection or release resource handles."""
        self._is_connected = False

    def close(self) -> None:
        """Alias for disconnect."""
        self.disconnect()

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Test connection reachability, credentials, and basic read capabilities."""
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """List all available tables, views, or dataset entities in the legacy source."""
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> TableSchema:
        """Discover and return column definitions, primary keys, and types for a table."""
        pass

    @abstractmethod
    def get_row_count(
        self, table_name: str, filter_condition: Optional[Any] = None
    ) -> int:
        """Return total or filtered row count for a given table."""
        pass

    @abstractmethod
    def preview_table(
        self,
        table_name: str,
        limit: int = 100,
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a small preview slice of rows from a table."""
        pass

    @abstractmethod
    def extract_chunks(
        self,
        table_name: str,
        chunk_size: int = 1000,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
        order_by: Optional[str] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream table rows in memory-safe batches of chunk_size.
        
        Yields:
            List[Dict[str, Any]]: A batch of rows formatted as dictionaries.
        """
        pass

    def extract_all(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Extract all rows for a table by consuming extract_chunks."""
        all_rows: List[Dict[str, Any]] = []
        for chunk in self.extract_chunks(
            table_name=table_name,
            chunk_size=2000,
            columns=columns,
            filter_condition=filter_condition,
        ):
            all_rows.extend(chunk)
        return all_rows

    @staticmethod
    def serialize_value(val: Any) -> Any:
        """Normalize database/legacy values into JSON-compatible Python primitives."""
        if val is None:
            return None
        if isinstance(val, (datetime, date)):
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, bytes):
            try:
                return val.decode("utf-8")
            except Exception:
                return val.hex()
        return val
