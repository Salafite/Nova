"""Unit tests for Automated Data Cleansing and Phantom Product Detection Engine.

Tests cover:
1. TextSanitizer (unicode normalization, Arabic digits, control characters, whitespace)
2. ContactSanitizer (phone cleaning, dummy phone filtering, email normalization, dummy email filtering)
3. PhantomProductDetector (inactivity thresholds, zero stock checks, cutoff dates, transaction overrides)
4. DeduplicationEngine (SKU/barcode deduplication, missing SKU generation, resolution strategies)
5. LookupValidator (default category/UOM/warehouse/customer group/terms assignment, lookup discovery)
6. NumericBoundsClamper (negative stock, negative price, tax rate bounds, rating bounds, credit limits)
7. CleansingService (single record cleansing, batch processing, phantom action policies, scan_phantom_products)
"""

from datetime import date, datetime, timedelta
import pytest

from modules.migration.models.migration import (
    CleansingLogItem,
    CleansingSummary,
    DataCleansingConfig,
)
from modules.migration.services.cleansing_service import (
    CleansingService,
    ContactSanitizer,
    DeduplicationEngine,
    LookupValidator,
    NumericBoundsClamper,
    PhantomProductDetector,
    TextSanitizer,
    cleansing_service,
)


# ==============================================================================
# 1. TextSanitizer Tests
# ==============================================================================

class TestTextSanitizer:
    def test_sanitize_none(self):
        assert TextSanitizer.sanitize(None) is None

    def test_sanitize_empty_and_whitespace(self):
        assert TextSanitizer.sanitize("") is None
        assert TextSanitizer.sanitize("   \t  \n  ") is None

    def test_sanitize_arabic_digits(self):
        # Eastern Arabic digits ٠١٢٣٤٥٦٧٨٩ -> 0123456789
        result = TextSanitizer.sanitize("المنتج رقم ١٢٣")
        assert result == "المنتج رقم 123"

    def test_sanitize_control_characters(self):
        raw = "Item\x00Name\x08With\x1fControls"
        result = TextSanitizer.sanitize(raw)
        assert result == "ItemNameWithControls"

    def test_sanitize_whitespace_collapsing(self):
        raw = "  Product   Name   with    spaces  "
        result = TextSanitizer.sanitize(raw)
        assert result == "Product Name with spaces"

    def test_preserve_newlines(self):
        raw = "Line 1\nLine 2\nLine 3"
        result = TextSanitizer.sanitize(raw)
        assert result == "Line 1\nLine 2\nLine 3"


# ==============================================================================
# 2. ContactSanitizer Tests
# ==============================================================================

