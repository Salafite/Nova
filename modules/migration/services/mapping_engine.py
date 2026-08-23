"""Automated Legacy ERP Schema and Entity Mapping Engine.

Provides:
1. Default mapping dictionaries for legacy F&B, retail, and accounting schemas.
2. Heuristic fuzzy matching for tables and column names (English and Arabic aliases).
3. Data type coercion, value transformations, and date/numeric normalization.
4. Row-level translation from legacy dictionaries to Nova T-code entity schemas.
5. Automated MigrationMappingConfig generation from discovered legacy table schemas.
"""

from datetime import date, datetime
from decimal import Decimal
import difflib
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from modules.migration.models.migration import (
    FieldMappingRule,
    MigrationMappingConfig,
    TableMappingRule,
    TableMetadata,
)


# ==============================================================================
# Target Entity & Table Definitions (Nova ERP T-codes)
# ==============================================================================

ENTITY_TARGET_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "products": {
        "tcode": "T0003",
        "table": "t0003",
        "primary_key": "id",
        "required_fields": ["name", "sku"],
        "fields": {
            "name": {"type": "string", "default": None, "required": True},
            "sku": {"type": "string", "default": None, "required": True},
            "barcode": {"type": "string", "default": None},
            "description": {"type": "string", "default": None},
            "type": {"type": "string", "default": "stockable"},
            "price": {"type": "float", "default": 0.0},
            "cost_price": {"type": "float", "default": 0.0},
            "category": {"type": "string", "default": "General"},
            "brand": {"type": "string", "default": None},
            "tax_rate": {"type": "float", "default": 0.0},
            "weight": {"type": "float", "default": 0.0},
            "volume": {"type": "float", "default": 0.0},
            "image_url": {"type": "string", "default": None},
            "is_purchasable": {"type": "bool", "default": True},
            "is_saleable": {"type": "bool", "default": True},
            "is_phantom": {"type": "bool", "default": False},
            "last_transaction_date": {"type": "datetime", "default": None},
            "is_active": {"type": "bool", "default": True},
        },
    },
    "product_barcodes": {
        "tcode": "T0004",
        "table": "t0004",
        "primary_key": "id",
        "required_fields": ["product_id", "barcode"],
        "fields": {
            "product_id": {"type": "int", "default": None, "required": True},
            "barcode": {"type": "string", "default": None, "required": True},
            "barcode_type": {"type": "string", "default": "EAN13"},
            "is_primary": {"type": "bool", "default": False},
        },
    },
    "customers": {
        "tcode": "T0010",
        "table": "t0010",
        "primary_key": "id",
        "required_fields": ["name"],
        "fields": {
            "name": {"type": "string", "default": None, "required": True},
            "group_name": {"type": "string", "default": "Retail"},
            "phone": {"type": "string", "default": None},
            "email": {"type": "string", "default": None},
            "credit_limit": {"type": "float", "default": 0.0},
            "balance": {"type": "float", "default": 0.0},
            "is_active": {"type": "bool", "default": True},
            "default_price_list_id": {"type": "int", "default": None},
            "default_tax_rate_id": {"type": "int", "default": None},
            "payment_term_id": {"type": "int", "default": None},
        },
    },
    "suppliers": {
        "tcode": "T0011",
        "table": "t0011",
        "primary_key": "id",
        "required_fields": ["name"],
        "fields": {
            "name": {"type": "string", "default": None, "required": True},
            "category": {"type": "string", "default": "General"},
            "phone": {"type": "string", "default": None},
            "email": {"type": "string", "default": None},
            "payment_terms": {"type": "string", "default": "Net 30"},
            "rating": {"type": "int", "default": 0},
            "is_active": {"type": "bool", "default": True},
        },
    },
    "price_lists": {
        "tcode": "T0083",
        "table": "t0083",
        "primary_key": "id",
        "required_fields": ["name", "code"],
        "fields": {
            "name": {"type": "string", "default": None, "required": True},
            "code": {"type": "string", "default": None, "required": True},
            "description": {"type": "string", "default": None},
            "currency": {"type": "string", "default": "USD"},
            "is_active": {"type": "bool", "default": True},
            "is_default": {"type": "bool", "default": False},
        },
    },
    "price_list_items": {
        "tcode": "T0084",
        "table": "t0084",
        "primary_key": "id",
        "required_fields": ["price_list_id", "product_id", "unit_price"],
        "fields": {
            "price_list_id": {"type": "int", "default": None, "required": True},
            "product_id": {"type": "int", "default": None, "required": True},
            "unit_price": {"type": "float", "default": 0.0, "required": True},
            "min_qty": {"type": "int", "default": 1},
            "uom_id": {"type": "int", "default": None},
            "effective_from": {"type": "date", "default": None},
            "effective_to": {"type": "date", "default": None},
            "line_number": {"type": "int", "default": 1},
            "is_active": {"type": "bool", "default": True},
        },
    },
    "chart_of_accounts": {
        "tcode": "T0026",
        "table": "t0026",
        "primary_key": "id",
        "required_fields": ["account_code", "account_name", "account_type"],
        "fields": {
            "account_code": {"type": "string", "default": None, "required": True},
            "account_name": {"type": "string", "default": None, "required": True},
            "account_type": {"type": "string", "default": "Asset", "required": True},
            "parent_id": {"type": "int", "default": None},
            "currency": {"type": "string", "default": "USD"},
            "is_active": {"type": "bool", "default": True},
        },
    },
    "customer_opening_balances": {
        "tcode": "T0090",
        "table": "t0090",
        "primary_key": "id",
        "required_fields": ["invoice_number", "partner_id", "total_amount"],
        "fields": {
            "invoice_number": {"type": "string", "default": None, "required": True},
            "invoice_type": {"type": "string", "default": "OpeningBalance"},
            "partner_id": {"type": "int", "default": None, "required": True},
            "sales_order_id": {"type": "int", "default": None},
            "issue_date": {"type": "date", "default": None},
            "due_date": {"type": "date", "default": None},
            "total_amount": {"type": "float", "default": 0.0, "required": True},
            "freight_amount": {"type": "float", "default": 0.0},
            "discount_amount": {"type": "float", "default": 0.0},
            "sales_rep_id": {"type": "int", "default": None},
            "status": {"type": "string", "default": "Posted"},
            "notes": {"type": "string", "default": "Legacy opening balance migration"},
        },
    },
    "payments": {
        "tcode": "T0091",
        "table": "t0091",
        "primary_key": "id",
        "required_fields": ["partner_id", "amount", "payment_method"],
        "fields": {
            "payment_date": {"type": "date", "default": None},
            "invoice_id": {"type": "int", "default": None},
            "partner_id": {"type": "int", "default": None, "required": True},
            "amount": {"type": "float", "default": 0.0, "required": True},
            "payment_method": {"type": "string", "default": "Cash"},
            "reference": {"type": "string", "default": None},
            "status": {"type": "string", "default": "Completed"},
            "notes": {"type": "string", "default": None},
        },
    },
    "warehouses": {
        "tcode": "T0008",
        "table": "t0008",
        "primary_key": "id",
        "required_fields": ["name"],
        "fields": {
            "name": {"type": "string", "default": None, "required": True},
            "location": {"type": "string", "default": None},
            "is_active": {"type": "bool", "default": True},
        },
    },
    "inventory_opening": {
        "tcode": "T0009",
        "table": "t0009",
        "primary_key": "id",
        "required_fields": ["product_id", "warehouse_id", "qty"],
        "fields": {
            "product_id": {"type": "int", "default": None, "required": True},
            "warehouse_id": {"type": "int", "default": 1, "required": True},
            "qty": {"type": "float", "default": 0.0, "required": True},
            "reserved_qty": {"type": "float", "default": 0.0},
            "reorder_level": {"type": "float", "default": 0.0},
        },
    },
    "sales_orders": {
        "tcode": "T0012",
        "table": "t0012",
        "primary_key": "id",
        "required_fields": ["order_number", "customer_id", "grand_total"],
        "fields": {
            "order_number": {"type": "string", "default": None, "required": True},
            "customer_id": {"type": "int", "default": None, "required": True},
            "warehouse_id": {"type": "int", "default": 1},
            "subtotal": {"type": "float", "default": 0.0},
            "tax": {"type": "float", "default": 0.0},
            "grand_total": {"type": "float", "default": 0.0, "required": True},
            "freight_amount": {"type": "float", "default": 0.0},
            "discount_amount": {"type": "float", "default": 0.0},
            "sales_rep_id": {"type": "int", "default": None},
            "status": {"type": "string", "default": "Confirmed"},
            "order_date": {"type": "date", "default": None},
            "notes": {"type": "string", "default": None},
            "price_list_id": {"type": "int", "default": None},
            "tax_rate_id": {"type": "int", "default": None},
            "payment_term_id": {"type": "int", "default": None},
            "client_order_uuid": {"type": "string", "default": None},
            "is_offline_sync": {"type": "bool", "default": False},
            "sync_status": {"type": "string", "default": "Synced"},
        },
    },
    "sales_order_items": {
        "tcode": "T0013",
        "table": "t0013",
        "primary_key": "id",
        "required_fields": ["sales_order_id", "product_id", "qty", "unit_price"],
        "fields": {
            "sales_order_id": {"type": "int", "default": None, "required": True},
            "product_id": {"type": "int", "default": None, "required": True},
            "product_name": {"type": "string", "default": None},
            "uom_id": {"type": "int", "default": None},
            "qty": {"type": "float", "default": 1.0, "required": True},
            "unit_price": {"type": "float", "default": 0.0, "required": True},
            "cost_price": {"type": "float", "default": 0.0},
            "discount": {"type": "float", "default": 0.0},
            "line_total": {"type": "float", "default": 0.0},
            "line_number": {"type": "int", "default": 1},
        },
    },
    "purchase_orders": {
        "tcode": "T0014",
        "table": "t0014",
        "primary_key": "id",
        "required_fields": ["order_number", "supplier_id", "total"],
        "fields": {
            "order_number": {"type": "string", "default": None, "required": True},
            "supplier_id": {"type": "int", "default": None, "required": True},
            "total": {"type": "float", "default": 0.0, "required": True},
            "status": {"type": "string", "default": "Confirmed"},
            "order_date": {"type": "date", "default": None},
            "expected_date": {"type": "date", "default": None},
            "notes": {"type": "string", "default": None},
            "converted_rfq_id": {"type": "int", "default": None},
        },
    },
    "purchase_order_items": {
        "tcode": "T0015",
        "table": "t0015",
        "primary_key": "id",
        "required_fields": ["purchase_order_id", "product_id", "qty", "unit_price"],
        "fields": {
            "purchase_order_id": {"type": "int", "default": None, "required": True},
            "product_id": {"type": "int", "default": None, "required": True},
            "product_name": {"type": "string", "default": None},
            "uom_id": {"type": "int", "default": None},
            "qty": {"type": "float", "default": 1.0, "required": True},
            "unit_price": {"type": "float", "default": 0.0, "required": True},
            "line_total": {"type": "float", "default": 0.0},
            "line_number": {"type": "int", "default": 1},
        },
    },
}


