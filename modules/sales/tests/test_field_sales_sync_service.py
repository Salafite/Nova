from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from modules.sales.services.field_sales_sync_service import (
    FieldSalesSyncService,
    _to_float,
    _to_int,
    _get_utc_now,
)
from modules.sales.models.field_sales import (
    ConflictResolutionItem,
    ConflictType,
    FieldSalesBatchSyncRequest,
    FieldSalesBatchSyncResponse,
    FieldSalesOrderLine,
    FieldSalesOrderSubmission,
    FieldSalesResolveConflictRequest,
    FieldSalesValidationRequest,
    LineConflictDetail,
    OrderSyncResult,
    ResolutionAction,
    SyncStatus,
)


def test_sync_helper_functions():
    assert _to_float(25.5) == 25.5
    assert _to_float(Decimal("99.95")) == 99.95
    assert _to_float("12.34") == 12.34
    assert _to_float(None, 1.0) == 1.0
    assert _to_float("invalid", 2.0) == 2.0

    assert _to_int(42) == 42
    assert _to_int("100") == 100
    assert _to_int(None) is None
    assert _to_int("bad", 5) == 5

    now = _get_utc_now()
    assert now.tzinfo is not None


def test_sync_idempotency_hit():
    """Verify that an order with a previously synced client_order_uuid is returned without duplicate insertion."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # find_order_by_uuid returns existing row
    mock_cursor.fetchone.return_value = {
        "id": 101,
        "order_number": "FSO-20260822-0001",
        "customer_id": 5,
        "warehouse_id": 1,
        "subtotal": Decimal("100.00"),
        "tax": Decimal("5.00"),
        "grand_total": Decimal("105.00"),
        "status": "Pending",
        "sync_status": "Synced",
        "client_order_uuid": "uuid-existing-1234",
    }

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-existing-1234",
        customer_id=5,
        warehouse_id=1,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=10,
                product_name="Product A",
                qty=2.0,
                unit_price=50.0,
                line_total=100.0,
            )
        ],
    )

    request = FieldSalesBatchSyncRequest(orders=[order_sub])
    response = service.sync_batch(request, conn=mock_conn)

    assert response.success is True
    assert len(response.results) == 1
    res = response.results[0]
    assert res.status == "AlreadySynced"
    assert res.is_duplicate is True
    assert res.server_order_id == 101
    assert res.order_number == "FSO-20260822-0001"
    assert res.grand_total == 105.00


def test_sync_successful_order_creation_with_stock_deduction():
    """Verify successful atomic insertion into t0012, t0013, stock deduction in t0009, movement in t0064, and customer balance update in t0010."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Sequence of cursor queries:
    # 1. find_order_by_uuid -> None
    # 2. check_order_conflicts:
    #    - customer lookup -> customer active, credit limit 1000, balance 100
    #    - product lookup line 1 -> product 10 active, price 20
    #    - stock lookup line 1 -> qty 50
    # 3. sync_single_order_transaction:
    #    - tax rate lookup -> rate 5.0
    #    - order number taken check -> False
    #    - insert t0012 -> returning id=201
    #    - insert t0013 line 1
    #    - stock select for update -> current qty 50
    #    - stock update t0009 -> new qty 48
    #    - insert t0064 movement
    #    - update t0010 customer balance

    mock_cursor.fetchone.side_effect = [
        # 1. find_order_by_uuid
        None,
        # 2. customer lookup
        {"id": 5, "name": "Acme Supermarket", "is_active": True, "credit_limit": Decimal("1000.00"), "balance": Decimal("100.00")},
        # 3. product lookup
        {"id": 10, "name": "Fresh Apples 1kg", "sku": "APP-01", "price": Decimal("20.00"), "category": "Produce", "is_active": True},
        # 4. stock lookup
        {"qty": Decimal("50.0")},
        # 5. tax rate lookup (t0085)
        {"rate": Decimal("5.0")},
        # 6. order number taken check (t0012)
        None,
        # 7. insert t0012 returning id
        {"id": 201},
        # 8. stock select for update (t0009)
        {"id": 88, "qty": Decimal("50.0")},
    ]

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-fresh-9999",
        order_number="FSO-20260822-0099",
        customer_id=5,
        warehouse_id=1,
        tax_rate_id=2,
        notes="Deliver to back door",
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=10,
                product_name="Fresh Apples 1kg",
                qty=2.0,
                unit_price=20.0,
                discount_pct=10.0,  # 2 * 20 * 0.9 = 36.00
                line_total=36.00,
            )
        ],
    )

    response = service.sync_batch(FieldSalesBatchSyncRequest(orders=[order_sub]), conn=mock_conn)

    assert response.success is True
    assert response.synced_count == 1
    assert response.conflict_count == 0
    assert response.failed_count == 0
    assert len(response.results) == 1

    res = response.results[0]
    assert res.status == SyncStatus.SYNCED.value
    assert res.server_order_id == 201
    assert res.order_number == "FSO-20260822-0099"
    assert res.subtotal == 36.00
    assert res.tax == 1.80  # 36 * 5% = 1.80
    assert res.grand_total == 37.80
    assert mock_conn.commit.called


