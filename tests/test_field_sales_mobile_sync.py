from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from apps.api.main import app as main_app
from modules.sales.controllers import field_sales_controller
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
from packages.auth.deps import get_current_user, require_permission


# ============================================================================
# Test App Setup & Fixtures
# ============================================================================

@pytest.fixture
def authorized_user():
    return {
        "id": 42,
        "username": "sales_rep_john",
        "role": "Sales Rep",
        "permissions": ["FIELD_SALES_MOBILE", "SALES_VIEW", "SALES_CREATE"],
    }


@pytest.fixture
def unauthorized_user():
    return {
        "id": 99,
        "username": "warehouse_staff",
        "role": "Warehouse Staff",
        "permissions": ["INVENTORY_VIEW"],
    }


@pytest.fixture
def app_client(authorized_user):
    """TestClient with FIELD_SALES_MOBILE permission override."""
    test_app = FastAPI()
    test_app.dependency_overrides[get_current_user] = lambda: authorized_user
    test_app.include_router(field_sales_controller.router)
    return TestClient(test_app)


@pytest.fixture
def unauth_client():
    """TestClient without any user override (simulates unauthenticated calls)."""
    test_app = FastAPI()
    test_app.include_router(field_sales_controller.router)
    return TestClient(test_app)


@pytest.fixture
def forbidden_client(unauthorized_user):
    """TestClient with user lacking FIELD_SALES_MOBILE permission."""
    test_app = FastAPI()
    test_app.dependency_overrides[get_current_user] = lambda: unauthorized_user
    test_app.include_router(field_sales_controller.router)
    return TestClient(test_app)


# ============================================================================
# 1. Full Mobile Sync Integration Workflow
# ============================================================================