# ==============================================================================
# Default Legacy Column Aliases and Dictionaries (English & Arabic)
# ==============================================================================

DEFAULT_FIELD_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "products": {
        "name": [
            "itemname", "item_name", "productname", "product_name", "itemdesc",
            "item_desc", "description", "title", "name", "prod_name", "item_title",
            "اسم_الصنف", "الاسم", "اسم_المنتج", "اسم_المادة", "بيان_الصنف"
        ],
        "sku": [
            "itemcode", "item_code", "productcode", "product_code", "item_no",
            "itemno", "code", "part_number", "part_no", "sku", "product_sku",
            "item_num", "item_id_legacy", "رقم_الصنف", "كود_الصنف", "رمز_الصنف"
        ],
        "barcode": [
            "barcode", "bar_code", "upc", "ean", "ean13", "qr_code", "item_barcode",
            "باركود", "بار_كود", "رمز_الباركود"
        ],
        "price": [
            "unitprice", "unit_price", "sellingprice", "selling_price", "price",
            "sale_price", "retail_price", "standard_price", "sales_price", "pos_price",
            "سعر_البيع", "السعر", "سعر_الوحدة", "سعر_القطاعي"
        ],
        "cost_price": [
            "costprice", "cost_price", "unitcost", "unit_cost", "cost",
            "purchase_price", "buying_price", "standard_cost", "avg_cost", "average_cost",
            "سعر_التكلفة", "التكلفة", "سعر_الشراء", "تكلفة_الوحدة"
        ],
        "category": [
            "category", "category_name", "categoryname", "group", "group_name",
            "item_group", "itemgroup", "department", "dept_name", "family", "class",
            "التصنيف", "المجموعة", "القسم", "فئة_الصنف"
        ],
        "brand": [
            "brand", "brand_name", "manufacturer", "make", "vendor_brand", "trademark",
            "الماركة", "العلامة_التجارية", "الشركة_المصنعة"
        ],
        "tax_rate": [
            "tax", "tax_rate", "taxrate", "vat", "vat_rate", "tax_percent", "vat_percent",
            "الضريبة", "نسبة_الضريبة", "ضريبة_القيمة_المضافة"
        ],
        "weight": [
            "weight", "item_weight", "net_weight", "gross_weight", "الوزن", "الوزن_الصافي"
        ],
        "volume": [
            "volume", "cbm", "item_volume", "الحجم"
        ],
        "image_url": [
            "image", "image_url", "photo", "picture", "img_path", "صورة_الصنف"
        ],
        "is_active": [
            "is_active", "active", "isactive", "enabled", "status", "نشط", "فعال"
        ],
        "is_phantom": [
            "is_phantom", "phantom", "discontinued", "inactive_legacy", "ghost", "راكد"
        ],
        "last_transaction_date": [
            "last_sale_date", "last_transaction_date", "last_activity_date", "last_order_date",
            "last_trans_date", "تاريخ_اخر_حركة", "اخر_بيع"
        ],
        "description": [
            "notes", "memo", "details", "long_description", "remark", "comment", "الوصف", "ملاحظات"
        ],
    },
    "customers": {
        "name": [
            "custname", "customer_name", "customername", "client_name", "name",
            "fullname", "company_name", "company", "account_name", "cust_title",
            "اسم_العميل", "الاسم", "اسم_الشركة", "العميل"
        ],
        "phone": [
            "phone", "telephone", "mobile", "phone_number", "cell", "tel",
            "phone1", "mobile_no", "contact_phone", "الهاتف", "الجوال", "رقم_الهاتف"
        ],
        "email": [
            "email", "email_address", "mail", "e_mail", "contact_email", "البريد", "الايميل"
        ],
        "group_name": [
            "group", "group_name", "customer_group", "cust_group", "category",
            "type", "tier", "cust_class", "مجموعة_العملاء", "فئة_العميل", "تصنيف_العميل"
        ],
        "credit_limit": [
            "credit_limit", "creditlimit", "max_credit", "limit", "حد_الائتمان", "سقف_الائتمان"
        ],
        "balance": [
            "balance", "current_balance", "open_balance", "opening_balance",
            "outstanding_balance", "due_balance", "الرصيد", "الرصيد_الحالي", "الرصيد_الافتتاحي"
        ],
        "is_active": [
            "is_active", "active", "isactive", "status", "نشط", "الحالة"
        ],
    },
    "suppliers": {
        "name": [
            "suppname", "supplier_name", "suppliername", "vendor_name", "vendorname",
            "vendor", "name", "company", "supp_title", "اسم_المورد", "المورد", "اسم_الشركة"
        ],
        "category": [
            "category", "supp_category", "vendor_type", "type", "group_name", "تصنيف_المورد", "فئة_المورد"
        ],
        "phone": [
            "phone", "telephone", "mobile", "phone_number", "tel", "الهاتف", "الجوال"
        ],
        "email": [
            "email", "email_address", "contact_email", "البريد"
        ],
        "payment_terms": [
            "payment_terms", "terms", "pay_terms", "credit_days", "term_name", "شروط_الدفع", "فترة_السداد"
        ],
        "rating": [
            "rating", "score", "rank", "grade", "vendor_rating", "التقييم"
        ],
        "is_active": [
            "is_active", "active", "isactive", "status", "نشط"
        ],
    },
    "price_lists": {
        "name": [
            "pricelist_name", "price_list_name", "name", "title", "list_name", "اسم_قائمة_الاسعار"
        ],
        "code": [
            "code", "pricelist_code", "list_code", "price_list_code", "كود_القائمة"
        ],
        "description": [
            "description", "desc", "notes", "memo", "الوصف"
        ],
        "currency": [
            "currency", "curr", "currency_code", "العملة"
        ],
        "is_default": [
            "is_default", "default_list", "isdefault", "القائمة_الافتراضية"
        ],
        "is_active": [
            "is_active", "active", "isactive", "نشط"
        ],
    },
    "price_list_items": {
        "price_list_id": [
            "price_list_id", "pricelist_id", "list_id", "price_id", "رقم_القائمة"
        ],
        "product_id": [
            "product_id", "item_id", "sku", "item_code", "product_code", "رقم_الصنف"
        ],
        "unit_price": [
            "unit_price", "price", "rate", "special_price", "list_price", "السعر", "سعر_الوحدة"
        ],
        "min_qty": [
            "min_qty", "minimum_quantity", "min_quantity", "qty_break", "اقل_كمية"
        ],
        "uom_id": [
            "uom_id", "uom", "unit_id", "unit", "الوحدة"
        ],
        "effective_from": [
            "effective_from", "start_date", "valid_from", "from_date", "من_تاريخ"
        ],
        "effective_to": [
            "effective_to", "end_date", "valid_to", "to_date", "الى_تاريخ"
        ],
    },
    "chart_of_accounts": {
        "account_code": [
            "account_code", "code", "acct_code", "account_no", "acc_no", "gl_code", "رقم_الحساب", "كود_الحساب"
        ],
        "account_name": [
            "account_name", "name", "acct_name", "title", "gl_name", "اسم_الحساب"
        ],
        "account_type": [
            "account_type", "type", "acct_type", "category", "نوع_الحساب", "طبيعة_الحساب"
        ],
        "parent_id": [
            "parent_id", "parent_code", "parent_account", "الحساب_الرئيسي"
        ],
        "currency": [
            "currency", "curr", "العملة"
        ],
    },
    "customer_opening_balances": {
        "invoice_number": [
            "inv_no", "invoice_no", "invoiceno", "doc_no", "ref_no", "bill_no", "voucher_no", "رقم_الفاتورة", "رقم_السند"
        ],
        "partner_id": [
            "partner_id", "customer_id", "cust_id", "customer_code", "client_id", "cust_no", "رقم_العميل", "كود_العميل"
        ],
        "issue_date": [
            "issue_date", "invoice_date", "inv_date", "date", "doc_date", "trans_date", "تاريخ_الفاتورة", "التاريخ"
        ],
        "due_date": [
            "due_date", "payment_due", "maturity_date", "تاريخ_الاستحقاق"
        ],
        "total_amount": [
            "total_amount", "total", "amount", "net_amount", "grand_total", "balance_due", "open_balance", "المبلغ", "الصافي", "الرصيد"
        ],
        "freight_amount": [
            "freight_amount", "freight", "shipping", "مبلغ_الشحن"
        ],
        "discount_amount": [
            "discount_amount", "discount", "disc", "الخصم"
        ],
        "notes": [
            "notes", "memo", "remarks", "details", "ملاحظات", "البيان"
        ],
    },
    "payments": {
        "payment_date": [
            "payment_date", "pay_date", "date", "receipt_date", "trans_date", "تاريخ_الدفع", "تاريخ_السند"
        ],
        "invoice_id": [
            "invoice_id", "inv_id", "bill_id", "ref_invoice", "رقم_الفاتورة"
        ],
        "partner_id": [
            "partner_id", "customer_id", "client_id", "supplier_id", "cust_id", "رقم_العميل"
        ],
        "amount": [
            "amount", "paid_amount", "payment_amt", "total", "المبلغ_المدفوع", "المبلغ"
        ],
        "payment_method": [
            "payment_method", "method", "pay_type", "payment_type", "mode", "طريقة_الدفع"
        ],
        "reference": [
            "reference", "ref_no", "check_no", "trans_id", "receipt_no", "رقم_المرجع", "رقم_الشيك"
        ],
        "notes": [
            "notes", "memo", "remarks", "ملاحظات"
        ],
    },
    "warehouses": {
        "name": [
            "name", "warehouse_name", "wh_name", "location_name", "store_name", "branch_name", "اسم_المستودع", "اسم_المخزن", "الفرع"
        ],
        "location": [
            "location", "address", "city", "wh_location", "الموقع", "العنوان"
        ],
        "is_active": [
            "is_active", "active", "نشط"
        ],
    },
    "inventory_opening": {
        "product_id": [
            "product_id", "item_id", "sku", "item_code", "product_code", "barcode", "رقم_الصنف", "كود_الصنف"
        ],
        "warehouse_id": [
            "warehouse_id", "wh_id", "store_id", "branch_id", "location_id", "رقم_المستودع", "المستودع"
        ],
        "qty": [
            "qty", "quantity", "stock_qty", "on_hand", "balance_qty", "opening_qty",
            "qty_on_hand", "physical_qty", "stock", "الكمية", "الرصيد_الحالي", "رصيد_المخزون"
        ],
        "reserved_qty": [
            "reserved_qty", "reserved", "allocated_qty", "كمية_محجوزة"
        ],
        "reorder_level": [
            "reorder_level", "min_stock", "reorder_point", "safety_stock", "حد_الطلب"
        ],
    },
    "sales_orders": {
        "order_number": [
            "order_number", "order_no", "so_no", "doc_no", "sale_no", "receipt_no", "bill_no", "رقم_الطلب", "رقم_الفاتورة"
        ],
        "customer_id": [
            "customer_id", "cust_id", "client_id", "customer_code", "رقم_العميل"
        ],
        "order_date": [
            "order_date", "date", "sale_date", "doc_date", "trans_date", "تاريخ_الطلب", "التاريخ"
        ],
        "subtotal": [
            "subtotal", "sub_total", "net_amount", "المجموع_قبل_الضريبة"
        ],
        "tax": [
            "tax", "tax_amount", "vat", "الضريبة"
        ],
        "grand_total": [
            "grand_total", "total", "total_amount", "net_total", "amount", "المجموع_الكلي", "الإجمالي"
        ],
        "discount_amount": [
            "discount_amount", "discount", "disc", "الخصم"
        ],
        "freight_amount": [
            "freight_amount", "freight", "shipping", "الشحن"
        ],
        "status": [
            "status", "order_status", "state", "الحالة"
        ],
        "notes": [
            "notes", "memo", "remarks", "ملاحظات"
        ],
    },
    "sales_order_items": {
        "sales_order_id": [
            "sales_order_id", "order_id", "so_id", "order_no", "parent_order_id", "رقم_الطلب"
        ],
        "product_id": [
            "product_id", "item_id", "sku", "item_code", "رقم_الصنف"
        ],
        "product_name": [
            "product_name", "item_name", "description", "اسم_الصنف"
        ],
        "qty": [
            "qty", "quantity", "sold_qty", "الكمية"
        ],
        "unit_price": [
            "unit_price", "price", "rate", "سعر_الوحدة"
        ],
        "cost_price": [
            "cost_price", "cost", "unit_cost", "التكلفة"
        ],
        "discount": [
            "discount", "line_discount", "disc", "خصم_البند"
        ],
        "line_total": [
            "line_total", "total", "amount", "إجمالي_البند"
        ],
        "line_number": [
            "line_number", "line_no", "row_no", "seq", "رقم_السطر"
        ],
    },
    "purchase_orders": {
        "order_number": [
            "order_number", "po_no", "order_no", "purchase_no", "bill_no", "رقم_امر_الشراء", "رقم_الشراء"
        ],
        "supplier_id": [
            "supplier_id", "vendor_id", "supplier_code", "رقم_المورد"
        ],
        "order_date": [
            "order_date", "po_date", "date", "تاريخ_الشراء"
        ],
        "expected_date": [
            "expected_date", "delivery_date", "due_date", "تاريخ_التسليم"
        ],
        "total": [
            "total", "total_amount", "grand_total", "amount", "المجموع"
        ],
        "status": [
            "status", "po_status", "state", "الحالة"
        ],
        "notes": [
            "notes", "memo", "remarks", "ملاحظات"
        ],
    },
    "purchase_order_items": {
        "purchase_order_id": [
            "purchase_order_id", "po_id", "purchase_order_no", "parent_po_id", "رقم_امر_الشراء"
        ],
        "product_id": [
            "product_id", "item_id", "sku", "item_code", "رقم_الصنف"
        ],
        "product_name": [
            "product_name", "item_name", "desc", "اسم_الصنف"
        ],
        "qty": [
            "qty", "quantity", "po_qty", "الكمية"
        ],
        "unit_price": [
            "unit_price", "price", "cost", "unit_cost", "السعر"
        ],
        "line_total": [
            "line_total", "total", "amount", "إجمالي_البند"
        ],
        "line_number": [
            "line_number", "line_no", "row_no", "seq", "رقم_السطر"
        ],
    },
}


