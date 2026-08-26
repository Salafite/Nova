"""
Nova ERP — Replenishment REST Controller Unit & API Tests
Tests endpoints:
- GET /api/inventory/replenishment/suggestions
- POST /api/inventory/replenishment/generate-transfers
- GET /api/inventory/replenishment/summary
"""
import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from modules.inventory.controllers.replenishment_controller import router, service
from modules.core.context import get_current_tenant, set_current_tenant
from packages.auth.deps import get_current_user, require_permission


@pytest.fixture
def api_client():
    app = FastAPI()
    # Override auth dependencies
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 10,
        "username": "inventory_mgr",
        "role": "Inventory Manager",
        "permissions": ["*"],
        "business_id": 1,
    }
    # Override permission check
    app.dependency_overrides[require_permission("INVENTORY_VIEW")] = lambda: True

    app.include_router(router)
    return TestClient(app)


def test_get_replenishment_suggestions_success(api_client):
    mock_response = {
        "total_suggestions": 2,
        "critical_count": 1,
        "high_count": 1,
        "items": [
            {
                "product_id": 101,
                "product_code": "SKU-101",
                "product_name": "Product A",
                "destination_warehouse_id": 3,
                "destination_warehouse_name": "Branch North",
                "current_stock": 0.0,
                "reserved_stock": 0.0,
                "in_transit_stock": 0.0,
                "available_stock": 0.0,
                "reorder_point": 50.0,
                "safety_stock": 25.0,
                "suggested_transfer_qty": 75.0,
                "source_warehouse_id": 1,
                "source_warehouse_name": "Central Hub",
                "source_available_stock": 200.0,
                "priority": "Critical",
                "reason": "Out of stock",
            },
            {
                "product_id": 102,
                "product_code": "SKU-102",
                "product_name": "Product B",
                "destination_warehouse_id": 3,
                "destination_warehouse_name": "Branch North",
                "current_stock": 10.0,
                "reserved_stock": 0.0,
                "in_transit_stock": 5.0,
                "available_stock": 10.0,
                "reorder_point": 30.0,
                "safety_stock": 15.0,
                "suggested_transfer_qty": 30.0,
                "source_warehouse_id": 1,
                "source_warehouse_name": "Central Hub",
                "source_available_stock": 150.0,
                "priority": "High",
                "reason": "Low stock",
            },
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch.object(service, "get_replenishment_suggestions", return_value=mock_response) as mock_get:
        response = api_client.get(
            "/api/inventory/replenishment/suggestions",
            params={
                "warehouse_id": 3,
                "priority": "Critical",
                "min_deficit": 10.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_suggestions"] == 2
        assert data["critical_count"] == 1
        assert len(data["items"]) == 2
        assert data["items"][0]["product_code"] == "SKU-101"
        assert data["items"][0]["priority"] == "Critical"

        mock_get.assert_called_once_with(
            warehouse_id=3,
            source_warehouse_id=None,
            product_id=None,
            category=None,
            priority="Critical",
            min_deficit=10.0,
            safety_stock_ratio=0.5,
            target_coverage_multiplier=1.5,
        )


def test_get_replenishment_suggestions_404_warehouse_not_found(api_client):
    with patch.object(service, "get_replenishment_suggestions", side_effect=HTTPException(404, "Warehouse #999 not found")):
        response = api_client.get("/api/inventory/replenishment/suggestions?warehouse_id=999")
        assert response.status_code == 404
        assert "Warehouse #999 not found" in response.json()["detail"]


def test_get_replenishment_suggestions_value_error_returns_400(api_client):
    with patch.object(service, "get_replenishment_suggestions", side_effect=ValueError("Invalid ratio")):
        response = api_client.get("/api/inventory/replenishment/suggestions")
        assert response.status_code == 400
        assert "Invalid ratio" in response.json()["detail"]


def test_generate_replenishment_transfers_success(api_client):
    mock_gen_response = {
        "transfers_created": 1,
        "transfer_ids": [55],
        "transfer_numbers": ["TRF-2026-00055"],
        "transfers": [
            {
                "id": 55,
                "transfer_number": "TRF-2026-00055",
                "source_warehouse_id": 1,
                "destination_warehouse_id": 3,
                "status": "Draft",
                "transfer_date": "2026-08-26",
                "expected_delivery_date": "2026-08-28",
                "carrier": "Internal Logistics",
                "notes": "Automated replenishment",
                "lines": [
                    {
                        "id": 101,
                        "transfer_id": 55,
                        "product_id": 101,
                        "qty_requested": 50.0,
                        "qty_dispatched": 0.0,
                        "qty_received": 0.0,
                        "qty_lost": 0.0,
                        "line_number": 1,
                    }
                ],
            }
        ],
    }

    with patch.object(service, "generate_transfers", return_value=mock_gen_response) as mock_gen:
        payload = {
            "source_warehouse_id": 1,
            "destination_warehouse_id": 3,
            "carrier": "Internal Logistics",
            "notes": "Automated replenishment",
            "items": [
                {
                    "product_id": 101,
                    "destination_warehouse_id": 3,
                    "source_warehouse_id": 1,
                    "suggested_transfer_qty": 50.0,
                }
            ],
        }

        response = api_client.post("/api/inventory/replenishment/generate-transfers", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["transfers_created"] == 1
        assert data["transfer_ids"] == [55]
        assert data["transfer_numbers"] == ["TRF-2026-00055"]
        assert len(data["transfers"]) == 1
        assert data["transfers"][0]["transfer_number"] == "TRF-2026-00055"


def test_generate_replenishment_transfers_empty_body(api_client):
    mock_gen_response = {
        "transfers_created": 0,
        "transfer_ids": [],
        "transfer_numbers": [],
        "transfers": [],
    }

    with patch.object(service, "generate_transfers", return_value=mock_gen_response):
        response = api_client.post("/api/inventory/replenishment/generate-transfers", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["transfers_created"] == 0
        assert data["transfer_ids"] == []


def test_generate_replenishment_transfers_validation_error(api_client):
    with patch.object(service, "generate_transfers", side_effect=ValueError("Invalid transfer params")):
        response = api_client.post("/api/inventory/replenishment/generate-transfers", json={})
        assert response.status_code == 400
        assert "Invalid transfer params" in response.json()["detail"]


def test_get_replenishment_summary_success(api_client):
    mock_summary = {
        "total_products": 45,
        "total_warehouses": 4,
        "total_deficits": 8,
        "critical_deficits": 3,
        "high_deficits": 5,
        "active_in_transit_transfers": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch.object(service, "get_stock_health_summary", return_value=mock_summary):
        response = api_client.get("/api/inventory/replenishment/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 45
        assert data["total_warehouses"] == 4
        assert data["total_deficits"] == 8
        assert data["critical_deficits"] == 3
        assert data["active_in_transit_transfers"] == 2
