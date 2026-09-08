from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class ConfidenceInterval(BaseModel):
    lower_bound: float = Field(..., description="Lower bound of the confidence interval")
    upper_bound: float = Field(..., description="Upper bound of the confidence interval")


class WeeklyForecastPoint(BaseModel):
    week_start_date: date = Field(..., description="Start date of the week")
    predicted_demand: float = Field(..., description="Predicted demand quantity for the week")
    confidence_80: ConfidenceInterval = Field(..., description="80% confidence interval for the prediction")
    confidence_95: ConfidenceInterval = Field(..., description="95% confidence interval for the prediction")


# Alias for backward compatibility
WeeklyDemandProjection = WeeklyForecastPoint


class HistoricalSalesAggregation(BaseModel):
    period_start_date: date = Field(..., description="Start date of the historical period")
    period_end_date: date = Field(..., description="End date of the historical period")
    total_sales: float = Field(..., description="Total sales quantity during the period")
    average_daily_sales: float = Field(..., description="Average daily sales during the period")


class SeasonalTrendAdjustment(BaseModel):
    season_identifier: str = Field(..., description="Identifier for the season (e.g., Q1, Summer, Holiday)")
    adjustment_factor: float = Field(..., description="Multiplier applied to base demand for this season")


class SKUForecastParameters(BaseModel):
    product_id: int = Field(..., description="ID of the product (SKU)")
    warehouse_id: Optional[int] = Field(None, description="Optional warehouse ID if forecasting per warehouse")
    base_velocity: float = Field(..., description="Calculated base sales velocity (e.g., units per week)")
    trend_factor: float = Field(..., description="Calculated trend factor (e.g., 1.05 for 5% growth)")
    seasonality_adjustments: List[SeasonalTrendAdjustment] = Field(default_factory=list, description="Seasonal adjustments applied")
    weekly_projections: List[WeeklyForecastPoint] = Field(default_factory=list, description="Future weekly demand projections")
    historical_data: List[HistoricalSalesAggregation] = Field(default_factory=list, description="Historical sales data used for the forecast")


class DemandForecastResponse(BaseModel):
    product_id: Optional[int] = Field(None, description="Product ID if single SKU forecast")
    warehouse_id: Optional[int] = Field(None, description="Warehouse ID filter")
    forecasts: List[SKUForecastParameters] = Field(default_factory=list, description="List of SKU forecasts")
    base_velocity: Optional[float] = Field(None, description="Base sales velocity")
    trend_factor: Optional[float] = Field(None, description="Trend factor")
    weekly_projections: List[WeeklyForecastPoint] = Field(default_factory=list, description="Weekly projections")
