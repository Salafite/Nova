"""Direct Microsoft SQL Server Connector for Nova Migration Bridge.

Implements BaseConnector providing:
1. Connection testing with latency metrics and version introspection
2. Schema discovery (tables, columns, data types, primary keys, foreign keys, row counts)
3. Preview sampling
4. Memory-safe chunked streaming extraction with cursor pagination
5. Data type conversion (datetime, decimal, bit, binary, nvarchar, etc.)
6. Graceful driver handling (pyodbc / pymssql) with mockable fallback engine for testing
"""

from datetime import date, datetime
from decimal import Decimal
import logging
import re
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
)

logger = logging.getLogger(__name__)

# Standard SQL Server to normalized data type map
SQL_TYPE_MAP: Dict[str, str] = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "tinyint": "INTEGER",
    "smallint": "INTEGER",
    "bigint": "BIGINT",
    "bit": "BOOLEAN",
    "decimal": "DECIMAL",
    "numeric": "DECIMAL",
    "money": "DECIMAL",
    "smallmoney": "DECIMAL",
    "float": "FLOAT",
    "real": "FLOAT",
    "varchar": "VARCHAR",
    "nvarchar": "VARCHAR",
    "char": "VARCHAR",
    "nchar": "VARCHAR",
    "text": "VARCHAR",
    "ntext": "VARCHAR",
    "date": "DATE",
    "datetime": "DATETIME",
    "datetime2": "DATETIME",
    "smalldatetime": "DATETIME",
    "datetimeoffset": "DATETIME",
    "time": "TIME",
    "binary": "BINARY",
    "varbinary": "BINARY",
    "image": "BINARY",
    "uniqueidentifier": "UUID",
    "xml": "XML",
    "json": "JSON",
}


def normalize_sql_type(raw_type: str) -> str:
    """Normalize raw SQL Server data type to standard uppercase type."""
    if not raw_type:
        return "VARCHAR"
    clean = raw_type.lower().strip()
    # Remove length/precision specifiers, e.g. varchar(255) -> varchar
    clean = re.sub(r"\(.*\)", "", clean).strip()
    return SQL_TYPE_MAP.get(clean, clean.upper())