class TestContactSanitizer:
    def test_sanitize_phone_none_or_empty(self):
        phone, mod, reason = ContactSanitizer.sanitize_phone(None)
        assert phone is None
        assert mod is False

        phone, mod, reason = ContactSanitizer.sanitize_phone("")
        assert phone is None
        assert mod is False

    def test_sanitize_phone_valid(self):
        phone, mod, reason = ContactSanitizer.sanitize_phone("  +1 (555) 123-4567  ")
        assert phone == "+15551234567"
        assert mod is True

        phone, mod, reason = ContactSanitizer.sanitize_phone("0501234567")
        assert phone == "0501234567"
        assert mod is False

    def test_sanitize_phone_arabic_numerals(self):
        phone, mod, reason = ContactSanitizer.sanitize_phone("٠٥٠١٢٣٤٥٦٧")
        assert phone == "0501234567"
        assert mod is True

    def test_sanitize_phone_dummy_filtering(self):
        for dummy in ["000", "0000000000", "123456", "n/a", "none", "null", "no phone", "99999999"]:
            phone, mod, reason = ContactSanitizer.sanitize_phone(dummy)
            assert phone is None
            assert mod is True

    def test_sanitize_phone_insufficient_digits(self):
        phone, mod, reason = ContactSanitizer.sanitize_phone("54321")
        assert phone is None
        assert mod is True
        assert "Insufficient digits" in reason

    def test_sanitize_email_none_or_empty(self):
        email, mod, reason = ContactSanitizer.sanitize_email(None)
        assert email is None
        assert mod is False

        email, mod, reason = ContactSanitizer.sanitize_email("   ")
        assert email is None
        assert mod is False

    def test_sanitize_email_valid(self):
        email, mod, reason = ContactSanitizer.sanitize_email("  User.Name@Example.COM  ")
        assert email == "user.name@example.com"
        assert mod is True

        email, mod, reason = ContactSanitizer.sanitize_email("test.user+tag@domain.co.uk")
        assert email == "test.user+tag@domain.co.uk"
        assert mod is False

    def test_sanitize_email_dummy_filtering(self):
        for dummy in ["none@none.com", "test@test.com", "test@example.com", "a@b.com", "null@null.com"]:
            email, mod, reason = ContactSanitizer.sanitize_email(dummy)
            assert email is None
            assert mod is True
            assert "placeholder" in reason

    def test_sanitize_email_invalid_format(self):
        for invalid in ["notanemail", "user@", "@domain.com", "user@domain"]:
            email, mod, reason = ContactSanitizer.sanitize_email(invalid)
            assert email is None
            assert mod is True
            assert "Invalid email format" in reason

    def test_sanitize_email_invalid_domain(self):
        for invalid in ["user@server.local", "test@domain.test", "admin@localhost"]:
            email, mod, reason = ContactSanitizer.sanitize_email(invalid)
            assert email is None
            assert mod is True


# ==============================================================================
# 3. PhantomProductDetector Tests
# ==============================================================================

class TestPhantomProductDetector:
    def test_parse_date_value(self):
        assert PhantomProductDetector.parse_date_value(None) is None
        assert PhantomProductDetector.parse_date_value(date(2025, 5, 1)) == date(2025, 5, 1)
        assert PhantomProductDetector.parse_date_value(datetime(2025, 5, 1, 10, 0)) == date(2025, 5, 1)
        assert PhantomProductDetector.parse_date_value("2025-05-01") == date(2025, 5, 1)
        assert PhantomProductDetector.parse_date_value("01/05/2025") == date(2025, 5, 1)
        # Epoch dates ignored
        assert PhantomProductDetector.parse_date_value("1970-01-01") is None
        assert PhantomProductDetector.parse_date_value("1900-01-01") is None

    def test_calculate_cutoff_date(self):
        ref = date(2026, 8, 1)
        cutoff = PhantomProductDetector.calculate_cutoff_date(reference_date=ref, inactivity_months=12)
        # ~365 days ago -> August 2025
        assert cutoff < date(2025, 9, 1)
        assert cutoff > date(2025, 7, 1)

    def test_evaluate_product_detection_disabled(self):
        cfg = DataCleansingConfig(enable_phantom_detection=False)
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            {"name": "Old Product", "last_transaction_date": "2020-01-01"},
            config=cfg,
        )
        assert is_phantom is False

    def test_evaluate_product_inactive_over_12_months(self):
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_inactivity_months=12)
        ref_date = date(2026, 8, 1)

        # Inactive for 3 years
        product = {
            "sku": "OLD-001",
            "name": "Discontinued Sauce",
            "last_transaction_date": "2023-01-15",
            "stock_quantity": 0,
        }
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            product,
            config=cfg,
            reference_date=ref_date,
        )
        assert is_phantom is True
        assert "No transaction activity" in reason
        assert last_dt == date(2023, 1, 15)

    def test_evaluate_product_recent_activity(self):
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_inactivity_months=12)
        ref_date = date(2026, 8, 1)

        # Active last month
        product = {
            "sku": "ACT-001",
            "name": "Fresh Milk",
            "last_transaction_date": "2026-07-10",
            "stock_quantity": 10,
        }
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            product,
            config=cfg,
            reference_date=ref_date,
        )
        assert is_phantom is False
        assert last_dt == date(2026, 7, 10)

    def test_evaluate_product_zero_stock_no_history(self):
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_zero_stock_check=True)
        product = {
            "sku": "NO-HIST-001",
            "name": "Ghost Item",
            "stock_quantity": 0,
        }
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            product,
            config=cfg,
        )
        assert is_phantom is True
        assert "zero/empty stock" in reason

    def test_evaluate_product_positive_stock_no_history(self):
        # Product has no transaction date but physical stock exists -> not phantom
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_zero_stock_check=True)
        product = {
            "sku": "STOCK-001",
            "name": "New Inventory Item",
            "stock_quantity": 50,
        }
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            product,
            config=cfg,
        )
        assert is_phantom is False

    def test_evaluate_product_preflagged_in_source(self):
        cfg = DataCleansingConfig(enable_phantom_detection=True)
        product = {
            "sku": "FLAG-001",
            "name": "Preflagged Phantom",
            "is_phantom": True,
        }
        is_phantom, reason, last_dt = PhantomProductDetector.evaluate_product(
            product,
            config=cfg,
        )
        assert is_phantom is True
        assert "Pre-flagged" in reason