def test_conflict_detection_out_of_stock_and_insufficient_qty():
    """Verify conflict detection when stock is depleted or insufficient with substitute suggestions."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Query responses for check_order_conflicts:
    # 1. customer lookup -> active
    # 2. product 1 lookup -> active, category='Beverages'
    # 3. stock 1 lookup -> 0.0 (OUT_OF_STOCK)
    # 4. substitute query for product 1 -> [substitute 1]
    # 5. product 2 lookup -> active, category='Beverages'
    # 6. stock 2 lookup -> 5.0 (requested 10.0 -> INSUFFICIENT_QTY)
    # 7. substitute query for product 2 -> [substitute 2]

    mock_cursor.fetchone.side_effect = [
        # Customer
        {"id": 1, "name": "Corner Store", "is_active": True, "credit_limit": Decimal("5000"), "balance": Decimal("0")},
        # Product 1
        {"id": 101, "name": "Orange Juice 1L", "sku": "OJ-01", "price": Decimal("4.00"), "category": "Beverages", "is_active": True},
        # Stock 1 (0 stock)
        {"qty": Decimal("0.0")},
        # Product 2
        {"id": 102, "name": "Apple Juice 1L", "sku": "AJ-01", "price": Decimal("3.80"), "category": "Beverages", "is_active": True},
        # Stock 2 (5 available, 10 requested)
        {"qty": Decimal("5.0")},
    ]

    mock_cursor.fetchall.side_effect = [
        # Substitutes for Product 1
        [{"id": 103, "name": "Grape Juice 1L", "sku": "GJ-01", "price": Decimal("4.20"), "available_qty": Decimal("20.0")}],
        # Substitutes for Product 2
        [{"id": 104, "name": "Pear Juice 1L", "sku": "PJ-01", "price": Decimal("3.90"), "available_qty": Decimal("15.0")}],
    ]

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-conflict-1",
        customer_id=1,
        warehouse_id=2,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=101,
                product_name="Orange Juice 1L",
                qty=5.0,
                unit_price=4.00,
                line_total=20.00,
            ),
            FieldSalesOrderLine(
                line_number=2,
                product_id=102,
                product_name="Apple Juice 1L",
                qty=10.0,
                unit_price=3.80,
                line_total=38.00,
            ),
        ],
    )

    conflicts = service.check_order_conflicts(order_sub, conn=mock_conn)

    assert len(conflicts) == 2

    # Conflict 1: Out of stock
    c1 = conflicts[0]
    assert c1.product_id == 101
    assert c1.conflict_type == ConflictType.OUT_OF_STOCK.value
    assert c1.available_qty == 0.0
    assert c1.suggested_action == ResolutionAction.SUBSTITUTE.value
    assert len(c1.suggested_substitutes) == 1
    assert c1.suggested_substitutes[0]["name"] == "Grape Juice 1L"

    # Conflict 2: Insufficient quantity
    c2 = conflicts[1]
    assert c2.product_id == 102
    assert c2.conflict_type == ConflictType.INSUFFICIENT_QTY.value
    assert c2.requested_qty == 10.0
    assert c2.available_qty == 5.0
    assert c2.suggested_action == ResolutionAction.ADJUST_QTY.value


def test_conflict_detection_inactive_customer_and_price_mismatch():
    """Verify conflict detection for inactive customer and price list rule mismatches."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. Customer inactive
    mock_cursor.fetchone.return_value = {
        "id": 99,
        "name": "Defunct Mart",
        "is_active": False,
        "credit_limit": Decimal("0"),
        "balance": Decimal("0"),
    }

    order_inactive = FieldSalesOrderSubmission(
        client_order_uuid="uuid-inactive-cust",
        customer_id=99,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=1,
                product_name="Bread",
                qty=1.0,
                unit_price=2.00,
                line_total=2.00,
            )
        ],
    )

    conflicts = service.check_order_conflicts(order_inactive, conn=mock_conn)
    assert len(conflicts) >= 1
    assert conflicts[0].conflict_type == ConflictType.CUSTOMER_INACTIVE.value


