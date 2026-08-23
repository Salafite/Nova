import os
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from modules.sales.models.field_sales import (
    CatalogProductItem,
    ConflictResolutionItem,
    ConflictType,
    CustomerOrderLineSummary,
    CustomerOrderSummary,
    CustomerPriceRule,
    FieldSalesBatchSyncRequest,
    FieldSalesBatchSyncResponse,
    FieldSalesCatalogBundle,
    FieldSalesCustomerProfile,
    FieldSalesOrderLine,
    FieldSalesOrderSubmission,
    FieldSalesResolveConflictRequest,
    FieldSalesValidationRequest,
    FieldSalesValidationResponse,
    LineConflictDetail,
    OrderSyncResult,
    ResolutionAction,
    SyncStatus,
)
from modules.sales.services.field_sales_catalog_service import FieldSalesCatalogService
from modules.sales.services.field_sales_sync_service import (
    FieldSalesSyncService,
    _get_utc_now,
    _to_float,
    _to_int,
)


# ============================================================================
# 1. Field Sales Catalog Delta & Export Tests
# ============================================================================

class TestFieldSalesCatalogDeltaExport:
    """Tests for mobile catalog bundling, delta timestamps, and customer history."""

    @pytest.fixture
    def mock_db_cursor(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_full_catalog_bundle_assembly(self):
        service = FieldSalesCatalogService(schema="Nova")
        mock_conn = MagicMock()

        products = [
            CatalogProductItem(
                id=1,
                sku="SKU-MILK-01",
                barcode="1111222233334",
                name="Fresh Whole Milk 1L",
                category="Dairy",
                base_price=3.50,
                available_qty=120.0,
                warehouse_stock={"1": 120.0},
            )
        ]
        customers = [
            FieldSalesCustomerProfile(
                id=10,
                name="Acme Grocery Store",
                group_name="Retail Key",
                credit_limit=5000.0,
                balance=1250.0,
                available_credit=3750.0,
                recent_orders=[
                    CustomerOrderSummary(
                        id=1001,
                        order_number="SO-2026-001",
                        grand_total=350.0,
                        status="Confirmed",
                        lines=[
                            CustomerOrderLineSummary(
                                product_id=1,
                                product_name="Fresh Whole Milk 1L",
                                qty=100.0,
                                unit_price=3.50,
                                line_total=350.0,
                            )
                        ],
                    )
                ],
            )
        ]
        price_rules = [
            CustomerPriceRule(
                id=1,
                price_list_id=1,
                product_id=1,
                unit_price=3.20,
                min_qty=50.0,
            )
        ]
        metadata = {
            "warehouses": [{"id": 1, "code": "WH-MAIN", "name": "Main Distribution Center"}],
            "tax_rates": [{"id": 1, "name": "Standard VAT", "rate": 5.0, "is_default": True}],
            "payment_terms": [{"id": 1, "name": "Net 30 Days", "days": 30}],
        }

        with patch.object(service, "get_products", return_value=products):
            with patch.object(service, "get_customers", return_value=customers):
                with patch.object(service, "get_price_rules", return_value=price_rules):
                    with patch.object(service, "get_metadata_lookups", return_value=metadata):
                        bundle = service.get_mobile_catalog(warehouse_id=1, sales_rep_id=42, conn=mock_conn)

                        assert isinstance(bundle, FieldSalesCatalogBundle)
                        assert bundle.total_products == 1
                        assert bundle.total_customers == 1
                        assert len(bundle.products) == 1
                        assert bundle.products[0].sku == "SKU-MILK-01"
                        assert bundle.products[0].available_qty == 120.0

                        assert len(bundle.customers) == 1
                        cust = bundle.customers[0]
                        assert cust.id == 10
                        assert cust.available_credit == 3750.0
                        assert len(cust.recent_orders) == 1
                        assert cust.recent_orders[0].order_number == "SO-2026-001"

                        assert len(bundle.price_rules) == 1
                        assert bundle.price_rules[0].unit_price == 3.20
                        assert len(bundle.warehouses) == 1
                        assert len(bundle.tax_rates) == 1
                        assert len(bundle.payment_terms) == 1

    def test_delta_catalog_export_with_timestamp_filter(self):
        service = FieldSalesCatalogService(schema="Nova")
        mock_conn = MagicMock()

        with patch.object(service, "get_products", return_value=[]):
            with patch.object(service, "get_customers", return_value=[]):
                with patch.object(service, "get_price_rules", return_value=[]):
                    with patch.object(service, "get_metadata_lookups", return_value={"warehouses": [], "tax_rates": [], "payment_terms": []}):
                        delta_time = "2026-08-22T00:00:00Z"
                        bundle = service.get_mobile_catalog(delta_timestamp=delta_time, conn=mock_conn)

                        assert isinstance(bundle, FieldSalesCatalogBundle)
                        assert bundle.total_products == 0
                        assert bundle.total_customers == 0
                        assert len(bundle.products) == 0
                        assert len(bundle.customers) == 0


# ============================================================================
# 2. Idempotency & Batch Offline Order Synchronization Tests
# ============================================================================

class TestFieldSalesSyncIdempotencyAndBatch:
    """Tests for idempotent order creation and atomic batch processing."""

    @pytest.fixture
    def service(self):
        return FieldSalesSyncService(schema="Nova")

    @pytest.fixture
    def mock_db(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_duplicate_order_uuid_returns_already_synced_without_writing(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        # DB returns existing record for client_order_uuid
        mock_cursor.fetchone.return_value = {
            "id": 905,
            "order_number": "FSO-20260823-0905",
            "customer_id": 10,
            "warehouse_id": 1,
            "subtotal": Decimal("250.00"),
            "tax": Decimal("12.50"),
            "grand_total": Decimal("262.50"),
            "status": "Pending",
            "sync_status": "Synced",
            "client_order_uuid": "e4b5d21a-4c3e-4b2a-89a1-000000000001",
        }

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000001",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Product A",
                    qty=10.0,
                    unit_price=25.0,
                    line_total=250.0,
                )
            ],
        )

        request = FieldSalesBatchSyncRequest(orders=[submission])
        response = service.sync_batch(request, conn=mock_conn)

        assert response.success is True
        assert response.synced_count == 0
        assert response.conflict_count == 0
        assert response.failed_count == 0
        assert len(response.results) == 1

        result = response.results[0]
        assert result.client_order_uuid == "e4b5d21a-4c3e-4b2a-89a1-000000000001"
        assert result.status == "AlreadySynced"
        assert result.is_duplicate is True
        assert result.server_order_id == 905
        assert result.order_number == "FSO-20260823-0905"
        assert result.grand_total == 262.50

    def test_successful_offline_order_creation_with_full_audit(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        # Sequence of cursor queries:
        # 1. find_order_by_uuid -> None
        # 2. check_order_conflicts:
        #    - customer lookup -> customer active, credit limit 10000, balance 1000
        #    - product lookup line 1 -> product 1 active, price 10
        #    - stock lookup line 1 -> qty 50
        # 3. sync_single_order_transaction:
        #    - tax rate lookup -> rate 5.0
        #    - order number taken check -> False
        #    - insert t0012 -> returning id=1050
        #    - insert t0013 line 1
        #    - stock select for update -> current qty 50
        #    - stock update t0009
        #    - insert t0064 movement
        #    - update t0010 customer balance
        mock_cursor.fetchone.side_effect = [
            None,  # find_order_by_uuid
            {"id": 10, "name": "Key Supermarket", "is_active": True, "credit_limit": Decimal("10000.00"), "balance": Decimal("1000.00")},  # customer
            {"id": 1, "name": "Fresh Juice", "sku": "SKU-1", "price": Decimal("10.00"), "category": "Beverages", "is_active": True},  # product
            {"qty": Decimal("50.0")},  # stock
            {"rate": Decimal("5.0")},  # tax rate
            None,  # order number taken check
            {"id": 1050},  # insert t0012 returning id
            {"id": 99, "qty": Decimal("50.0")},  # stock select for update
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000002",
            order_number="FSO-20260823-1050",
            customer_id=10,
            warehouse_id=1,
            sales_rep_id=42,
            tax_rate_id=1,
            offline_created_at=datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc),
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Fresh Juice",
                    sku="SKU-1",
                    qty=5.0,
                    unit_price=10.0,
                    line_total=50.0,
                )
            ],
            notes="Deliver to back dock",
        )

        request = FieldSalesBatchSyncRequest(orders=[submission])
        response = service.sync_batch(request, conn=mock_conn)

        assert response.success is True
        assert response.synced_count == 1
        assert response.conflict_count == 0
        assert response.failed_count == 0
        assert len(response.results) == 1

        result = response.results[0]
        assert result.status == SyncStatus.SYNCED.value
        assert result.server_order_id == 1050
        assert result.is_duplicate is False
        assert result.subtotal == 50.0
        assert result.tax == 2.5
        assert result.grand_total == 52.5
        assert mock_conn.commit.called

    def test_batch_sync_mixed_outcomes(self, service, mock_db):
        """Verify processing a batch containing 1 valid order, 1 duplicate, and 1 conflict."""
        mock_conn, mock_cursor = mock_db

        order1_valid = FieldSalesOrderSubmission(
            client_order_uuid="uuid-valid-1",
            customer_id=1,
            warehouse_id=1,
            lines=[FieldSalesOrderLine(line_number=1, product_id=1, product_name="Item 1", qty=2.0, unit_price=10.0, line_total=20.0)],
        )
        order2_duplicate = FieldSalesOrderSubmission(
            client_order_uuid="uuid-duplicate-2",
            customer_id=1,
            warehouse_id=1,
            lines=[FieldSalesOrderLine(line_number=1, product_id=1, product_name="Item 1", qty=2.0, unit_price=10.0, line_total=20.0)],
        )
        order3_conflict = FieldSalesOrderSubmission(
            client_order_uuid="uuid-conflict-3",
            customer_id=1,
            warehouse_id=1,
            lines=[FieldSalesOrderLine(line_number=1, product_id=2, product_name="Item 2", qty=5.0, unit_price=10.0, line_total=50.0)],
        )

        # Mock the internal helper calls for isolation
        with patch.object(service, "_sync_single_order_transaction") as mock_sync_single:
            mock_sync_single.side_effect = [
                OrderSyncResult(client_order_uuid="uuid-valid-1", server_order_id=101, order_number="FSO-001", status=SyncStatus.SYNCED.value, is_duplicate=False, grand_total=20.0),
                OrderSyncResult(client_order_uuid="uuid-duplicate-2", server_order_id=100, order_number="FSO-000", status="AlreadySynced", is_duplicate=True, grand_total=20.0),
                OrderSyncResult(client_order_uuid="uuid-conflict-3", status=SyncStatus.CONFLICT.value, is_duplicate=False, conflicts=[
                    LineConflictDetail(line_number=1, product_id=2, product_name="Item 2", conflict_type=ConflictType.OUT_OF_STOCK.value, requested_qty=5.0, available_qty=0.0, message="Out of stock")
                ]),
            ]

            request = FieldSalesBatchSyncRequest(orders=[order1_valid, order2_duplicate, order3_conflict])
            response = service.sync_batch(request, conn=mock_conn)

            # success is False because 1 order had conflicts
            assert response.success is False
            assert response.synced_count == 1
            assert response.conflict_count == 1
            assert response.failed_count == 0
            assert len(response.results) == 3
            assert response.results[0].status == SyncStatus.SYNCED.value
            assert response.results[1].status == "AlreadySynced"
            assert response.results[2].status == SyncStatus.CONFLICT.value

    def test_sync_database_error_handles_rollback_cleanly(self, service, mock_db):
        """Verify DB exception inside transaction triggers rollback and returns FAILED status."""
        mock_conn, mock_cursor = mock_db

        # 1. find_order_by_uuid -> None
        # 2. check_order_conflicts -> active customer, active product, in stock
        # 3. tax rate lookup -> throws psycopg2 exception
        mock_cursor.fetchone.side_effect = [
            None,
            {"id": 1, "name": "Customer 1", "is_active": True, "credit_limit": Decimal("1000"), "balance": Decimal("0")},
            {"id": 10, "name": "Product 10", "sku": "SKU-10", "price": Decimal("15.00"), "is_active": True},
            {"qty": Decimal("20.0")},
            RuntimeError("Database connection lost during insert"),
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="uuid-error-rollback",
            customer_id=1,
            warehouse_id=1,
            tax_rate_id=1,
            lines=[FieldSalesOrderLine(line_number=1, product_id=10, product_name="Product 10", qty=1.0, unit_price=15.0, line_total=15.0)],
        )

        response = service.sync_batch(FieldSalesBatchSyncRequest(orders=[submission]), conn=mock_conn)

        assert response.failed_count == 1
        assert len(response.results) == 1
        res = response.results[0]
        assert res.status == SyncStatus.FAILED.value
        assert "Database connection lost" in (res.message or "")
        assert mock_conn.rollback.called


