"""
Nova ERP — Predictive Inventory & Spoilage REST Controller Unit & API Tests
Tests endpoints:
- GET /api/inventory/predictive-demand
- GET /api/inventory/spoilage-risk
- POST /api/inventory/spoilage-risk/propose-discount
- POST /api/inventory/spoilage-promotions/apply
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.inventory.controllers.predictive_inventory_controller import (
    router,
    demand_service,
    spoilage_service,
)
from modules.inventory.models.predictive_demand import (
    SKUForecastParameters,
    WeeklyForecastPoint,
    ConfidenceInterval,
)
from modules.inventory.models.spoilage_prevention import (
    SpoilageRiskReport,
    BatchSpoilageItem,
    PromotionRecommendation,
    ApplyPromotionResponse,
)
from packages.auth.deps import get_current_user, require_permission


@pytest.fixture
def api_client():
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "inventory_mgr",
        "role": "Inventory Manager",
        "permissions": ["*"],
        "business_id": 1,
    }
    app.dependency_overrides[require_permission("INVENTORY_VIEW")] = lambda: True
    app.include_router(router)
    return TestClient(app)


def test_get_predictive_demand_single_product(api_client):
    mock_forecast = SKUForecastParameters(
        product_id=10,
        warehouse_id=2,
        base_velocity=25.0,
        trend_factor=1.0,
        seasonality_adjustments=[],
        weekly_projections=[
            WeeklyForecastPoint(
                week_start_date=date(2026, 9, 7),
                predicted_demand=25.0,
                confidence_80=ConfidenceInterval(lower_bound=20.0, upper_bound=30.0),
                confidence_95=ConfidenceInterval(lower_bound=18.0, upper_bound=32.0),
            )
        ],
        historical_data=[],
    )

    with patch.object(demand_service, "generate_demand_forecast", return_value=mock_forecast) as mock_gen:
        response = api_client.get(
            "/api/inventory/predictive-demand",
            params={"product_id": 10, "warehouse_id": 2, "lookback_days": 90, "forecast_weeks": 4},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["product_id"] == 10
        assert data[0]["base_velocity"] == 25.0

        mock_gen.assert_called_once_with(
            product_id=10,
            warehouse_id=2,
            lookback_days=90,
            forecast_weeks=4,
        )


def test_get_predictive_demand_all_products(api_client):
    mock_forecasts = [
        SKUForecastParameters(
            product_id=10,
            warehouse_id=None,
            base_velocity=25.0,
            trend_factor=1.0,
            weekly_projections=[],
        ),
        SKUForecastParameters(
            product_id=11,
            warehouse_id=None,
            base_velocity=15.0,
            trend_factor=1.0,
            weekly_projections=[],
        ),
    ]

    with patch.object(demand_service, "list_demand_forecasts", return_value=mock_forecasts) as mock_list:
        response = api_client.get("/api/inventory/predictive-demand")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["product_id"] == 10
        assert data[1]["product_id"] == 11

        mock_list.assert_called_once_with(
            product_ids=None,
            warehouse_id=None,
            lookback_days=90,
            forecast_weeks=4,
        )


def test_get_predictive_demand_error_500(api_client):
    with patch.object(demand_service, "generate_demand_forecast", side_effect=Exception("Database query timeout")):
        response = api_client.get("/api/inventory/predictive-demand?product_id=10")
        assert response.status_code == 500
        assert "Failed to calculate predictive demand forecast" in response.json()["detail"]


def test_get_spoilage_risk_alerts_success(api_client):
    mock_report = SpoilageRiskReport(
        total_batches_analyzed=15,
        at_risk_batches_count=2,
        total_estimated_spoilage_quantity=45.0,
        alerts=[
            BatchSpoilageItem(
                batch_id=101,
                batch_number="BAT-2026-001",
                product_id=10,
                product_name="Organic Milk 1L",
                warehouse_id=1,
                warehouse_name="Main Warehouse",
                current_quantity=50.0,
                expiry_date=date(2026, 9, 15),
                days_to_expiry=11,
                daily_consumption_velocity=1.8,
                projected_consumption_units=20.0,
                estimated_spoilage_quantity=30.0,
                spoilage_risk_percentage=60.0,
                risk_severity="HIGH",
                recommended_discount_percentage=30.0,
                recommended_action="Apply 30% markdown promotion",
            )
        ],
    )

    with patch.object(spoilage_service, "evaluate_spoilage_risks", return_value=mock_report) as mock_eval:
        response = api_client.get(
            "/api/inventory/spoilage-risk",
            params={"warehouse_id": 1, "min_severity": "high", "days_to_expiry_threshold": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["at_risk_batches_count"] == 2
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["batch_number"] == "BAT-2026-001"

        mock_eval.assert_called_once_with(
            warehouse_id=1,
            product_id=None,
            min_severity="high",
            days_to_expiry_threshold=30,
        )


def test_get_spoilage_risk_alerts_alias_route(api_client):
    mock_report = SpoilageRiskReport(
        total_batches_analyzed=0,
        at_risk_batches_count=0,
        total_estimated_spoilage_quantity=0.0,
        alerts=[],
    )

    with patch.object(spoilage_service, "evaluate_spoilage_risks", return_value=mock_report):
        response = api_client.get("/api/inventory/spoilage-risks")
        assert response.status_code == 200
        assert response.json()["at_risk_batches_count"] == 0


def test_get_spoilage_risk_error_500(api_client):
    with patch.object(spoilage_service, "evaluate_spoilage_risks", side_effect=RuntimeError("Calculation failure")):
        response = api_client.get("/api/inventory/spoilage-risk")
        assert response.status_code == 500
        assert "Failed to evaluate batch spoilage risks" in response.json()["detail"]


def test_propose_batch_discount_promotion_success(api_client):
    mock_proposal = PromotionRecommendation(
        proposal_id="PROP-101",
        batch_id=101,
        batch_number="BAT-2026-001",
        product_id=10,
        product_name="Organic Milk 1L",
        current_price=10.0,
        discount_percentage=30.0,
        discounted_price=7.0,
        estimated_units_saved=30.0,
        estimated_revenue_recovered=210.0,
        effective_start_date=date(2026, 9, 4),
        effective_end_date=date(2026, 9, 15),
    )

    with patch.object(spoilage_service, "propose_batch_discount_promotion", return_value=mock_proposal) as mock_prop:
        response = api_client.post(
            "/api/inventory/spoilage-risk/propose-discount",
            params={"batch_id": 101, "discount_percentage": 30.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == 101
        assert data["discount_percentage"] == 30.0
        assert data["discounted_price"] == 7.0

        mock_prop.assert_called_once_with(
            batch_id=101,
            override_discount_pct=30.0,
        )


def test_propose_batch_discount_promotion_not_found(api_client):
    with patch.object(
        spoilage_service,
        "propose_batch_discount_promotion",
        side_effect=ValueError("Batch #999 not found"),
    ):
        response = api_client.post(
            "/api/inventory/spoilage-risk/propose-discount",
            params={"batch_id": 999},
        )
        assert response.status_code == 404
        assert "Batch #999 not found" in response.json()["detail"]


def test_apply_spoilage_promotion_body_success(api_client):
    mock_applied = ApplyPromotionResponse(
        success=True,
        message="Successfully updated promotional markdown price.",
        batch_id=101,
        applied_discount_percentage=25.0,
        new_price=7.5,
        promotion=None,
    )

    with patch.object(spoilage_service, "apply_promotion", return_value=mock_applied) as mock_apply:
        payload = {"batch_id": 101, "discount_percentage": 25.0}
        response = api_client.post("/api/inventory/spoilage-promotions/apply", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["new_price"] == 7.5


def test_apply_spoilage_promotion_missing_params(api_client):
    response = api_client.post("/api/inventory/spoilage-promotions/apply")
    assert response.status_code == 400
    assert "batch_id and discount_percentage are required" in response.json()["detail"]