def test_validate_batch_pre_sync_check():
    """Verify pre-sync batch validation without committing changes."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Order 1: Idempotency hit (already synced)
    # Order 2: Clean order (valid)
    mock_cursor.fetchone.side_effect = [
        # Order 1 UUID lookup -> found
        {"id": 50, "order_number": "FSO-20260822-0050", "subtotal": Decimal("50.00"), "tax": Decimal("2.50"), "grand_total": Decimal("52.50")},
        # Order 2 UUID lookup -> not found
        None,
        # Order 2 Customer check
        {"id": 2, "name": "Daily Store", "is_active": True, "credit_limit": Decimal("1000"), "balance": Decimal("50")},
        # Order 2 Product check
        {"id": 20, "name": "Butter 250g", "sku": "BUT-01", "price": Decimal("3.00"), "category": "Dairy", "is_active": True},
        # Order 2 Stock check
        {"qty": Decimal("100.0")},
    ]

    order_1 = FieldSalesOrderSubmission(
        client_order_uuid="uuid-dup",
        customer_id=1,
        lines=[FieldSalesOrderLine(product_id=10, product_name="P1", qty=1.0, unit_price=50.0, line_total=50.0)],
    )
    order_2 = FieldSalesOrderSubmission(
        client_order_uuid="uuid-new",
        customer_id=2,
        lines=[FieldSalesOrderLine(product_id=20, product_name="Butter 250g", qty=2.0, unit_price=3.0, line_total=6.0)],
    )

    validation_req = FieldSalesValidationRequest(orders=[order_1, order_2])
    validation_resp = service.validate_batch(validation_req, conn=mock_conn)

    assert validation_resp.valid is True
    assert validation_resp.total_orders == 2
    assert validation_resp.conflicts_found == 0
    assert validation_resp.results[0].status == "AlreadySynced"
    assert validation_resp.results[1].status == "Valid"


def test_resolve_and_sync_adjust_qty_and_substitute():
    """Verify conflict resolution flow applying adjust_qty, substitute, and price acceptance."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # In resolve_and_sync:
    # 1. Fetch substitute product details (id=103 -> price=4.20)
    # 2. _sync_single_order_transaction:
    #    - find_order_by_uuid -> None
    #    - check_order_conflicts:
    #      - customer -> active
    #      - product line 1 (adjusted qty=2) -> product 102 active
    #      - stock line 1 -> 5.0 (requested 2.0 -> valid!)
    #      - product line 2 (substitute id=103) -> product 103 active
    #      - stock line 2 -> 20.0 (requested 1.0 -> valid!)
    #    - tax rate lookup -> 5%
    #    - order number check -> None
    #    - insert t0012 -> id=301
    #    - stock updates & customer balance

    mock_cursor.fetchone.side_effect = [
        # 1. Substitute product lookup
        {"name": "Grape Juice 1L", "sku": "GJ-01", "price": Decimal("4.20")},
        # 2. UUID lookup
        None,
        # 3. Customer check
        {"id": 1, "name": "Best Mart", "is_active": True, "credit_limit": Decimal("5000"), "balance": Decimal("0")},
        # 4. Line 1 Product lookup (Apple Juice)
        {"id": 102, "name": "Apple Juice 1L", "sku": "AJ-01", "price": Decimal("3.80"), "category": "Beverages", "is_active": True},
        # 5. Line 1 Stock lookup (5.0 available)
        {"qty": Decimal("5.0")},
        # 6. Line 2 Product lookup (Grape Juice substitute)
        {"id": 103, "name": "Grape Juice 1L", "sku": "GJ-01", "price": Decimal("4.20"), "category": "Beverages", "is_active": True},
        # 7. Line 2 Stock lookup (20.0 available)
        {"qty": Decimal("20.0")},
        # 8. Tax rate lookup
        {"rate": Decimal("0.0")},
        # 9. Order number lookup
        None,
        # 10. Insert t0012
        {"id": 301},
        # 11. Line 1 stock select for update
        {"id": 1, "qty": Decimal("5.0")},
        # 12. Line 2 stock select for update
        {"id": 2, "qty": Decimal("20.0")},
    ]

    original_order = FieldSalesOrderSubmission(
        client_order_uuid="uuid-resolve-1",
        customer_id=1,
        warehouse_id=1,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=102,
                product_name="Apple Juice 1L",
                qty=10.0,
                unit_price=3.80,
                line_total=38.00,
            ),
            FieldSalesOrderLine(
                line_number=2,
                product_id=101,
                product_name="Orange Juice 1L",
                qty=1.0,
                unit_price=4.00,
                line_total=4.00,
            ),
        ],
    )

    resolutions = [
        # Line 1: Adjust quantity to 2.0
        ConflictResolutionItem(
            line_number=1,
            product_id=102,
            action=ResolutionAction.ADJUST_QTY.value,
            adjusted_qty=2.0,
        ),
        # Line 2: Substitute with Grape Juice (id=103)
        ConflictResolutionItem(
            line_number=2,
            product_id=101,
            action=ResolutionAction.SUBSTITUTE.value,
            substitute_product_id=103,
            substitute_product_name="Grape Juice 1L",
        ),
    ]

    resolve_req = FieldSalesResolveConflictRequest(
        client_order_uuid="uuid-resolve-1",
        order_data=original_order,
        resolutions=resolutions,
    )

    result = service.resolve_and_sync(resolve_req, conn=mock_conn)

    assert result.status == SyncStatus.SYNCED.value
    assert result.server_order_id == 301
    assert result.is_duplicate is False
    # Line 1: 2 * 3.80 = 7.60; Line 2: 1 * 4.20 = 4.20 -> Subtotal = 11.80
    assert result.subtotal == 11.80
    assert result.grand_total == 11.80