# ==============================================================================
# Default Table Name Aliases and Guesses (English & Arabic)
# ==============================================================================

DEFAULT_TABLE_ALIASES: Dict[str, List[str]] = {
    "products": [
        "products", "tbl_products", "items", "tbl_items", "product", "item",
        "tbl_item", "tbl_product", "articles", "goods", "menu_items", "stock_items",
        "inventory_items", "tbl_menu", "tbl_menuitems", "اصناف", "الاصناف", "منتجات", "المواد"
    ],
    "customers": [
        "customers", "tbl_customers", "customer", "tbl_customer", "clients",
        "tbl_clients", "client", "debtors", "accounts_receivable", "cust_table",
        "عملاء", "العملاء", "الزبائن"
    ],
    "suppliers": [
        "suppliers", "tbl_suppliers", "supplier", "tbl_supplier", "vendors",
        "tbl_vendors", "vendor", "creditors", "accounts_payable", "موردين", "الموردين"
    ],
    "price_lists": [
        "pricelists", "price_lists", "tbl_pricelists", "tbl_price_lists", "price_tiers",
        "pricing", "pricelist_headers", "قوائم_الاسعار", "لائحة_الاسعار"
    ],
    "price_list_items": [
        "pricelist_items", "price_list_items", "price_list_details", "pricing_details",
        "tbl_pricelist_items", "tbl_price_items", "تفاصيل_قوائم_الاسعار"
    ],
    "chart_of_accounts": [
        "chart_of_accounts", "accounts", "gl_accounts", "coa", "tbl_accounts",
        "general_ledger", "account_master", "دليل_الحسابات", "شجرة_الحسابات"
    ],
    "customer_opening_balances": [
        "opening_balances", "customer_balances", "receivables", "cust_balances",
        "open_invoices", "ar_balances", "customer_opening_balances", "ar_opening",
        "ارصدة_افتتاحية_عملاء", "ارصدة_العملاء"
    ],
    "payments": [
        "payments", "tbl_payments", "receipts", "cash_receipts", "voucher_receipts",
        "customer_payments", "سندات_القبض", "المدفوعات"
    ],
    "warehouses": [
        "warehouses", "tbl_warehouses", "stores", "branches", "locations",
        "tbl_stores", "tbl_branches", "مستودعات", "المخازن", "الفروع"
    ],
    "inventory_opening": [
        "inventory_opening", "stock_opening", "stock", "inventory", "stock_levels",
        "on_hand", "inventory_balance", "opening_stock", "stock_balances", "item_stock",
        "رصيد_المخزون", "المخزون_الافتتاحي", "بضاعة_اول_المدة"
    ],
    "sales_orders": [
        "sales_orders", "orders", "sales", "invoices", "sales_invoices", "tbl_sales",
        "pos_sales", "sales_headers", "tbl_orders", "فاتورة_مبيعات", "المبيعات", "الطلبات"
    ],
    "sales_order_items": [
        "sales_order_items", "sales_details", "sales_items", "invoice_items",
        "order_lines", "order_items", "sales_lines", "تفاصيل_المبيعات", "بنود_الفواتير"
    ],
    "purchase_orders": [
        "purchase_orders", "purchases", "po_headers", "tbl_purchases", "bills",
        "purchase_invoices", "المشتريات", "اوامر_الشراء", "فواتير_الشراء"
    ],
    "purchase_order_items": [
        "purchase_order_items", "purchase_details", "po_lines", "bill_items",
        "purchase_lines", "تفاصيل_المشتريات", "بنود_الشراء"
    ],
}


