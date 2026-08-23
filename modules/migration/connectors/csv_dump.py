"""Multi-table CSV and SQL Dump Connector for Nova Migration Bridge.

Implements BaseConnector providing:
1. Multi-file CSV directory, ZIP archive, and SQL dump script ingestion
2. Automatic delimiter detection (comma, semicolon, tab, pipe)
3. Character encoding autodetection (UTF-8, UTF-8-BOM, CP1252, Windows-1256 for Arabic datasets)
4. Automatic header detection and column name normalization
5. Schema discovery and data type inference (INTEGER, DECIMAL, BOOLEAN, DATE, DATETIME, VARCHAR)
6. Preview sampling
7. Memory-safe chunked streaming extraction for large datasets
8. In-memory virtual file support for rapid testing and programmatic ETL
"""

import csv
from datetime import date, datetime
from decimal import Decimal
import io
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union
import zipfile

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
)

logger = logging.getLogger(__name__)

# Common date and datetime regex patterns
DATE_REGEX = re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$")
DATETIME_REGEX = re.compile(
    r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}[ T]\d{1,2}:\d{1,2}(:\d{1,2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)
INT_REGEX = re.compile(r"^[+-]?\d+$")
FLOAT_REGEX = re.compile(r"^[+-]?\d+\.\d+([eE][+-]?\d+)?$")
BOOLEAN_TRUE_VALUES = {"true", "1", "yes", "y", "t", "on", "نعم"}
BOOLEAN_FALSE_VALUES = {"false", "0", "no", "n", "f", "off", "لا"}


def detect_encoding(raw_bytes: bytes, user_encoding: Optional[str] = None) -> str:
    """Detect character encoding from byte sequence.
    
    Checks BOMs, tests user encoding if given, UTF-8, and falls back to legacy encodings
    like Windows-1256 (Arabic) and CP1252 (Western European).
    """
    if user_encoding:
        try:
            raw_bytes[:4096].decode(user_encoding)
            return user_encoding
        except Exception:
            pass

    # Check BOMs
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw_bytes.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw_bytes.startswith(b"\xfe\xff"):
        return "utf-16-be"

    # Try UTF-8
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Candidate legacy encodings
    candidate_encodings = ["windows-1256", "cp1252", "iso-8859-1", "latin1"]
    for enc in candidate_encodings:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def detect_delimiter(sample_text: str, user_delimiter: Optional[str] = None) -> str:
    """Detect delimiter from sample text.
    
    Supports comma, semicolon, tab, and pipe.
    """
    if user_delimiter:
        return user_delimiter

    if not sample_text or not sample_text.strip():
        return ","

    # Try standard csv.Sniffer
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text[:4096], delimiters=[",", ";", "\t", "|"])
        if dialect.delimiter:
            return dialect.delimiter
    except Exception:
        pass

    # Frequency analysis across non-empty lines
    lines = [line.strip() for line in sample_text.splitlines() if line.strip()][:10]
    if not lines:
        return ","

    candidate_delims = [",", ";", "\t", "|"]
    best_delim = ","
    best_score = -1

    for delim in candidate_delims:
        counts = [line.count(delim) for line in lines]
        if all(c > 0 for c in counts):
            # Check consistency (uniform column counts per line)
            avg_count = sum(counts) / len(counts)
            variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
            score = avg_count / (1.0 + variance)
            if score > best_score:
                best_score = score
                best_delim = delim

    return best_delim


def detect_header(sample_lines: List[str], delimiter: str = ",", user_has_header: Optional[bool] = None) -> bool:
    """Detect whether the first row is a header row."""
    if user_has_header is not None:
        return user_has_header

    if not sample_lines:
        return True

    try:
        sample_text = "\n".join(sample_lines[:10])
        sniffer = csv.Sniffer()
        return sniffer.has_header(sample_text)
    except Exception:
        pass

    # Heuristic: Check if first row contains non-numeric strings while subsequent rows have numbers
    reader = csv.reader(sample_lines[:5], delimiter=delimiter)
    rows = list(reader)
    if len(rows) < 2:
        return True

    header_row = rows[0]
    data_rows = rows[1:]

    # If first row has pure numbers, it's likely data
    if all(INT_REGEX.match(cell.strip()) or FLOAT_REGEX.match(cell.strip()) for cell in header_row if cell.strip()):
        return False

    return True