# ============================================================================
# 3. Stock Conflict Detection & Resolution Tests
# ============================================================================

class TestFieldSalesStockConflicts:
    """Tests for conflict detection (depleted stock, insufficient qty, price mismatch, credit limit)."""

    @pytest.fixture
    def service(self):
        return FieldSalesSyncService(schema="Nova")

    @pytest.fixture
    def mock_db(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_out_of_stock_conflict_triggers_substitute_recommendation(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        mock_cursor.fetchone.side_effect = [
            # Customer
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("500.00")},
            # Product
            {"id": 1, "sku": "SKU-OUT", "name": "Vanilla Yogurt", "base_price": Decimal("5.00"), "price": Decimal("5.00"), "is_active": True, "category": "Dairy"},
            # Stock: 0.0 available
            {"qty": Decimal("0.0")},
        ]
        # Substitute query
        mock_cursor.fetchall.return_value = [
            {"id": 2, "sku": "SKU-SUB", "name": "Greek Yogurt", "price": Decimal("5.50"), "available_qty": Decimal("30.0")}
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000003",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Vanilla Yogurt",
                    qty=10.0,
                    unit_price=5.0,
                    line_total=50.0,
                )
            ],
        )

        conflicts = service.check_order_conflicts(submission, conn=mock_conn)

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.conflict_type == ConflictType.OUT_OF_STOCK.value
        assert conflict.requested_qty == 10.0
        assert conflict.available_qty == 0.0
        assert conflict.suggested_action == ResolutionAction.SUBSTITUTE.value
        assert len(conflict.suggested_substitutes) == 1
        assert conflict.suggested_substitutes[0]["name"] == "Greek Yogurt"

    def test_insufficient_qty_conflict_suggests_available_qty(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        mock_cursor.fetchone.side_effect = [
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("500.00")},
            {"id": 1, "sku": "SKU-LOW", "name": "Organic Milk", "price": Decimal("4.00"), "is_active": True, "category": "Dairy"},
            {"qty": Decimal("4.0")},  # Only 4 in stock, requested 10
        ]
        mock_cursor.fetchall.return_value = []

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000004",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Organic Milk",
                    qty=10.0,
                    unit_price=4.0,
                    line_total=40.0,
                )
            ],
        )

        conflicts = service.check_order_conflicts(submission, conn=mock_conn)

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.conflict_type == ConflictType.INSUFFICIENT_QTY.value
        assert conflict.requested_qty == 10.0
        assert conflict.available_qty == 4.0
        assert conflict.suggested_action == ResolutionAction.ADJUST_QTY.value

    def test_credit_limit_overflow_conflict(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        mock_cursor.fetchone.side_effect = [
            # Customer credit limit 1000, balance 950 -> available credit = 50
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("1000.00"), "balance": Decimal("950.00")},
            {"id": 1, "sku": "SKU-1", "name": "Bulk Coffee", "price": Decimal("100.00"), "is_active": True, "category": "Beverages"},
            {"qty": Decimal("20.0")},  # Stock is enough
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000005",
            customer_id=10,
            warehouse_id=1,
            grand_total=200.0,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Bulk Coffee",
                    qty=2.0,
                    unit_price=100.0,
                    line_total=200.0,
                )
            ],
        )

        conflicts = service.check_order_conflicts(submission, conn=mock_conn)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.CREDIT_LIMIT_EXCEEDED.value

    def test_resolve_conflict_and_sync_flow(self, service, mock_db):
        """Verify resolving conflicts with adjust_qty and substitute actions successfully creates the order."""
        mock_conn, mock_cursor = mock_db

        # resolve_and_sync queries:
        # 1. Substitute product lookup in t0003: name, sku, price
        # 2. _sync_single_order_transaction:
        #    - find_order_by_uuid -> None
        #    - check_order_conflicts:
        #      - customer lookup
        #      - product 1 lookup
        #      - product 1 stock
        #      - product 2 lookup
        #      - product 2 stock
        #    - tax rate lookup (t0010 default) -> None
        #    - order number taken check -> False
        #    - insert t0012 returning id=1099
        #    - insert t0013 lines
        #    - stock select for update line 1
        #    - stock update t0009 line 1
        #    - insert t0064 line 1
        #    - stock select for update line 2
        #    - stock update t0009 line 2
        #    - insert t0064 line 2
        #    - update t0010 customer balance
        mock_cursor.fetchone.side_effect = [
            # 1. Substitute product lookup
            {"name": "Greek Yogurt", "sku": "SKU-SUB", "price": Decimal("5.50")},
            # 2. find_order_by_uuid
            None,
            # 3. Customer check
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("500.00")},
            # 4. Product 1 check
            {"id": 1, "sku": "SKU-1", "name": "Organic Milk", "price": Decimal("4.00"), "is_active": True, "category": "Dairy"},
            # 5. Product 1 stock (enough for adjusted qty 4)
            {"qty": Decimal("4.0")},
            # 6. Product 2 check (substitute product)
            {"id": 2, "sku": "SKU-SUB", "name": "Greek Yogurt", "price": Decimal("5.50"), "is_active": True, "category": "Dairy"},
            # 7. Product 2 stock (enough for substitute qty 5)
            {"qty": Decimal("20.0")},
            # 8. Tax rate lookup
            None,
            # 9. Order number taken check
            None,
            # 10. Insert t0012 returning id
            {"id": 1099},
            # 11. Stock select for update line 1
            {"id": 101, "qty": Decimal("4.0")},
            # 12. Stock select for update line 2
            {"id": 102, "qty": Decimal("20.0")},
        ]

        original_submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000006",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Organic Milk",
                    qty=10.0,
                    unit_price=4.0,
                    line_total=40.0,
                ),
                FieldSalesOrderLine(
                    line_number=2,
                    product_id=3,
                    product_name="Vanilla Yogurt",
                    qty=5.0,
                    unit_price=5.0,
                    line_total=25.0,
                ),
            ],
        )

        resolutions = [
            ConflictResolutionItem(
                line_number=1,
                product_id=1,
                action=ResolutionAction.ADJUST_QTY.value,
                adjusted_qty=4.0,
            ),
            ConflictResolutionItem(
                line_number=2,
                product_id=3,
                action=ResolutionAction.SUBSTITUTE.value,
                substitute_product_id=2,
                substitute_product_name="Greek Yogurt",
                adjusted_qty=5.0,
            ),
        ]

        req = FieldSalesResolveConflictRequest(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000006",
            order_data=original_submission,
            resolutions=resolutions,
        )

        result = service.resolve_and_sync(req, conn=mock_conn)

        assert result.status == SyncStatus.SYNCED.value
        assert result.server_order_id == 1099
        assert result.is_duplicate is False
        # subtotal: 4 * 4.0 (16.0) + 5 * 5.5 (27.5) = 43.5
        assert result.subtotal == 43.5
        assert result.grand_total == 43.5

    def test_inactive_customer_conflict(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        mock_cursor.fetchone.side_effect = [
            {"id": 99, "name": "Closed Supermarket", "is_active": False, "credit_limit": Decimal("5000.00"), "balance": Decimal("0.00")},
            {"id": 1, "sku": "SKU-1", "name": "Item", "price": Decimal("10.00"), "is_active": True, "category": "General"},
            {"qty": Decimal("50.0")},
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="uuid-inactive-cust",
            customer_id=99,
            warehouse_id=1,
            lines=[FieldSalesOrderLine(line_number=1, product_id=1, product_name="Item", qty=1.0, unit_price=10.0, line_total=10.0)],
        )

        conflicts = service.check_order_conflicts(submission, conn=mock_conn)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.CUSTOMER_INACTIVE.value
        assert "inactive" in conflicts[0].message.lower()

    def test_price_mismatch_conflict(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        mock_cursor.fetchone.side_effect = [
            # Customer
            {"id": 10, "is_active": True, "name": "Active Customer", "credit_limit": Decimal("5000.00"), "balance": Decimal("0.00")},
            # Product
            {"id": 1, "sku": "SKU-1", "name": "Special Tea", "price": Decimal("20.00"), "is_active": True, "category": "Beverages"},
            # Stock: enough
            {"qty": Decimal("100.0")},
            # Price list rule check in t0084: contracted price is 15.00, submitted was 20.00
            {"unit_price": Decimal("15.00")},
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="uuid-price-mismatch",
            customer_id=10,
            warehouse_id=1,
            price_list_id=3,
            lines=[FieldSalesOrderLine(line_number=1, product_id=1, product_name="Special Tea", qty=2.0, unit_price=20.0, line_total=40.0)],
        )

        conflicts = service.check_order_conflicts(submission, conn=mock_conn)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.PRICE_MISMATCH.value
        assert conflicts[0].requested_price == 20.0
        assert conflicts[0].current_price == 15.0
        assert conflicts[0].suggested_action == ResolutionAction.ACCEPT_PRICE.value

    def test_resolve_and_sync_with_remove_item_and_accept_price(self, service, mock_db):
        mock_conn, mock_cursor = mock_db

        # 1. find_order_by_uuid -> None
        # 2. Customer check
        # 3. Product 2 check
        # 4. Product 2 stock (enough)
        # 5. Tax rate lookup
        # 6. Order number taken check
        # 7. Insert t0012 returning id
        # 8. Stock select for update
        mock_cursor.fetchone.side_effect = [
            None,
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("0.00")},
            {"id": 2, "sku": "SKU-2", "name": "Item 2", "price": Decimal("15.00"), "is_active": True, "category": "General"},
            {"qty": Decimal("50.0")},
            None,
            None,
            {"id": 1200},
            {"id": 88, "qty": Decimal("50.0")},
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="uuid-resolve-remove-accept",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(line_number=1, product_id=1, product_name="Item 1 (dropped)", qty=5.0, unit_price=10.0, line_total=50.0),
                FieldSalesOrderLine(line_number=2, product_id=2, product_name="Item 2 (accepted price)", qty=2.0, unit_price=20.0, line_total=40.0),
            ],
        )

        resolutions = [
            ConflictResolutionItem(line_number=1, product_id=1, action=ResolutionAction.REMOVE_ITEM.value),
            ConflictResolutionItem(line_number=2, product_id=2, action=ResolutionAction.ACCEPT_PRICE.value, accepted_price=15.0),
        ]

        req = FieldSalesResolveConflictRequest(
            client_order_uuid="uuid-resolve-remove-accept",
            order_data=submission,
            resolutions=resolutions,
        )

        result = service.resolve_and_sync(req, conn=mock_conn)
        assert result.status == SyncStatus.SYNCED.value
        assert result.server_order_id == 1200
        # Line 1 was removed, Line 2 with accepted price 15.0 * 2 = 30.0
        assert result.grand_total == 30.0


