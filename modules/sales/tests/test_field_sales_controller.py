from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from modules.sales.controllers import field_sales_controller
from modules.sales.models.field_sales import (
    CatalogProductItem,
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
)
from packages.auth.deps import get_current_user


app = FastAPI()
app.dependency_overrides[get_current_user] = lambda: {
    "id": 42,
    "username": "salesrep1",
    "role": "Sales Rep",
    "permissions": ["FIELD_SALES_MOBILE"],
}
app.include_router(field_sales_controller.router)
client = TestClient(app)


# ---------------------------------------------------------------------------
# Mock Fixtures
# ---------------------------------------------------------------------------

MOCK_CATALOG_BUNDLE = FieldSalesCatalogBundle(
    sync_timestamp=datetime.now(timezone.utc),
    products=[
        CatalogProductItem(
            id=1,
            sku="SKU-001",
            barcode="1234567890123",
            name="Organic Whole Milk",
            category="Dairy",
            base_price=4.99,
            available_qty=150.0,
            warehouse_stock={"1": 100.0, "2": 50.0},
        )
    ],
    customers=[
        FieldSalesCustomerProfile(
            id=10,
            name="Supermart Downtown",
            group_name="Key Accounts",
            credit_limit=5000.0,
            balance=1200.0,
            available_credit=3800.0,
            recent_orders=[
                CustomerOrderSummary(
                    id=501,
                    order_number="SO-2026-0001",
                    grand_total=350.0,
                    status="Confirmed",
                    item_count=1,
                    lines=[
                        CustomerOrderLineSummary(
                            product_id=1,
                            product_name="Organic Whole Milk",
                            qty=70.0,
                            unit_price=4.99,
                            line_total=349.30,
                        )
                    ],
                )
            ],
        )
    ],
    price_rules=[
        CustomerPriceRule(
            id=1,
            price_list_id=2,
            product_id=1,
            unit_price=4.50,
            min_qty=10.0,
        )
    ],
    warehouses=[{"id": 1, "name": "Main Distribution Center"}],
    tax_rates=[{"id": 1, "name": "Standard VAT", "rate": 5.0}],
    payment_terms=[{"id": 1, "name": "Net 30", "due_days": 30}],
    total_products=1,
    total_customers=1,
)