# ==============================================================================
# 4. DeduplicationEngine Tests
# ==============================================================================

class TestDeduplicationEngine:
    def test_process_sku_missing_generation(self):
        engine = DeduplicationEngine()
        sku, mod, old, act = engine.process_sku(None, "Chicken Burger", "skip", 1)
        assert sku.startswith("SKU-CHICKE-00001")
        assert mod is True
        assert act == "generated_missing_sku"

    def test_process_sku_unique(self):
        engine = DeduplicationEngine()
        sku, mod, old, act = engine.process_sku("BURGER-01", "Burger", "skip", 1)
        assert sku == "BURGER-01"
        assert mod is False
        assert act == "unique"

    def test_process_sku_duplicate_skip(self):
        engine = DeduplicationEngine()
        engine.process_sku("BURGER-01", "Burger", "skip", 1)
        sku2, mod2, old2, act2 = engine.process_sku("BURGER-01", "Burger Duplicate", "skip", 2)
        assert sku2 is None
        assert mod2 is True
        assert act2 == "skipped_duplicate"

    def test_process_sku_duplicate_suffix(self):
        engine = DeduplicationEngine()
        engine.process_sku("BURGER-01", "Burger 1", "suffix", 1)
        sku2, mod2, old2, act2 = engine.process_sku("BURGER-01", "Burger 2", "suffix", 2)
        assert sku2 == "BURGER-01_DUP2"
        assert mod2 is True
        assert act2 == "suffixed_duplicate"

        sku3, mod3, old3, act3 = engine.process_sku("BURGER-01", "Burger 3", "suffix", 3)
        assert sku3 == "BURGER-01_DUP3"

    def test_process_sku_duplicate_overwrite(self):
        engine = DeduplicationEngine()
        engine.process_sku("BURGER-01", "Burger 1", "overwrite", 1)
        sku2, mod2, old2, act2 = engine.process_sku("BURGER-01", "Burger 2", "overwrite", 2)
        assert sku2 == "BURGER-01"
        assert mod2 is True
        assert act2 == "overwritten_duplicate"

    def test_process_barcode_deduplication(self):
        engine = DeduplicationEngine()
        # Empty barcode
        bc, mod, old, act = engine.process_barcode(None, "skip")
        assert bc is None

        # Unique barcode
        bc1, mod1, old1, act1 = engine.process_barcode("628100123456", "skip")
        assert bc1 == "628100123456"
        assert act1 == "unique"

        # Duplicate barcode with skip (cleared)
        bc2, mod2, old2, act2 = engine.process_barcode("628100123456", "skip")
        assert bc2 is None
        assert act2 == "cleared_duplicate_barcode"

        # Duplicate barcode with suffix
        engine.reset()
        engine.process_barcode("628100123456", "suffix")
        bc_suf, mod_suf, old_suf, act_suf = engine.process_barcode("628100123456", "suffix")
        assert bc_suf == "628100123456_DUP2"
        assert act_suf == "suffixed_duplicate_barcode"