# ==============================================================================
# Helper Functions: String Normalization and Heuristic Matching
# ==============================================================================

def normalize_identifier(text: str) -> str:
    """Normalize a table or column identifier for robust fuzzy comparison.
    
    Converts to lowercase, removes standard database prefixes (tbl_, vw_, fld_, etc.),
    strips non-alphanumeric separators, and normalizes Arabic characters.
    """
    if not text:
        return ""
    
    cleaned = str(text).strip().lower()
    
    # Strip common SQL / schema prefixes
    prefixes_to_strip = [
        "tbl_", "tbl", "vw_", "view_", "fld_", "col_", "dbo.", "sys_", "legacy_"
    ]
    for prefix in prefixes_to_strip:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix):
            cleaned = cleaned[len(prefix):]
            break
            
    # Normalize Arabic characters
    arabic_replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي",
        "َ": "", "ً": "", "ُ": "", "ٌ": "", "ِ": "", "ٍ": "", "ْ": "", "ّ": ""
    }
    for orig, repl in arabic_replacements.items():
        cleaned = cleaned.replace(orig, repl)
        
    # Replace separators with underscore
    cleaned = re.sub(r"[\s\-\.\/]+", "_", cleaned)
    # Remove any character that is not alphanumeric or underscore
    cleaned = re.sub(r"[^\w\d_]", "", cleaned)
    return cleaned.strip("_")