MOCK_ORDER_SUBMISSION = FieldSalesOrderSubmission(
    client_order_uuid="uuid-rep1-1001",
    customer_id=10,
    warehouse_id=1,
    subtotal=90.0,
    tax=4.5,
    grand_total=94.5,
    lines=[
        FieldSalesOrderLine(
            line_number=1,
            product_id=1,
            product_name="Organic Whole Milk",
            sku="SKU-001",
            qty=20.0,
            unit_price=4.50,
            line_total=90.0,
        )
    ],
)


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestFieldSalesController:
    """Test suite for Field Sales Mobile REST API endpoints."""

    def test_get_mobile_catalog_endpoint(self):
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_mobile_catalog",
            return_value=MOCK_CATALOG_BUNDLE,
        ) as mock_get_bundle:
            resp = client.get("/api/sales/mobile/catalog?warehouse_id=1&sales_rep_id=42")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert "products" in data
            assert len(data["products"]) == 1
            assert data["products"][0]["sku"] == "SKU-001"
            assert data["products"][0]["barcode"] == "1234567890123"

            assert "customers" in data
            assert len(data["customers"]) == 1
            assert data["customers"][0]["name"] == "Supermart Downtown"
            assert data["customers"][0]["available_credit"] == 3800.0
            assert len(data["customers"][0]["recent_orders"]) == 1

            assert "price_rules" in data
            assert len(data["price_rules"]) == 1
            assert data["price_rules"][0]["unit_price"] == 4.50

            mock_get_bundle.assert_called_once_with(
                delta_timestamp=None,
                warehouse_id=1,
                sales_rep_id=42,
            )

    def test_get_mobile_catalog_with_delta_timestamp(self):
        delta_str = "2026-08-20T12:00:00Z"
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_mobile_catalog",
            return_value=MOCK_CATALOG_BUNDLE,
        ) as mock_get_bundle:
            resp = client.get(f"/api/sales/mobile/catalog?delta_timestamp={delta_str}")
            assert resp.status_code == status.HTTP_200_OK
            mock_get_bundle.assert_called_once_with(
                delta_timestamp=delta_str,
                warehouse_id=None,
                sales_rep_id=None,
            )

    def test_get_mobile_catalog_error_handling(self):
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_mobile_catalog",
            side_effect=RuntimeError("Database connection lost"),
        ):
            resp = client.get("/api/sales/mobile/catalog")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to fetch mobile catalog bundle" in resp.json()["detail"]

    def test_get_mobile_customers_endpoint(self):
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_customers",
            return_value=MOCK_CATALOG_BUNDLE.customers,
        ) as mock_get_customers:
            resp = client.get("/api/sales/mobile/customers?sales_rep_id=42&include_recent_orders=true")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == 10
            assert data[0]["name"] == "Supermart Downtown"
            assert data[0]["credit_limit"] == 5000.0

            mock_get_customers.assert_called_once_with(
                delta_timestamp=None,
                sales_rep_id=42,
                include_recent_orders=True,
            )

    def test_get_mobile_customers_error_handling(self):
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_customers",
            side_effect=Exception("Database failure"),
        ):
            resp = client.get("/api/sales/mobile/customers")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to fetch customer profiles" in resp.json()["detail"]

    def test_get_customer_history_endpoint(self):
        mock_history = MOCK_CATALOG_BUNDLE.customers[0].recent_orders
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_customer_history",
            return_value=mock_history,
        ) as mock_get_history:
            resp = client.get("/api/sales/mobile/customers/10/history?limit=5")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == 501
            assert data[0]["order_number"] == "SO-2026-0001"
            assert data[0]["grand_total"] == 350.0
            assert len(data[0]["lines"]) == 1

            mock_get_history.assert_called_once_with(customer_id=10, limit=5)

    def test_get_customer_history_error_handling(self):
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_customer_history",
            side_effect=Exception("Timeout reading orders"),
        ):
            resp = client.get("/api/sales/mobile/customers/10/history")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to fetch customer order history" in resp.json()["detail"]

    def test_sync_offline_orders_success(self):
        mock_sync_response = FieldSalesBatchSyncResponse(
            success=True,
            synced_count=1,
            conflict_count=0,
            failed_count=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="uuid-rep1-1001",
                    server_order_id=201,
                    order_number="SO-2026-0099",
                    status="Synced",
                    subtotal=90.0,
                    tax=4.5,
                    grand_total=94.5,
                    message="Order synchronized successfully.",
                )
            ],
            message="Processed 1 orders: 1 synced, 0 conflicts, 0 failed",
        )

        payload = {
            "orders": [MOCK_ORDER_SUBMISSION.model_dump(mode="json")],
            "device_id": "tablet-android-01",
        }

        with patch.object(
            field_sales_controller._sync_svc,
            "sync_batch",
            return_value=mock_sync_response,
        ) as mock_sync_batch:
            resp = client.post("/api/sales/mobile/sync", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert data["success"] is True
            assert data["synced_count"] == 1
            assert data["conflict_count"] == 0
            assert len(data["results"]) == 1
            assert data["results"][0]["client_order_uuid"] == "uuid-rep1-1001"
            assert data["results"][0]["status"] == "Synced"
            assert data["results"][0]["server_order_id"] == 201

            mock_sync_batch.assert_called_once()
            called_req = mock_sync_batch.call_args[0][0]
            # Verify sales_rep_id was automatically populated with authenticated user id (42)
            assert called_req.orders[0].sales_rep_id == 42

    def test_sync_offline_orders_with_conflicts(self):
        mock_sync_response = FieldSalesBatchSyncResponse(
            success=False,
            synced_count=0,
            conflict_count=1,
            failed_count=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="uuid-rep1-1001",
                    status="Conflict",
                    conflicts=[
                        LineConflictDetail(
                            line_number=1,
                            product_id=1,
                            product_name="Organic Whole Milk",
                            conflict_type="INSUFFICIENT_QTY",
                            requested_qty=20.0,
                            available_qty=10.0,
                            message="Insufficient stock for 'Organic Whole Milk'. Requested 20.0, only 10.0 available.",
                            suggested_action="adjust_qty",
                        )
                    ],
                    message="Detected 1 stock or pricing conflict(s). Resolution required.",
                )
            ],
            message="Processed 1 orders: 0 synced, 1 conflicts, 0 failed",
        )

        payload = {
            "orders": [MOCK_ORDER_SUBMISSION.model_dump(mode="json")],
        }

        with patch.object(
            field_sales_controller._sync_svc,
            "sync_batch",
            return_value=mock_sync_response,
        ):
            resp = client.post("/api/sales/mobile/sync", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert data["success"] is False
            assert data["conflict_count"] == 1
            assert data["results"][0]["status"] == "Conflict"
            assert len(data["results"][0]["conflicts"]) == 1
            assert data["results"][0]["conflicts"][0]["conflict_type"] == "INSUFFICIENT_QTY"

    def test_sync_offline_orders_error_handling(self):
        payload = {
            "orders": [MOCK_ORDER_SUBMISSION.model_dump(mode="json")],
        }
        with patch.object(
            field_sales_controller._sync_svc,
            "sync_batch",
            side_effect=Exception("Transaction commit error"),
        ):
            resp = client.post("/api/sales/mobile/sync", json=payload)
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to synchronize offline orders" in resp.json()["detail"]

    def test_validate_offline_orders_endpoint(self):
        mock_validation_response = FieldSalesValidationResponse(
            valid=True,
            total_orders=1,
            conflicts_found=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="uuid-rep1-1001",
                    status="Valid",
                    message="Order is valid and ready to sync.",
                )
            ],
        )

        payload = {
            "orders": [MOCK_ORDER_SUBMISSION.model_dump(mode="json")],
        }

        with patch.object(
            field_sales_controller._sync_svc,
            "validate_batch",
            return_value=mock_validation_response,
        ) as mock_validate:
            resp = client.post("/api/sales/mobile/validate", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert data["valid"] is True
            assert data["total_orders"] == 1
            assert data["conflicts_found"] == 0
            assert len(data["results"]) == 1
            assert data["results"][0]["status"] == "Valid"

            mock_validate.assert_called_once()

    def test_validate_offline_orders_error_handling(self):
        payload = {
            "orders": [MOCK_ORDER_SUBMISSION.model_dump(mode="json")],
        }
        with patch.object(
            field_sales_controller._sync_svc,
            "validate_batch",
            side_effect=Exception("Inventory lookup failed"),
        ):
            resp = client.post("/api/sales/mobile/validate", json=payload)
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to validate offline orders" in resp.json()["detail"]

    def test_resolve_conflict_and_sync_endpoint(self):
        mock_sync_result = OrderSyncResult(
            client_order_uuid="uuid-rep1-1001",
            server_order_id=202,
            order_number="SO-2026-0100",
            status="Synced",
            subtotal=45.0,
            tax=2.25,
            grand_total=47.25,
            message="Order synchronized successfully.",
        )

        payload = {
            "client_order_uuid": "uuid-rep1-1001",
            "order_data": MOCK_ORDER_SUBMISSION.model_dump(mode="json"),
            "resolutions": [
                {
                    "line_number": 1,
                    "product_id": 1,
                    "action": "adjust_qty",
                    "adjusted_qty": 10.0,
                }
            ],
        }

        with patch.object(
            field_sales_controller._sync_svc,
            "resolve_and_sync",
            return_value=mock_sync_result,
        ) as mock_resolve:
            resp = client.post("/api/sales/mobile/resolve-conflict", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()

            assert data["status"] == "Synced"
            assert data["server_order_id"] == 202
            assert data["order_number"] == "SO-2026-0100"

            mock_resolve.assert_called_once()

    def test_resolve_conflict_alias_endpoint(self):
        mock_sync_result = OrderSyncResult(
            client_order_uuid="uuid-rep1-1001",
            server_order_id=203,
            order_number="SO-2026-0101",
            status="Synced",
            message="Order synchronized successfully.",
        )

        payload = {
            "client_order_uuid": "uuid-rep1-1001",
            "order_data": MOCK_ORDER_SUBMISSION.model_dump(mode="json"),
            "resolutions": [],
        }

        with patch.object(
            field_sales_controller._sync_svc,
            "resolve_and_sync",
            return_value=mock_sync_result,
        ):
            resp = client.post("/api/sales/mobile/resolve", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["server_order_id"] == 203

    def test_resolve_conflict_error_handling(self):
        payload = {
            "client_order_uuid": "uuid-rep1-1001",
            "order_data": MOCK_ORDER_SUBMISSION.model_dump(mode="json"),
            "resolutions": [],
        }
        with patch.object(
            field_sales_controller._sync_svc,
            "resolve_and_sync",
            side_effect=Exception("Database lock conflict"),
        ):
            resp = client.post("/api/sales/mobile/resolve-conflict", json=payload)
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to resolve order conflict" in resp.json()["detail"]
