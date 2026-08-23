from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from modules.sales.services.field_sales_catalog_service import (
    FieldSalesCatalogService,
    _to_float,
    _to_int,
    _parse_timestamp,
)
from modules.sales.models.field_sales import (
    FieldSalesCatalogBundle,
    CatalogProductItem,
    FieldSalesCustomerProfile,
    CustomerOrderSummary,
)


def test_helper_functions():
    assert _to_float(10.5) == 10.5
    assert _to_float(Decimal("15.25")) == 15.25
    assert _to_float("3.14") == 3.14
    assert _to_float(None, 0.0) == 0.0
    assert _to_float("invalid", 5.0) == 5.0

    assert _to_int(10) == 10
    assert _to_int("20") == 20
    assert _to_int(None) is None
    assert _to_int("invalid", 1) == 1

    dt = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
    assert _parse_timestamp(dt) == dt
    parsed = _parse_timestamp("2026-08-22T10:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert _parse_timestamp(None) is None
    assert _parse_timestamp("invalid") is None


def test_get_products_with_stock_and_barcodes():
    service = FieldSalesCatalogService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Query 1: Stock levels (T0009)
    # Query 2: Barcodes (T0004)
    # Query 3: UOMs (T0007 / T0001)
    # Query 4: Products (T0003)
    mock_cursor.fetchall.side_effect = [
        # Stock levels
        [
            {"product_id": 1, "warehouse_id": 10, "qty": Decimal("25.0")},
            {"product_id": 1, "warehouse_id": 20, "qty": Decimal("15.0")},
            {"product_id": 2, "warehouse_id": 10, "qty": Decimal("50.0")},
        ],
        # Barcodes
        [
            {"product_id": 1, "barcode": "789123456001"},
            {"product_id": 2, "barcode": "789123456002"},
        ],
        # UOMs
        [
            {"product_id": 1, "base_uom_id": 1, "uom_code": "PCS", "uom_name": "Pieces"},
            {"product_id": 2, "base_uom_id": 2, "uom_code": "BOX", "uom_name": "Boxes"},
        ],
        # Products
        [
            {
                "id": 1,
                "name": "Milk 1L",
                "sku": "MILK-01",
                "price": Decimal("3.50"),
                "cost_price": Decimal("2.10"),
                "category": "Dairy",
                "brand": "FarmFresh",
                "tax_rate": Decimal("5.0"),
                "image_url": "http://img/milk.png",
                "is_active": True,
                "updated_at": datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc),
            },
            {
                "id": 2,
                "name": "Yogurt 500g",
                "sku": "YOG-01",
                "price": Decimal("4.20"),
                "cost_price": Decimal("2.80"),
                "category": "Dairy",
                "brand": "FarmFresh",
                "tax_rate": Decimal("5.0"),
                "image_url": None,
                "is_active": True,
                "updated_at": datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc),
            },
        ],
    ]

    products = service.get_products(conn=mock_conn)
    assert len(products) == 2

    p1 = products[0]
    assert p1.id == 1
    assert p1.name == "Milk 1L"
    assert p1.sku == "MILK-01"
    assert p1.barcode == "789123456001"
    assert p1.uom_code == "PCS"
    assert p1.base_price == 3.50
    assert p1.available_qty == 40.0  # 25 + 15 across warehouses
    assert p1.warehouse_stock == {"10": 25.0, "20": 15.0}

    # Test warehouse_id filtering
    mock_cursor.fetchall.side_effect = [
        [{"product_id": 1, "warehouse_id": 10, "qty": Decimal("25.0")}],
        [{"product_id": 1, "barcode": "789123456001"}],
        [{"product_id": 1, "base_uom_id": 1, "uom_code": "PCS", "uom_name": "Pieces"}],
        [{
            "id": 1,
            "name": "Milk 1L",
            "sku": "MILK-01",
            "price": Decimal("3.50"),
            "cost_price": None,
            "category": "Dairy",
            "brand": None,
            "tax_rate": Decimal("0.0"),
            "image_url": None,
            "is_active": True,
            "updated_at": None,
        }],
    ]
    p_wh10 = service.get_products(warehouse_id=10, conn=mock_conn)
    assert p_wh10[0].available_qty == 25.0
    assert p_wh10[0].warehouse_id == 10