def infer_column_type(values: List[str]) -> Tuple[str, bool]:
    """Infer column data type and nullability from a sample of string values.
    
    Returns:
        Tuple[str, bool]: (data_type, is_nullable)
    """
    non_empty = [v.strip() for v in values if v is not None and v.strip() != "" and v.strip().upper() != "NULL"]
    is_nullable = len(non_empty) < len(values)

    if not non_empty:
        return "VARCHAR", True

    # 1. Check Boolean
    all_bool = True
    for v in non_empty:
        low = v.lower()
        if low not in BOOLEAN_TRUE_VALUES and low not in BOOLEAN_FALSE_VALUES:
            all_bool = False
            break
    if all_bool:
        return "BOOLEAN", is_nullable

    # 2. Check Integer
    if all(INT_REGEX.match(v) for v in non_empty):
        return "INTEGER", is_nullable

    # 3. Check Decimal / Float
    if all(FLOAT_REGEX.match(v) or INT_REGEX.match(v) for v in non_empty):
        return "DECIMAL", is_nullable

    # 4. Check Datetime
    if all(DATETIME_REGEX.match(v) for v in non_empty):
        return "DATETIME", is_nullable

    # 5. Check Date
    if all(DATE_REGEX.match(v) for v in non_empty):
        return "DATE", is_nullable

    return "VARCHAR", is_nullable


def coerce_value(val: Any, target_type: str) -> Any:
    """Coerce raw string or primitive value into typed Python object."""
    if val is None:
        return None

    if not isinstance(val, str):
        return BaseConnector.serialize_value(val)

    s = val.strip()
    if not s or s.upper() == "NULL":
        return None

    t_upper = target_type.upper()
    try:
        if t_upper in ("INT", "INTEGER", "SMALLINT", "BIGINT", "TINYINT"):
            return int(float(s)) if "." in s else int(s)
        if t_upper in ("DECIMAL", "NUMERIC", "FLOAT", "REAL", "DOUBLE", "MONEY"):
            return float(s)
        if t_upper in ("BOOL", "BOOLEAN", "BIT"):
            low = s.lower()
            if low in BOOLEAN_TRUE_VALUES:
                return True
            if low in BOOLEAN_FALSE_VALUES:
                return False
            return bool(s)
        if t_upper in ("DATE",):
            # Parse date string
            clean_date = s.replace("/", "-").replace(".", "-")
            parts = clean_date.split("-")
            if len(parts) == 3:
                if len(parts[0]) == 4:  # YYYY-MM-DD
                    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                if len(parts[2]) == 4:  # DD-MM-YYYY or MM-DD-YYYY
                    return f"{int(parts[2]):04d}-{int(parts[1]):02d}-{int(parts[0]):02d}"
            return s
        if t_upper in ("DATETIME", "DATETIME2", "TIMESTAMP"):
            return s
    except Exception:
        return s

    return s


def _sort_key_helper(val: Any) -> Tuple[int, Any]:
    """Helper to sort rows naturally by value, handling mixed types and nulls."""
    if val is None:
        return (0, 0)
    if isinstance(val, (int, float, Decimal)):
        return (1, float(val))
    if isinstance(val, (datetime, date)):
        return (2, str(val))
    return (3, str(val))


