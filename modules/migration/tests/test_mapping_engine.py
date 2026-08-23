"""Unit tests for the legacy entity and T-code schema mapping engine."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from modules.migration.models.migration import (
    FieldMappingRule,
    MigrationMappingConfig,
    TableMappingRule,
    TableMetadata,
    ColumnMetadata,
)
from modules.migration.services.mapping_engine import (
    DataCastingEngine,
    MappingEngine,
    calculate_similarity,
    mapping_engine,
    normalize_identifier,
    ENTITY_TARGET_SCHEMAS,
)


# ==============================================================================
# String Normalization & Similarity Tests
# ==============================================================================

def test_normalize_identifier_prefixes_and_separators():
    assert normalize_identifier("tbl_Products") == "products"
    assert normalize_identifier("tblItems") == "items"
    assert normalize_identifier("vw_Customer_List") == "customer_list"
    assert normalize_identifier("fld_Item_Code") == "item_code"
    assert normalize_identifier("dbo.Orders") == "orders"
    assert normalize_identifier("col_Unit_Price") == "unit_price"
    assert normalize_identifier("Item Name / Desc") == "item_name_desc"
    assert normalize_identifier("") == ""


def test_normalize_identifier_arabic():
    # Arabic letters normalization (alif variations, taa marbuta, yaa, diacritics)
    assert normalize_identifier("أصناف") == "اصناف"
    assert normalize_identifier("إجمالي") == "اجمالي"
    assert normalize_identifier("قائمة_الأسعار") == "قائمه_الاسعار"
    assert normalize_identifier("ضَرِيبَة") == "ضريبه"


def test_calculate_similarity():
    assert calculate_similarity("item_name", "item_name") == 1.0
    assert calculate_similarity("itemname", "item_name") >= 0.85
    assert calculate_similarity("product_code", "prod_code") >= 0.70
    assert calculate_similarity("completely_different", "item_name") < 0.50
    assert calculate_similarity("", "test") == 0.0


# ==============================================================================
# Data Type Casting & Value Transformation Tests
# ==============================================================================

class TestDataCastingEngine:
    def test_cast_string_and_transforms(self):
        assert DataCastingEngine.cast("  hello world  ", "string") == "hello world"
        assert DataCastingEngine.cast("hello", "string", transform="uppercase") == "HELLO"
        assert DataCastingEngine.cast("HELLO", "string", transform="lowercase") == "hello"
        assert DataCastingEngine.cast("  trimmed  ", "string", transform="trim") == "trimmed"
        assert DataCastingEngine.cast("john doe", "string", transform="titlecase") == "John Doe"
        assert DataCastingEngine.cast("+1 (555) 019-2834", "string", transform="sanitize_phone") == "+1 (555) 019-2834"
        assert DataCastingEngine.cast("  USER@Example.COM  ", "string", transform="sanitize_email") == "user@example.com"
        assert DataCastingEngine.cast("invalid-email", "string", transform="sanitize_email") is None
        assert DataCastingEngine.cast("", "string", default="DefaultVal") == "DefaultVal"

    def test_cast_int(self):
        assert DataCastingEngine.cast("123", "int") == 123
        assert DataCastingEngine.cast("1,234", "int") == 1234
        assert DataCastingEngine.cast("$500", "int") == 500
        assert DataCastingEngine.cast(45.0, "int") == 45
        assert DataCastingEngine.cast("45.00", "int") == 45
        assert DataCastingEngine.cast(Decimal("100"), "int") == 100
        assert DataCastingEngine.cast("invalid", "int", default=0) == 0

    def test_cast_float_and_decimal(self):
        assert DataCastingEngine.cast("123.45", "float") == 123.45
        assert DataCastingEngine.cast("1,234.56", "float") == 1234.56
        assert DataCastingEngine.cast("$99.99", "float") == 99.99
        assert DataCastingEngine.cast("€ 45.50", "float") == 45.50
        assert DataCastingEngine.cast("(150.75)", "float") == -150.75  # Accounting negative
        assert DataCastingEngine.cast(12.3456, "float", transform="round_2") == 12.35
        assert DataCastingEngine.cast(12.345678, "float", transform="round_4") == 12.3457
        assert DataCastingEngine.cast("invalid", "float", default=0.0) == 0.0

    def test_cast_bool(self):
        assert DataCastingEngine.cast("true", "bool") is True
        assert DataCastingEngine.cast("1", "bool") is True
        assert DataCastingEngine.cast(1, "bool") is True
        assert DataCastingEngine.cast("yes", "bool") is True
        assert DataCastingEngine.cast("Y", "bool") is True
        assert DataCastingEngine.cast("نعم", "bool") is True
        assert DataCastingEngine.cast("active", "bool") is True

        assert DataCastingEngine.cast("false", "bool") is False
        assert DataCastingEngine.cast("0", "bool") is False
        assert DataCastingEngine.cast(0, "bool") is False
        assert DataCastingEngine.cast("no", "bool") is False
        assert DataCastingEngine.cast("N", "bool") is False
        assert DataCastingEngine.cast("لا", "bool") is False
        assert DataCastingEngine.cast("inactive", "bool") is False
        assert DataCastingEngine.cast("", "bool", default=True) is True

    def test_cast_date(self):
        assert DataCastingEngine.cast("2024-05-18", "date") == "2024-05-18"
        assert DataCastingEngine.cast("18/05/2024", "date") == "2024-05-18"
        assert DataCastingEngine.cast("05/18/2024", "date") == "2024-05-18"
        assert DataCastingEngine.cast("2024/05/18", "date") == "2024-05-18"
        assert DataCastingEngine.cast("2024-05-18T14:30:00", "date") == "2024-05-18"
        assert DataCastingEngine.cast(date(2024, 5, 18), "date") == "2024-05-18"
        assert DataCastingEngine.cast(datetime(2024, 5, 18, 10, 0, 0), "date") == "2024-05-18"
        assert DataCastingEngine.cast("invalid-date", "date") is None

    def test_cast_datetime(self):
        assert "2024-05-18T14:30:00" in DataCastingEngine.cast("2024-05-18 14:30:00", "datetime")
        assert "2024-05-18" in DataCastingEngine.cast("2024-05-18", "datetime")
        assert DataCastingEngine.cast(date(2024, 5, 18), "datetime") == "2024-05-18T00:00:00"
        assert DataCastingEngine.cast("invalid", "datetime") is None

    def test_strict_mode(self):
        with pytest.raises(ValueError):
            DataCastingEngine.cast("not-a-number", "int", strict=True)


# ==============================================================================
# MappingEngine Heuristic Table & Column Matching Tests
# ==============================================================================

class TestMappingEngineHeuristics:
    @pytest.fixture
    def engine(self):
        return MappingEngine()

    def test_supported_entities(self, engine):
        entities = engine.get_supported_entities()
        assert "products" in entities
        assert "customers" in entities
        assert "suppliers" in entities
        assert "price_lists" in entities
        assert "price_list_items" in entities
        assert "chart_of_accounts" in entities
        assert "customer_opening_balances" in entities
        assert "payments" in entities
        assert "warehouses" in entities
        assert "inventory_opening" in entities
        assert "sales_orders" in entities
        assert "sales_order_items" in entities
        assert "purchase_orders" in entities
        assert "purchase_order_items" in entities

    def test_guess_entity_type_for_table(self, engine):
        assert engine.guess_entity_type_for_table("tbl_Items") == "products"
        assert engine.guess_entity_type_for_table("Products") == "products"
        assert engine.guess_entity_type_for_table("tbl_Customers") == "customers"
        assert engine.guess_entity_type_for_table("Clients") == "customers"
        assert engine.guess_entity_type_for_table("tbl_Vendors") == "suppliers"
        assert engine.guess_entity_type_for_table("Suppliers") == "suppliers"
        assert engine.guess_entity_type_for_table("tbl_PriceLists") == "price_lists"
        assert engine.guess_entity_type_for_table("tbl_PriceList_Items") == "price_list_items"
        assert engine.guess_entity_type_for_table("GL_Accounts") == "chart_of_accounts"
        assert engine.guess_entity_type_for_table("Customer_Opening_Balances") == "customer_opening_balances"
        assert engine.guess_entity_type_for_table("tbl_Warehouses") == "warehouses"
        assert engine.guess_entity_type_for_table("Stock_Opening") == "inventory_opening"
        assert engine.guess_entity_type_for_table("Sales_Invoices") == "sales_orders"
        assert engine.guess_entity_type_for_table("Sales_Details") == "sales_order_items"
        assert engine.guess_entity_type_for_table("PO_Headers") == "purchase_orders"
        assert engine.guess_entity_type_for_table("PO_Lines") == "purchase_order_items"

    def test_guess_entity_type_arabic_tables(self, engine):
        assert engine.guess_entity_type_for_table("اصناف") == "products"
        assert engine.guess_entity_type_for_table("العملاء") == "customers"
        assert engine.guess_entity_type_for_table("الموردين") == "suppliers"
        assert engine.guess_entity_type_for_table("دليل_الحسابات") == "chart_of_accounts"
        assert engine.guess_entity_type_for_table("رصيد_المخزون") == "inventory_opening"

    def test_match_discovered_tables(self, engine):
        discovered = [
            "tbl_Items",
            "tbl_Customers",
            "tbl_Vendors",
            "StockOnHand",
            "Unknown_Log_Table"
        ]
        matches = engine.match_discovered_tables(discovered)
        assert matches.get("products") == "tbl_Items"
        assert matches.get("customers") == "tbl_Customers"
        assert matches.get("suppliers") == "tbl_Vendors"

    def test_suggest_field_mappings_products(self, engine):
        source_cols = [
            "ItemCode",
            "ItemName",
            "Bar_Code",
            "SellingPrice",
            "UnitCost",
            "ItemGroup",
            "BrandName",
            "VatRate",
            "IsActive"
        ]
        suggestions = engine.suggest_field_mappings(source_cols, "products")
        assert suggestions.get("ItemCode") == "sku"
        assert suggestions.get("ItemName") == "name"
        assert suggestions.get("Bar_Code") == "barcode"
        assert suggestions.get("SellingPrice") == "price"
        assert suggestions.get("UnitCost") == "cost_price"
        assert suggestions.get("ItemGroup") == "category"
        assert suggestions.get("BrandName") == "brand"
        assert suggestions.get("VatRate") == "tax_rate"
        assert suggestions.get("IsActive") == "is_active"

    def test_suggest_field_mappings_arabic_columns(self, engine):
        source_cols = [
            "كود_الصنف",
            "اسم_الصنف",
            "سعر_البيع",
            "سعر_التكلفة",
            "التصنيف",
            "الباركود"
        ]
        suggestions = engine.suggest_field_mappings(source_cols, "products")
        assert suggestions.get("كود_الصنف") == "sku"
        assert suggestions.get("اسم_الصنف") == "name"
        assert suggestions.get("سعر_البيع") == "price"
        assert suggestions.get("سعر_التكلفة") == "cost_price"
        assert suggestions.get("التصنيف") == "category"
        assert suggestions.get("الباركود") == "barcode"

    def test_suggest_field_mappings_customers_and_balances(self, engine):
        cust_cols = ["CustName", "Phone_Number", "Email_Address", "CreditLimit", "Open_Balance"]
        cust_suggestions = engine.suggest_field_mappings(cust_cols, "customers")
        assert cust_suggestions.get("CustName") == "name"
        assert cust_suggestions.get("Phone_Number") == "phone"
        assert cust_suggestions.get("Email_Address") == "email"
        assert cust_suggestions.get("CreditLimit") == "credit_limit"
        assert cust_suggestions.get("Open_Balance") == "balance"


# ==============================================================================
# Mapping Configuration Generation & Row Translation Tests
# ==============================================================================

class TestMappingExecution:
    @pytest.fixture
    def engine(self):
        return MappingEngine()

    def test_create_table_mapping_rule(self, engine):
        cols = ["ItemCode", "ItemName", "Price", "Cost"]
        rule = engine.create_table_mapping_rule(
            entity_type="products",
            source_table="tbl_Items",
            source_columns=cols,
            custom_overrides={"Price": "price", "Cost": "cost_price"},
        )
        assert rule.entity_type == "products"
        assert rule.target_tcode == "T0003"
        assert rule.target_table == "t0003"
        assert rule.source_table == "tbl_Items"
        assert rule.field_mappings.get("ItemCode") == "sku"
        assert rule.field_mappings.get("ItemName") == "name"
        assert rule.field_mappings.get("Price") == "price"
        assert rule.field_mappings.get("Cost") == "cost_price"
        assert len(rule.advanced_field_rules) >= 4

    def test_generate_mapping_config(self, engine):
        discovered = {
            "tbl_Items": ["ItemCode", "ItemName", "Price"],
            "tbl_Customers": ["CustName", "Phone", "Email"],
        }
        config = engine.generate_mapping_config(discovered)
        assert isinstance(config, MigrationMappingConfig)
        assert "products" in config.mappings
        assert "customers" in config.mappings
        assert config.mappings["products"].source_table == "tbl_Items"
        assert config.mappings["customers"].source_table == "tbl_Customers"

    def test_map_single_row_products(self, engine):
        rule = engine.create_table_mapping_rule(
            entity_type="products",
            source_table="tbl_Items",
            source_columns=["ItemCode", "ItemName", "SellingPrice", "UnitCost", "Group", "Active"],
        )

        raw_row = {
            "ItemCode": "PROD-001",
            "ItemName": "Specialty Espresso Beans 1kg",
            "SellingPrice": "45.50",
            "UnitCost": "22.00",
            "Group": "Beverages",
            "Active": "1",
        }

        mapped, warnings = engine.map_row(raw_row, rule)
        assert mapped["sku"] == "PROD-001"
        assert mapped["name"] == "Specialty Espresso Beans 1kg"
        assert mapped["price"] == 45.50
        assert mapped["cost_price"] == 22.00
        assert mapped["category"] == "Beverages"
        assert mapped["is_active"] is True
        assert mapped["type"] == "stockable"  # Schema default
        assert len(warnings) == 0

    def test_map_row_missing_required_fields(self, engine):
        rule = engine.create_table_mapping_rule(
            entity_type="products",
            source_table="tbl_Items",
            source_columns=["ItemName", "SellingPrice"],
        )

        # Missing 'ItemCode' (sku is required)
        raw_row = {
            "ItemName": "Espresso Without SKU",
            "SellingPrice": "15.00",
        }

        mapped, warnings = engine.map_row(raw_row, rule, strict=False)
        assert any("Missing required field 'sku'" in w for w in warnings)

        with pytest.raises(ValueError):
            engine.map_row(raw_row, rule, strict=True)

    def test_map_rows_batch(self, engine):
        rule = engine.create_table_mapping_rule(
            entity_type="products",
            source_table="tbl_Items",
            source_columns=["ItemCode", "ItemName", "Price"],
        )

        batch_data = [
            {"ItemCode": "SKU-1", "ItemName": "Item 1", "Price": "10.00"},
            {"ItemCode": "SKU-2", "ItemName": "Item 2", "Price": "20.50"},
            {"ItemCode": None, "ItemName": "Invalid Item Missing SKU", "Price": "30.00"},
            {"ItemCode": "SKU-4", "ItemName": "Item 4", "Price": "40.00"},
        ]

        valid_records, errors = engine.map_rows(batch_data, rule)
        assert len(valid_records) == 3
        assert len(errors) == 1
        assert errors[0]["row_index"] == 2
        assert "Missing required field 'sku'" in errors[0]["error"]
        assert valid_records[0]["sku"] == "SKU-1"
        assert valid_records[1]["sku"] == "SKU-2"
        assert valid_records[2]["sku"] == "SKU-4"

    def test_map_row_customer_opening_balance(self, engine):
        rule = engine.create_table_mapping_rule(
            entity_type="customer_opening_balances",
            source_table="tbl_OpenBalances",
            source_columns=["InvNo", "CustID", "Amount", "InvDate", "Notes"],
        )

        raw_row = {
            "InvNo": "OB-2024-001",
            "CustID": "101",
            "Amount": "1,500.75",
            "InvDate": "2024-01-01",
            "Notes": "Opening balance from legacy system",
        }

        mapped, warnings = engine.map_row(raw_row, rule)
        assert mapped["invoice_number"] == "OB-2024-001"
        assert mapped["partner_id"] == 101
        assert mapped["total_amount"] == 1500.75
        assert mapped["issue_date"] == "2024-01-01"
        assert mapped["invoice_type"] == "OpeningBalance"
        assert mapped["status"] == "Posted"
        assert len(warnings) == 0
