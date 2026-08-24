"""Automated Data Cleansing and Phantom Product Detection Engine.

Provides:
1. Phantom product detection (inactivity threshold, zero stock, discontinued status, transaction referencing).
2. Deduplication engine for SKUs, barcodes, and unique business keys (skip, overwrite, suffix).
3. Contact sanitization for phone numbers and email addresses (cleaning, formatting, dummy filtering).
4. Foreign key validation and lookup auto-creation tracking (categories, UOMs, warehouses, customer groups).
5. Numeric bounds clamping (negative stock clamping, negative prices, tax rates, credit limits, ratings).
6. Text casing, whitespace normalization, and control character sanitization.
7. Detailed cleansing audit logs and aggregated CleansingSummary statistics.
"""

from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from modules.migration.models.migration import (
    CleansingLogItem,
    CleansingSummary,
    DataCleansingConfig,
)
from modules.migration.services.mapping_engine import DataCastingEngine


# ==============================================================================
# Helper Constants and Character Translations
# ==============================================================================

# Map Eastern Arabic (٠-٩) and Persian (۰-۹) digits to ASCII (0-9)
ARABIC_DIGITS_TABLE = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Common dummy or placeholder email patterns
DUMMY_EMAIL_PATTERNS = {
    "none@none.com",
    "no@email.com",
    "test@test.com",
    "test@example.com",
    "a@b.com",
    "null@null.com",
    "na@na.com",
    "no@mail.com",
    "noreply@example.com",
    "sample@sample.com",
    "admin@admin.com",
    "info@info.com",
}

# Common dummy or placeholder phone strings
DUMMY_PHONE_PATTERNS = {
    "0",
    "00",
    "000",
    "0000",
    "000000",
    "0000000000",
    "123",
    "1234",
    "12345",
    "123456",
    "123456789",
    "none",
    "null",
    "nil",
    "n/a",
    "na",
    "no phone",
    "test",
    "-",
    ".",
}

# Email validation regex (RFC 5322 compatible subset)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*(?:\.[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*)*\.[a-zA-Z]{2,}$"
)


# ==============================================================================
# 1. Text and String Sanitizer
# ==============================================================================

class TextSanitizer:
    """Sanitizes text strings, stripping control characters, normalizing whitespace."""

    @staticmethod
    def sanitize(text: Any) -> Optional[str]:
        """Normalize unicode, strip non-printable control characters, and collapse spaces."""
        if text is None:
            return None
        s = str(text)
        # Convert Eastern/Persian numerals
        s = s.translate(ARABIC_DIGITS_TABLE)
        # Normalize Unicode (NFC standard)
        s = unicodedata.normalize("NFC", s)
        # Remove null bytes and non-printable control characters (except newline, carriage return, tab)
        s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")
        # Collapse multiple spaces while preserving single newlines
        s = re.sub(r"[^\S\r\n]+", " ", s)
        s = s.strip()
        return s if s != "" else None


# ==============================================================================
# 2. Contact Information Sanitizer (Phone & Email)
# ==============================================================================

class ContactSanitizer:
    """Sanitizes and validates phone numbers and email addresses."""

    @staticmethod
    def sanitize_phone(phone: Any) -> Tuple[Optional[str], bool, Optional[str]]:
        """Sanitize phone number string.
        
        Returns:
            Tuple[Optional[str], bool, Optional[str]]: (cleaned_phone, was_modified, reason)
        """
        if phone is None:
            return None, False, None

        orig_str = str(phone).strip()
        if not orig_str:
            return None, False, None

        raw = orig_str.translate(ARABIC_DIGITS_TABLE)
        raw_lower = raw.lower()
        if raw_lower in DUMMY_PHONE_PATTERNS:
            return None, True, "Filtered placeholder phone number"

        # Check if leading plus exists
        has_plus = raw.startswith("+")

        # Strip all characters except digits
        digits_only = re.sub(r"[^\d]", "", raw)

        # Check if phone consists of only repetitive digits (e.g. 99999999)
        if len(digits_only) > 0 and len(set(digits_only)) == 1:
            return None, True, "Filtered repetitive dummy phone number"

        # A valid phone number usually needs at least 6 digits
        if len(digits_only) < 6:
            return None, True, f"Insufficient digits for valid phone ({len(digits_only)} digits)"

        formatted = f"+{digits_only}" if has_plus else digits_only

        was_modified = (formatted != orig_str)
        reason = "Normalized phone characters and formatting" if was_modified else None
        return formatted, was_modified, reason

    @staticmethod
    def sanitize_email(email: Any) -> Tuple[Optional[str], bool, Optional[str]]:
        """Sanitize and validate email address format.
        
        Returns:
            Tuple[Optional[str], bool, Optional[str]]: (cleaned_email, was_modified, reason)
        """
        if email is None:
            return None, False, None

        orig_str = str(email).strip()
        if not orig_str:
            return None, False, None

        raw = orig_str.translate(ARABIC_DIGITS_TABLE)
        cleaned = raw.lower()

        # Remove surrounding brackets or quotes
        cleaned = cleaned.strip("<>\"' ")

        if cleaned in DUMMY_EMAIL_PATTERNS:
            return None, True, "Filtered placeholder dummy email address"

        # Validate with regex
        if not EMAIL_REGEX.match(cleaned):
            return None, True, f"Invalid email format '{orig_str}'"

        # Check domain parts
        parts = cleaned.split("@")
        if len(parts) != 2:
            return None, True, f"Invalid email structure '{orig_str}'"

        user_part, domain_part = parts
        if domain_part.endswith(".local") or domain_part.endswith(".test") or domain_part == "localhost":
            return None, True, f"Invalid local/test domain '{domain_part}'"

        was_modified = (cleaned != orig_str)
        reason = "Normalized email casing and whitespace" if was_modified else None
        return cleaned, was_modified, reason