class SQLDumpTableParser:
    """Parses SQL DDL (CREATE TABLE) and DML (INSERT INTO) statements from SQL dump files."""

    @staticmethod
    def parse_sql_dump(content: str) -> Dict[str, Dict[str, Any]]:
        """Parse SQL dump string into structured table schemas and row dictionaries.
        
        Returns:
            Dict[table_name, {"columns": List[ColumnSchema], "primary_key": List[str], "rows": List[Dict[str, Any]]}]
        """
        tables: Dict[str, Dict[str, Any]] = {}

        # 1. Parse CREATE TABLE statements
        create_table_regex = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[`\"\[]?\w+[`\"\]]?\.)?[`\"\[]?(\w+)[`\"\]]?\s*\((.*?)\);",
            re.IGNORECASE | re.DOTALL,
        )

        for match in create_table_regex.finditer(content):
            table_name = match.group(1)
            body = match.group(2)
            columns: List[ColumnSchema] = []
            primary_keys: List[str] = []

            # Split column definitions by comma (ignoring commas inside parentheses)
            col_defs = SQLDumpTableParser._split_definitions(body)
            for idx, col_def in enumerate(col_defs):
                col_def_clean = col_def.strip()
                if not col_def_clean:
                    continue

                # Check for table-level PRIMARY KEY (col1, col2)
                pk_match = re.match(
                    r"PRIMARY\s+KEY\s*\((.*?)\)", col_def_clean, re.IGNORECASE
                )
                if pk_match:
                    pks = [
                        re.sub(r"[`\"\[\]\s]", "", p)
                        for p in pk_match.group(1).split(",")
                    ]
                    primary_keys.extend(pks)
                    continue

                # Check for CONSTRAINT ... FOREIGN KEY ...
                if re.match(r"(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY", col_def_clean, re.IGNORECASE):
                    continue

                # Parse single column: name type [NULL/NOT NULL] [PRIMARY KEY] [DEFAULT ...]
                col_parts = col_def_clean.split(None, 2)
                if not col_parts:
                    continue

                raw_col_name = re.sub(r"[`\"\[\]]", "", col_parts[0])
                raw_type = col_parts[1] if len(col_parts) > 1 else "VARCHAR"
                rest = col_parts[2] if len(col_parts) > 2 else ""

                is_pk = "PRIMARY KEY" in rest.upper()
                if is_pk and raw_col_name not in primary_keys:
                    primary_keys.append(raw_col_name)

                is_nullable = "NOT NULL" not in rest.upper() and not is_pk

                norm_type = raw_type.upper()
                if any(x in norm_type for x in ("INT", "SERIAL")):
                    norm_type = "INTEGER"
                elif any(x in norm_type for x in ("DECIMAL", "NUMERIC", "FLOAT", "MONEY", "REAL", "DOUBLE")):
                    norm_type = "DECIMAL"
                elif any(x in norm_type for x in ("BOOL", "BIT")):
                    norm_type = "BOOLEAN"
                elif any(x in norm_type for x in ("DATE", "TIME")):
                    norm_type = "DATETIME" if "TIME" in norm_type else "DATE"
                else:
                    norm_type = "VARCHAR"

                columns.append(
                    ColumnSchema(
                        name=raw_col_name,
                        data_type=norm_type,
                        is_nullable=is_nullable,
                        is_primary_key=is_pk,
                        ordinal_position=idx + 1,
                        raw_type=raw_type,
                    )
                )

            # Update PK flags on column schemas if PK was specified at table level
            for col in columns:
                if col.name in primary_keys:
                    col.is_primary_key = True
                    col.is_nullable = False

            tables[table_name] = {
                "columns": columns,
                "primary_key": primary_keys,
                "rows": [],
            }

        # 2. Parse INSERT INTO statements
        insert_regex = re.compile(
            r"INSERT\s+INTO\s+(?:[`\"\[]?\w+[`\"\]]?\.)?[`\"\[]?(\w+)[`\"\]]?\s*(?:\((.*?)\))?\s*VALUES\s*(.*?);",
            re.IGNORECASE | re.DOTALL,
        )

        for match in insert_regex.finditer(content):
            table_name = match.group(1)
            raw_cols = match.group(2)
            values_str = match.group(3)

            col_names: Optional[List[str]] = None
            if raw_cols:
                col_names = [
                    re.sub(r"[`\"\[\]\s]", "", c) for c in raw_cols.split(",")
                ]

            # Parse value tuples: (val1, val2, ...), (val3, val4, ...)
            parsed_rows = SQLDumpTableParser._parse_insert_values(values_str)

            if table_name not in tables:
                tables[table_name] = {
                    "columns": [],
                    "primary_key": [],
                    "rows": [],
                }

            table_entry = tables[table_name]
            existing_cols = [c.name for c in table_entry["columns"]]

            if not existing_cols and col_names:
                for idx, c_name in enumerate(col_names):
                    table_entry["columns"].append(
                        ColumnSchema(name=c_name, data_type="VARCHAR", ordinal_position=idx + 1)
                    )
                existing_cols = col_names

            for row_vals in parsed_rows:
                row_dict: Dict[str, Any] = {}
                if col_names:
                    for i, c_name in enumerate(col_names):
                        val = row_vals[i] if i < len(row_vals) else None
                        row_dict[c_name] = val
                else:
                    for i, val in enumerate(row_vals):
                        c_name = existing_cols[i] if i < len(existing_cols) else f"col_{i+1}"
                        row_dict[c_name] = val

                # Type-coerce values if column types are known from CREATE TABLE
                if table_entry["columns"]:
                    type_lookup = {c.name: c.data_type for c in table_entry["columns"]}
                    for k, v in list(row_dict.items()):
                        target_t = type_lookup.get(k)
                        if target_t == "BOOLEAN":
                            if v in (1, "1", "true", "True", True):
                                row_dict[k] = True
                            elif v in (0, "0", "false", "False", False):
                                row_dict[k] = False
                        elif target_t == "DECIMAL" and isinstance(v, (int, float)):
                            row_dict[k] = float(v)

                table_entry["rows"].append(row_dict)

        return tables

    @staticmethod
    def _split_definitions(body: str) -> List[str]:
        """Split table body definitions by comma without breaking nested parens."""
        definitions = []
        current: List[str] = []
        depth = 0
        in_quote = False
        quote_char = ""

        for char in body:
            if char in ("'", '"', "`") and not in_quote:
                in_quote = True
                quote_char = char
            elif in_quote and char == quote_char:
                in_quote = False
            elif not in_quote:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                elif char == "," and depth == 0:
                    definitions.append("".join(current))
                    current = []
                    continue
            current.append(char)

        if current:
            definitions.append("".join(current))
        return definitions

    @staticmethod
    def _parse_insert_values(values_str: str) -> List[List[Any]]:
        """Parse SQL INSERT values clause into Python literals."""
        rows: List[List[Any]] = []
        current_row: List[Any] = []
        current_val: List[str] = []
        in_paren = False
        in_quote = False
        quote_char = ""

        i = 0
        n = len(values_str)
        while i < n:
            char = values_str[i]

            if not in_paren:
                if char == "(":
                    in_paren = True
                    current_row = []
                    current_val = []
                i += 1
                continue

            # Inside parentheses (row)
            if in_quote:
                if char == quote_char:
                    # Check escaped quote '' or \'
                    if i + 1 < n and values_str[i + 1] == quote_char:
                        current_val.append(quote_char)
                        i += 2
                        continue
                    in_quote = False
                    i += 1
                    continue
                elif char == "\\" and i + 1 < n:
                    next_char = values_str[i + 1]
                    if next_char in ("n", "t", "r", "'", '"', "\\"):
                        escape_map = {"n": "\n", "t": "\t", "r": "\r", "'": "'", '"': '"', "\\": "\\"}
                        current_val.append(escape_map.get(next_char, next_char))
                        i += 2
                        continue
                current_val.append(char)
                i += 1
                continue

            # Not inside quote
            if char in ("'", '"'):
                in_quote = True
                quote_char = char
                i += 1
                continue

            if char == ",":
                val_str = "".join(current_val).strip()
                current_row.append(SQLDumpTableParser._convert_literal(val_str))
                current_val = []
                i += 1
                continue

            if char == ")":
                val_str = "".join(current_val).strip()
                current_row.append(SQLDumpTableParser._convert_literal(val_str))
                rows.append(current_row)
                current_row = []
                current_val = []
                in_paren = False
                i += 1
                continue

            current_val.append(char)
            i += 1

        return rows

    @staticmethod
    def _convert_literal(val_str: str) -> Any:
        """Convert raw SQL literal string into Python value."""
        if not val_str:
            return ""
        if val_str.upper() == "NULL":
            return None
        if (val_str.startswith("'") and val_str.endswith("'")) or (val_str.startswith('"') and val_str.endswith('"')):
            val_str = val_str[1:-1]
        if INT_REGEX.match(val_str):
            return int(val_str)
        if FLOAT_REGEX.match(val_str):
            return float(val_str)
        if val_str.lower() in ("true", "1"):
            return True
        if val_str.lower() in ("false", "0"):
            return False
        return val_str


