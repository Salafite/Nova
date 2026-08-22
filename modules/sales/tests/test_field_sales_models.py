from datetime import date, datetime
import pytest
from pydantic import ValidationError

from modules.sales.models.field_sales import (
    ConflictType,
    SyncStatus,
    ResolutionAction,
    CatalogProductItem,
    CustomerPriceRule,
    CustomerOrderLineSummary,
    CustomerOrderSummary,
    FieldSalesCustomerProfile,
    FieldSalesCatalogBundle,
    FieldSalesOrderLine,
    FieldSalesOrderSubmission,
    FieldSalesBatchSyncRequest,
    LineConflictDetail,
    OrderSyncResult,
    FieldSalesBatchSyncResponse,
    FieldSalesValidationRequest,
    FieldSalesValidationResponse,
    ConflictResolutionItem,
    FieldSalesResolveConflictRequest,
)


def test_field_sales_enums():
    assert ConflictType.OUT_OF_STOCK == "OUT_OF_STOCK"
    assert ConflictType.INSUFFICIENT_QTY == "INSUFFICIENT_QTY"
    assert ConflictType.PRICE_MISMATCH == "PRICE_MISMATCH"
    assert SyncStatus.SYNCED == "Synced"
    assert SyncStatus.CONFLICT == "Conflict"
    assert ResolutionAction.ADJUST_QTY == "adjust_qty"


def test_catalog_product_item():
    item = CatalogProductItem(
        id=101,
        sku="SKU-TEST-01",
        barcode="123456789012",
        name="Fresh Whole Milk 1L",
        category="Dairy",
        base_price=3.50,
        available_qty=50.0,
        warehouse_id=1,
        warehouse_stock={"1": 50.0},
    )
    assert item.id == 101
    assert item.sku == "SKU-TEST-01"
    assert item.base_price == 3.50
    assert item.is_active is True
    assert item.warehouse_stock["1"] == 50.0


def test_customer_profile_and_history():
    order_summary = CustomerOrderSummary(
        id=501,
        order_number="SO-2026-001",
        order_date=date(2026, 8, 20),
        grand_total=175.50,
        status="Confirmed",
        item_count=2,
        lines=[
            CustomerOrderLineSummary(
                product_id=101,
                product_name="Fresh Whole Milk 1L",
                qty=10.0,
                unit_price=3.50,
                line_total=35.0,
            )
        ],
    )
    profile = FieldSalesCustomerProfile(
        id=1,
        name="Metro Grocery Store #12",
        credit_limit=5000.0,
        balance=1200.0,
        available_credit=3800.0,
        payment_term_id=2,
        payment_term_name="Net 30",
        payment_term_days=30,
        recent_orders=[order_summary],
    )
    assert profile.name == "Metro Grocery Store #12"
    assert len(profile.recent_orders) == 1
    assert profile.recent_orders[0].grand_total == 175.50
    assert profile.recent_orders[0].lines[0].qty == 10.0


def test_catalog_bundle():
    bundle = FieldSalesCatalogBundle(
        total_products=1,
        total_customers=1,
        products=[
            CatalogProductItem(
                id=1,
                name="Butter 250g",
                base_price=2.20,
            )
        ],
        customers=[
            FieldSalesCustomerProfile(
                id=1,
                name="Cafe Deluxe",
            )
        ],
        price_rules=[
            CustomerPriceRule(
                price_list_id=1,
                product_id=1,
                unit_price=1.95,
            )
        ],
    )
    assert bundle.total_products == 1
    assert len(bundle.products) == 1
    assert len(bundle.customers) == 1
    assert len(bundle.price_rules) == 1
    assert isinstance(bundle.sync_timestamp, datetime)


def test_order_submission_and_batch_request():
    order = FieldSalesOrderSubmission(
        client_order_uuid="uuid-1234-5678-9abc",
        customer_id=1,
        sales_rep_id=5,
        warehouse_id=1,
        offline_created_at=datetime(2026, 8, 22, 10, 30, 0),
        subtotal=70.0,
        tax=7.0,
        grand_total=77.0,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=101,
                product_name="Fresh Whole Milk 1L",
                qty=20.0,
                unit_price=3.50,
                line_total=70.0,
            )
        ],
    )
    assert order.client_order_uuid == "uuid-1234-5678-9abc"
    assert len(order.lines) == 1

    batch_req = FieldSalesBatchSyncRequest(
        orders=[order],
        device_id="iPad-Field-01",
    )
    assert len(batch_req.orders) == 1
    assert batch_req.device_id == "iPad-Field-01"


def test_order_submission_validation_error():
    # Empty lines should fail validation
    with pytest.raises(ValidationError):
        FieldSalesOrderSubmission(
            client_order_uuid="uuid-1234",
            customer_id=1,
            lines=[],
        )


def test_conflict_reporting_and_batch_response():
    conflict = LineConflictDetail(
        line_number=1,
        product_id=101,
        product_name="Fresh Whole Milk 1L",
        conflict_type=ConflictType.INSUFFICIENT_QTY.value,
        requested_qty=20.0,
        available_qty=8.0,
        message="Only 8 units available in warehouse",
        suggested_action="adjust_qty",
    )
    result = OrderSyncResult(
        client_order_uuid="uuid-1234",
        status=SyncStatus.CONFLICT.value,
        conflicts=[conflict],
    )
    response = FieldSalesBatchSyncResponse(
        success=False,
        synced_count=0,
        conflict_count=1,
        failed_count=0,
        results=[result],
    )
    assert response.conflict_count == 1
    assert len(response.results[0].conflicts) == 1
    assert response.results[0].conflicts[0].conflict_type == "INSUFFICIENT_QTY"


def test_conflict_resolution_models():
    resolution = ConflictResolutionItem(
        line_number=1,
        product_id=101,
        action=ResolutionAction.ADJUST_QTY.value,
        adjusted_qty=8.0,
    )
    order_data = FieldSalesOrderSubmission(
        client_order_uuid="uuid-1234",
        customer_id=1,
        lines=[
            FieldSalesOrderLine(
                line_number=1,
                product_id=101,
                product_name="Fresh Whole Milk 1L",
                qty=8.0,
                unit_price=3.50,
                line_total=28.0,
            )
        ],
    )
    req = FieldSalesResolveConflictRequest(
        client_order_uuid="uuid-1234",
        order_data=order_data,
        resolutions=[resolution],
    )
    assert req.client_order_uuid == "uuid-1234"
    assert req.resolutions[0].action == "adjust_qty"
