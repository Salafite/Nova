"""
Unit tests for SpoilagePreventionService
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest

from modules.core.context import set_current_tenant, clear_current_tenant
from modules.inventory.models.predictive_forecast import SKUForecastParameters
from modules.inventory.services.spoilage_prevention_service import SpoilagePreventionService


@pytest.fixture
def mock_demand_service():
    service = MagicMock()
    # Default weekly base velocity of 14 units => 2 units per day
    service.generate_demand_forecast.return_value = SKUForecastParameters(
        product_id=101,
        warehouse_id=1,
        base_velocity=14.0,
        trend_factor=1.0,
        seasonality_adjustments=[],
        weekly_projections=[],
        historical_data=[],
    )
    return service


def test_evaluate_spoilage_risks_near_expiry_critical(mock_demand_service):
    spoilage_svc = SpoilagePreventionService(demand_service=mock_demand_service)
    ref_date = date(2026, 9, 1)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Batch of 100 units expiring in 5 days. Daily velocity = 2 units/day. Usable consumption = 10 units.
    # Estimated spoilage = 90 units (90% risk).
    mock_cursor.fetchall.return_value = [
        {
            'batch_id': 501,
            'batch_number': 'BATCH-CRIT-01',
            'product_id': 101,
            'product_name': 'Fresh Milk 1L',
            'product_price': 5.0,
            'warehouse_id': 1,
            'warehouse_name': 'Main Warehouse',
            'expiry_date': ref_date + timedelta(days=5),
            'current_quantity': 100.0,
        }
    ]

    summary = spoilage_svc.evaluate_spoilage_risks(
        warehouse_id=1,
        days_to_expiry_threshold=30,
        reference_date=ref_date,
        conn=mock_conn,
    )

    assert summary.total_batches_analyzed == 1
    assert summary.at_risk_batches_count == 1
    assert summary.total_estimated_spoilage_quantity == 90.0

    alert = summary.alerts[0]
    assert alert.batch_id == 501
    assert alert.risk_severity == 'critical'
    assert alert.recommended_discount_percentage == 50.0
    assert alert.estimated_spoilage_quantity == 90.0


def test_evaluate_spoilage_risks_filtering_by_min_severity(mock_demand_service):
    spoilage_svc = SpoilagePreventionService(demand_service=mock_demand_service)
    ref_date = date(2026, 9, 1)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Batch expiring in 25 days, low velocity -> medium severity
    mock_cursor.fetchall.return_value = [
        {
            'batch_id': 502,
            'batch_number': 'BATCH-MED-01',
            'product_id': 101,
            'product_name': 'Yogurt 500g',
            'product_price': 3.0,
            'warehouse_id': 1,
            'warehouse_name': 'Main Warehouse',
            'expiry_date': ref_date + timedelta(days=25),
            'current_quantity': 60.0,  # daily vel 2 * 25 = 50 consumed => 10 spoiled (16.7%) -> medium
        }
    ]

    summary = spoilage_svc.evaluate_spoilage_risks(
        warehouse_id=1,
        min_severity='high',  # Should filter out 'medium' severity
        reference_date=ref_date,
        conn=mock_conn,
    )

    assert summary.at_risk_batches_count == 0


def test_propose_batch_discount_promotion(mock_demand_service):
    spoilage_svc = SpoilagePreventionService(demand_service=mock_demand_service)
    ref_date = date(2026, 9, 1)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = {
        'batch_id': 501,
        'batch_number': 'BATCH-501',
        'product_id': 101,
        'product_name': 'Fresh Milk 1L',
        'current_price': 10.0,
        'expiry_date': ref_date + timedelta(days=10),
        'current_quantity': 50.0,
    }

    proposal = spoilage_svc.propose_batch_discount_promotion(
        batch_id=501,
        reference_date=ref_date,
        conn=mock_conn,
    )

    assert proposal.batch_id == 501
    assert proposal.current_price == 10.0
    assert proposal.discount_percentage == 30.0  # 10 days <= 14 days => 30%
    assert proposal.discounted_price == 7.0
    assert proposal.estimated_units_saved > 0
    assert proposal.estimated_revenue_recovered > 0


def test_spoilage_prevention_tenant_isolation(mock_demand_service):
    spoilage_svc = SpoilagePreventionService(demand_service=mock_demand_service)
    set_current_tenant(8)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    try:
        spoilage_svc.evaluate_spoilage_risks(
            reference_date=date(2026, 9, 1),
            conn=mock_conn,
        )

        executed_sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        assert "b.business_id = %s" in executed_sql
        assert 8 in params
    finally:
        clear_current_tenant()