def test_resolve_and_sync_all_removed():
    """Verify that removing all line items returns a failure response without creating an empty order."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()

    order = FieldSalesOrderSubmission(
        client_order_uuid="uuid-empty-order",
        customer_id=1,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=10,
                product_name="Out of Stock Item",
                qty=1.0,
                unit_price=10.0,
                line_total=10.0,
            )
        ],
    )

    resolve_req = FieldSalesResolveConflictRequest(
        client_order_uuid="uuid-empty-order",
        order_data=order,
        resolutions=[
            ConflictResolutionItem(
                line_number=1,
                product_id=10,
                action=ResolutionAction.REMOVE_ITEM.value,
            )
        ],
    )

    result = service.resolve_and_sync(resolve_req, conn=mock_conn)

    assert result.status == SyncStatus.FAILED.value
    assert "cannot be empty" in result.message.lower()


def test_price_mismatch_and_accept_price_resolution():
    """Verify price mismatch detection when unit_price deviates from contracted price list, and resolution with accept_price."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. Customer check -> active
    # 2. Product check -> active, base price 10.00
    # 3. Stock check -> 100.0
    # 4. Price rule check (t0084) -> contracted price is 8.50 (order submitted 10.00)
    mock_cursor.fetchone.side_effect = [
        {"id": 1, "name": "Key Account A", "is_active": True, "credit_limit": Decimal("10000"), "balance": Decimal("0")},
        {"id": 55, "name": "Bulk Sugar 25kg", "sku": "SUG-25", "price": Decimal("10.00"), "category": "Pantry", "is_active": True},
        {"qty": Decimal("100.0")},
        {"unit_price": Decimal("8.50")},
    ]

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-price-mismatch",
        customer_id=1,
        warehouse_id=1,
        price_list_id=3,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=55,
                product_name="Bulk Sugar 25kg",
                qty=10.0,
                unit_price=10.00,  # Differs from contracted price 8.50
                line_total=100.00,
            )
        ],
    )

    conflicts = service.check_order_conflicts(order_sub, conn=mock_conn)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.conflict_type == ConflictType.PRICE_MISMATCH.value
    assert c.requested_price == 10.00
    assert c.current_price == 8.50
    assert c.suggested_action == ResolutionAction.ACCEPT_PRICE.value

    # Now test resolving with accept_price
    # Sequence of cursor queries for resolve_and_sync:
    # 1. UUID lookup -> None
    # 2. check_order_conflicts:
    #    - Customer -> active
    #    - Product -> active
    #    - Stock -> 100.0
    #    - Price rule -> 8.50 (now matching 8.50!)
    # 3. Tax rate lookup -> None
    # 4. Order number lookup -> None
    # 5. Insert t0012 -> returning id=401
    # 6. Stock update t0009
    mock_cursor.fetchone.side_effect = [
        None,
        {"id": 1, "name": "Key Account A", "is_active": True, "credit_limit": Decimal("10000"), "balance": Decimal("0")},
        {"id": 55, "name": "Bulk Sugar 25kg", "sku": "SUG-25", "price": Decimal("10.00"), "category": "Pantry", "is_active": True},
        {"qty": Decimal("100.0")},
        {"unit_price": Decimal("8.50")},
        {"rate": Decimal("0.0")},
        None,
        {"id": 401},
        {"id": 99, "qty": Decimal("100.0")},
    ]

    resolve_req = FieldSalesResolveConflictRequest(
        client_order_uuid="uuid-price-mismatch",
        order_data=order_sub,
        resolutions=[
            ConflictResolutionItem(
                line_number=1,
                product_id=55,
                action=ResolutionAction.ACCEPT_PRICE.value,
                accepted_price=8.50,
            )
        ],
    )

    result = service.resolve_and_sync(resolve_req, conn=mock_conn)
    assert result.status == SyncStatus.SYNCED.value
    assert result.server_order_id == 401
    assert result.subtotal == 85.00  # 10 * 8.50 = 85.00