# ==============================================================================
# 5. LookupValidator Tests
# ==============================================================================

class TestLookupValidator:
    def test_validate_product_lookups_defaults(self):
        validator = LookupValidator()
        cfg = DataCleansingConfig(default_category="Beverages", default_uom="BOTTLE")
        record = {"sku": "COLA-01", "name": "Cola"}

        logs = validator.validate_product_lookups(record, cfg)
        assert record["category"] == "Beverages"
        assert record["uom"] == "BOTTLE"
        assert len(logs) == 2

        lookups = validator.get_discovered_lookups()
        assert "Beverages" in lookups["categories"]
        assert "BOTTLE" in lookups["uoms"]

    def test_validate_warehouse_lookups_defaults(self):
        validator = LookupValidator()
        cfg = DataCleansingConfig(default_warehouse="Central Depot")
        record = {"sku": "COLA-01", "quantity": 100}

        logs = validator.validate_warehouse_lookups("inventory_opening", record, cfg)
        assert record["warehouse_name"] == "Central Depot"
        assert len(logs) == 1
        assert "Central Depot" in validator.get_discovered_lookups()["warehouses"]

    def test_validate_customer_lookups_defaults(self):
        validator = LookupValidator()
        record = {"name": "John Doe"}
        logs = validator.validate_customer_lookups(record)
        assert record["group_name"] == "Retail"
        assert len(logs) == 1
        assert "Retail" in validator.get_discovered_lookups()["customer_groups"]

    def test_validate_supplier_lookups_defaults(self):
        validator = LookupValidator()
        record = {"name": "Global Foods Ltd"}
        logs = validator.validate_supplier_lookups(record)
        assert record["payment_terms"] == "Net 30"
        assert record["category"] == "General"
        assert len(logs) == 1
        assert "Net 30" in validator.get_discovered_lookups()["payment_terms"]


# ==============================================================================
# 6. NumericBoundsClamper Tests
# ==============================================================================

class TestNumericBoundsClamper:
    def test_clamp_negative_stock(self):
        cfg = DataCleansingConfig(clamp_negative_stock=True)
        record = {"sku": "ITEM-1", "quantity": -15.5}
        logs = NumericBoundsClamper.clamp_record("inventory_opening", record, cfg)
        assert record["quantity"] == 0.0
        assert len(logs) == 1
        assert logs[0].rule == "clamp_negative_stock"

    def test_clamp_negative_price(self):
        cfg = DataCleansingConfig()
        record = {"sku": "ITEM-1", "price": -50.0, "cost_price": -20.0}
        logs = NumericBoundsClamper.clamp_record("products", record, cfg)
        assert record["price"] == 0.0
        assert record["cost_price"] == 0.0
        assert len(logs) == 2

    def test_clamp_tax_rate_bounds(self):
        cfg = DataCleansingConfig()
        record_neg = {"sku": "ITEM-1", "tax_rate": -5.0}
        logs_neg = NumericBoundsClamper.clamp_record("products", record_neg, cfg)
        assert record_neg["tax_rate"] == 0.0
        assert len(logs_neg) == 1

        record_excess = {"sku": "ITEM-2", "tax_rate": 150.0}
        logs_excess = NumericBoundsClamper.clamp_record("products", record_excess, cfg)
        assert record_excess["tax_rate"] == 100.0
        assert len(logs_excess) == 1

    def test_clamp_rating_bounds(self):
        cfg = DataCleansingConfig()
        record_low = {"name": "Supplier A", "rating": -1}
        NumericBoundsClamper.clamp_record("suppliers", record_low, cfg)
        assert record_low["rating"] == 0

        record_high = {"name": "Supplier B", "rating": 10}
        NumericBoundsClamper.clamp_record("suppliers", record_high, cfg)
        assert record_high["rating"] == 5

    def test_clamp_negative_credit_limit(self):
        cfg = DataCleansingConfig()
        record = {"name": "Customer A", "credit_limit": -1000.0}
        NumericBoundsClamper.clamp_record("customers", record, cfg)
        assert record["credit_limit"] == 0.0


