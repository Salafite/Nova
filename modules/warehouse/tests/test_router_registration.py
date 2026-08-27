"""
Tests for main application router registration, RBAC permissions, and tenant isolation
for Stock Transfers (T0108I), Stock Transfer Lines (T0111I), and Inter-Branch Replenishment controllers.
"""
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.auth.jwt import create_access_token
from modules.core.context import clear_current_tenant


@pytest.fixture(autouse=True)
def cleanup_tenant():
    clear_current_tenant()
    yield
    clear_current_tenant()


@pytest.fixture
def client():
    return TestClient(app)


def test_main_app_routes_registered():
    """Verify that all transfer and replenishment routes are exposed in the main FastAPI app."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # T0108I endpoints
    assert "/api/T0108I/" in paths
    assert "/api/T0108I/count" in paths
    assert "/api/T0108I/in-transit" in paths
    assert "/api/T0108I/{id}" in paths
    assert "/api/T0108I/{id}/detail" in paths
    assert "/api/T0108I/{id}/dispatch" in paths
    assert "/api/T0108I/{id}/receive" in paths
    assert "/api/T0108I/{id}/cancel" in paths
    assert "/api/T0108I/{id}/lines" in paths
    assert "/api/T0108I/{id}/lines/{line_id}" in paths

    # T0111I endpoints
    assert "/api/T0111I/" in paths
    assert "/api/T0111I/count" in paths
    assert "/api/T0111I/{id}" in paths

    # Replenishment endpoints
    assert "/api/inventory/replenishment/suggestions" in paths
    assert "/api/inventory/replenishment/generate-transfers" in paths
    assert "/api/inventory/replenishment/summary" in paths


def test_stock_transfers_unauthenticated_access_denied(client):
    """Unauthenticated requests to /api/T0108I endpoints should be rejected."""
    resp = client.get("/api/T0108I/")
    assert resp.status_code in (401, 403)

    resp = client.get("/api/T0108I/in-transit")
    assert resp.status_code in (401, 403)


def test_replenishment_unauthenticated_access_denied(client):
    """Unauthenticated requests to /api/inventory/replenishment endpoints should be rejected."""
    resp = client.get("/api/inventory/replenishment/suggestions")
    assert resp.status_code in (401, 403)

    resp = client.get("/api/inventory/replenishment/summary")
    assert resp.status_code in (401, 403)


def test_stock_transfers_authenticated_access_with_permissions(client):
    """Authenticated requests with WAREHOUSE_VIEW permission should succeed."""
    token = create_access_token(user_id=101, business_id=1)
    mock_user = {
        "id": 101,
        "username": "wh_mgr",
        "role": "Manager",
        "permissions": ["WAREHOUSE_VIEW", "INVENTORY_VIEW"],
        "business_id": 1,
    }

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user), \
         patch("modules.warehouse.controllers.T0108I.service.list", return_value=[]):
        resp = client.get("/api/T0108I/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []


def test_stock_transfers_insufficient_permissions_denied(client):
    """Authenticated requests without WAREHOUSE_VIEW permission should be rejected with 403."""
    token = create_access_token(user_id=102, business_id=1)
    mock_user = {
        "id": 102,
        "username": "limited_user",
        "role": "Sales Rep",
        "permissions": ["SALES_VIEW"],
        "business_id": 1,
    }

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user):
        resp = client.get("/api/T0108I/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


def test_replenishment_authenticated_access_with_permissions(client):
    """Authenticated requests with INVENTORY_VIEW permission should access replenishment summary."""
    token = create_access_token(user_id=103, business_id=1)
    mock_user = {
        "id": 103,
        "username": "inv_mgr",
        "role": "Manager",
        "permissions": ["INVENTORY_VIEW", "WAREHOUSE_VIEW"],
        "business_id": 1,
    }

    mock_summary = {
        "total_monitored_products": 50,
        "total_active_warehouses": 5,
        "total_stockout_items": 2,
        "total_reorder_deficit_items": 8,
        "total_critical_items": 2,
        "total_high_priority_items": 3,
        "in_transit_transfers_count": 4,
    }

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user), \
         patch("modules.inventory.controllers.replenishment_controller.service.get_stock_health_summary", return_value=mock_summary):
        resp = client.get("/api/inventory/replenishment/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_monitored_products"] == 50
        assert data["total_stockout_items"] == 2


def test_replenishment_insufficient_permissions_denied(client):
    """Authenticated requests without INVENTORY_VIEW permission should be rejected with 403."""
    token = create_access_token(user_id=104, business_id=1)
    mock_user = {
        "id": 104,
        "username": "hr_user",
        "role": "Employee",
        "permissions": ["HR_VIEW"],
        "business_id": 1,
    }

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user):
        resp = client.get("/api/inventory/replenishment/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