class TestFieldSalesMobileSyncWorkflow:
    """End-to-end integration tests simulating a sales rep going into the field,
    caching data, taking orders offline, syncing, handling conflicts, and resolving.
    """

    def test_full_field_sales_online_to_offline_workflow(self, app_client):
        # ---------------------------------------------------------------------
        # Step 1: Initial Full Catalog Sync (Online Morning Prep)
        # ---------------------------------------------------------------------
        mock_bundle = FieldSalesCatalogBundle(
            sync_timestamp=datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc),
            products=[
                CatalogProductItem(
                    id=101,
                    sku="MILK-001",
                    barcode="7890001",
                    name="Organic Whole Milk 1L",
                    category="Dairy",
                    base_price=3.50,
                    available_qty=100.0,
                    warehouse_stock={"1": 100.0},
                ),
                CatalogProductItem(
                    id=102,
                    sku="YOG-001",
                    barcode="7890002",
                    name="Greek Yogurt 500g",
                    category="Dairy",
                    base_price=4.50,
                    available_qty=40.0,
                    warehouse_stock={"1": 40.0},
                ),
            ],
            customers=[
                FieldSalesCustomerProfile(
                    id=501,
                    name="Grand Market",
                    group_name="Key Accounts",
                    credit_limit=10000.0,
                    balance=2000.0,
                    available_credit=8000.0,
                    recent_orders=[
                        CustomerOrderSummary(
                            id=8801,
                            order_number="SO-2026-08801",
                            grand_total=350.0,
                            status="Confirmed",
                            lines=[
                                CustomerOrderLineSummary(
                                    product_id=101,
                                    product_name="Organic Whole Milk 1L",
                                    qty=100.0,
                                    unit_price=3.50,
                                    line_total=350.0,
                                )
                            ],
                        )
                    ],
                )
            ],
            price_rules=[
                CustomerPriceRule(
                    id=1,
                    price_list_id=1,
                    product_id=101,
                    unit_price=3.20,
                    min_qty=50.0,
                )
            ],
            warehouses=[{"id": 1, "code": "WH-MAIN", "name": "Main DC"}],
            tax_rates=[{"id": 1, "name": "Standard VAT", "rate": 5.0, "is_default": True}],
            payment_terms=[{"id": 1, "name": "Net 30", "days": 30}],
            total_products=2,
            total_customers=1,
        )

        with patch.object(field_sales_controller._catalog_svc, "get_mobile_catalog", return_value=mock_bundle):
            resp = app_client.get("/api/sales/mobile/catalog?warehouse_id=1")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["total_products"] == 2
            assert data["total_customers"] == 1
            assert data["products"][0]["sku"] == "MILK-001"
            assert data["customers"][0]["name"] == "Grand Market"
            assert data["customers"][0]["available_credit"] == 8000.0

        # ---------------------------------------------------------------------
        # Step 2: Delta Catalog Sync (Midday Check)
        # ---------------------------------------------------------------------
        mock_delta_bundle = FieldSalesCatalogBundle(
            sync_timestamp=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
            delta_timestamp=datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc),
            products=[],
            customers=[],
            total_products=0,
            total_customers=0,
        )

        with patch.object(field_sales_controller._catalog_svc, "get_mobile_catalog", return_value=mock_delta_bundle) as mock_get_cat:
            resp = app_client.get("/api/sales/mobile/catalog?delta_timestamp=2026-08-23T08:00:00Z")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json()["total_products"] == 0
            mock_get_cat.assert_called_once_with(
                delta_timestamp="2026-08-23T08:00:00Z",
                warehouse_id=None,
                sales_rep_id=None,
            )

        # ---------------------------------------------------------------------
        # Step 3: Customer History Inspection (1-Tap Reorder)
        # ---------------------------------------------------------------------
        with patch.object(
            field_sales_controller._catalog_svc,
            "get_customer_history",
            return_value=mock_bundle.customers[0].recent_orders,
        ):
            resp = app_client.get("/api/sales/mobile/customers/501/history")
            assert resp.status_code == status.HTTP_200_OK
            history = resp.json()
            assert len(history) == 1
            assert history[0]["order_number"] == "SO-2026-08801"
            assert history[0]["lines"][0]["product_name"] == "Organic Whole Milk 1L"

        # ---------------------------------------------------------------------
        # Step 4: Pre-Sync Validation (Offline Rep Validates Captured Batch)
        # ---------------------------------------------------------------------
        valid_batch_req = {
            "orders": [
                {
                    "client_order_uuid": "offline-uuid-001",
                    "customer_id": 501,
                    "warehouse_id": 1,
                    "sales_rep_id": 42,
                    "lines": [
                        {
                            "line_number": 1,
                            "product_id": 101,
                            "product_name": "Organic Whole Milk 1L",
                            "qty": 20.0,
                            "unit_price": 3.50,
                            "line_total": 70.0,
                        }
                    ],
                }
            ]
        }

        mock_validation_resp = FieldSalesValidationResponse(
            valid=True,
            total_orders=1,
            conflicts_found=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="offline-uuid-001",
                    status="Valid",
                    is_duplicate=False,
                    message="Order is valid and ready to sync.",
                )
            ],
        )

        with patch.object(field_sales_controller._sync_svc, "validate_batch", return_value=mock_validation_resp):
            resp = app_client.post("/api/sales/mobile/validate", json=valid_batch_req)
            assert resp.status_code == status.HTTP_200_OK
            val_data = resp.json()
            assert val_data["valid"] is True
            assert val_data["conflicts_found"] == 0

        # ---------------------------------------------------------------------
        # Step 5: Batch Order Synchronization
        # ---------------------------------------------------------------------
        mock_sync_resp = FieldSalesBatchSyncResponse(
            success=True,
            synced_count=1,
            conflict_count=0,
            failed_count=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="offline-uuid-001",
                    server_order_id=5001,
                    order_number="FSO-20260823-5001",
                    status=SyncStatus.SYNCED.value,
                    is_duplicate=False,
                    subtotal=70.0,
                    tax=3.5,
                    grand_total=73.5,
                    message="Order synchronized successfully.",
                )
            ],
        )

        with patch.object(field_sales_controller._sync_svc, "sync_batch", return_value=mock_sync_resp):
            resp = app_client.post("/api/sales/mobile/sync", json=valid_batch_req)
            assert resp.status_code == status.HTTP_200_OK
            sync_data = resp.json()
            assert sync_data["success"] is True
            assert sync_data["synced_count"] == 1
            assert sync_data["results"][0]["server_order_id"] == 5001
            assert sync_data["results"][0]["status"] == "Synced"

        # ---------------------------------------------------------------------
        # Step 6: Idempotent Re-Sync (Network Glitch Repetition)
        # ---------------------------------------------------------------------
        mock_duplicate_resp = FieldSalesBatchSyncResponse(
            success=True,
            synced_count=0,
            conflict_count=0,
            failed_count=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="offline-uuid-001",
                    server_order_id=5001,
                    order_number="FSO-20260823-5001",
                    status="AlreadySynced",
                    is_duplicate=True,
                    subtotal=70.0,
                    tax=3.5,
                    grand_total=73.5,
                    message="Order was already synchronized.",
                )
            ],
        )

        with patch.object(field_sales_controller._sync_svc, "sync_batch", return_value=mock_duplicate_resp):
            resp = app_client.post("/api/sales/mobile/sync", json=valid_batch_req)
            assert resp.status_code == status.HTTP_200_OK
            re_data = resp.json()
            assert re_data["results"][0]["is_duplicate"] is True
            assert re_data["results"][0]["status"] == "AlreadySynced"
            assert re_data["results"][0]["server_order_id"] == 5001

    def test_stock_conflict_detection_and_resolution_flow(self, app_client):
        # ---------------------------------------------------------------------
        # Step 1: Rep submits order with item that depleted while offline
        # ---------------------------------------------------------------------
        conflict_batch_req = {
            "orders": [
                {
                    "client_order_uuid": "offline-conflict-uuid-002",
                    "customer_id": 501,
                    "warehouse_id": 1,
                    "lines": [
                        {
                            "line_number": 1,
                            "product_id": 102,
                            "product_name": "Greek Yogurt 500g",
                            "qty": 50.0,
                            "unit_price": 4.50,
                            "line_total": 225.0,
                        }
                    ],
                }
            ]
        }

        mock_conflict_resp = FieldSalesBatchSyncResponse(
            success=False,
            synced_count=0,
            conflict_count=1,
            failed_count=0,
            results=[
                OrderSyncResult(
                    client_order_uuid="offline-conflict-uuid-002",
                    status=SyncStatus.CONFLICT.value,
                    is_duplicate=False,
                    conflicts=[
                        LineConflictDetail(
                            line_number=1,
                            product_id=102,
                            product_name="Greek Yogurt 500g",
                            conflict_type=ConflictType.INSUFFICIENT_QTY.value,
                            requested_qty=50.0,
                            available_qty=40.0,
                            current_price=4.50,
                            message="Insufficient stock for 'Greek Yogurt 500g'. Requested 50.0, only 40.0 available.",
                            suggested_action=ResolutionAction.ADJUST_QTY.value,
                        )
                    ],
                )
            ],
        )

        with patch.object(field_sales_controller._sync_svc, "sync_batch", return_value=mock_conflict_resp):
            resp = app_client.post("/api/sales/mobile/sync", json=conflict_batch_req)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["success"] is False
            assert data["conflict_count"] == 1
            result = data["results"][0]
            assert result["status"] == "Conflict"
            assert result["conflicts"][0]["conflict_type"] == "INSUFFICIENT_QTY"
            assert result["conflicts"][0]["available_qty"] == 40.0

        # ---------------------------------------------------------------------
        # Step 2: Rep resolves conflict by adjusting quantity to available 40.0
        # ---------------------------------------------------------------------
        resolve_req = {
            "client_order_uuid": "offline-conflict-uuid-002",
            "order_data": conflict_batch_req["orders"][0],
            "resolutions": [
                {
                    "line_number": 1,
                    "product_id": 102,
                    "action": "adjust_qty",
                    "adjusted_qty": 40.0,
                }
            ],
        }

        mock_resolved_result = OrderSyncResult(
            client_order_uuid="offline-conflict-uuid-002",
            server_order_id=5002,
            order_number="FSO-20260823-5002",
            status=SyncStatus.SYNCED.value,
            is_duplicate=False,
            subtotal=180.0,
            tax=9.0,
            grand_total=189.0,
            message="Conflict resolved and order synchronized successfully.",
        )

        with patch.object(field_sales_controller._sync_svc, "resolve_and_sync", return_value=mock_resolved_result) as mock_res_sync:
            resp = app_client.post("/api/sales/mobile/resolve-conflict", json=resolve_req)
            assert resp.status_code == status.HTTP_200_OK
            res_data = resp.json()
            assert res_data["status"] == "Synced"
            assert res_data["server_order_id"] == 5002
            assert res_data["grand_total"] == 189.0