class CsvDumpConnector(BaseConnector):
    """Connector for multi-table CSV files, ZIP archives, SQL dumps, and in-memory files.
    
    Provides schema introspection, delimiter & encoding autodetection, type inference,
    preview sampling, and memory-safe chunked streaming extraction.
    """

    def __init__(
        self,
        dump_path: Optional[Union[str, Path]] = None,
        zip_file_path: Optional[Union[str, Path]] = None,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
        quote_char: str = '"',
        has_header: bool = True,
        in_memory_files: Optional[Dict[str, Union[str, bytes]]] = None,
        config: Optional[Union[Dict[str, Any], Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Allow passing config model or dict
        if config is not None:
            if hasattr(config, "model_dump"):
                cfg = config.model_dump()
            elif hasattr(config, "dict"):
                cfg = config.dict()
            elif isinstance(config, dict):
                cfg = config
            else:
                cfg = {}

            self.dump_path = cfg.get("dump_path", dump_path)
            self.zip_file_path = cfg.get("zip_file_path", zip_file_path)
            self.delimiter = cfg.get("delimiter", delimiter)
            self.encoding = cfg.get("encoding", encoding)
            self.quote_char = cfg.get("quote_char", quote_char)
            self.has_header = cfg.get("has_header", has_header)
        else:
            self.dump_path = kwargs.get("dump_path", dump_path)
            self.zip_file_path = kwargs.get("zip_file_path", zip_file_path)
            self.delimiter = kwargs.get("delimiter", delimiter)
            self.encoding = kwargs.get("encoding", encoding)
            self.quote_char = kwargs.get("quote_char", quote_char)
            self.has_header = kwargs.get("has_header", has_header)

        # In-memory virtual files for tests and direct payload processing
        self._in_memory_files: Dict[str, Union[str, bytes]] = (
            dict(in_memory_files) if in_memory_files is not None else {}
        )
        if kwargs.get("files") is not None and isinstance(kwargs.get("files"), dict):
            self._in_memory_files.update(kwargs.get("files"))

        # Cached schemas and table metadata
        self._table_schemas: Dict[str, TableSchema] = {}
        self._table_file_map: Dict[str, Dict[str, Any]] = {}
        self._sql_dump_data: Dict[str, Dict[str, Any]] = {}

    def set_in_memory_file(self, filename: str, content: Union[str, bytes]) -> None:
        """Register or update an in-memory virtual file."""
        self._in_memory_files[filename] = content
        self._table_schemas.clear()
        self._table_file_map.clear()
        self._sql_dump_data.clear()

    def connect(self) -> None:
        """Discover files and build table index."""
        if self._is_connected:
            return

        self._discover_tables_and_files()
        self._is_connected = True

    def disconnect(self) -> None:
        """Release handles."""
        self._is_connected = False

    def _discover_tables_and_files(self) -> None:
        """Scan directory, ZIP, SQL dumps, and in-memory files to index available tables."""
        self._table_file_map.clear()
        self._sql_dump_data.clear()

        # 1. In-memory files
        for filename, content in self._in_memory_files.items():
            self._index_file_entry(
                source_kind="memory",
                filepath=filename,
                raw_bytes=content.encode("utf-8") if isinstance(content, str) else content,
            )

        # 2. ZIP file
        zip_path = self.zip_file_path or (self.dump_path if self.dump_path and str(self.dump_path).lower().endswith(".zip") else None)
        if zip_path and os.path.isfile(zip_path):
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        name_lower = info.filename.lower()
                        if any(name_lower.endswith(ext) for ext in (".csv", ".tsv", ".txt", ".sql")):
                            file_bytes = z.read(info.filename)
                            self._index_file_entry(
                                source_kind="zip",
                                filepath=info.filename,
                                zip_archive_path=str(zip_path),
                                raw_bytes=file_bytes,
                            )
            except Exception as e:
                logger.error(f"Error reading zip archive {zip_path}: {e}")

        # 3. Directory or Single file
        if self.dump_path and not str(self.dump_path).lower().endswith(".zip"):
            p = Path(self.dump_path)
            if p.is_file():
                try:
                    with open(p, "rb") as f:
                        file_bytes = f.read()
                    self._index_file_entry(
                        source_kind="file",
                        filepath=str(p),
                        raw_bytes=file_bytes,
                    )
                except Exception as e:
                    logger.error(f"Error reading file {p}: {e}")
            elif p.is_dir():
                for root, _, files in os.walk(p):
                    for f in files:
                        f_lower = f.lower()
                        if any(f_lower.endswith(ext) for ext in (".csv", ".tsv", ".txt", ".sql")):
                            full_path = os.path.join(root, f)
                            try:
                                with open(full_path, "rb") as fh:
                                    file_bytes = fh.read()
                                self._index_file_entry(
                                    source_kind="file",
                                    filepath=full_path,
                                    raw_bytes=file_bytes,
                                )
                            except Exception as e:
                                logger.error(f"Error reading directory file {full_path}: {e}")

    def _index_file_entry(
        self,
        source_kind: str,
        filepath: str,
        raw_bytes: bytes,
        zip_archive_path: Optional[str] = None,
    ) -> None:
        """Register a discovered file (CSV or SQL) into the table registry."""
        filename = os.path.basename(filepath)
        name_stem, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == ".sql":
            # Parse SQL dump
            enc = detect_encoding(raw_bytes, self.encoding)
            try:
                sql_content = raw_bytes.decode(enc)
                parsed_tables = SQLDumpTableParser.parse_sql_dump(sql_content)
                for tbl_name, tbl_data in parsed_tables.items():
                    clean_tbl_name = tbl_name
                    self._sql_dump_data[clean_tbl_name] = tbl_data
                    self._table_file_map[clean_tbl_name] = {
                        "source_kind": "sql_dump",
                        "table_name": clean_tbl_name,
                        "filepath": filepath,
                        "encoding": enc,
                    }
            except Exception as e:
                logger.error(f"Failed to parse SQL dump {filepath}: {e}")
            return

        # CSV / TSV / TXT
        table_name = name_stem
        enc = detect_encoding(raw_bytes, self.encoding)
        try:
            sample_head = raw_bytes[:8192].decode(enc, errors="replace")
            delim = detect_delimiter(sample_head, self.delimiter)
        except Exception:
            delim = self.delimiter or ","

        self._table_file_map[table_name] = {
            "source_kind": source_kind,
            "table_name": table_name,
            "filepath": filepath,
            "zip_archive_path": zip_archive_path,
            "raw_bytes": raw_bytes,
            "encoding": enc,
            "delimiter": delim,
        }

    def test_connection(self) -> ConnectionTestResult:
        """Test file/directory readability, introspect tables, and compute latency."""
        start_time = time.perf_counter()
        try:
            self._discover_tables_and_files()
            self._is_connected = True
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            tables = sorted(list(self._table_file_map.keys()))
            if not tables and not self.dump_path and not self.zip_file_path and not self._in_memory_files:
                return ConnectionTestResult(
                    success=False,
                    message="No dump path, ZIP archive, or files specified for CSV Dump Connector",
                    latency_ms=elapsed_ms,
                    tables_count=0,
                    tables=[],
                    error="Missing source files or directory",
                )

            # Check if non-existent file or directory path was given
            if self.dump_path and not os.path.exists(str(self.dump_path)) and not self._in_memory_files:
                return ConnectionTestResult(
                    success=False,
                    message=f"Specified dump path does not exist: {self.dump_path}",
                    latency_ms=elapsed_ms,
                    tables_count=0,
                    tables=[],
                    error=f"Path not found: {self.dump_path}",
                )

            if self.zip_file_path and not os.path.exists(str(self.zip_file_path)) and not self._in_memory_files:
                return ConnectionTestResult(
                    success=False,
                    message=f"Specified ZIP archive does not exist: {self.zip_file_path}",
                    latency_ms=elapsed_ms,
                    tables_count=0,
                    tables=[],
                    error=f"ZIP not found: {self.zip_file_path}",
                )

            source_desc = "in-memory files"
            if self.zip_file_path:
                source_desc = f"ZIP archive: {self.zip_file_path}"
            elif self.dump_path:
                source_desc = f"path: {self.dump_path}"

            details = {
                "source_type": "csv_dump",
                "tables_indexed": len(tables),
                "source_description": source_desc,
                "file_formats": list(
                    set(meta.get("source_kind") for meta in self._table_file_map.values())
                ),
            }

            return ConnectionTestResult(
                success=True,
                message=f"Successfully connected to legacy dump source ({len(tables)} tables discovered)",
                latency_ms=elapsed_ms,
                server_version="CSV/SQL Dump Engine 1.0",
                database_name=Path(str(self.dump_path or self.zip_file_path or "dump")).stem,
                tables_count=len(tables),
                tables=tables,
                details=details,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"CSV dump connection test failed: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                latency_ms=elapsed_ms,
                tables_count=0,
                tables=[],
                error=str(e),
            )

    def get_tables(self) -> List[str]:
        """List all discovered table entities."""
        if not self._is_connected:
            self.connect()
        return sorted(list(self._table_file_map.keys()))

    def get_table_schema(self, table_name: str) -> TableSchema:
        """Introspect table schema, column types, and primary key heuristics."""
        if not self._is_connected:
            self.connect()

        matching_key = self._find_matching_table_key(table_name)
        if not matching_key:
            raise KeyError(f"Table '{table_name}' not found in CSV/dump sources. Available: {self.get_tables()}")

        if matching_key in self._table_schemas:
            return self._table_schemas[matching_key]

        meta = self._table_file_map[matching_key]

        # 1. SQL Dump Table
        if meta.get("source_kind") == "sql_dump" and matching_key in self._sql_dump_data:
            sql_entry = self._sql_dump_data[matching_key]
            cols = sql_entry.get("columns", [])
            pks = sql_entry.get("primary_key", [])
            rows = sql_entry.get("rows", [])
            schema = TableSchema(
                table_name=matching_key,
                columns=cols,
                primary_key=pks,
                foreign_keys=[],
                row_count_estimate=len(rows),
                description="Parsed from SQL dump script",
            )
            self._table_schemas[matching_key] = schema
            return schema

        # 2. CSV / File Source
        raw_bytes = meta.get("raw_bytes")
        if raw_bytes is None:
            raw_bytes = self._read_file_bytes(meta)

        enc = meta.get("encoding") or detect_encoding(raw_bytes, self.encoding)
        text = raw_bytes.decode(enc, errors="replace")
        delim = meta.get("delimiter") or detect_delimiter(text[:4096], self.delimiter)

        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            schema = TableSchema(
                table_name=matching_key,
                columns=[],
                primary_key=[],
                foreign_keys=[],
                row_count_estimate=0,
            )
            self._table_schemas[matching_key] = schema
            return schema

        has_hdr = detect_header(lines[:10], delimiter=delim, user_has_header=self.has_header)
        reader = csv.reader(io.StringIO(text), delimiter=delim, quotechar=self.quote_char)
        all_rows = list(reader)

        if not all_rows:
            schema = TableSchema(table_name=matching_key, columns=[], primary_key=[], row_count_estimate=0)
            self._table_schemas[matching_key] = schema
            return schema

        if has_hdr:
            raw_headers = all_rows[0]
            # Strip BOM from first header if present
            raw_headers = [h.lstrip("\ufeff").strip() for h in raw_headers]
            data_rows = all_rows[1:]
        else:
            first_row_len = len(all_rows[0])
            raw_headers = [f"column_{i+1}" for i in range(first_row_len)]
            data_rows = all_rows

        # Ensure header uniqueness and non-empty names
        headers: List[str] = []
        seen_headers: Set[str] = set()
        for idx, h in enumerate(raw_headers):
            name = h if h else f"column_{idx+1}"
            if name in seen_headers:
                suffix = 2
                while f"{name}_{suffix}" in seen_headers:
                    suffix += 1
                name = f"{name}_{suffix}"
            seen_headers.add(name)
            headers.append(name)

        # Sample up to 100 data rows for type inference
        sample_rows = data_rows[:100]
        columns: List[ColumnSchema] = []
        primary_keys: List[str] = []

        for idx, col_name in enumerate(headers):
            col_values = [row[idx] for row in sample_rows if idx < len(row)]
            inferred_type, is_nullable = infer_column_type(col_values)

            # Heuristic primary key detection
            is_pk = False
            col_lower = col_name.lower()
            if col_lower in ("id", f"{matching_key.lower()}_id", "code", "itemcode", "custcode", "sku"):
                is_pk = True
                primary_keys.append(col_name)

            columns.append(
                ColumnSchema(
                    name=col_name,
                    data_type=inferred_type,
                    is_nullable=is_nullable and not is_pk,
                    is_primary_key=is_pk,
                    ordinal_position=idx + 1,
                    raw_type=inferred_type,
                )
            )

        # Default PK if none matched
        if not primary_keys and columns:
            if columns[0].name.lower() in ("id", "code") or columns[0].data_type == "INTEGER":
                columns[0].is_primary_key = True
                columns[0].is_nullable = False
                primary_keys.append(columns[0].name)

        schema = TableSchema(
            table_name=matching_key,
            columns=columns,
            primary_key=primary_keys,
            foreign_keys=[],
            row_count_estimate=len(data_rows),
        )
        self._table_schemas[matching_key] = schema
        return schema

    def get_row_count(self, table_name: str, filter_condition: Optional[Any] = None) -> int:
        """Get total or filtered row count for a table."""
        if not self._is_connected:
            self.connect()

        matching_key = self._find_matching_table_key(table_name)
        if not matching_key:
            return 0

        count = 0
        for chunk in self.extract_chunks(matching_key, chunk_size=2000, filter_condition=filter_condition):
            count += len(chunk)
        return count

    def preview_table(
        self,
        table_name: str,
        limit: int = 100,
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a small sample preview of rows from a table."""
        if not self._is_connected:
            self.connect()

        matching_key = self._find_matching_table_key(table_name)
        if not matching_key:
            raise KeyError(f"Table '{table_name}' not found.")

        preview_rows: List[Dict[str, Any]] = []
        for chunk in self.extract_chunks(
            table_name=matching_key,
            chunk_size=limit,
            columns=columns,
        ):
            preview_rows.extend(chunk)
            if len(preview_rows) >= limit:
                break
        return preview_rows[:limit]

    def extract_chunks(
        self,
        table_name: str,
        chunk_size: int = 1000,
        columns: Optional[List[str]] = None,
        filter_condition: Optional[Any] = None,
        order_by: Optional[str] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream table rows in memory-safe chunks."""
        if not self._is_connected:
            self.connect()

        matching_key = self._find_matching_table_key(table_name)
        if not matching_key:
            raise KeyError(f"Table '{table_name}' not found.")

        meta = self._table_file_map[matching_key]
        schema = self.get_table_schema(matching_key)
        type_lookup = {col.name: col.data_type for col in schema.columns}

        # 1. SQL Dump Stream
        if meta.get("source_kind") == "sql_dump" and matching_key in self._sql_dump_data:
            rows = self._sql_dump_data[matching_key].get("rows", [])
            yield from self._stream_in_memory_rows(
                rows=rows,
                chunk_size=chunk_size,
                columns=columns,
                filter_condition=filter_condition,
                order_by=order_by,
                type_lookup=type_lookup,
            )
            return

        # 2. CSV Line-by-Line Streaming
        raw_bytes = meta.get("raw_bytes")
        if raw_bytes is None:
            raw_bytes = self._read_file_bytes(meta)

        enc = meta.get("encoding") or detect_encoding(raw_bytes, self.encoding)
        delim = meta.get("delimiter") or self.delimiter or ","

        text_stream = io.StringIO(raw_bytes.decode(enc, errors="replace"))
        reader = csv.reader(text_stream, delimiter=delim, quotechar=self.quote_char)

        try:
            first_line = next(reader)
        except StopIteration:
            return

        has_hdr = detect_header([",".join(first_line)], delimiter=delim, user_has_header=self.has_header)

        if has_hdr:
            raw_headers = [h.lstrip("\ufeff").strip() for h in first_line]
        else:
            raw_headers = [f"column_{i+1}" for i in range(len(first_line))]
            # Need to process first line as data row
            text_stream.seek(0)
            reader = csv.reader(text_stream, delimiter=delim, quotechar=self.quote_char)

        # Build clean header names matching schema
        header_names = schema.column_names if schema.column_names else raw_headers
        target_cols = columns if columns else header_names
        target_cols_set = set(target_cols)

        # If order_by is requested, we need to collect rows to sort
        if order_by:
            all_filtered: List[Dict[str, Any]] = []
            for row in reader:
                if not row or (len(row) == 1 and not row[0].strip()):
                    continue
                row_dict = self._build_row_dict(row, header_names, type_lookup, target_cols_set)
                if self._matches_filter(row_dict, filter_condition):
                    all_filtered.append(row_dict)

            # Sort
            reverse = False
            sort_key = order_by.strip()
            if sort_key.upper().endswith(" DESC"):
                sort_key = sort_key[:-5].strip()
                reverse = True
            elif sort_key.upper().endswith(" ASC"):
                sort_key = sort_key[:-4].strip()

            all_filtered.sort(key=lambda r: _sort_key_helper(r.get(sort_key)), reverse=reverse)

            for i in range(0, len(all_filtered), chunk_size):
                yield all_filtered[i : i + chunk_size]
            return

        # Normal chunked streaming without sorting
        chunk: List[Dict[str, Any]] = []
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue

            row_dict = self._build_row_dict(row, header_names, type_lookup, target_cols_set)

            if self._matches_filter(row_dict, filter_condition):
                chunk.append(row_dict)
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []

        if chunk:
            yield chunk

    def _build_row_dict(
        self,
        row: List[str],
        headers: List[str],
        type_lookup: Dict[str, str],
        target_cols_set: Set[str],
    ) -> Dict[str, Any]:
        """Convert CSV row into typed dictionary."""
        row_dict: Dict[str, Any] = {}
        for idx, col_name in enumerate(headers):
            if col_name not in target_cols_set:
                continue
            raw_val = row[idx] if idx < len(row) else None
            col_type = type_lookup.get(col_name, "VARCHAR")
            coerced = coerce_value(raw_val, col_type)
            row_dict[col_name] = self.serialize_value(coerced)
        return row_dict

    def _stream_in_memory_rows(
        self,
        rows: List[Dict[str, Any]],
        chunk_size: int,
        columns: Optional[List[str]],
        filter_condition: Optional[Any],
        order_by: Optional[str],
        type_lookup: Dict[str, str],
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream in-memory rows in chunks with filtering and sorting."""
        filtered_rows: List[Dict[str, Any]] = []
        for r in rows:
            if self._matches_filter(r, filter_condition):
                coerced_row: Dict[str, Any] = {}
                for k, v in r.items():
                    if columns and k not in columns:
                        continue
                    t = type_lookup.get(k, "VARCHAR")
                    val = coerce_value(v, t)
                    coerced_row[k] = self.serialize_value(val)
                filtered_rows.append(coerced_row)

        if order_by:
            reverse = False
            sort_key = order_by.strip()
            if sort_key.upper().endswith(" DESC"):
                sort_key = sort_key[:-5].strip()
                reverse = True
            elif sort_key.upper().endswith(" ASC"):
                sort_key = sort_key[:-4].strip()

            filtered_rows.sort(key=lambda x: _sort_key_helper(x.get(sort_key)), reverse=reverse)

        for i in range(0, len(filtered_rows), chunk_size):
            yield filtered_rows[i : i + chunk_size]

    def _matches_filter(self, row: Dict[str, Any], filter_condition: Optional[Any]) -> bool:
        """Check if row matches filter condition."""
        if filter_condition is None:
            return True
        if callable(filter_condition):
            return bool(filter_condition(row))
        if isinstance(filter_condition, dict):
            for k, v in filter_condition.items():
                if row.get(k) != v:
                    return False
            return True
        return True

    def _find_matching_table_key(self, table_name: str) -> Optional[str]:
        """Find matching table name ignoring case."""
        if table_name in self._table_file_map:
            return table_name

        name_lower = table_name.lower()
        for key in self._table_file_map:
            if key.lower() == name_lower:
                return key
        return None

    def _read_file_bytes(self, meta: Dict[str, Any]) -> bytes:
        """Read bytes for a file entry."""
        if meta.get("raw_bytes") is not None:
            return meta["raw_bytes"]

        source_kind = meta.get("source_kind")
        filepath = meta.get("filepath", "")

        if source_kind == "zip":
            zip_path = meta.get("zip_archive_path")
            if zip_path and os.path.isfile(zip_path):
                with zipfile.ZipFile(zip_path, "r") as z:
                    return z.read(filepath)
        elif source_kind == "file":
            if os.path.isfile(filepath):
                with open(filepath, "rb") as f:
                    return f.read()

        return b""
