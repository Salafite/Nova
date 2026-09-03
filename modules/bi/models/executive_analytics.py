from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


# ---------------------------------------------------------------------------
# Filter and Query Parameters
# ---------------------------------------------------------------------------

class ExecutiveAnalyticsFilter(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    period: str = 'Monthly'  # Daily, Weekly, Monthly, Quarterly, YTD, Custom
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    brand: Optional[str] = None
    sales_rep_id: Optional[int] = None
    customer_id: Optional[int] = None
    customer_tier: Optional[str] = None
    warehouse_id: Optional[int] = None
    delivery_route: Optional[str] = None
    quadrant: Optional[str] = None
    min_margin_pct: Optional[float] = None
    max_margin_pct: Optional[float] = None


# ---------------------------------------------------------------------------
# Executive Margin Summary & KPIs
# ---------------------------------------------------------------------------

class ExecutiveMarginSummary(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    contribution_margin: float = 0.0
    contribution_margin_pct: float = 0.0
    total_orders: int = 0
    total_customers: int = 0
    average_order_value: float = 0.0
    low_margin_order_count: int = 0
    target_margin_pct: float = 20.0
    prev_period_gross_profit: Optional[float] = None
    gross_profit_growth_pct: Optional[float] = None
    prev_period_margin_pct: Optional[float] = None


# ---------------------------------------------------------------------------
# Category & SKU Margin Breakdown
# ---------------------------------------------------------------------------

class CategoryMarginItem(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    contribution_margin: float = 0.0
    contribution_margin_pct: float = 0.0
    revenue_share_pct: float = 0.0
    units_sold: float = 0.0
    order_count: int = 0
    is_low_margin: bool = False  # < 15% alert threshold
    status: str = 'Healthy'


class CategoryMarginResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_categories: int = 0
    low_margin_category_count: int = 0
    items: List[CategoryMarginItem] = Field(default_factory=list)


class SkuMarginItem(BaseModel):
    product_id: int
    sku_code: Optional[str] = None
    product_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    units_sold: float = 0.0
    avg_selling_price: float = 0.0
    unit_cost: float = 0.0
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    contribution_margin: float = 0.0
    contribution_margin_pct: float = 0.0
    is_low_margin: bool = False


class SkuMarginResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_skus: int = 0
    low_margin_sku_count: int = 0
    items: List[SkuMarginItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sales Rep Minimum Acceptable Price Boundaries
# ---------------------------------------------------------------------------

class MinimumPriceBoundaryItem(BaseModel):
    product_id: int
    sku_code: Optional[str] = None
    product_name: str
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    units_sold: float = 0.0
    unit_cost: float = 0.0
    unit_freight: float = 0.0
    total_unit_cost: float = 0.0
    target_margin_pct: float = 20.0
    min_acceptable_price: float = 0.0
    avg_selling_price: float = 0.0
    current_margin_pct: float = 0.0
    is_below_minimum: bool = False
    price_headroom: float = 0.0
    status: str = 'Pass'  # 'Pass', 'Warning', 'Violation'


class MinimumPriceBoundaryResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    target_margin_pct: float = 20.0
    total_skus: int = 0
    below_minimum_count: int = 0
    items: List[MinimumPriceBoundaryItem] = Field(default_factory=list)


class PriceThresholdValidationRequest(BaseModel):
    product_id: int
    proposed_unit_price: float
    target_margin_pct: float = 20.0
    customer_id: Optional[int] = None
    sales_rep_id: Optional[int] = None


class PriceThresholdValidationResponse(BaseModel):
    product_id: int
    sku_code: Optional[str] = None
    product_name: str
    unit_cost: float = 0.0
    proposed_unit_price: float = 0.0
    target_margin_pct: float = 20.0
    min_acceptable_price: float = 0.0
    projected_margin_pct: float = 0.0
    is_approved: bool = True
    margin_deficit_pct: float = 0.0
    message: str


class PeriodMarginTrendItem(BaseModel):
    period_key: str
    period_label: str
    start_date: date
    end_date: date
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    order_count: int = 0


class PeriodMarginTrendResponse(BaseModel):
    period_type: str = 'Monthly'
    items: List[PeriodMarginTrendItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Customer Profitability Matrix & 4-Quadrant Account Segmentation
# ---------------------------------------------------------------------------

class CustomerProfitabilityItem(BaseModel):
    customer_id: int
    customer_code: Optional[str] = None
    customer_name: str
    customer_group: Optional[str] = None
    sales_rep_id: Optional[int] = None
    sales_rep_name: Optional[str] = None
    order_count: int = 0
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    average_order_value: float = 0.0
    quadrant: str = 'Core Stars'  # Core Stars, Volume Risks, High Potential, Unprofitable / Drain
    quadrant_code: str = 'Q1'     # Q1, Q2, Q3, Q4
    recommendation: Optional[str] = None


class QuadrantSummaryItem(BaseModel):
    quadrant: str
    quadrant_code: str
    description: str
    customer_count: int = 0
    total_net_revenue: float = 0.0
    total_gross_profit: float = 0.0
    avg_margin_pct: float = 0.0
    revenue_share_pct: float = 0.0
    profit_share_pct: float = 0.0


class CustomerProfitabilityResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_customers: int = 0
    revenue_median_threshold: float = 0.0
    margin_threshold_pct: float = 15.0
    quadrants: List[QuadrantSummaryItem] = Field(default_factory=list)
    customers: List[CustomerProfitabilityItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Delivery Route Fulfillment Analytics
# ---------------------------------------------------------------------------

class DeliveryRouteMetricItem(BaseModel):
    delivery_route: str
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    total_deliveries: int = 0
    completed_deliveries: int = 0
    on_time_deliveries: int = 0
    delayed_deliveries: int = 0
    on_time_delivery_rate: float = 0.0  # OTD %
    route_completion_rate: float = 0.0
    total_freight_cost: float = 0.0
    avg_freight_per_delivery: float = 0.0
    total_qty_ordered: float = 0.0
    total_qty_shipped: float = 0.0
    fulfillment_variance_pct: float = 0.0


class DeliveryFulfillmentSummaryResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_routes: int = 0
    total_deliveries: int = 0
    overall_on_time_rate: float = 0.0
    overall_completion_rate: float = 0.0
    total_freight_cost: float = 0.0
    avg_freight_cost_per_order: float = 0.0
    routes: List[DeliveryRouteMetricItem] = Field(default_factory=list)


class WarehouseDeliveryMetricItem(BaseModel):
    warehouse_id: int
    warehouse_name: str
    location: Optional[str] = None
    total_deliveries: int = 0
    completed_deliveries: int = 0
    on_time_deliveries: int = 0
    delayed_deliveries: int = 0
    on_time_delivery_rate: float = 0.0
    route_completion_rate: float = 0.0
    total_freight_cost: float = 0.0
    avg_freight_per_delivery: float = 0.0
    total_qty_shipped: float = 0.0


class CustomerDestinationMetricItem(BaseModel):
    customer_id: int
    customer_name: str
    customer_code: Optional[str] = None
    delivery_route: Optional[str] = None
    total_deliveries: int = 0
    completed_deliveries: int = 0
    on_time_delivery_rate: float = 0.0
    total_freight_cost: float = 0.0
    avg_freight_per_delivery: float = 0.0
    total_qty_shipped: float = 0.0


class DeliveryVarianceLineItem(BaseModel):
    delivery_id: int
    delivery_number: str
    delivery_route: Optional[str] = None
    product_id: Optional[int] = None
    product_name: str
    qty_ordered: float = 0.0
    qty_shipped: float = 0.0
    variance_qty: float = 0.0
    variance_pct: float = 0.0
    status: str = 'Dispatched'



# ---------------------------------------------------------------------------
# Financial Export Requests & Responses
# ---------------------------------------------------------------------------

class ExecutiveExportRequest(BaseModel):
    export_format: str = 'pdf'  # pdf, excel, csv
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    period: str = 'Monthly'
    category_id: Optional[int] = None
    sales_rep_id: Optional[int] = None
    customer_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    delivery_route: Optional[str] = None
    include_kpi_summary: bool = True
    include_category_margins: bool = True
    include_sku_margins: bool = True
    include_customer_matrix: bool = True
    include_commissions: bool = True
    include_routes: bool = True
    confidentiality_notice: Optional[str] = 'CONFIDENTIAL - BOARD & EXECUTIVE REVIEW ONLY'


class ExecutiveExportResponse(BaseModel):
    filename: str
    content_type: str
    file_size_bytes: int = 0
    download_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Route Margin Breakdown & Price Boundary Validation Models
# ---------------------------------------------------------------------------

class RouteMarginItem(BaseModel):
    delivery_route: str
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    order_count: int = 0
    units_sold: float = 0.0
    gross_sales: float = 0.0
    discount_amount: float = 0.0
    net_revenue: float = 0.0
    cogs: float = 0.0
    freight_cost: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    contribution_margin: float = 0.0
    contribution_margin_pct: float = 0.0
    is_low_margin: bool = False
    status: str = 'Healthy'


class RouteMarginResponse(BaseModel):
    period: str = 'Monthly'
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_routes: int = 0
    low_margin_route_count: int = 0
    items: List[RouteMarginItem] = Field(default_factory=list)


class MinAcceptablePriceCheckRequest(BaseModel):
    product_id: int
    unit_price: float
    target_margin_pct: float = 20.0
    customer_tier: Optional[str] = None
    freight_cost_per_unit: float = 0.0


class MinAcceptablePriceCheckResponse(BaseModel):
    product_id: int
    sku_code: Optional[str] = None
    product_name: str
    cost_price: float = 0.0
    unit_price: float = 0.0
    freight_cost_per_unit: float = 0.0
    net_realized_price: float = 0.0
    effective_margin_pct: float = 0.0
    min_acceptable_price: float = 0.0
    target_margin_pct: float = 20.0
    is_above_min_price: bool = True
    margin_shortfall_pct: float = 0.0
    status: str = 'Pass'
    recommendation: str = ''