# ============================================================================
# 2. RBAC & Security Integration Tests
# ============================================================================

class TestFieldSalesSecurityAndPermissions:
    """Security tests verifying that only authorized sales reps can access mobile endpoints."""

    def test_unauthenticated_request_is_rejected(self, unauth_client):
        resp = unauth_client.get("/api/sales/mobile/catalog")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_forbidden_role_without_permission_is_rejected(self, forbidden_client):
        resp = forbidden_client.get("/api/sales/mobile/catalog")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_authorized_sales_rep_permitted(self, app_client):
        mock_bundle = FieldSalesCatalogBundle()
        with patch.object(field_sales_controller._catalog_svc, "get_mobile_catalog", return_value=mock_bundle):
            resp = app_client.get("/api/sales/mobile/catalog")
            assert resp.status_code == status.HTTP_200_OK


# ============================================================================
# 3. Validation & Error Handling Integration Tests
# ============================================================================

class TestFieldSalesValidationAndErrorHandling:
    """Integration tests for invalid payload rejection and 404/500 scenarios."""

    def test_sync_with_missing_lines_returns_422(self, app_client):
        invalid_req = {
            "orders": [
                {
                    "client_order_uuid": "uuid-no-lines",
                    "customer_id": 10,
                    "lines": [],  # Empty lines should fail validation
                }
            ]
        }
        resp = app_client.post("/api/sales/mobile/sync", json=invalid_req)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_sync_with_missing_client_uuid_returns_422(self, app_client):
        invalid_req = {
            "orders": [
                {
                    "customer_id": 10,
                    "lines": [
                        {
                            "line_number": 1,
                            "product_id": 1,
                            "product_name": "Item",
                            "qty": 1.0,
                            "unit_price": 10.0,
                        }
                    ],
                }
            ]
        }
        resp = app_client.post("/api/sales/mobile/sync", json=invalid_req)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_customer_with_no_history_returns_empty_list(self, app_client):
        with patch.object(field_sales_controller._catalog_svc, "get_customer_history", return_value=[]):
            resp = app_client.get("/api/sales/mobile/customers/999999/history")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json() == []

    def test_service_exception_returns_500(self, app_client):
        with patch.object(field_sales_controller._catalog_svc, "get_mobile_catalog", side_effect=RuntimeError("Database crashed")):
            resp = app_client.get("/api/sales/mobile/catalog")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to fetch mobile catalog bundle" in resp.json()["detail"]
