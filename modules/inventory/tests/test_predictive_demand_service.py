"""
Unit tests for PredictiveDemandService
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest

from modules.core.context import set_current_tenant, clear_current_tenant
from modules.inventory.services.predictive_demand_service import PredictiveDemandService


def test_generate_demand_forecast_with_sales_history():
    service = PredictiveDemandService()
    ref_date = date(2026, 9, 1)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # 90 days of daily sales rows
    mock_rows = []
    start_date = ref_date - timedelta(days=90)
    curr = start_date
    day_idx = 0
    while curr <= ref_date:
        # Simulate growing sales volume
        mock_rows.append({
            'sale_date': curr,
            'daily_qty': 10.0 + (day_idx * 0.1),
        })
        curr += timedelta(days=1)
        day_idx += 1

    mock_cursor.fetchall.return_value = mock_rows

    forecast = service.generate_demand_forecast(
        product_id=101,
        warehouse_id=1,
        lookback_days=90,
        forecast_weeks=4,
        reference_date=ref_date,
        conn=mock_conn,
    )

    assert forecast.product_id == 101
    assert forecast.warehouse_id == 1
    assert forecast.base_velocity > 0
    assert forecast.trend_factor >= 1.0
    assert len(forecast.weekly_projections) == 4

    for proj in forecast.weekly_projections:
        assert proj.predicted_demand >= 0
        assert proj.confidence_80.lower_bound <= proj.predicted_demand
        assert proj.confidence_80.upper_bound >= proj.predicted_demand
        assert proj.confidence_95.lower_bound <= proj.confidence_80.lower_bound
        assert proj.confidence_95.upper_bound >= proj.confidence_80.upper_bound


def test_generate_demand_forecast_zero_demand():
    service = PredictiveDemandService()
    ref_date = date(2026, 9, 1)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    forecast = service.generate_demand_forecast(
        product_id=202,
        lookback_days=90,
        forecast_weeks=4,
        reference_date=ref_date,
        conn=mock_conn,
    )

    assert forecast.product_id == 202
    assert forecast.base_velocity == 0.0
    assert forecast.trend_factor == 1.0
    assert len(forecast.weekly_projections) == 4
    for proj in forecast.weekly_projections:
        assert proj.predicted_demand == 0.0
        assert proj.confidence_80.lower_bound == 0.0
        assert proj.confidence_80.upper_bound == 0.0


def test_generate_demand_forecast_tenant_isolation():
    service = PredictiveDemandService()
    set_current_tenant(5)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    try:
        service.generate_demand_forecast(
            product_id=101,
            lookback_days=90,
            reference_date=date(2026, 9, 1),
            conn=mock_conn,
        )

        executed_sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        assert "so.business_id = %s" in executed_sql
        assert 5 in params
    finally:
        clear_current_tenant()


def test_list_demand_forecasts():
    service = PredictiveDemandService()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.side_effect = [
        [{'id': 1}, {'id': 2}],  # Product list fetch
        [],  # Product 1 sales fetch
        [],  # Product 2 sales fetch
    ]

    forecasts = service.list_demand_forecasts(
        product_ids=None,
        lookback_days=90,
        forecast_weeks=4,
        conn=mock_conn,
    )

    assert len(forecasts) == 2
    assert forecasts[0].product_id == 1
    assert forecasts[1].product_id == 2