# ============================================================================
# 4. Dry-Run Pre-Sync Validation Tests
# ============================================================================

class TestFieldSalesPreSyncValidation:
    """Tests for pre-sync dry-run conflict check."""

    def test_dry_run_validation_identifies_conflicts_without_writing(self):
        service = FieldSalesSyncService(schema="Nova")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            None,  # find_order_by_uuid -> not found
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("500.00")},
            {"id": 1, "sku": "SKU-OUT", "name": "Vanilla Yogurt", "price": Decimal("5.00"), "is_active": True, "category": "Dairy"},
            {"qty": Decimal("0.0")},  # Out of stock
        ]
        mock_cursor.fetchall.return_value = []

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000007",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Vanilla Yogurt",
                    qty=10.0,
                    unit_price=5.0,
                    line_total=50.0,
                )
            ],
        )

        validation_req = FieldSalesValidationRequest(orders=[submission])
        val_response = service.validate_batch(validation_req, conn=mock_conn)

        assert isinstance(val_response, FieldSalesValidationResponse)
        assert val_response.valid is False
        assert val_response.total_orders == 1
        assert val_response.conflicts_found == 1
        assert len(val_response.results) == 1
        res = val_response.results[0]
        assert res.status == SyncStatus.CONFLICT.value
        assert len(res.conflicts) == 1
        assert res.conflicts[0].conflict_type == ConflictType.OUT_OF_STOCK.value

    def test_dry_run_validation_all_valid(self):
        service = FieldSalesSyncService(schema="Nova")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            None,  # find_order_by_uuid -> not found
            {"id": 10, "is_active": True, "name": "Key Supermarket", "credit_limit": Decimal("5000.00"), "balance": Decimal("500.00")},
            {"id": 1, "sku": "SKU-OK", "name": "Fresh Milk", "price": Decimal("4.00"), "is_active": True, "category": "Dairy"},
            {"qty": Decimal("50.0")},  # In stock
        ]

        submission = FieldSalesOrderSubmission(
            client_order_uuid="e4b5d21a-4c3e-4b2a-89a1-000000000008",
            customer_id=10,
            warehouse_id=1,
            lines=[
                FieldSalesOrderLine(
                    line_number=1,
                    product_id=1,
                    product_name="Fresh Milk",
                    qty=5.0,
                    unit_price=4.0,
                    line_total=20.0,
                )
            ],
        )

        validation_req = FieldSalesValidationRequest(orders=[submission])
        val_response = service.validate_batch(validation_req, conn=mock_conn)

        assert val_response.valid is True
        assert val_response.conflicts_found == 0
        assert len(val_response.results) == 1
        assert val_response.results[0].status == "Valid"