def test_sync_db_exception_rollback():
    """Verify transaction rollback and failure result when DB error occurs during order creation."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. find_order_by_uuid -> None
    # 2. check_order_conflicts:
    #    - Customer -> active
    #    - Product -> active
    #    - Stock -> 50.0
    # 3. Tax lookup -> raises database exception on execute
    mock_cursor.fetchone.side_effect = [
        None,
        {"id": 1, "name": "Test Cust", "is_active": True, "credit_limit": Decimal("1000"), "balance": Decimal("0")},
        {"id": 10, "name": "Prod 10", "sku": "P10", "price": Decimal("5.0"), "category": "Cat1", "is_active": True},
        {"qty": Decimal("50.0")},
    ]
    mock_cursor.execute.side_effect = [
        None,  # find_order_by_uuid
        None,  # customer
        None,  # product
        None,  # stock
        Exception("Postgres connection dropped!"),  # error during order creation
    ]

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-error-1",
        customer_id=1,
        warehouse_id=1,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=10,
                product_name="Prod 10",
                qty=1.0,
                unit_price=5.0,
                line_total=5.0,
            )
        ],
    )

    response = service.sync_batch(FieldSalesBatchSyncRequest(orders=[order_sub]), conn=mock_conn)

    assert response.success is False
    assert response.failed_count == 1
    assert len(response.results) == 1
    assert response.results[0].status == SyncStatus.FAILED.value
    assert "Postgres connection dropped" in response.results[0].message
    assert mock_conn.rollback.called


def test_get_suggested_substitutes():
    """Verify suggested substitutes lookup across category and warehouses."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # With warehouse_id specified
    mock_cursor.fetchall.return_value = [
        {"id": 201, "name": "Almond Milk 1L", "sku": "AM-01", "price": Decimal("4.50"), "available_qty": Decimal("12.0")},
        {"id": 202, "name": "Soy Milk 1L", "sku": "SM-01", "price": Decimal("3.80"), "available_qty": Decimal("8.0")},
    ]

    subs = service.get_suggested_substitutes(
        product_id=200,
        category="Dairy Alternatives",
        warehouse_id=1,
        limit=2,
        conn=mock_conn,
    )

    assert len(subs) == 2
    assert subs[0]["name"] == "Almond Milk 1L"
    assert subs[0]["available_qty"] == 12.0
    assert subs[1]["name"] == "Soy Milk 1L"
    assert subs[1]["available_qty"] == 8.0


def test_conflict_detection_base_catalog_price_shift():
    """Verify conflict detection when base catalog price in t0003 shifted while offline and price_list_id is None."""
    service = FieldSalesSyncService(schema="Nova")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # 1. Customer check -> active
    # 2. Product check -> active, current catalog price 15.00 (order captured at 12.00)
    # 3. Stock check -> 50.0
    mock_cursor.fetchone.side_effect = [
        {"id": 1, "name": "Regular Customer", "is_active": True, "credit_limit": Decimal("5000"), "balance": Decimal("0")},
        {"id": 77, "name": "Olive Oil 1L", "sku": "OIL-01", "price": Decimal("15.00"), "category": "Pantry", "is_active": True},
        {"qty": Decimal("50.0")},
    ]

    order_sub = FieldSalesOrderSubmission(
        client_order_uuid="uuid-base-price-shift",
        customer_id=1,
        warehouse_id=1,
        price_list_id=None,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=77,
                product_name="Olive Oil 1L",
                qty=5.0,
                unit_price=12.00,  # Differs from current base catalog price 15.00
                line_total=60.00,
            )
        ],
    )

    conflicts = service.check_order_conflicts(order_sub, conn=mock_conn)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.conflict_type == ConflictType.PRICE_MISMATCH.value
    assert c.requested_price == 12.00
    assert c.current_price == 15.00
    assert c.suggested_action == ResolutionAction.ACCEPT_PRICE.value


