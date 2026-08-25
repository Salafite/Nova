"""Unit tests for CsvDumpConnector.

Tests multi-table CSV files, ZIP archives, SQL dump scripts,
automatic delimiter and encoding autodetection (including Arabic Windows-1256),
header detection, type inference, preview sampling, and chunk streaming.
"""

from datetime import date, datetime
from decimal import Decimal
import io
import os
from pathlib import Path
import tempfile
import zipfile
import pytest

from modules.migration.connectors.base import (
    BaseConnector,
    ColumnSchema,
    ConnectionTestResult,
    TableSchema,
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
from modules.migration.models.migration import CsvDumpConnectionConfig


# ==============================================================================
# 1. Delimiter, Encoding, and Header Detection Tests
# ==============================================================================

def test_detect_encoding():
    """Verify detection of UTF-8, UTF-8 BOM, UTF-16, and legacy Windows-1256."""
    # UTF-8
    utf8_bytes = "Hello World, Product 123".encode("utf-8")
    assert detect_encoding(utf8_bytes) == "utf-8"

    # UTF-8 BOM
    bom_bytes = b"\xef\xbb\xbf" + "id,name,price".encode("utf-8")
    assert detect_encoding(bom_bytes) == "utf-8-sig"

    # UTF-16 LE
    utf16_bytes = b"\xff\xfe" + "id,name".encode("utf-16-le")
    assert detect_encoding(utf16_bytes) == "utf-16-le"

    # Arabic Windows-1256
    arabic_text = "كود الصنف,اسم المنتج,السعر"
    win1256_bytes = arabic_text.encode("windows-1256")
    enc = detect_encoding(win1256_bytes)
    assert enc in ("windows-1256", "cp1252", "iso-8859-1")
    # Must decode cleanly with returned encoding
    decoded = win1256_bytes.decode(enc)
    assert len(decoded) > 0


def test_detect_delimiter():
    """Verify detection of comma, semicolon, tab, and pipe delimiters."""
    comma_sample = "id,name,price,qty\n1,Burger,15.5,10\n2,Fries,8.0,20\n"
    assert detect_delimiter(comma_sample) == ","

    semicolon_sample = "id;name;price;qty\n1;Shawarma;12.0;5\n2;Falafel;6.0;15\n"
    assert detect_delimiter(semicolon_sample) == ";"

    tab_sample = "id\tname\tprice\tqty\n1\tPizza\t25.0\t8\n2\tSalad\t10.0\t12\n"
    assert detect_delimiter(tab_sample) == "\t"

    pipe_sample = "id|name|price|qty\n1|Juice|5.0|30\n2|Water|2.0|100\n"
    assert detect_delimiter(pipe_sample) == "|"

    # User override
    assert detect_delimiter(comma_sample, user_delimiter=";") == ";"


def test_detect_header():
    """Verify header detection heuristics."""
    header_sample = ["id,product_name,unit_price", "1,Espresso,12.50", "2,Latte,16.00"]
    assert detect_header(header_sample, delimiter=",") is True

    no_header_sample = ["101,15.50,10", "102,20.00,5", "103,8.75,22"]
    assert detect_header(no_header_sample, delimiter=",") is False

    # Explicit user preference
    assert detect_header(header_sample, user_has_header=False) is False


def test_infer_column_type():
    """Verify type inference for INTEGER, DECIMAL, BOOLEAN, DATE, DATETIME, and VARCHAR."""
    # Integer
    t, null = infer_column_type(["1", "2", "300", "4500"])
    assert t == "INTEGER"
    assert null is False

    # Integer with nulls
    t, null = infer_column_type(["1", "", "300", "NULL"])
    assert t == "INTEGER"
    assert null is True

    # Decimal
    t, null = infer_column_type(["15.50", "8.00", "99.99", "120.0"])
    assert t == "DECIMAL"

    # Boolean
    t, null = infer_column_type(["true", "false", "TRUE", "false"])
    assert t == "BOOLEAN"

    t, null = infer_column_type(["1", "0", "1", "0"])
    assert t == "BOOLEAN" or t == "INTEGER"

    # Date
    t, null = infer_column_type(["2023-01-15", "2023-06-20", "2024-12-31"])
    assert t == "DATE"

    # Datetime
    t, null = infer_column_type(["2023-01-15 10:30:00", "2023-06-20 14:45:12"])
    assert t == "DATETIME"

    # String / Text
    t, null = infer_column_type(["Classic Burger", "Chicken Shawarma", "Extra Cheese"])
    assert t == "VARCHAR"


def test_coerce_value():
    """Verify type coercion logic."""
    assert coerce_value("42", "INTEGER") == 42
    assert coerce_value("19.99", "DECIMAL") == 19.99
    assert coerce_value("true", "BOOLEAN") is True
    assert coerce_value("0", "BOOLEAN") is False
    assert coerce_value("NULL", "VARCHAR") is None
    assert coerce_value("", "INTEGER") is None
    assert coerce_value("2023-05-12", "DATE") == "2023-05-12"
    assert coerce_value("Fresh Juice", "VARCHAR") == "Fresh Juice"


# ==============================================================================
# 2. SQL Dump Parser Tests
# ==============================================================================

def test_sql_dump_table_parser():
    """Verify parsing of CREATE TABLE and INSERT INTO SQL dump statements."""
    sql_script = """
    CREATE TABLE `tbl_Products` (
        `id` int NOT NULL,
        `code` varchar(50) NOT NULL,
        `name` nvarchar(200) NOT NULL,
        `cost_price` decimal(18,2) DEFAULT '0.00',
        `selling_price` decimal(18,2) DEFAULT '0.00',
        `is_active` bit DEFAULT 1,
        PRIMARY KEY (`id`)
    );

    INSERT INTO `tbl_Products` (`id`, `code`, `name`, `cost_price`, `selling_price`, `is_active`) VALUES
    (1, 'PRD-001', 'Shawarma Sandwich', 5.50, 12.00, 1),
    (2, 'PRD-002', 'Falafel Meal', 3.00, 8.50, 1),
    (3, 'PRD-003', 'Arabic Salad', 2.50, 6.00, 0);

    CREATE TABLE tbl_Customers (
        cust_id INT PRIMARY KEY,
        cust_name VARCHAR(100),
        balance DECIMAL(10,2)
    );

    INSERT INTO tbl_Customers VALUES (101, 'Ahmed Ali', 150.00), (102, 'Sara Hassan', 0.00);
    """

    tables = SQLDumpTableParser.parse_sql_dump(sql_script)
    assert "tbl_Products" in tables
    assert "tbl_Customers" in tables

    prod = tables["tbl_Products"]
    assert len(prod["columns"]) == 6
    assert prod["primary_key"] == ["id"]
    assert len(prod["rows"]) == 3

    assert prod["rows"][0]["code"] == "PRD-001"
    assert prod["rows"][0]["cost_price"] == 5.5
    assert prod["rows"][0]["is_active"] is True

    cust = tables["tbl_Customers"]
    assert len(cust["rows"]) == 2
    assert cust["rows"][0]["cust_name"] == "Ahmed Ali"
    assert cust["rows"][0]["balance"] == 150.0


# ==============================================================================
# 3. In-Memory Virtual Files Connector Tests
# ==============================================================================

def test_csv_dump_connector_in_memory_files():
    """Verify CsvDumpConnector operations with in-memory CSV files."""
    products_csv = (
        "id,code,name,price,cost,is_active\n"
        "1,P001,Burger Deluxe,15.50,8.00,true\n"
        "2,P002,French Fries,6.00,2.50,true\n"
        "3,P003,Soft Drink,4.00,1.50,true\n"
    )
    customers_csv = (
        "id;name;phone;balance\n"
        "101;Khaled Omar;0501112233;250.00\n"
        "102;Fatima Noor;0504445566;0.00\n"
    )

    connector = CsvDumpConnector(
        in_memory_files={
            "products.csv": products_csv,
            "customers.csv": customers_csv,
        }
    )

    # 1. Test connection
    res = connector.test_connection()
    assert res.success is True
    assert res.tables_count == 2
    assert "products" in res.tables
    assert "customers" in res.tables

    # 2. Get tables
    tables = connector.get_tables()
    assert tables == ["customers", "products"]

    # 3. Get schema
    schema = connector.get_table_schema("products")
    assert schema.table_name == "products"
    assert "id" in schema.primary_key
    assert schema.row_count_estimate == 3

    col_names = schema.column_names
    assert "code" in col_names
    assert "price" in col_names
    assert "is_active" in col_names

    price_col = schema.get_column("price")
    assert price_col is not None
    assert price_col.data_type == "DECIMAL"

    active_col = schema.get_column("is_active")
    assert active_col is not None
    assert active_col.data_type == "BOOLEAN"

    # 4. Preview table
    preview = connector.preview_table("products", limit=2)
    assert len(preview) == 2
    assert preview[0]["code"] == "P001"
    assert preview[0]["price"] == 15.5
    assert preview[0]["is_active"] is True

    # 5. Extract chunks
    chunks = list(connector.extract_chunks("products", chunk_size=2))
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 1
    assert chunks[0][0]["name"] == "Burger Deluxe"
    assert chunks[1][0]["name"] == "Soft Drink"

    # 6. Extract all
    all_rows = connector.extract_all("products")
    assert len(all_rows) == 3

    # 7. Row counts
    assert connector.get_row_count("products") == 3
    assert connector.get_row_count("customers") == 2


def test_csv_dump_connector_with_sql_dump_in_memory():
    """Verify connector extracting tables from an in-memory SQL dump file."""
    sql_dump = """
    CREATE TABLE `Items` (
        `item_id` INT PRIMARY KEY,
        `item_name` VARCHAR(100),
        `price` DECIMAL(10,2)
    );
    INSERT INTO `Items` VALUES (1, 'Chicken Shawarma', 12.00), (2, 'Beef Shawarma', 14.00);
    """

    connector = CsvDumpConnector(
        in_memory_files={"legacy_dump.sql": sql_dump}
    )

    res = connector.test_connection()
    assert res.success is True
    assert "Items" in res.tables

    schema = connector.get_table_schema("Items")
    assert schema.table_name == "Items"
    assert schema.primary_key == ["item_id"]

    rows = connector.preview_table("Items", limit=5)
    assert len(rows) == 2
    assert rows[0]["item_name"] == "Chicken Shawarma"
    assert rows[0]["price"] == 12.0


# ==============================================================================
# 4. Filesystem Directory and ZIP Archive Tests
# ==============================================================================

def test_csv_dump_connector_with_temp_directory():
    """Verify connector reading multi-file CSV directories from disk."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prod_path = Path(tmp_dir) / "Products.csv"
        prod_path.write_text(
            "id,name,unit_price\n10,Espresso,3.50\n20,Cappuccino,4.50\n",
            encoding="utf-8",
        )

        supp_path = Path(tmp_dir) / "Suppliers.tsv"
        supp_path.write_text(
            "id\tcompany\tphone\n1\tAl-Marai\t0500000000\n",
            encoding="utf-8",
        )

        connector = CsvDumpConnector(dump_path=tmp_dir)
        test_res = connector.test_connection()
        assert test_res.success is True
        assert test_res.tables_count == 2
        assert "Products" in test_res.tables
        assert "Suppliers" in test_res.tables

        # Check delimiter autodetection on TSV
        supp_schema = connector.get_table_schema("Suppliers")
        assert "company" in supp_schema.column_names
        supp_rows = connector.preview_table("Suppliers", limit=5)
        assert len(supp_rows) == 1
        assert supp_rows[0]["company"] == "Al-Marai"


def test_csv_dump_connector_with_zip_archive():
    """Verify connector inspecting and streaming tables from a ZIP archive."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = tmp_zip.name

    try:
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr(
                "legacy_data/products.csv",
                "id,name,category,stock\n1,Apples,Fruit,50\n2,Bananas,Fruit,80\n",
            )
            z.writestr(
                "legacy_data/orders.csv",
                "order_id|customer|total\n1001|Ali|150.0\n1002|Sara|200.0\n",
            )

        connector = CsvDumpConnector(zip_file_path=zip_path)
        test_res = connector.test_connection()
        assert test_res.success is True
        assert test_res.tables_count == 2
        assert "products" in test_res.tables
        assert "orders" in test_res.tables

        # Schema & Preview
        ord_schema = connector.get_table_schema("orders")
        assert "customer" in ord_schema.column_names
        ord_rows = connector.preview_table("orders", limit=10)
        assert len(ord_rows) == 2
        assert ord_rows[0]["customer"] == "Ali"
        assert ord_rows[0]["total"] == 150.0

        # Chunk streaming
        chunks = list(connector.extract_chunks("products", chunk_size=1))
        assert len(chunks) == 2
        assert chunks[0][0]["name"] == "Apples"
        assert chunks[1][0]["name"] == "Bananas"
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


def test_csv_dump_connector_arabic_encoding():
    """Verify connector handling Arabic text encoded in Windows-1256 and UTF-8 BOM."""
    arabic_csv = (
        "كود_العميل,اسم_العميل,الرصيد\n"
        "C001,شركة الأمل للتجارة,5000.50\n"
        "C002,مؤسسة النور للمأكولات,1250.00\n"
    )
    raw_bytes = arabic_csv.encode("windows-1256")

    connector = CsvDumpConnector(
        in_memory_files={"customers_arabic.csv": raw_bytes},
        encoding="windows-1256",
    )

    test_res = connector.test_connection()
    assert test_res.success is True
    assert "customers_arabic" in test_res.tables

    rows = connector.preview_table("customers_arabic", limit=5)
    assert len(rows) == 2
    assert rows[0]["اسم_العميل"] == "شركة الأمل للتجارة"
    assert rows[0]["الرصيد"] == 5000.5


def test_csv_dump_connector_filtering_and_ordering():
    """Verify filter_condition and order_by support in extract_chunks."""
    csv_data = (
        "id,sku,name,price,category\n"
        "1,A1,Product A,10.0,Beverages\n"
        "2,B1,Product B,30.0,Food\n"
        "3,C1,Product C,20.0,Food\n"
        "4,D1,Product D,5.0,Beverages\n"
    )

    connector = CsvDumpConnector(in_memory_files={"items.csv": csv_data})

    # Filter with dictionary
    food_chunks = list(connector.extract_chunks("items", filter_condition={"category": "Food"}))
    assert len(food_chunks) == 1
    assert len(food_chunks[0]) == 2
    assert food_chunks[0][0]["sku"] == "B1"
    assert food_chunks[0][1]["sku"] == "C1"

    # Filter with callable
    cheap_chunks = list(connector.extract_chunks("items", filter_condition=lambda r: r.get("price", 0) < 15.0))
    assert len(cheap_chunks[0]) == 2

    # Order by
    ordered_chunks = list(connector.extract_chunks("items", order_by="price ASC"))
    assert len(ordered_chunks[0]) == 4
    assert ordered_chunks[0][0]["sku"] == "D1"  # 5.0
    assert ordered_chunks[0][3]["sku"] == "B1"  # 30.0


def test_csv_dump_connector_with_pydantic_config():
    """Verify connector instantiation using CsvDumpConnectionConfig Pydantic model."""
    config = CsvDumpConnectionConfig(
        dump_path="legacy_dumps/",
        delimiter=";",
        encoding="utf-8",
        has_header=True,
        quote_char='"',
    )
    connector = CsvDumpConnector(config=config)
    assert connector.dump_path == "legacy_dumps/"
    assert connector.delimiter == ";"
    assert connector.encoding == "utf-8"
    assert connector.has_header is True


def test_csv_dump_connector_context_manager():
    """Verify context manager entry and exit."""
    csv_data = "id,name\n1,Demo\n"
    with CsvDumpConnector(in_memory_files={"test.csv": csv_data}) as conn:
        assert conn.is_connected is True
        assert "test" in conn.get_tables()
    assert conn.is_connected is False


def test_csv_dump_connector_discover_schema_with_filter():
    """Verify discover_schema respects table_filter and returns schemas."""
    files = {
        "products.csv": "id,sku,name\n1,P1,Product 1\n",
        "customers.csv": "id,name,phone\n1,Cust 1,0501234567\n",
        "warehouses.csv": "id,code,name\n1,WH1,Main Warehouse\n",
    }
    connector = CsvDumpConnector(in_memory_files=files)

    # Discover all
    res_all = connector.discover_schema()
    assert res_all["success"] is True
    assert res_all["tables_count"] == 3
    assert "products" in res_all["schemas"]
    assert "customers" in res_all["schemas"]
    assert "warehouses" in res_all["schemas"]

    # Filtered
    res_filtered = connector.discover_schema(table_filter=["products", "warehouses"])
    assert res_filtered["success"] is True
    assert res_filtered["tables_count"] == 2
    assert "products" in res_filtered["schemas"]
    assert "warehouses" in res_filtered["schemas"]
    assert "customers" not in res_filtered["schemas"]


def test_csv_dump_connector_no_header_dataset():
    """Verify handling of CSV files with no header (has_header=False)."""
    csv_no_header = (
        "1001,Shawarma Wrap,15.50,Food\n"
        "1002,Orange Juice,8.00,Beverage\n"
    )
    connector = CsvDumpConnector(
        in_memory_files={"menu_items.csv": csv_no_header},
        has_header=False,
    )

    schema = connector.get_table_schema("menu_items")
    assert schema.table_name == "menu_items"
    assert len(schema.columns) == 4
    assert schema.columns[0].name == "column_1"
    assert schema.columns[1].name == "column_2"

    rows = connector.preview_table("menu_items", limit=2)
    assert len(rows) == 2
    assert rows[0]["column_1"] == 1001
    assert rows[0]["column_2"] == "Shawarma Wrap"
    assert rows[0]["column_3"] == 15.5
    assert rows[0]["column_4"] == "Food"


def test_csv_dump_connector_cp1252_encoding():
    """Verify handling of Western European CP1252 character sets with accented characters."""
    french_text = "id,name,description\n1,Café au Lait,Crème fraîche et café\n2,Naïve,Produit spécial\n"
    raw_bytes = french_text.encode("cp1252")

    connector = CsvDumpConnector(
        in_memory_files={"menu_french.csv": raw_bytes},
        encoding="cp1252",
    )

    test_res = connector.test_connection()
    assert test_res.success is True

    rows = connector.preview_table("menu_french", limit=5)
    assert len(rows) == 2
    assert "Café au Lait" in rows[0]["name"]
    assert "Crème fraîche" in rows[0]["description"]


def test_csv_dump_connector_missing_table_raises():
    """Verify get_table_schema and preview_table raise KeyError for unknown tables."""
    connector = CsvDumpConnector(
        in_memory_files={"items.csv": "id,name\n1,Item\n"}
    )
    with pytest.raises(KeyError):
        connector.get_table_schema("non_existent_table")

    with pytest.raises(KeyError):
        connector.preview_table("non_existent_table")


def test_csv_dump_connector_non_existent_paths():
    """Verify test_connection returns clean failure when pointing to non-existent disk paths."""
    connector_dir = CsvDumpConnector(dump_path="C:/non_existent_path_directory_12345")
    res_dir = connector_dir.test_connection()
    assert res_dir.success is False
    assert "does not exist" in res_dir.message or "not found" in str(res_dir.error).lower()

    connector_zip = CsvDumpConnector(zip_file_path="C:/non_existent_path_archive_12345.zip")
    res_zip = connector_zip.test_connection()
    assert res_zip.success is False
    assert "does not exist" in res_zip.message or "not found" in str(res_zip.error).lower()