def test_get_customers_with_credit_and_history():
    service = FieldSalesCatalogService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Query 1: Customer profiles (T0010 + T0096 + T0085)
    # Query 2: Batch recent orders (T0012)
    # Query 3: Batch order lines (T0013)
    mock_cursor.fetchall.side_effect = [
        # Customer profiles
        [
            {
                "id": 101,
                "name": "Corner Market",
                "group_name": "Retail",
                "phone": "555-1234",
                "email": "corner@market.test",
                "credit_limit": Decimal("2000.00"),
                "balance": Decimal("500.00"),
                "is_active": True,
                "default_price_list_id": 2,
                "default_tax_rate_id": 1,
                "payment_term_id": 3,
                "updated_at": datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc),
                "payment_term_name": "Net 30",
                "payment_term_days": 30,
                "tax_rate_pct": Decimal("5.0"),
            },
            {
                "id": 102,
                "name": "Big Supermarket",
                "group_name": "Key Accounts",
                "phone": "555-9876",
                "email": "big@super.test",
                "credit_limit": Decimal("0.00"),  # Unlimited
                "balance": Decimal("1500.00"),
                "is_active": True,
                "default_price_list_id": 1,
                "default_tax_rate_id": 1,
                "payment_term_id": None,
                "updated_at": None,
                "payment_term_name": None,
                "payment_term_days": None,
                "tax_rate_pct": Decimal("5.0"),
            },
        ],
        # Ranked recent orders
        [
            {
                "id": 501,
                "order_number": "SO-2026-001",
                "customer_id": 101,
                "order_date": date(2026, 8, 20),
                "grand_total": Decimal("105.00"),
                "status": "Confirmed",
            },
        ],
        # Order lines
        [
            {
                "sales_order_id": 501,
                "product_id": 1,
                "product_name": "Milk 1L",
                "qty": Decimal("30.0"),
                "unit_price": Decimal("3.50"),
                "line_total": Decimal("105.00"),
            }
        ],
    ]

    customers = service.get_customers(include_recent_orders=True, conn=mock_conn)
    assert len(customers) == 2

    c1 = customers[0]
    assert c1.id == 101
    assert c1.name == "Corner Market"
    assert c1.credit_limit == 2000.0
    assert c1.balance == 500.0
    assert c1.available_credit == 1500.0
    assert c1.payment_term_name == "Net 30"
    assert c1.payment_term_days == 30
    assert len(c1.recent_orders) == 1
    assert c1.recent_orders[0].order_number == "SO-2026-001"
    assert c1.recent_orders[0].grand_total == 105.0
    assert len(c1.recent_orders[0].lines) == 1
    assert c1.recent_orders[0].lines[0].product_name == "Milk 1L"
    assert c1.recent_orders[0].lines[0].qty == 30.0

    c2 = customers[1]
    assert c2.id == 102
    assert c2.credit_limit == 0.0
    assert c2.available_credit == 999999.0  # Unlimited credit
    assert len(c2.recent_orders) == 0


def test_get_price_rules():
    service = FieldSalesCatalogService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        {
            "id": 1,
            "price_list_id": 2,
            "product_id": 10,
            "unit_price": Decimal("2.85"),
            "min_qty": 5,
            "uom_id": 1,
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
        },
    ]

    rules = service.get_price_rules(price_list_id=2, conn=mock_conn)
    assert len(rules) == 1
    assert rules[0].price_list_id == 2
    assert rules[0].product_id == 10
    assert rules[0].unit_price == 2.85
    assert rules[0].min_qty == 5.0


def test_get_metadata_lookups():
    service = FieldSalesCatalogService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchall.side_effect = [
        # Warehouses
        [{"id": 1, "name": "Main Warehouse", "location": "Downtown", "is_active": True}],
        # Tax Rates
        [{"id": 1, "name": "Standard VAT 5%", "code": "VAT5", "rate": Decimal("5.0"), "type": "Percentage", "is_default": True}],
        # Payment Terms
        [{"id": 1, "name": "Net 30", "code": "NET30", "description": "30 days", "due_days": 30, "discount_percentage": Decimal("0.0"), "discount_days": 0}],
    ]

    meta = service.get_metadata_lookups(conn=mock_conn)
    assert len(meta["warehouses"]) == 1
    assert meta["warehouses"][0]["name"] == "Main Warehouse"
    assert len(meta["tax_rates"]) == 1
    assert meta["tax_rates"][0]["rate"] == 5.0
    assert len(meta["payment_terms"]) == 1
    assert meta["payment_terms"][0]["due_days"] == 30


def test_get_mobile_catalog_bundle():
    service = FieldSalesCatalogService(schema="Nova")

    mock_conn = MagicMock()
    with patch.object(service, "get_products", return_value=[CatalogProductItem(id=1, name="Item 1", base_price=10.0)]):
        with patch.object(service, "get_customers", return_value=[FieldSalesCustomerProfile(id=1, name="Customer 1")]):
            with patch.object(service, "get_price_rules", return_value=[]):
                with patch.object(service, "get_metadata_lookups", return_value={"warehouses": [], "tax_rates": [], "payment_terms": []}):
                    bundle = service.get_mobile_catalog(conn=mock_conn)

                    assert isinstance(bundle, FieldSalesCatalogBundle)
                    assert bundle.total_products == 1
                    assert bundle.total_customers == 1
                    assert len(bundle.products) == 1
                    assert len(bundle.customers) == 1