# ==============================================================================
# 7. CleansingService End-to-End Orchestrator Tests
# ==============================================================================

class TestCleansingService:
    def test_cleanse_single_product_flag_phantom(self):
        svc = CleansingService()
        raw_product = {
            "sku": "OLD-999",
            "name": "  Legacy Item   ٠١٢  ",
            "price": -10.0,
            "tax_rate": 15.0,
            "last_transaction_date": "2020-01-01",
            "stock_quantity": 0,
        }
        cfg = DataCleansingConfig(
            enable_phantom_detection=True,
            phantom_action="flag",
            default_category="General",
            default_uom="PCS",
        )
        cleaned, logs = svc.cleanse_record(
            "products",
            raw_product,
            config=cfg,
            reference_date=date(2026, 8, 1),
        )

        assert cleaned is not None
        assert cleaned["name"] == "Legacy Item 012"
        assert cleaned["price"] == 0.0
        assert cleaned["category"] == "General"
        assert cleaned["uom"] == "PCS"
        assert cleaned["is_phantom"] is True
        assert len(logs) >= 3

    def test_cleanse_single_product_skip_phantom(self):
        svc = CleansingService()
        raw_product = {
            "sku": "OLD-999",
            "name": "Obsolete Item",
            "last_transaction_date": "2020-01-01",
        }
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_action="skip")
        cleaned, logs = svc.cleanse_record(
            "products",
            raw_product,
            config=cfg,
            reference_date=date(2026, 8, 1),
        )
        assert cleaned is None
        assert any(l.action_taken == "skipped_phantom_product" for l in logs)

    def test_cleanse_single_product_isolate_phantom(self):
        svc = CleansingService()
        raw_product = {
            "sku": "OLD-999",
            "name": "Obsolete Item",
            "last_transaction_date": "2020-01-01",
        }
        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_action="isolate")
        cleaned, logs = svc.cleanse_record(
            "products",
            raw_product,
            config=cfg,
            reference_date=date(2026, 8, 1),
        )
        assert cleaned is not None
        assert cleaned["is_phantom"] is True
        assert cleaned["is_active"] is False

    def test_cleanse_customer_record(self):
        svc = CleansingService()
        raw_customer = {
            "name": "  Al-Ameen Trading  ",
            "phone": "  +966 50 123 4567  ",
            "email": "contact@al-ameen.com",
            "credit_limit": -500.0,
        }
        cleaned, logs = svc.cleanse_record("customers", raw_customer)
        assert cleaned is not None
        assert cleaned["name"] == "Al-Ameen Trading"
        assert cleaned["phone"] == "+966501234567"
        assert cleaned["email"] == "contact@al-ameen.com"
        assert cleaned["credit_limit"] == 0.0
        assert cleaned["group_name"] == "Retail"

    def test_cleanse_records_list_and_summary(self):
        svc = CleansingService()
        ref_date = date(2026, 8, 1)

        products = [
            {"sku": "P1", "name": "Active Item 1", "last_transaction_date": "2026-07-01", "price": 10.0},
            {"sku": "P2", "name": "Active Item 2", "last_transaction_date": "2026-06-01", "price": 20.0},
            {"sku": "P3", "name": "Dead Item", "last_transaction_date": "2022-01-01", "stock_quantity": 0},
            {"sku": "P1", "name": "Duplicate P1", "last_transaction_date": "2026-07-01"},
        ]

        cfg = DataCleansingConfig(
            enable_phantom_detection=True,
            phantom_action="flag",
            deduplicate_skus=True,
            duplicate_resolution="suffix",
        )

        cleaned, summary = svc.cleanse_records(
            "products",
            products,
            config=cfg,
            reference_date=ref_date,
        )

        assert len(cleaned) == 4
        assert summary.total_records_processed == 4
        assert summary.phantom_products_detected == 1
        assert summary.duplicates_resolved == 1
        assert cleaned[3]["sku"] == "P1_DUP2"
        assert "General" in summary.discovered_lookups["categories"]

    def test_cleanse_batch_cross_entity_referencing(self):
        svc = CleansingService()
        ref_date = date(2026, 8, 1)

        dataset = {
            "products": [
                {"sku": "P1", "name": "Item with sales in orders", "price": 50.0, "stock_quantity": 0},
                {"sku": "P2", "name": "Item never sold", "price": 30.0, "stock_quantity": 0},
            ],
            "sales_order_items": [
                {"sku": "P1", "quantity": 5, "order_date": "2026-07-15"},
            ],
            "customers": [
                {"name": "Customer 1", "phone": "0501234567", "email": "test@test.com"},
            ],
        }

        cfg = DataCleansingConfig(enable_phantom_detection=True, phantom_action="flag")
        cleaned_batch, total_summary = svc.cleanse_batch(
            dataset,
            config=cfg,
            reference_date=ref_date,
        )

        assert "products" in cleaned_batch
        assert "customers" in cleaned_batch

        # P1 has transaction history in sales_order_items -> NOT phantom
        p1 = next(p for p in cleaned_batch["products"] if p["sku"] == "P1")
        assert p1["is_phantom"] is False

        # P2 has no transaction history and 0 stock -> phantom
        p2 = next(p for p in cleaned_batch["products"] if p["sku"] == "P2")
        assert p2["is_phantom"] is True

        # Customer 1 email was dummy (test@test.com) -> filtered to None
        c1 = cleaned_batch["customers"][0]
        assert c1["email"] is None

        assert total_summary.phantom_products_detected == 1
        assert total_summary.contacts_sanitized >= 1

    def test_scan_phantom_products(self):
        svc = CleansingService()
        ref_date = date(2026, 8, 1)

        prods = [
            {"sku": "A1", "name": "Live Product", "last_transaction_date": "2026-06-01"},
            {"sku": "A2", "name": "Ghost Product", "last_transaction_date": "2021-01-01", "stock": 0},
        ]

        active, phantoms, summary = svc.scan_phantom_products(prods, reference_date=ref_date)
        assert len(active) == 1
        assert active[0]["sku"] == "A1"
        assert len(phantoms) == 1
        assert phantoms[0]["sku"] == "A2"
        assert summary.phantom_products_detected == 1

    def test_custom_inactivity_thresholds(self):
        svc = CleansingService()
        ref_date = date(2026, 8, 1)

        # Product inactive for 8 months (since 2025-12-01)
        product = {
            "sku": "MID-001",
            "name": "Mid-Inactivity Item",
            "last_transaction_date": "2025-12-01",
            "stock_quantity": 0,
        }

        # Threshold 6 months -> should be phantom
        cfg_6m = DataCleansingConfig(enable_phantom_detection=True, phantom_inactivity_months=6)
        is_phantom, reason, _ = PhantomProductDetector.evaluate_product(
            product, config=cfg_6m, reference_date=ref_date
        )
        assert is_phantom is True

        # Threshold 12 months -> should NOT be phantom (only 8 months inactive)
        cfg_12m = DataCleansingConfig(enable_phantom_detection=True, phantom_inactivity_months=12)
        is_phantom_12, _, _ = PhantomProductDetector.evaluate_product(
            product, config=cfg_12m, reference_date=ref_date
        )
        assert is_phantom_12 is False

    def test_cleanse_empty_batch(self):
        svc = CleansingService()
        cleaned_batch, summary = svc.cleanse_batch({})
        assert cleaned_batch == {}
        assert summary.total_records_processed == 0