def calculate_similarity(s1: str, s2: str) -> float:
    """Compute normalized similarity ratio between two strings (0.0 to 1.0)."""
    norm1 = normalize_identifier(s1)
    norm2 = normalize_identifier(s2)
    
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    if norm1 in norm2 or norm2 in norm1:
        # High score for substring containment
        shorter, longer = (norm1, norm2) if len(norm1) <= len(norm2) else (norm2, norm1)
        return 0.85 + (0.15 * (len(shorter) / len(longer)))
        
    # Difflib SequenceMatcher ratio
    matcher_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    # Also check token overlap without underscores
    token1 = set(norm1.split("_"))
    token2 = set(norm2.split("_"))
    if token1 and token2:
        jaccard = len(token1.intersection(token2)) / len(token1.union(token2))
        return max(matcher_ratio, jaccard)
        
    return matcher_ratio


# ==============================================================================
# Type Casting and Value Transformation Engine
# ==============================================================================

class DataCastingEngine:
    """Handles type coercion, numeric parsing, date parsing, and string transforms."""

    @staticmethod
    def cast(
        value: Any,
        target_type: str,
        transform: Optional[str] = None,
        default: Any = None,
        strict: bool = False,
    ) -> Any:
        """Cast and transform a raw legacy value to the target Nova data type."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return default

        # Apply pre-cast transform if specified
        if transform:
            value = DataCastingEngine._apply_transform(value, transform)

        target_type_clean = (target_type or "string").lower()

        try:
            if target_type_clean in ("string", "text", "varchar", "char"):
                return DataCastingEngine.to_string(value, default, strict=strict)
            elif target_type_clean in ("int", "integer", "bigint", "smallint"):
                return DataCastingEngine.to_int(value, default, strict=strict)
            elif target_type_clean in ("float", "double", "real"):
                return DataCastingEngine.to_float(value, default, strict=strict)
            elif target_type_clean in ("decimal", "numeric", "money"):
                return DataCastingEngine.to_decimal(value, default, strict=strict)
            elif target_type_clean in ("bool", "boolean", "bit"):
                return DataCastingEngine.to_bool(value, default, strict=strict)
            elif target_type_clean in ("date",):
                return DataCastingEngine.to_date(value, default, strict=strict)
            elif target_type_clean in ("datetime", "timestamptz", "timestamp"):
                return DataCastingEngine.to_datetime(value, default, strict=strict)
            else:
                return value
        except Exception as e:
            if strict:
                raise ValueError(f"Failed casting value '{value}' to {target_type}: {e}")
            return default

    @staticmethod
    def _apply_transform(val: Any, transform: str) -> Any:
        """Apply string or numeric formatting transform."""
        if val is None:
            return None
        t = transform.lower()
        if t == "uppercase":
            return str(val).upper()
        if t == "lowercase":
            return str(val).lower()
        if t == "trim":
            return str(val).strip()
        if t == "titlecase":
            return str(val).title()
        if t == "strip_non_numeric":
            return re.sub(r"[^\d\.]", "", str(val))
        if t == "round_2":
            try:
                return round(float(val), 2)
            except Exception:
                return val
        if t == "round_4":
            try:
                return round(float(val), 4)
            except Exception:
                return val
        if t == "sanitize_phone":
            cleaned = re.sub(r"[^\d\+\(\)\-\s]", "", str(val)).strip()
            return cleaned
        if t == "sanitize_email":
            cleaned = str(val).strip().lower()
            return cleaned if "@" in cleaned else None
        return val

    @staticmethod
    def to_string(val: Any, default: Any = None, strict: bool = False) -> Optional[str]:
        if val is None:
            return default
        s = str(val).strip()
        return s if s != "" else default

    @staticmethod
    def to_int(val: Any, default: Any = None, strict: bool = False) -> Optional[int]:
        if val is None:
            return default
        if isinstance(val, int):
            return val
        if isinstance(val, (float, Decimal)):
            return int(val)
        if isinstance(val, str):
            s = val.strip().replace(",", "").replace("$", "")
            if s == "":
                return default
            # Handle float strings like '10.00'
            if "." in s:
                try:
                    return int(float(s))
                except ValueError:
                    if strict:
                        raise ValueError(f"Cannot cast string '{val}' to int")
                    return default
            try:
                return int(s)
            except ValueError:
                if strict:
                    raise ValueError(f"Cannot cast string '{val}' to int")
                return default
        if strict:
            raise ValueError(f"Cannot cast type {type(val)} to int")
        return default

    @staticmethod
    def to_float(val: Any, default: Any = None, strict: bool = False) -> Optional[float]:
        if val is None:
            return default
        if isinstance(val, (float, int)):
            return float(val)
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, str):
            s = val.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
            # Handle parenthesized negative numbers e.g. (100.50) -> -100.50
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1].strip()
            if s == "":
                return default
            try:
                return float(s)
            except ValueError:
                if strict:
                    raise ValueError(f"Cannot cast string '{val}' to float")
                return default
        if strict:
            raise ValueError(f"Cannot cast type {type(val)} to float")
        return default

    @staticmethod
    def to_decimal(val: Any, default: Any = None, strict: bool = False) -> Optional[float]:
        """Convert to rounded 2-decimal float."""
        res = DataCastingEngine.to_float(val, default, strict=strict)
        if res is not None:
            return round(res, 2)
        return default

    @staticmethod
    def to_bool(val: Any, default: Any = None, strict: bool = False) -> Optional[bool]:
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val != 0)
        if isinstance(val, str):
            s = val.strip().lower()
            if s in ("1", "true", "t", "yes", "y", "on", "نعم", "صحيح", "active"):
                return True
            if s in ("0", "false", "f", "no", "n", "off", "لا", "خطأ", "inactive"):
                return False
            if strict:
                raise ValueError(f"Cannot cast string '{val}' to bool")
        if strict:
            raise ValueError(f"Cannot cast type {type(val)} to bool")
        return default

    @staticmethod
    def to_date(val: Any, default: Any = None, strict: bool = False) -> Optional[str]:
        if val is None:
            return default
        if isinstance(val, (datetime, date)):
            return val.strftime("%Y-%m-%d")
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return default
            # Clean ISO timestamps e.g. "2023-01-15T00:00:00" -> "2023-01-15"
            if "T" in s:
                s = s.split("T")[0]
            if " " in s:
                s = s.split(" ")[0]

            formats = [
                "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
                "%d-%m-%Y", "%m-%d-%Y", "%Y%m%d", "%d.%m.%Y"
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            if strict:
                raise ValueError(f"Cannot parse date '{val}'")
        elif strict:
            raise ValueError(f"Cannot cast type {type(val)} to date")
        return default

    @staticmethod
    def to_datetime(val: Any, default: Any = None, strict: bool = False) -> Optional[str]:
        if val is None:
            return default
        if isinstance(val, (datetime, date)):
            if isinstance(val, date) and not isinstance(val, datetime):
                return datetime.combine(val, datetime.min.time()).isoformat()
            return val.isoformat()
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return default
            formats = [
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                "%d/%m/%Y", "%m/%d/%Y"
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            if strict:
                raise ValueError(f"Cannot parse datetime '{val}'")
        elif strict:
            raise ValueError(f"Cannot cast type {type(val)} to datetime")
        return default


# ==============================================================================
# Mapping Engine Main Implementation
# ==============================================================================

class MappingEngine:
    """Core schema mapping, heuristic fuzzy matching, and entity translation service."""

    def __init__(self) -> None:
        self.target_schemas = ENTITY_TARGET_SCHEMAS
        self.field_aliases = DEFAULT_FIELD_ALIASES
        self.table_aliases = DEFAULT_TABLE_ALIASES
        self.caster = DataCastingEngine()

    def get_supported_entities(self) -> List[str]:
        """Return list of all supported Nova migration entity types."""
        return list(self.target_schemas.keys())

    def get_entity_target_schema(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """Return the target T-code and field specifications for an entity."""
        return self.target_schemas.get(entity_type)

    def guess_entity_type_for_table(
        self, table_name: str, threshold: float = 0.7
    ) -> Optional[str]:
        """Heuristically infer the entity type from a legacy table name."""
        norm_input = normalize_identifier(table_name)
        if not norm_input:
            return None

        best_entity = None
        best_score = 0.0

        for entity_type, aliases in self.table_aliases.items():
            for alias in aliases:
                norm_alias = normalize_identifier(alias)
                if norm_input == norm_alias:
                    return entity_type  # Exact match
                score = calculate_similarity(norm_input, norm_alias)
                if score > best_score:
                    best_score = score
                    best_entity = entity_type

        if best_score >= threshold:
            return best_entity
        return None

    def match_discovered_tables(
        self, table_names: List[str], threshold: float = 0.7
    ) -> Dict[str, str]:
        """Match a list of discovered legacy table names to Nova entity types.
        
        Returns:
            Dict[str, str]: Mapping from entity_type -> legacy table_name
        """
        matched: Dict[str, str] = {}
        assigned_tables: Set[str] = set()

        # Phase 1: Exact matches first
        for entity_type, aliases in self.table_aliases.items():
            for table in table_names:
                if table in assigned_tables:
                    continue
                norm_tbl = normalize_identifier(table)
                for alias in aliases:
                    if norm_tbl == normalize_identifier(alias):
                        matched[entity_type] = table
                        assigned_tables.add(table)
                        break
                if entity_type in matched:
                    break

        # Phase 2: Heuristic fuzzy similarity for unmatched entities
        for entity_type, aliases in self.table_aliases.items():
            if entity_type in matched:
                continue

            best_table = None
            best_score = 0.0

            for table in table_names:
                if table in assigned_tables:
                    continue
                norm_tbl = normalize_identifier(table)
                for alias in aliases:
                    score = calculate_similarity(norm_tbl, normalize_identifier(alias))
                    if score > best_score:
                        best_score = score
                        best_table = table

            if best_score >= threshold and best_table:
                matched[entity_type] = best_table
                assigned_tables.add(best_table)

        return matched

    def suggest_field_mappings(
        self,
        source_columns: List[str],
        entity_type: str,
        threshold: float = 0.65,
    ) -> Dict[str, str]:
        """Suggest field mappings from legacy source columns to Nova entity fields.
        
        Returns:
            Dict[str, str]: Mapping from legacy source_column -> Nova target_field
        """
        if entity_type not in self.target_schemas:
            return {}

        target_schema = self.target_schemas[entity_type]
        target_fields = target_schema["fields"]
        known_aliases = self.field_aliases.get(entity_type, {})

        suggested: Dict[str, str] = {}
        mapped_target_fields: Set[str] = set()

        # Step 1: Direct name matching and alias dictionary lookup
        for col in source_columns:
            norm_col = normalize_identifier(col)

            # Check exact target field name match
            for tgt_field in target_fields.keys():
                if tgt_field in mapped_target_fields:
                    continue
                if norm_col == normalize_identifier(tgt_field):
                    suggested[col] = tgt_field
                    mapped_target_fields.add(tgt_field)
                    break
            if col in suggested:
                continue

            # Check alias list
            for tgt_field, aliases in known_aliases.items():
                if tgt_field in mapped_target_fields:
                    continue
                for alias in aliases:
                    if norm_col == normalize_identifier(alias):
                        suggested[col] = tgt_field
                        mapped_target_fields.add(tgt_field)
                        break
                if col in suggested:
                    break

        # Step 2: Heuristic fuzzy matching for remaining unmapped columns
        for col in source_columns:
            if col in suggested:
                continue

            norm_col = normalize_identifier(col)
            best_target = None
            best_score = 0.0

            for tgt_field, field_spec in target_fields.items():
                if tgt_field in mapped_target_fields:
                    continue

                # Compare with target field name
                score = calculate_similarity(norm_col, normalize_identifier(tgt_field))
                if score > best_score:
                    best_score = score
                    best_target = tgt_field

                # Compare with all aliases of target field
                for alias in known_aliases.get(tgt_field, []):
                    alias_score = calculate_similarity(norm_col, normalize_identifier(alias))
                    if alias_score > best_score:
                        best_score = alias_score
                        best_target = tgt_field

            if best_score >= threshold and best_target:
                suggested[col] = best_target
                mapped_target_fields.add(best_target)

        return suggested

    def create_table_mapping_rule(
        self,
        entity_type: str,
        source_table: str,
        source_columns: Optional[List[str]] = None,
        custom_overrides: Optional[Dict[str, str]] = None,
        primary_key_field: Optional[str] = None,
        filter_clause: Optional[str] = None,
    ) -> TableMappingRule:
        """Create a complete TableMappingRule for an entity with suggested and custom mappings."""
        if entity_type not in self.target_schemas:
            raise ValueError(f"Unsupported entity type: '{entity_type}'")

        schema_info = self.target_schemas[entity_type]
        tcode = schema_info["tcode"]
        target_table = schema_info["table"]

        # Generate base mappings
        field_mappings: Dict[str, str] = {}
        if source_columns:
            field_mappings = self.suggest_field_mappings(source_columns, entity_type)

        # Apply user custom overrides
        if custom_overrides:
            for src_col, tgt_field in custom_overrides.items():
                field_mappings[src_col] = tgt_field

        # Build advanced field rules
        advanced_rules: List[FieldMappingRule] = []
        target_field_specs = schema_info["fields"]

        for src_col, tgt_field in field_mappings.items():
            spec = target_field_specs.get(tgt_field, {})
            advanced_rules.append(
                FieldMappingRule(
                    source_field=src_col,
                    target_field=tgt_field,
                    target_type=spec.get("type", "string"),
                    default_value=spec.get("default"),
                    is_required=spec.get("required", False),
                )
            )

        return TableMappingRule(
            entity_type=entity_type,
            target_tcode=tcode,
            target_table=target_table,
            source_table=source_table,
            primary_key_field=primary_key_field,
            field_mappings=field_mappings,
            advanced_field_rules=advanced_rules,
            filter_clause=filter_clause,
            enabled=True,
        )

    def generate_mapping_config(
        self,
        discovered_tables: Union[List[str], Dict[str, TableMetadata], Dict[str, List[str]]],
        auto_fuzzy: bool = True,
        custom_overrides: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> MigrationMappingConfig:
        """Generate a complete MigrationMappingConfig from discovered legacy tables and columns."""
        table_columns_map: Dict[str, List[str]] = {}

        if isinstance(discovered_tables, list):
            for tbl in discovered_tables:
                table_columns_map[tbl] = []
        elif isinstance(discovered_tables, dict):
            for tbl, val in discovered_tables.items():
                if isinstance(val, TableMetadata):
                    table_columns_map[tbl] = val.column_names
                elif isinstance(val, list):
                    table_columns_map[tbl] = val
                else:
                    table_columns_map[tbl] = []

        table_names = list(table_columns_map.keys())
        entity_matches = self.match_discovered_tables(table_names) if auto_fuzzy else {}

        mappings: Dict[str, TableMappingRule] = {}
        overrides = custom_overrides or {}

        for entity_type, source_table in entity_matches.items():
            cols = table_columns_map.get(source_table, [])
            entity_overrides = overrides.get(entity_type, {})
            rule = self.create_table_mapping_rule(
                entity_type=entity_type,
                source_table=source_table,
                source_columns=cols,
                custom_overrides=entity_overrides,
            )
            mappings[entity_type] = rule

        return MigrationMappingConfig(
            mappings=mappings,
            auto_fuzzy_match=auto_fuzzy,
            custom_overrides=overrides,
        )

    def map_row(
        self,
        row: Dict[str, Any],
        mapping_rule: TableMappingRule,
        strict: bool = False,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Translate a single legacy dictionary row into target Nova ERP entity attributes.
        
        Args:
            row: Raw legacy record dictionary.
            mapping_rule: Table mapping rule specification.
            strict: If True, raises exceptions on required field violations.
            
        Returns:
            Tuple[Dict[str, Any], List[str]]: Mapped entity dictionary and list of warnings.
        """
        entity_type = mapping_rule.entity_type
        if entity_type not in self.target_schemas:
            raise ValueError(f"Unknown entity type: '{entity_type}'")

        schema_spec = self.target_schemas[entity_type]
        target_fields = schema_spec["fields"]
        required_fields = schema_spec.get("required_fields", [])

        mapped_record: Dict[str, Any] = {}
        warnings: List[str] = []

        # Populate schema default values first
        for f_name, f_spec in target_fields.items():
            if f_spec.get("default") is not None:
                mapped_record[f_name] = f_spec.get("default")

        # Map via field_mappings / advanced_field_rules
        advanced_rule_map: Dict[str, FieldMappingRule] = {
            r.source_field: r for r in mapping_rule.advanced_field_rules
        }

        for src_col, val in row.items():
            # Find target field
            target_field = mapping_rule.field_mappings.get(src_col)
            if not target_field:
                continue

            rule = advanced_rule_map.get(src_col)
            target_type = (rule.target_type if rule else None) or target_fields.get(
                target_field, {}
            ).get("type", "string")
            transform = rule.transform if rule else None
            default_val = rule.default_value if rule else target_fields.get(target_field, {}).get("default")

            cast_val = self.caster.cast(
                value=val,
                target_type=target_type,
                transform=transform,
                default=default_val,
                strict=strict,
            )

            if cast_val is not None:
                mapped_record[target_field] = cast_val

        # Check required fields
        for req_field in required_fields:
            if req_field not in mapped_record or mapped_record[req_field] is None:
                msg = f"Missing required field '{req_field}' for entity '{entity_type}'"
                warnings.append(msg)
                if strict:
                    raise ValueError(msg)

        return mapped_record, warnings

    def map_rows(
        self,
        rows: List[Dict[str, Any]],
        mapping_rule: TableMappingRule,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Translate a batch of legacy records.
        
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
                (valid_mapped_records, row_errors)
        """
        valid_records: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for idx, row in enumerate(rows):
            try:
                mapped, row_warnings = self.map_row(row, mapping_rule, strict=False)
                has_critical_error = False
                for warning in row_warnings:
                    if "Missing required field" in warning:
                        has_critical_error = True
                        errors.append({
                            "row_index": idx,
                            "error": warning,
                            "raw_data": row,
                        })
                        break

                if not has_critical_error:
                    valid_records.append(mapped)
            except Exception as e:
                errors.append({
                    "row_index": idx,
                    "error": str(e),
                    "raw_data": row,
                })

        return valid_records, errors


# Global singleton instance
mapping_engine = MappingEngine()