# ==============================================================================
# 3. Phantom Product Detection Engine
# ==============================================================================

class PhantomProductDetector:
    """Identifies and classifies phantom products based on transaction history and stock levels."""

    @staticmethod
    def parse_date_value(val: Any) -> Optional[date]:
        """Convert varied date/datetime inputs into a standard date object."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val

        # Handle numeric timestamps (Unix epochs)
        if isinstance(val, (int, float)):
            try:
                # Check for ms vs sec
                ts = val / 1000.0 if val > 1e11 else val
                return datetime.fromtimestamp(ts).date()
            except Exception:
                return None

        # Parse string dates
        parsed_dt = DataCastingEngine.to_datetime(val)
        if parsed_dt:
            try:
                d = date.fromisoformat(parsed_dt[:10])
                # Ignore epoch 1970-01-01 or 1900-01-01
                if d <= date(1970, 1, 2) or d <= date(1900, 1, 2):
                    return None
                return d
            except Exception:
                return None

        return None

    @staticmethod
    def calculate_cutoff_date(
        reference_date: Optional[Union[date, datetime]] = None,
        inactivity_months: int = 12,
    ) -> date:
        """Calculate the historical cutoff date for inactivity."""
        if reference_date is None:
            ref = date.today()
        elif isinstance(reference_date, datetime):
            ref = reference_date.date()
        else:
            ref = reference_date

        # Approximate months using average month length (~30.4375 days) or month math
        days_offset = int(inactivity_months * 30.4375)
        return ref - timedelta(days=days_offset)

    @classmethod
    def evaluate_product(
        cls,
        product: Dict[str, Any],
        config: DataCleansingConfig,
        reference_date: Optional[Union[date, datetime]] = None,
        last_tx_date_override: Optional[Union[date, datetime]] = None,
    ) -> Tuple[bool, Optional[str], Optional[date]]:
        """Evaluate if a product is a phantom product.
        
        Returns:
            Tuple[bool, Optional[str], Optional[date]]: (is_phantom, reason, last_activity_date)
        """
        if not config.enable_phantom_detection:
            return False, None, None

        cutoff = cls.calculate_cutoff_date(reference_date, config.phantom_inactivity_months)

        # 1. Determine last activity date
        last_date: Optional[date] = None
        if last_tx_date_override is not None:
            last_date = cls.parse_date_value(last_tx_date_override)
        else:
            for field_name in (
                "last_transaction_date",
                "last_order_date",
                "last_sold_date",
                "last_sale_date",
                "last_purchase_date",
                "last_activity_date",
                "transaction_date",
                "updated_at",
            ):
                val = product.get(field_name)
                if val is not None:
                    parsed = cls.parse_date_value(val)
                    if parsed:
                        last_date = parsed
                        break

        # 2. Determine stock quantity
        stock_val: Optional[float] = None
        for stock_field in (
            "stock_quantity",
            "quantity",
            "available_quantity",
            "stock",
            "qty",
            "opening_balance",
            "on_hand",
        ):
            if stock_field in product and product[stock_field] is not None:
                try:
                    stock_val = float(product[stock_field])
                    break
                except (ValueError, TypeError):
                    pass

        # 3. Check Explicit is_phantom flag from legacy source
        if product.get("is_phantom") is True:
            return True, "Pre-flagged as phantom in legacy source data", last_date

        # 4. Evaluation logic
        # Scenario A: Product has recorded transaction date
        if last_date is not None:
            if last_date < cutoff:
                months_ago = int((cutoff - last_date).days / 30.4375) + config.phantom_inactivity_months
                return (
                    True,
                    f"No transaction activity for {months_ago} months (last activity: {last_date.isoformat()})",
                    last_date,
                )
            return False, None, last_date

        # Scenario B: Product has NO recorded transaction date (never transacted or missing history)
        if config.phantom_zero_stock_check:
            # If stock is zero or missing, and no transaction history -> Phantom
            if stock_val is None or stock_val <= 0:
                return (
                    True,
                    "No transaction history and zero/empty stock on hand",
                    None,
                )
            # If stock > 0, keep active (has real physical inventory)
            return False, None, None

        # Scenario C: Inactive flag check when zero stock check is disabled
        is_inactive = (
            product.get("is_active") is False
            or str(product.get("status", "")).lower() in ("inactive", "discontinued", "deleted", "archived")
        )
        if is_inactive:
            return (
                True,
                "Discontinued or inactive product with no transaction history",
                None,
            )

        return False, None, None


# ==============================================================================
# 4. Deduplication Engine
# ==============================================================================

class DeduplicationEngine:
    """Tracks and deduplicates unique entity keys across migration batches."""

    def __init__(self) -> None:
        self.seen_skus: Set[str] = set()
        self.seen_barcodes: Set[str] = set()
        self.seen_customer_phones: Set[str] = set()
        self.seen_customer_emails: Set[str] = set()
        self.sku_counts: Dict[str, int] = {}
        self.barcode_counts: Dict[str, int] = {}

    def reset(self) -> None:
        """Reset deduplication caches."""
        self.seen_skus.clear()
        self.seen_barcodes.clear()
        self.seen_customer_phones.clear()
        self.seen_customer_emails.clear()
        self.sku_counts.clear()
        self.barcode_counts.clear()

    def process_sku(
        self,
        sku: Optional[str],
        product_name: Optional[str],
        resolution: str,
        index: int,
    ) -> Tuple[Optional[str], bool, Optional[str], str]:
        """Process SKU for deduplication or missing value generation.
        
        Returns:
            Tuple[Optional[str], bool, Optional[str], str]: (final_sku, was_modified, old_sku, action_taken)
        """
        raw_sku = (sku or "").strip()

        # Handle missing SKU
        if not raw_sku:
            base_name = re.sub(r"[^\w]", "", (product_name or "PROD").upper())[:6] or "PROD"
            generated_sku = f"SKU-{base_name}-{index:05d}"
            norm_gen = generated_sku.upper()
            self.seen_skus.add(norm_gen)
            self.sku_counts[norm_gen] = 1
            return generated_sku, True, None, "generated_missing_sku"

        norm_sku = raw_sku.upper()

        if norm_sku not in self.seen_skus:
            self.seen_skus.add(norm_sku)
            self.sku_counts[norm_sku] = 1
            return raw_sku, False, raw_sku, "unique"

        # Duplicate detected
        self.sku_counts[norm_sku] = self.sku_counts.get(norm_sku, 1) + 1
        count = self.sku_counts[norm_sku]

        if resolution == "skip":
            return None, True, raw_sku, "skipped_duplicate"
        elif resolution == "overwrite":
            return raw_sku, True, raw_sku, "overwritten_duplicate"
        elif resolution == "suffix":
            suffixed_sku = f"{raw_sku}_DUP{count}"
            self.seen_skus.add(suffixed_sku.upper())
            return suffixed_sku, True, raw_sku, "suffixed_duplicate"
        else:
            return raw_sku, False, raw_sku, "unresolved_duplicate"

    def process_barcode(
        self,
        barcode: Optional[str],
        resolution: str,
    ) -> Tuple[Optional[str], bool, Optional[str], str]:
        """Process barcode for duplicate handling.
        
        Returns:
            Tuple[Optional[str], bool, Optional[str], str]: (final_barcode, was_modified, old_barcode, action_taken)
        """
        if barcode is None:
            return None, False, None, "none"

        raw_barcode = str(barcode).strip()
        if not raw_barcode:
            return None, False, None, "empty"

        norm_barcode = raw_barcode.upper()

        if norm_barcode not in self.seen_barcodes:
            self.seen_barcodes.add(norm_barcode)
            self.barcode_counts[norm_barcode] = 1
            return raw_barcode, False, raw_barcode, "unique"

        self.barcode_counts[norm_barcode] = self.barcode_counts.get(norm_barcode, 1) + 1
        count = self.barcode_counts[norm_barcode]

        if resolution == "skip":
            # Clear duplicate barcode on this entity
            return None, True, raw_barcode, "cleared_duplicate_barcode"
        elif resolution == "overwrite":
            return raw_barcode, True, raw_barcode, "overwritten_duplicate_barcode"
        elif resolution == "suffix":
            suffixed_barcode = f"{raw_barcode}_DUP{count}"
            self.seen_barcodes.add(suffixed_barcode.upper())
            return suffixed_barcode, True, raw_barcode, "suffixed_duplicate_barcode"
        else:
            return raw_barcode, False, raw_barcode, "unresolved_duplicate"


# ==============================================================================
# 5. Foreign Key & Lookup Integrity Validator
# ==============================================================================

class LookupValidator:
    """Validates categories, UOMs, warehouses, and tracks discovered lookup entities."""

    def __init__(self) -> None:
        self.discovered_categories: Set[str] = set()
        self.discovered_uoms: Set[str] = set()
        self.discovered_warehouses: Set[str] = set()
        self.discovered_brands: Set[str] = set()
        self.discovered_customer_groups: Set[str] = set()
        self.discovered_payment_terms: Set[str] = set()

    def reset(self) -> None:
        """Reset discovered lookup sets."""
        self.discovered_categories.clear()
        self.discovered_uoms.clear()
        self.discovered_warehouses.clear()
        self.discovered_brands.clear()
        self.discovered_customer_groups.clear()
        self.discovered_payment_terms.clear()

    def get_discovered_lookups(self) -> Dict[str, List[str]]:
        """Return sorted dictionary of all discovered lookup entities."""
        return {
            "categories": sorted(list(self.discovered_categories)),
            "uoms": sorted(list(self.discovered_uoms)),
            "warehouses": sorted(list(self.discovered_warehouses)),
            "brands": sorted(list(self.discovered_brands)),
            "customer_groups": sorted(list(self.discovered_customer_groups)),
            "payment_terms": sorted(list(self.discovered_payment_terms)),
        }

    def validate_product_lookups(
        self,
        record: Dict[str, Any],
        config: DataCleansingConfig,
    ) -> List[CleansingLogItem]:
        """Validate and populate product category, UOM, and brand."""
        logs: List[CleansingLogItem] = []
        source_key = str(record.get("sku") or record.get("name") or "")

        # 1. Category
        cat = record.get("category")
        if not cat or str(cat).strip() == "":
            record["category"] = config.default_category
            logs.append(
                CleansingLogItem(
                    entity_type="products",
                    source_key=source_key,
                    rule="lookup_default_category",
                    field_name="category",
                    original_value=cat,
                    cleansed_value=config.default_category,
                    action_taken="assigned_default",
                    message=f"Missing category defaulted to '{config.default_category}'",
                )
            )
            self.discovered_categories.add(config.default_category)
        else:
            clean_cat = str(cat).strip()
            record["category"] = clean_cat
            self.discovered_categories.add(clean_cat)

        # 2. UOM (Unit of Measure)
        uom = record.get("uom") or record.get("unit_of_measure") or record.get("uom_name")
        if not uom or str(uom).strip() == "":
            record["uom"] = config.default_uom
            logs.append(
                CleansingLogItem(
                    entity_type="products",
                    source_key=source_key,
                    rule="lookup_default_uom",
                    field_name="uom",
                    original_value=uom,
                    cleansed_value=config.default_uom,
                    action_taken="assigned_default",
                    message=f"Missing UOM defaulted to '{config.default_uom}'",
                )
            )
            self.discovered_uoms.add(config.default_uom)
        else:
            clean_uom = str(uom).strip().upper()
            record["uom"] = clean_uom
            self.discovered_uoms.add(clean_uom)

        # 3. Brand
        brand = record.get("brand")
        if brand and str(brand).strip() != "":
            clean_brand = str(brand).strip()
            record["brand"] = clean_brand
            self.discovered_brands.add(clean_brand)

        return logs

    def validate_warehouse_lookups(
        self,
        entity_type: str,
        record: Dict[str, Any],
        config: DataCleansingConfig,
    ) -> List[CleansingLogItem]:
        """Validate warehouse and location names in inventory/order records."""
        logs: List[CleansingLogItem] = []
        source_key = str(record.get("sku") or record.get("name") or record.get("id") or "")

        wh = record.get("warehouse_name") or record.get("warehouse") or record.get("location")
        if not wh or str(wh).strip() == "":
            record["warehouse_name"] = config.default_warehouse
            logs.append(
                CleansingLogItem(
                    entity_type=entity_type,
                    source_key=source_key,
                    rule="lookup_default_warehouse",
                    field_name="warehouse_name",
                    original_value=wh,
                    cleansed_value=config.default_warehouse,
                    action_taken="assigned_default",
                    message=f"Missing warehouse defaulted to '{config.default_warehouse}'",
                )
            )
            self.discovered_warehouses.add(config.default_warehouse)
        else:
            clean_wh = str(wh).strip()
            record["warehouse_name"] = clean_wh
            self.discovered_warehouses.add(clean_wh)

        return logs

    def validate_customer_lookups(
        self,
        record: Dict[str, Any],
    ) -> List[CleansingLogItem]:
        """Validate customer group lookups."""
        logs: List[CleansingLogItem] = []
        source_key = str(record.get("name") or record.get("id") or "")

        group = record.get("group_name") or record.get("customer_group")
        if not group or str(group).strip() == "":
            record["group_name"] = "Retail"
            logs.append(
                CleansingLogItem(
                    entity_type="customers",
                    source_key=source_key,
                    rule="lookup_default_customer_group",
                    field_name="group_name",
                    original_value=group,
                    cleansed_value="Retail",
                    action_taken="assigned_default",
                    message="Missing customer group defaulted to 'Retail'",
                )
            )
            self.discovered_customer_groups.add("Retail")
        else:
            clean_group = str(group).strip()
            record["group_name"] = clean_group
            self.discovered_customer_groups.add(clean_group)

        return logs

    def validate_supplier_lookups(
        self,
        record: Dict[str, Any],
    ) -> List[CleansingLogItem]:
        """Validate supplier payment terms and category lookups."""
        logs: List[CleansingLogItem] = []
        source_key = str(record.get("name") or record.get("id") or "")

        # Payment terms
        terms = record.get("payment_terms")
        if not terms or str(terms).strip() == "":
            record["payment_terms"] = "Net 30"
            logs.append(
                CleansingLogItem(
                    entity_type="suppliers",
                    source_key=source_key,
                    rule="lookup_default_payment_terms",
                    field_name="payment_terms",
                    original_value=terms,
                    cleansed_value="Net 30",
                    action_taken="assigned_default",
                    message="Missing payment terms defaulted to 'Net 30'",
                )
            )
            self.discovered_payment_terms.add("Net 30")
        else:
            clean_terms = str(terms).strip()
            record["payment_terms"] = clean_terms
            self.discovered_payment_terms.add(clean_terms)

        # Supplier Category
        cat = record.get("category")
        if not cat or str(cat).strip() == "":
            record["category"] = "General"
            self.discovered_categories.add("General")
        else:
            clean_cat = str(cat).strip()
            record["category"] = clean_cat
            self.discovered_categories.add(clean_cat)

        return logs


# ==============================================================================
# 6. Numeric Bounds and Clamping Engine
# ==============================================================================

class NumericBoundsClamper:
    """Clamps numeric values into valid domains (stock, price, tax, rating, balance)."""

    @staticmethod
    def clamp_record(
        entity_type: str,
        record: Dict[str, Any],
        config: DataCleansingConfig,
    ) -> List[CleansingLogItem]:
        """Clamp numeric fields in a record.
        
        Returns:
            List[CleansingLogItem]: Log of all values modified by clamping
        """
        logs: List[CleansingLogItem] = []
        source_key = str(
            record.get("sku")
            or record.get("invoice_number")
            or record.get("order_number")
            or record.get("name")
            or record.get("id")
            or ""
        )

        # 1. Negative Stock Clamping
        if config.clamp_negative_stock:
            for field in ("quantity", "stock_quantity", "available_quantity", "opening_balance", "qty"):
                if field in record and record[field] is not None:
                    try:
                        val = float(record[field])
                        if val < 0:
                            record[field] = 0.0
                            logs.append(
                                CleansingLogItem(
                                    entity_type=entity_type,
                                    source_key=source_key,
                                    rule="clamp_negative_stock",
                                    field_name=field,
                                    original_value=val,
                                    cleansed_value=0.0,
                                    action_taken="clamped_to_zero",
                                    message=f"Negative stock {val} clamped to 0.0",
                                )
                            )
                    except (ValueError, TypeError):
                        pass

        # 2. Price and Cost bounds (must be >= 0)
        for field in ("price", "cost_price", "unit_price", "total_cost", "total_price"):
            if field in record and record[field] is not None:
                try:
                    val = float(record[field])
                    if val < 0:
                        record[field] = 0.0
                        logs.append(
                            CleansingLogItem(
                                entity_type=entity_type,
                                source_key=source_key,
                                rule="clamp_negative_price",
                                field_name=field,
                                original_value=val,
                                cleansed_value=0.0,
                                action_taken="clamped_to_zero",
                                message=f"Negative price {val} clamped to 0.0",
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # 3. Tax rate bounds (0 <= tax_rate <= 100)
        if "tax_rate" in record and record["tax_rate"] is not None:
            try:
                tax = float(record["tax_rate"])
                if tax < 0:
                    record["tax_rate"] = 0.0
                    logs.append(
                        CleansingLogItem(
                            entity_type=entity_type,
                            source_key=source_key,
                            rule="clamp_tax_rate_min",
                            field_name="tax_rate",
                            original_value=tax,
                            cleansed_value=0.0,
                            action_taken="clamped_to_zero",
                            message=f"Negative tax rate {tax} clamped to 0.0",
                        )
                    )
                elif tax > 100:
                    record["tax_rate"] = 100.0
                    logs.append(
                        CleansingLogItem(
                            entity_type=entity_type,
                            source_key=source_key,
                            rule="clamp_tax_rate_max",
                            field_name="tax_rate",
                            original_value=tax,
                            cleansed_value=100.0,
                            action_taken="clamped_to_max",
                            message=f"Excessive tax rate {tax} clamped to 100.0",
                        )
                    )
            except (ValueError, TypeError):
                pass

        # 4. Supplier rating bounds (0 <= rating <= 5)
        if "rating" in record and record["rating"] is not None:
            try:
                rating = int(record["rating"])
                if rating < 0:
                    record["rating"] = 0
                    logs.append(
                        CleansingLogItem(
                            entity_type=entity_type,
                            source_key=source_key,
                            rule="clamp_rating_min",
                            field_name="rating",
                            original_value=rating,
                            cleansed_value=0,
                            action_taken="clamped_to_zero",
                            message=f"Negative rating {rating} clamped to 0",
                        )
                    )
                elif rating > 5:
                    record["rating"] = 5
                    logs.append(
                        CleansingLogItem(
                            entity_type=entity_type,
                            source_key=source_key,
                            rule="clamp_rating_max",
                            field_name="rating",
                            original_value=rating,
                            cleansed_value=5,
                            action_taken="clamped_to_max",
                            message=f"Rating {rating} clamped to max 5",
                        )
                    )
            except (ValueError, TypeError):
                pass

        # 5. Customer credit limit (credit_limit >= 0)
        if "credit_limit" in record and record["credit_limit"] is not None:
            try:
                cl = float(record["credit_limit"])
                if cl < 0:
                    record["credit_limit"] = 0.0
                    logs.append(
                        CleansingLogItem(
                            entity_type=entity_type,
                            source_key=source_key,
                            rule="clamp_credit_limit",
                            field_name="credit_limit",
                            original_value=cl,
                            cleansed_value=0.0,
                            action_taken="clamped_to_zero",
                            message=f"Negative credit limit {cl} clamped to 0.0",
                        )
                    )
            except (ValueError, TypeError):
                pass

        return logs


# ==============================================================================
# 7. Main Cleansing Service Orchestrator
# ==============================================================================

class CleansingService:
    """Complete data cleansing, phantom detection, deduplication, and normalization service."""

    def __init__(self) -> None:
        self.text_sanitizer = TextSanitizer()
        self.contact_sanitizer = ContactSanitizer()
        self.phantom_detector = PhantomProductDetector()
        self.dedup_engine = DeduplicationEngine()
        self.lookup_validator = LookupValidator()
        self.numeric_clamper = NumericBoundsClamper()

    def reset_session(self) -> None:
        """Reset stateful deduplication and lookup collection structures."""
        self.dedup_engine.reset()
        self.lookup_validator.reset()

    def cleanse_record(
        self,
        entity_type: str,
        raw_record: Dict[str, Any],
        config: Optional[DataCleansingConfig] = None,
        index: int = 1,
        reference_date: Optional[Union[date, datetime]] = None,
        last_tx_date_override: Optional[Union[date, datetime]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], List[CleansingLogItem]]:
        """Cleanse a single record across all normalization and validation rules.
        
        Returns:
            Tuple[Optional[Dict[str, Any]], List[CleansingLogItem]]:
                (cleansed_record, list_of_log_items). If record is dropped/skipped, record is None.
        """
        cfg = config or DataCleansingConfig()
        record = deepcopy(raw_record)
        logs: List[CleansingLogItem] = []

        source_key = str(
            record.get("sku")
            or record.get("invoice_number")
            or record.get("order_number")
            or record.get("name")
            or record.get("id")
            or f"row_{index}"
        )

        # Step 1: Text Casing and Whitespace Normalization
        if cfg.normalize_text_casing:
            for k, v in list(record.items()):
                if isinstance(v, str):
                    cleaned_txt = self.text_sanitizer.sanitize(v)
                    if cleaned_txt != v:
                        record[k] = cleaned_txt

        # Step 2: Contact Info Sanitization (Phone & Email)
        if cfg.sanitize_phone_numbers:
            for phone_field in ("phone", "mobile", "telephone", "contact_phone"):
                if phone_field in record and record[phone_field] is not None:
                    orig_phone = record[phone_field]
                    clean_phone, was_mod, reason = self.contact_sanitizer.sanitize_phone(orig_phone)
                    if was_mod:
                        record[phone_field] = clean_phone
                        logs.append(
                            CleansingLogItem(
                                entity_type=entity_type,
                                source_key=source_key,
                                rule="sanitize_phone",
                                field_name=phone_field,
                                original_value=orig_phone,
                                cleansed_value=clean_phone,
                                action_taken="sanitized_phone",
                                message=reason or "Sanitized phone number format",
                            )
                        )

        if cfg.sanitize_email_addresses:
            for email_field in ("email", "contact_email", "mail"):
                if email_field in record and record[email_field] is not None:
                    orig_email = record[email_field]
                    clean_email, was_mod, reason = self.contact_sanitizer.sanitize_email(orig_email)
                    if was_mod:
                        record[email_field] = clean_email
                        logs.append(
                            CleansingLogItem(
                                entity_type=entity_type,
                                source_key=source_key,
                                rule="sanitize_email",
                                field_name=email_field,
                                original_value=orig_email,
                                cleansed_value=clean_email,
                                action_taken="sanitized_email",
                                message=reason or "Sanitized email address format",
                            )
                        )

        # Step 3: Entity-Specific Cleansing Rules
        if entity_type == "products":
            # 3A. Phantom Product Detection
            is_phantom, phantom_reason, last_date = self.phantom_detector.evaluate_product(
                record,
                cfg,
                reference_date=reference_date,
                last_tx_date_override=last_tx_date_override,
            )

            if is_phantom:
                action = cfg.phantom_action
                if action == "skip":
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="phantom_product_skip",
                            field_name="is_phantom",
                            original_value=False,
                            cleansed_value=True,
                            action_taken="skipped_phantom_product",
                            message=f"Product skipped: {phantom_reason}",
                        )
                    )
                    return None, logs
                elif action == "isolate":
                    record["is_phantom"] = True
                    record["is_active"] = False
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="phantom_product_isolate",
                            field_name="is_phantom",
                            original_value=False,
                            cleansed_value=True,
                            action_taken="isolated_phantom_product",
                            message=f"Product isolated (inactive): {phantom_reason}",
                        )
                    )
                else:  # default "flag"
                    record["is_phantom"] = True
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="phantom_product_flag",
                            field_name="is_phantom",
                            original_value=False,
                            cleansed_value=True,
                            action_taken="flagged_as_phantom",
                            message=f"Product flagged as phantom: {phantom_reason}",
                        )
                    )
            else:
                record["is_phantom"] = False

            # 3B. SKU & Barcode Deduplication
            if cfg.deduplicate_skus:
                orig_sku = record.get("sku")
                p_name = record.get("name")
                final_sku, was_mod, old_sku, act = self.dedup_engine.process_sku(
                    orig_sku,
                    p_name,
                    cfg.duplicate_resolution,
                    index,
                )
                if act == "skipped_duplicate":
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="deduplicate_sku",
                            field_name="sku",
                            original_value=orig_sku,
                            cleansed_value=None,
                            action_taken="skipped_duplicate",
                            message=f"Duplicate SKU '{orig_sku}' skipped",
                        )
                    )
                    return None, logs
                elif was_mod:
                    record["sku"] = final_sku
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="deduplicate_sku",
                            field_name="sku",
                            original_value=orig_sku,
                            cleansed_value=final_sku,
                            action_taken=act,
                            message=f"SKU resolved via {act}: '{orig_sku}' -> '{final_sku}'",
                        )
                    )

            if cfg.deduplicate_barcodes and "barcode" in record:
                orig_bc = record.get("barcode")
                final_bc, was_mod, old_bc, act = self.dedup_engine.process_barcode(
                    orig_bc,
                    cfg.duplicate_resolution,
                )
                if was_mod:
                    record["barcode"] = final_bc
                    logs.append(
                        CleansingLogItem(
                            entity_type="products",
                            source_key=source_key,
                            rule="deduplicate_barcode",
                            field_name="barcode",
                            original_value=orig_bc,
                            cleansed_value=final_bc,
                            action_taken=act,
                            message=f"Barcode resolved via {act}: '{orig_bc}' -> '{final_bc}'",
                        )
                    )

            # 3C. Foreign Keys & Lookups (Category, UOM, Brand)
            if cfg.auto_create_missing_lookups or cfg.default_category or cfg.default_uom:
                fk_logs = self.lookup_validator.validate_product_lookups(record, cfg)
                logs.extend(fk_logs)

        elif entity_type in ("inventory_opening", "inventory_balances", "stock_items"):
            if cfg.auto_create_missing_lookups or cfg.default_warehouse:
                fk_logs = self.lookup_validator.validate_warehouse_lookups(entity_type, record, cfg)
                logs.extend(fk_logs)

        elif entity_type == "customers":
            fk_logs = self.lookup_validator.validate_customer_lookups(record)
            logs.extend(fk_logs)

        elif entity_type == "suppliers":
            fk_logs = self.lookup_validator.validate_supplier_lookups(record)
            logs.extend(fk_logs)

        # Step 4: Numeric Bounds and Clamping
        num_logs = self.numeric_clamper.clamp_record(entity_type, record, cfg)
        logs.extend(num_logs)

        return record, logs

    def cleanse_records(
        self,
        entity_type: str,
        records: List[Dict[str, Any]],
        config: Optional[DataCleansingConfig] = None,
        reference_date: Optional[Union[date, datetime]] = None,
        transactions: Optional[List[Dict[str, Any]]] = None,
        reset_session: bool = True,
    ) -> Tuple[List[Dict[str, Any]], CleansingSummary]:
        """Cleanse a list of entity records and generate a CleansingSummary.
        
        Args:
            entity_type: Target entity type (e.g. 'products', 'customers', 'inventory_opening')
            records: Raw records to cleanse
            config: DataCleansingConfig configuration options
            reference_date: Base reference date for inactivity checks (default: today)
            transactions: Optional historical transactions to compute latest product activity
            reset_session: If True, resets deduplication and lookup caches
            
        Returns:
            Tuple[List[Dict[str, Any]], CleansingSummary]: Cleaned records and summary metrics
        """
        if reset_session:
            self.reset_session()

        cfg = config or DataCleansingConfig()
        cleaned_records: List[Dict[str, Any]] = []

        summary = CleansingSummary(
            total_records_processed=len(records),
            phantom_products_detected=0,
            phantom_products_skipped=0,
            duplicates_resolved=0,
            contacts_sanitized=0,
            lookups_auto_created=0,
            clamped_numeric_values=0,
            discovered_lookups={},
            logs_sample=[],
        )

        # Pre-index transaction dates by product identifier if transactions provided
        product_tx_dates: Dict[str, date] = {}
        if transactions and entity_type == "products":
            for tx in transactions:
                tx_date = self.phantom_detector.parse_date_value(
                    tx.get("order_date") or tx.get("invoice_date") or tx.get("transaction_date") or tx.get("date")
                )
                if tx_date:
                    for key_field in ("product_id", "product_key", "sku", "product_name", "item_code", "id"):
                        if key_field in tx and tx[key_field] is not None:
                            k = str(tx[key_field]).strip().upper()
                            if k not in product_tx_dates or tx_date > product_tx_dates[k]:
                                product_tx_dates[k] = tx_date

        for idx, raw_row in enumerate(records, start=1):
            # Check if pre-computed transaction date exists for this product
            last_date_override: Optional[date] = None
            if entity_type == "products" and product_tx_dates:
                for k_field in ("id", "sku", "name", "product_id", "code"):
                    val = raw_row.get(k_field)
                    if val is not None:
                        norm_k = str(val).strip().upper()
                        if norm_k in product_tx_dates:
                            last_date_override = product_tx_dates[norm_k]
                            break

            cleansed_row, row_logs = self.cleanse_record(
                entity_type=entity_type,
                raw_record=raw_row,
                config=cfg,
                index=idx,
                reference_date=reference_date,
                last_tx_date_override=last_date_override,
            )

            # Update metrics from logs
            for log in row_logs:
                if "phantom" in log.rule:
                    summary.phantom_products_detected += 1
                    if log.action_taken == "skipped_phantom_product":
                        summary.phantom_products_skipped += 1
                elif "deduplicate" in log.rule or "duplicate" in log.action_taken:
                    summary.duplicates_resolved += 1
                elif "sanitize_phone" in log.rule or "sanitize_email" in log.rule:
                    summary.contacts_sanitized += 1
                elif "lookup" in log.rule:
                    summary.lookups_auto_created += 1
                elif "clamp" in log.rule:
                    summary.clamped_numeric_values += 1

                # Keep a sample of logs (up to 100 items)
                if len(summary.logs_sample) < 100:
                    summary.logs_sample.append(log)

            if cleansed_row is not None:
                cleaned_records.append(cleansed_row)

        summary.discovered_lookups = self.lookup_validator.get_discovered_lookups()
        return cleaned_records, summary

    def cleanse_batch(
        self,
        records_by_entity: Dict[str, List[Dict[str, Any]]],
        config: Optional[DataCleansingConfig] = None,
        reference_date: Optional[Union[date, datetime]] = None,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], CleansingSummary]:
        """Cleanse multi-entity datasets with cross-referencing and aggregated summary.
        
        Args:
            records_by_entity: Dictionary mapping entity_type -> list of row dicts
            config: DataCleansingConfig
            reference_date: Inactivity reference date
            
        Returns:
            Tuple[Dict[str, List[Dict[str, Any]]], CleansingSummary]:
                Cleaned records dictionary and total aggregated CleansingSummary
        """
        self.reset_session()
        cfg = config or DataCleansingConfig()
        cleaned_batch: Dict[str, List[Dict[str, Any]]] = {}

        total_summary = CleansingSummary(
            total_records_processed=0,
            phantom_products_detected=0,
            phantom_products_skipped=0,
            duplicates_resolved=0,
            contacts_sanitized=0,
            lookups_auto_created=0,
            clamped_numeric_values=0,
            discovered_lookups={},
            logs_sample=[],
        )

        # Collect any transaction lines across the batch for cross-referencing
        tx_lines: List[Dict[str, Any]] = []
        for tx_entity in (
            "sales_order_items",
            "purchase_order_items",
            "historical_transactions",
            "customer_opening_balances",
        ):
            if tx_entity in records_by_entity:
                tx_lines.extend(records_by_entity[tx_entity])

        # Cleanse in strategic order: master lookups -> products -> customers/suppliers -> transactions/opening
        entity_order = [
            e for e in [
                "chart_of_accounts",
                "warehouses",
                "products",
                "product_barcodes",
                "customers",
                "suppliers",
                "price_lists",
                "price_list_items",
                "inventory_opening",
                "customer_opening_balances",
                "sales_orders",
                "sales_order_items",
                "purchase_orders",
                "purchase_order_items",
            ] if e in records_by_entity
        ]
        # Add any remaining entities not in explicit list
        for e in records_by_entity.keys():
            if e not in entity_order:
                entity_order.append(e)

        for entity_type in entity_order:
            rows = records_by_entity[entity_type]
            clean_rows, entity_summary = self.cleanse_records(
                entity_type=entity_type,
                records=rows,
                config=cfg,
                reference_date=reference_date,
                transactions=tx_lines if entity_type == "products" else None,
                reset_session=False,  # Maintain cross-entity session state
            )
            cleaned_batch[entity_type] = clean_rows

            total_summary.total_records_processed += entity_summary.total_records_processed
            total_summary.phantom_products_detected += entity_summary.phantom_products_detected
            total_summary.phantom_products_skipped += entity_summary.phantom_products_skipped
            total_summary.duplicates_resolved += entity_summary.duplicates_resolved
            total_summary.contacts_sanitized += entity_summary.contacts_sanitized
            total_summary.lookups_auto_created += entity_summary.lookups_auto_created
            total_summary.clamped_numeric_values += entity_summary.clamped_numeric_values

            # Sample logs
            for log in entity_summary.logs_sample:
                if len(total_summary.logs_sample) < 100:
                    total_summary.logs_sample.append(log)

        total_summary.discovered_lookups = self.lookup_validator.get_discovered_lookups()
        return cleaned_batch, total_summary

    def scan_phantom_products(
        self,
        products: List[Dict[str, Any]],
        transactions: Optional[List[Dict[str, Any]]] = None,
        config: Optional[DataCleansingConfig] = None,
        reference_date: Optional[Union[date, datetime]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], CleansingSummary]:
        """Scan product records and partition them into active vs phantom products.
        
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]], CleansingSummary]:
                (active_products, phantom_products, cleansing_summary)
        """
        cfg = (config or DataCleansingConfig()).model_copy(update={"phantom_action": "flag"})
        cleaned_prods, summary = self.cleanse_records(
            entity_type="products",
            records=products,
            config=cfg,
            reference_date=reference_date,
            transactions=transactions,
            reset_session=True,
        )

        active = [p for p in cleaned_prods if not p.get("is_phantom")]
        phantoms = [p for p in cleaned_prods if p.get("is_phantom")]

        return active, phantoms, summary


# Singleton default instance
cleansing_service = CleansingService()
