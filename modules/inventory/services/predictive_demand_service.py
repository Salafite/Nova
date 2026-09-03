"""
Nova ERP — Predictive Inventory Demand Service
Aggregates historical sales order data (T0012, T0013) over 90+ days lookback window,
computes weekly sales buckets, baseline demand velocity, trend/seasonality adjustments,
and statistical variance to project weekly demand forecasts with 80% and 95% confidence intervals.
"""
import os
import math
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant
from modules.inventory.models.predictive_forecast import (
    ConfidenceInterval,
    WeeklyDemandProjection,
    HistoricalSalesAggregation,
    SeasonalTrendAdjustment,
    SKUForecastParameters,
)

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_FORECAST_WEEKS = 4


class PredictiveDemandService:
    """
    Service for calculating statistical weekly demand projections with confidence intervals.
    """

    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')

    def generate_demand_forecast(
        self,
        product_id: int,
        warehouse_id: Optional[int] = None,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        forecast_weeks: int = DEFAULT_FORECAST_WEEKS,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> SKUForecastParameters:
        """
        Generate weekly demand forecast for a single product SKU over forecast_weeks horizon.
        """
        ref_date = reference_date or date.today()
        start_date = ref_date - timedelta(days=lookback_days)

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            params: List[Any] = [product_id, start_date, ref_date]
            warehouse_clause = ""
            if warehouse_id is not None:
                warehouse_clause = "AND so.warehouse_id = %s"
                params.append(warehouse_id)

            tenant_clause = ""
            if tenant_id is not None:
                tenant_clause = "AND so.business_id = %s"
                params.append(tenant_id)

            query = f"""
                SELECT
                    so.order_date::date as sale_date,
                    COALESCE(SUM(si.qty), 0) as daily_qty
                FROM "{self.schema}".t0012 so
                JOIN "{self.schema}".t0013 si ON si.sales_order_id = so.id
                WHERE si.product_id = %s
                  AND so.order_date::date >= %s
                  AND so.order_date::date <= %s
                  AND so.status NOT IN ('CANCELLED', 'REJECTED', 'DRAFT')
                  {warehouse_clause}
                  {tenant_clause}
                GROUP BY so.order_date::date
                ORDER BY sale_date ASC
            """

            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            # Map daily sales into date dictionary
            daily_sales: Dict[date, float] = {r['sale_date']: float(r['daily_qty']) for r in rows}

            # Group into weekly buckets over lookback_days
            num_weeks = max(1, math.ceil(lookback_days / 7))
            weekly_quantities: List[float] = []
            historical_aggregations: List[HistoricalSalesAggregation] = []

            for i in range(num_weeks):
                w_start = start_date + timedelta(days=i * 7)
                w_end = min(ref_date, w_start + timedelta(days=6))

                # Sum daily sales in this 7-day window
                w_total = 0.0
                curr = w_start
                days_in_period = 0
                while curr <= w_end:
                    w_total += daily_sales.get(curr, 0.0)
                    curr += timedelta(days=1)
                    days_in_period += 1

                weekly_quantities.append(w_total)
                avg_daily = w_total / days_in_period if days_in_period > 0 else 0.0
                historical_aggregations.append(
                    HistoricalSalesAggregation(
                        period_start_date=w_start,
                        period_end_date=w_end,
                        total_sales=w_total,
                        average_daily_sales=round(avg_daily, 2),
                    )
                )

            # Compute statistics
            total_historical_qty = sum(weekly_quantities)
            avg_weekly_demand = total_historical_qty / len(weekly_quantities) if weekly_quantities else 0.0
            base_velocity = round(avg_weekly_demand, 2)

            # Trend calculation (comparing second half of historical weeks vs first half)
            half = len(weekly_quantities) // 2
            if half > 0:
                first_half_avg = sum(weekly_quantities[:half]) / half
                second_half_avg = sum(weekly_quantities[half:]) / (len(weekly_quantities) - half)
                if first_half_avg > 0:
                    trend_factor = second_half_avg / first_half_avg
                else:
                    trend_factor = 1.0 if second_half_avg == 0 else 1.1
            else:
                trend_factor = 1.0

            # Clamp trend factor to reasonable boundaries (0.5 to 2.0)
            trend_factor = max(0.5, min(2.0, round(trend_factor, 3)))

            # Variance and standard deviation calculation for confidence bounds
            if len(weekly_quantities) > 1:
                variance = sum((x - avg_weekly_demand) ** 2 for x in weekly_quantities) / (len(weekly_quantities) - 1)
                std_dev = math.sqrt(variance)
            else:
                std_dev = avg_weekly_demand * 0.2  # Default 20% std dev fallback if single sample

            # Seasonal adjustments
            seasonal_adjustments = [
                SeasonalTrendAdjustment(season_identifier="Baseline", adjustment_factor=1.0)
            ]

            # Generate weekly projections for future forecast_weeks
            weekly_projections: List[WeeklyDemandProjection] = []
            for w in range(1, forecast_weeks + 1):
                proj_start = ref_date + timedelta(days=(w - 1) * 7 + 1)

                projected_val = max(0.0, avg_weekly_demand * (trend_factor ** (w / 4)))

                # 80% CI Z=1.282, 95% CI Z=1.960
                margin_80 = 1.282 * std_dev
                margin_95 = 1.960 * std_dev

                lower_80 = max(0.0, round(projected_val - margin_80, 2))
                upper_80 = round(projected_val + margin_80, 2)
                lower_95 = max(0.0, round(projected_val - margin_95, 2))
                upper_95 = round(projected_val + margin_95, 2)

                weekly_projections.append(
                    WeeklyDemandProjection(
                        week_start_date=proj_start,
                        predicted_demand=round(projected_val, 2),
                        confidence_80=ConfidenceInterval(lower_bound=lower_80, upper_bound=upper_80),
                        confidence_95=ConfidenceInterval(lower_bound=lower_95, upper_bound=upper_95),
                    )
                )

            return SKUForecastParameters(
                product_id=product_id,
                warehouse_id=warehouse_id,
                base_velocity=base_velocity,
                trend_factor=trend_factor,
                seasonality_adjustments=seasonal_adjustments,
                weekly_projections=weekly_projections,
                historical_data=historical_aggregations,
            )

        finally:
            if should_release and conn:
                release_connection(conn)

    def list_demand_forecasts(
        self,
        product_ids: Optional[List[int]] = None,
        warehouse_id: Optional[int] = None,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        forecast_weeks: int = DEFAULT_FORECAST_WEEKS,
        conn=None,
    ) -> List[SKUForecastParameters]:
        """
        Generate weekly demand forecasts for multiple products or all active products.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            p_ids = product_ids
            if not p_ids:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                query = f'SELECT id FROM "{self.schema}".t0003 WHERE is_active = true'
                params: List[Any] = []
                if tenant_id is not None:
                    query += " AND business_id = %s"
                    params.append(tenant_id)
                query += " LIMIT 50"
                cursor.execute(query, params)
                rows = cursor.fetchall()
                cursor.close()
                p_ids = [r['id'] for r in rows]

            forecasts = []
            for pid in p_ids:
                f = self.generate_demand_forecast(
                    product_id=pid,
                    warehouse_id=warehouse_id,
                    lookback_days=lookback_days,
                    forecast_weeks=forecast_weeks,
                    conn=conn,
                )
                forecasts.append(f)
            return forecasts

        finally:
            if should_release and conn:
                release_connection(conn)