class MockSQLServerEngine:
    """In-memory mock database engine for testing SQL Server connector functionality
    without requiring a live external SQL Server instance or native ODBC drivers.
    """

    def __init__(
        self,
        tables_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        table_schemas: Optional[Dict[str, TableSchema]] = None,
        server_version: str = "Microsoft SQL Server 2019 (RTM-CU18) (KB5017593) - 15.0.4261.1 (X64)",
        database_name: str = "LegacyERP_DB",
    ) -> None:
        self.tables_data: Dict[str, List[Dict[str, Any]]] = tables_data or {}
        self.table_schemas: Dict[str, TableSchema] = table_schemas or {}
        self.server_version = server_version
        self.database_name = database_name

    def get_tables(self) -> List[str]:
        all_tables = set(self.tables_data.keys()) | set(self.table_schemas.keys())
        return sorted(list(all_tables))

    def get_table_schema(self, table_name: str) -> TableSchema:
        # Check if an explicit schema is provided
        for name, schema in self.table_schemas.items():
            if name.lower() == table_name.lower():
                return schema

        # Otherwise infer schema from mock data rows
        matching_key = None
        for key in self.tables_data:
            if key.lower() == table_name.lower():
                matching_key = key
                break

        rows = self.tables_data.get(matching_key or table_name, [])
        columns: List[ColumnSchema] = []
        primary_key: List[str] = []

        if rows:
            sample = rows[0]
            for idx, (col_name, val) in enumerate(sample.items()):
                raw_type = "nvarchar"
                is_pk = False
                if col_name.lower() in ("id", f"{table_name.lower()}_id", "code", "itemcode", "custcode"):
                    is_pk = True
                    primary_key.append(col_name)

                if isinstance(val, bool):
                    raw_type = "bit"
                elif isinstance(val, int):
                    raw_type = "int"
                elif isinstance(val, float) or isinstance(val, Decimal):
                    raw_type = "decimal"
                elif isinstance(val, (datetime, date)):
                    raw_type = "datetime"
                elif isinstance(val, bytes):
                    raw_type = "varbinary"

                columns.append(
                    ColumnSchema(
                        name=col_name,
                        data_type=normalize_sql_type(raw_type),
                        is_nullable=not is_pk,
                        is_primary_key=is_pk,
                        ordinal_position=idx + 1,
                        raw_type=raw_type,
                    )
                )
        else:
            columns.append(
                ColumnSchema(
                    name="id",
                    data_type="INTEGER",
                    is_nullable=False,
                    is_primary_key=True,
                    ordinal_position=1,
                    raw_type="int",
                )
            )
            primary_key = ["id"]

        return TableSchema(
            table_name=table_name,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=[],
            row_count_estimate=len(rows),
        )

    def get_rows(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        matching_key = None
        for key in self.tables_data:
            if key.lower() == table_name.lower():
                matching_key = key
                break

        rows = self.tables_data.get(matching_key or table_name, [])

        # Filter rows if filter_condition is a callable or dict
        filtered = rows
        if callable(filter_condition):
            filtered = [r for r in rows if filter_condition(r)]
        elif isinstance(filter_condition, dict):
            filtered = [
                r for r in rows
                if all(r.get(k) == v for k, v in filter_condition.items())
            ]

        # Apply offset and limit
        sliced = filtered[offset:]
        if limit is not None:
            sliced = sliced[:limit]

        # Project columns if requested
        if columns:
            col_set = set(columns)
            projected = []
            for r in sliced:
                projected.append({k: v for k, v in r.items() if k in col_set})
            return projected

        return [dict(r) for r in sliced]


class SQLServerConnector(BaseConnector):
    """Direct database connector for legacy Microsoft SQL Server instances.
    
    Supports schema inspection, preview extraction, chunk streaming,
    and type coercion using pyodbc, pymssql, or mock test engines.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1433,
        database: str = "",
        user: str = "sa",
        password: str = "",
        trust_server_certificate: bool = True,
        driver: Optional[str] = None,
        timeout: int = 30,
        schema_name: str = "dbo",
        connection_string: Optional[str] = None,
        mock_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        mock_schemas: Optional[Dict[str, TableSchema]] = None,
        mock_engine: Optional[MockSQLServerEngine] = None,
        config: Optional[Union[Dict[str, Any], Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Allow passing config dictionary or Pydantic model
        if config is not None:
            if hasattr(config, "model_dump"):
                cfg = config.model_dump()
            elif hasattr(config, "dict"):
                cfg = config.dict()
            elif isinstance(config, dict):
                cfg = config
            else:
                cfg = {}

            self.host = cfg.get("host", host)
            self.port = int(cfg.get("port", port))
            self.database = cfg.get("database", database)
            self.user = cfg.get("user", cfg.get("username", user))
            self.password = cfg.get("password", password)
            self.trust_server_certificate = bool(cfg.get("trust_server_certificate", trust_server_certificate))
            self.driver = cfg.get("driver", driver)
            self.timeout = int(cfg.get("timeout", timeout))
            self.schema_name = cfg.get("schema_name", schema_name)
            self.connection_string = cfg.get("connection_string", connection_string)
        else:
            self.host = kwargs.get("host", host)
            self.port = int(kwargs.get("port", port))
            self.database = kwargs.get("database", database)
            self.user = kwargs.get("user", kwargs.get("username", user))
            self.password = kwargs.get("password", password)
            self.trust_server_certificate = bool(kwargs.get("trust_server_certificate", trust_server_certificate))
            self.driver = kwargs.get("driver", driver)
            self.timeout = int(kwargs.get("timeout", timeout))
            self.schema_name = kwargs.get("schema_name", schema_name)
            self.connection_string = kwargs.get("connection_string", connection_string)

        self._conn: Optional[Any] = None
        self._active_driver: Optional[str] = None

        # Setup mock engine if provided or mock data passed
        if mock_engine is not None:
            self._mock_engine: Optional[MockSQLServerEngine] = mock_engine
        elif mock_data is not None or mock_schemas is not None:
            self._mock_engine = MockSQLServerEngine(
                tables_data=mock_data or {},
                table_schemas=mock_schemas or {},
                database_name=self.database or "LegacyERP_DB",
            )
        elif kwargs.get("mock_db") is not None:
            self._mock_engine = kwargs.get("mock_db")
        else:
            self._mock_engine = None

    @property
    def mock_engine(self) -> Optional[MockSQLServerEngine]:
        return self._mock_engine

    def set_mock_data(self, mock_data: Dict[str, List[Dict[str, Any]]]) -> None:
        """Set or update mock data tables for automated testing."""
        if self._mock_engine:
            self._mock_engine.tables_data = mock_data
        else:
            self._mock_engine = MockSQLServerEngine(
                tables_data=mock_data,
                database_name=self.database or "LegacyERP_DB",
            )

    def _build_odbc_conn_str(self) -> str:
        """Construct standard ODBC connection string."""
        if self.connection_string:
            return self.connection_string

        driver = self.driver
        if not driver:
            driver = "ODBC Driver 18 for SQL Server"

        trust_cert = "yes" if self.trust_server_certificate else "no"
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={self.host},{self.port}",
            f"DATABASE={self.database}",
            f"UID={self.user}",
            f"PWD={self.password}",
            f"TrustServerCertificate={trust_cert}",
            f"Connection Timeout={self.timeout}",
        ]
        return ";".join(parts)

    def connect(self) -> None:
        """Establish connection to SQL Server or initialize mock engine."""
        if self._is_connected:
            return

        if self._mock_engine is not None:
            self._is_connected = True
            self._active_driver = "mock"
            return

        # Attempt 1: pyodbc
        try:
            import pyodbc  # type: ignore
            conn_str = self._build_odbc_conn_str()
            self._conn = pyodbc.connect(conn_str, timeout=self.timeout)
            self._active_driver = "pyodbc"
            self._is_connected = True
            return
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"pyodbc connection attempt failed: {e}")
            pass

        # Attempt 2: pymssql
        try:
            import pymssql  # type: ignore
            self._conn = pymssql.connect(
                server=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                timeout=self.timeout,
                login_timeout=self.timeout,
                as_dict=True,
            )
            self._active_driver = "pymssql"
            self._is_connected = True
            return
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"pymssql connection attempt failed: {e}")
            raise ConnectionError(f"Failed to connect to SQL Server at {self.host}:{self.port}/{self.database}: {e}")

        # If no driver is installed and no mock is configured
        raise ConnectionError(
            "No SQL Server database driver installed (neither 'pyodbc' nor 'pymssql' found). "
            "Please install pyodbc/pymssql or supply mock_data/mock_engine for testing."
        )

    def disconnect(self) -> None:
        """Close SQL Server connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._is_connected = False

    def test_connection(self) -> ConnectionTestResult:
        """Test connectivity, retrieve version, and list accessible tables."""
        start_time = time.perf_counter()
        try:
            self.connect()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if self._mock_engine is not None:
                tables = self.get_tables()
                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to SQL Server (Mock Engine)",
                    latency_ms=elapsed_ms,
                    server_version=self._mock_engine.server_version,
                    database_name=self.database or self._mock_engine.database_name,
                    tables_count=len(tables),
                    tables=tables,
                    details={
                        "driver": "mock",
                        "host": self.host,
                        "port": self.port,
                        "schema": self.schema_name,
                    },
                )

            # Live DB queries
            cursor = self._conn.cursor()
            try:
                cursor.execute("SELECT @@VERSION, DB_NAME()")
                row = cursor.fetchone()
                version = row[0] if row else "Unknown"
                db_name = row[1] if row and len(row) > 1 else self.database

                tables = self.get_tables()

                return ConnectionTestResult(
                    success=True,
                    message="Successfully connected to SQL Server",
                    latency_ms=elapsed_ms,
                    server_version=str(version),
                    database_name=str(db_name),
                    tables_count=len(tables),
                    tables=tables,
                    details={
                        "driver": self._active_driver,
                        "host": self.host,
                        "port": self.port,
                        "schema": self.schema_name,
                    },
                )
            finally:
                cursor.close()

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"SQL Server connection test failed: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                latency_ms=elapsed_ms,
                database_name=self.database,
                tables_count=0,
                tables=[],
                error=str(e),
            )

    def get_tables(self) -> List[str]:
        """List all user tables in the legacy database."""
        if not self.is_connected:
            self.connect()

        if self._mock_engine is not None:
            return self._mock_engine.get_tables()

        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND (TABLE_SCHEMA = ? OR ? = '')
            ORDER BY TABLE_NAME
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute(query, (self.schema_name, self.schema_name))
            rows = cursor.fetchall()
            tables = []
            for r in rows:
                name = r[0] if not isinstance(r, dict) else r.get("TABLE_NAME")
                if name:
                    tables.append(str(name))
            return tables
        finally:
            cursor.close()

    def get_table_schema(self, table_name: str) -> TableSchema:
        """Introspect column definitions, primary keys, and foreign keys for a table."""
        if not self.is_connected:
            self.connect()

        if self._mock_engine is not None:
            return self._mock_engine.get_table_schema(table_name)

        cursor = self._conn.cursor()
        try:
            # 1. Columns query
            col_query = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    COLUMN_DEFAULT,
                    ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                  AND (TABLE_SCHEMA = ? OR ? = '')
                ORDER BY ORDINAL_POSITION
            """
            cursor.execute(col_query, (table_name, self.schema_name, self.schema_name))
            col_rows = cursor.fetchall()

            # 2. Primary key query
            pk_query = """
                SELECT kcu.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                  AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                WHERE tc.TABLE_NAME = ?
                  AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                  AND (tc.TABLE_SCHEMA = ? OR ? = '')
                ORDER BY kcu.ORDINAL_POSITION
            """
            cursor.execute(pk_query, (table_name, self.schema_name, self.schema_name))
            pk_rows = cursor.fetchall()
            primary_keys = [
                str(r[0] if not isinstance(r, dict) else r.get("COLUMN_NAME"))
                for r in pk_rows
            ]

            # 3. Foreign keys query
            fk_query = """
                SELECT 
                    kcu.COLUMN_NAME AS from_column,
                    ccu.TABLE_NAME AS to_table,
                    ccu.COLUMN_NAME AS to_column,
                    rc.CONSTRAINT_NAME AS fk_name
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                  ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
                  ON rc.UNIQUE_CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
                WHERE kcu.TABLE_NAME = ?
            """
            foreign_keys = []
            try:
                cursor.execute(fk_query, (table_name,))
                fk_rows = cursor.fetchall()
                for fk in fk_rows:
                    if isinstance(fk, dict):
                        foreign_keys.append({
                            "from_column": fk.get("from_column"),
                            "to_table": fk.get("to_table"),
                            "to_column": fk.get("to_column"),
                            "name": fk.get("fk_name"),
                        })
                    else:
                        foreign_keys.append({
                            "from_column": fk[0],
                            "to_table": fk[1],
                            "to_column": fk[2],
                            "name": fk[3] if len(fk) > 3 else None,
                        })
            except Exception as fk_err:
                logger.debug(f"FK introspection warning for {table_name}: {fk_err}")

            # 4. Build column schema objects
            columns: List[ColumnSchema] = []
            for r in col_rows:
                if isinstance(r, dict):
                    c_name = str(r.get("COLUMN_NAME"))
                    c_raw_type = str(r.get("DATA_TYPE") or "varchar")
                    c_nullable = str(r.get("IS_NULLABLE", "YES")).upper() == "YES"
                    c_max_len = r.get("CHARACTER_MAXIMUM_LENGTH")
                    c_prec = r.get("NUMERIC_PRECISION")
                    c_scale = r.get("NUMERIC_SCALE")
                    c_def = r.get("COLUMN_DEFAULT")
                    c_ord = r.get("ORDINAL_POSITION")
                else:
                    c_name = str(r[0])
                    c_raw_type = str(r[1] or "varchar")
                    c_nullable = str(r[2] or "YES").upper() == "YES"
                    c_max_len = r[3]
                    c_prec = r[4]
                    c_scale = r[5]
                    c_def = r[6]
                    c_ord = r[7]

                # Check if this column is a foreign key
                is_fk = False
                fk_table = None
                fk_col = None
                for fk_info in foreign_keys:
                    if fk_info.get("from_column") == c_name:
                        is_fk = True
                        fk_table = fk_info.get("to_table")
                        fk_col = fk_info.get("to_column")
                        break

                columns.append(
                    ColumnSchema(
                        name=c_name,
                        data_type=normalize_sql_type(c_raw_type),
                        is_nullable=c_nullable,
                        is_primary_key=c_name in primary_keys,
                        is_foreign_key=is_fk,
                        foreign_table=fk_table,
                        foreign_column=fk_col,
                        max_length=int(c_max_len) if c_max_len is not None and c_max_len > 0 else None,
                        precision=int(c_prec) if c_prec is not None else None,
                        scale=int(c_scale) if c_scale is not None else None,
                        default_value=str(c_def) if c_def is not None else None,
                        ordinal_position=int(c_ord) if c_ord is not None else None,
                        raw_type=c_raw_type,
                    )
                )

            # 5. Row count estimate
            row_count_estimate = self.get_row_count(table_name)

            return TableSchema(
                table_name=table_name,
                columns=columns,
                primary_key=primary_keys,
                foreign_keys=foreign_keys,
                row_count_estimate=row_count_estimate,
            )
        finally:
            cursor.close()

    def get_row_count(
        self, table_name: str, filter_condition: Optional[Any] = None
    ) -> int:
        """Return row count for a table with optional filter."""
        if not self.is_connected:
            self.connect()

        if self._mock_engine is not None:
            rows = self._mock_engine.get_rows(table_name, filter_condition=filter_condition)
            return len(rows)

        cursor = self._conn.cursor()
        try:
            safe_schema = self.schema_name or "dbo"
            sql = f"SELECT COUNT(*) FROM [{safe_schema}].[{table_name}]"
            params: Tuple[Any, ...] = ()
            if filter_condition:
                if isinstance(filter_condition, str):
                    sql += f" WHERE {filter_condition}"
                elif isinstance(filter_condition, dict):
                    clauses = []
                    vals = []
                    for k, v in filter_condition.items():
                        clauses.append(f"[{k}] = ?")
                        vals.append(v)
                    sql += " WHERE " + " AND ".join(clauses)
                    params = tuple(vals)

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row:
                return int(row[0] if not isinstance(row, dict) else list(row.values())[0])
            return 0
        finally:
            cursor.close()

    def preview_table(
        self,
        table_name: str,
        limit: int = 100,
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a small sample preview of rows from a table."""
        if not self.is_connected:
            self.connect()

        if self._mock_engine is not None:
            rows = self._mock_engine.get_rows(
                table_name=table_name,
                columns=columns,
                limit=limit,
                offset=0,
            )
            return [{k: self.serialize_value(v) for k, v in r.items()} for r in rows]

        safe_schema = self.schema_name or "dbo"
        col_clause = "*"
        if columns:
            col_clause = ", ".join([f"[{c}]" for c in columns])

        sql = f"SELECT TOP {int(limit)} {col_clause} FROM [{safe_schema}].[{table_name}]"

        cursor = self._conn.cursor()
        try:
            cursor.execute(sql)
            return self._fetch_all_as_dicts(cursor)
        finally:
            cursor.close()

    def extract_chunks(
        self,
        table_name: str,
        chunk_size: int = 1000,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
        order_by: Optional[str] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream table rows in memory-safe chunks using cursor iteration."""
        if not self.is_connected:
            self.connect()

        if self._mock_engine is not None:
            offset = 0
            while True:
                chunk = self._mock_engine.get_rows(
                    table_name=table_name,
                    columns=columns,
                    filter_condition=filter_condition,
                    limit=chunk_size,
                    offset=offset,
                )
                if not chunk:
                    break
                yield [{k: self.serialize_value(v) for k, v in r.items()} for r in chunk]
                offset += len(chunk)
                if len(chunk) < chunk_size:
                    break
            return

        safe_schema = self.schema_name or "dbo"
        col_clause = "*"
        if columns:
            col_clause = ", ".join([f"[{c}]" for c in columns])

        sql = f"SELECT {col_clause} FROM [{safe_schema}].[{table_name}]"
        params: Tuple[Any, ...] = ()

        if filter_condition:
            if isinstance(filter_condition, str):
                sql += f" WHERE {filter_condition}"
            elif isinstance(filter_condition, dict):
                clauses = []
                vals = []
                for k, v in filter_condition.items():
                    clauses.append(f"[{k}] = ?")
                    vals.append(v)
                sql += " WHERE " + " AND ".join(clauses)
                params = tuple(vals)

        if order_by:
            sql += f" ORDER BY {order_by}"

        cursor = self._conn.cursor()
        try:
            cursor.execute(sql, params)
            col_names = [col[0] for col in cursor.description] if cursor.description else []

            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break

                batch: List[Dict[str, Any]] = []
                for r in rows:
                    if isinstance(r, dict):
                        batch.append({k: self.serialize_value(v) for k, v in r.items()})
                    else:
                        row_dict = {}
                        for idx, col_name in enumerate(col_names):
                            val = r[idx] if idx < len(r) else None
                            row_dict[col_name] = self.serialize_value(val)
                        batch.append(row_dict)

                yield batch

                if len(rows) < chunk_size:
                    break
        finally:
            cursor.close()

    def _fetch_all_as_dicts(self, cursor: Any) -> List[Dict[str, Any]]:
        """Convert all cursor rows into serialized dictionaries."""
        rows = cursor.fetchall()
        if not rows:
            return []

        if isinstance(rows[0], dict):
            return [{k: self.serialize_value(v) for k, v in r.items()} for r in rows]

        col_names = [col[0] for col in cursor.description] if cursor.description else []
        results: List[Dict[str, Any]] = []
        for r in rows:
            row_dict = {}
            for idx, col_name in enumerate(col_names):
                val = r[idx] if idx < len(r) else None
                row_dict[col_name] = self.serialize_value(val)
            results.append(row_dict)
        return results
