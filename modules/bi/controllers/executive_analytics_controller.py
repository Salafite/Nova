import logging
from typing import Optional, List, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from packages.auth.deps import require_permission
from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    ExecutiveMarginSummary,
    CategoryMarginResponse,
    SkuMarginResponse,
    PeriodMarginTrendResponse,
    CustomerProfitabilityResponse,
    CustomerProfitabilityItem,
    DeliveryFulfillmentSummaryResponse,
    WarehouseDeliveryMetricItem,
    CustomerDestinationMetricItem,
    DeliveryVarianceLineItem,
)
from ..services.executive_analytics_service import (
    ExecutiveAnalyticsService,
    executive_analytics_service as default_executive_service,
)
from ..services.customer_profitability_service import (
    CustomerProfitabilityService,
    customer_profitability_service as default_customer_service,
)
from ..services.delivery_analytics_service import (
    DeliveryAnalyticsService,
    delivery_analytics_service as default_delivery_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/api/bi/executive',
    tags=['Executive Analytics'],
    dependencies=[Depends(require_permission('BI_VIEW'))],
)


def _build_filter(
    period: str = 'Monthly',
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category_id: Optional[int] = None,
    product_id: Optional[int] = None,
    brand: Optional[str] = None,
    sales_rep_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    delivery_route: Optional[str] = None,
    quadrant: Optional[str] = None,
    min_margin_pct: Optional[float] = None,
    max_margin_pct: Optional[float] = None,
) -> ExecutiveAnalyticsFilter:
    return ExecutiveAnalyticsFilter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        product_id=product_id,
        brand=brand,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
        quadrant=quadrant,
        min_margin_pct=min_margin_pct,
        max_margin_pct=max_margin_pct,
    )


# ---------------------------------------------------------------------------
# Gross Margin & Profitability Endpoints
# ---------------------------------------------------------------------------

@router.get('/summary', response_model=ExecutiveMarginSummary)
def get_margin_summary(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Filter by product category ID'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
    customer_id: Optional[int] = Query(None, description='Filter by customer ID'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
    delivery_route: Optional[str] = Query(None, description='Filter by delivery route'),
):
    """
    Returns executive gross margin summary: gross sales, discounts, net revenue,
    COGS, freight costs, gross profit, margin %, and period-over-period growth.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )
    return default_executive_service.get_margin_summary(filters=flt)


@router.get('/categories', response_model=CategoryMarginResponse)
def get_category_margins(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Filter by specific product category ID'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
    customer_id: Optional[int] = Query(None, description='Filter by customer ID'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
):
    """
    Returns real-time gross profit margin breakdown by product category,
    including revenue share and low-margin warning status (<15%).
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
    )
    return default_executive_service.get_category_margins(filters=flt)


@router.get('/skus', response_model=SkuMarginResponse)
def get_sku_margins(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Filter by product category ID'),
    brand: Optional[str] = Query(None, description='Filter by brand name'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
    customer_id: Optional[int] = Query(None, description='Filter by customer ID'),
    min_margin_pct: Optional[float] = Query(None, description='Filter minimum gross margin %'),
    max_margin_pct: Optional[float] = Query(None, description='Filter maximum gross margin %'),
    limit: int = Query(50, ge=1, le=500, description='Number of SKU records to return'),
    offset: int = Query(0, ge=0, description='Pagination offset'),
):
    """
    Returns line-item SKU gross margins comparing unit selling prices vs unit costs (COGS).
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        brand=brand,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        min_margin_pct=min_margin_pct,
        max_margin_pct=max_margin_pct,
    )
    return default_executive_service.get_sku_margins(filters=flt, limit=limit, offset=offset)


@router.get('/trends', response_model=PeriodMarginTrendResponse)
def get_period_margin_trends(
    period_type: str = Query('Monthly', description='Daily, Weekly, Monthly, or Quarterly'),
    periods_count: int = Query(12, ge=1, le=36, description='Number of trailing historical periods'),
    category_id: Optional[int] = Query(None, description='Filter by product category ID'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
):
    """
    Returns historical period margin trends for charting and forecasting.
    """
    flt = _build_filter(category_id=category_id, sales_rep_id=sales_rep_id)
    return default_executive_service.get_period_margin_trends(
        period_type=period_type,
        periods_count=periods_count,
        filters=flt,
    )


@router.get('/alerts')
def get_low_margin_alerts(
    threshold_pct: float = Query(15.0, description='Margin percentage alert threshold (default 15%)'),
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
):
    """
    Returns critical alert lists of categories and SKUs falling below the profitability threshold.
    """
    flt = _build_filter(period=period, date_from=date_from, date_to=date_to)
    return default_executive_service.get_low_margin_alerts(threshold_pct=threshold_pct, filters=flt)


# ---------------------------------------------------------------------------
# Customer Profitability Matrix & Quadrants
# ---------------------------------------------------------------------------

@router.get('/customer-matrix', response_model=CustomerProfitabilityResponse)
def get_customer_profitability_matrix(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    quadrant: Optional[str] = Query(None, description='Filter by quadrant code: Q1, Q2, Q3, or Q4'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
    margin_threshold_pct: float = Query(15.0, description='Target gross margin threshold % for quadrants'),
):
    """
    Returns 4-quadrant customer account segmentation (Core Stars, Volume Risks,
    High Potential, Unprofitable / Drain) with summary metrics and account recommendations.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        quadrant=quadrant,
        sales_rep_id=sales_rep_id,
    )
    return default_customer_service.get_customer_profitability_matrix(
        filters=flt,
        margin_threshold_pct=margin_threshold_pct,
    )


@router.get('/customers/top', response_model=List[CustomerProfitabilityItem])
def get_top_profitable_customers(
    limit: int = Query(10, ge=1, le=100, description='Number of top accounts to return'),
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
):
    """
    Returns top customer accounts ranked by total gross profit contribution $.
    """
    flt = _build_filter(period=period, date_from=date_from, date_to=date_to)
    return default_customer_service.get_top_profitable_customers(filters=flt, limit=limit)


@router.get('/customers/unprofitable', response_model=List[CustomerProfitabilityItem])
def get_unprofitable_customers(
    limit: int = Query(10, ge=1, le=100, description='Number of unprofitable accounts to return'),
    threshold_pct: float = Query(10.0, description='Maximum margin % threshold for drain accounts'),
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
):
    """
    Returns lowest-margin customer accounts requiring pricing adjustments or renegotiation.
    """
    flt = _build_filter(period=period, date_from=date_from, date_to=date_to)
    return default_customer_service.get_unprofitable_customers(
        filters=flt,
        limit=limit,
        threshold_pct=threshold_pct,
    )


@router.get('/customers/{customer_id}')
def get_customer_profitability_details(
    customer_id: int,
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
):
    """
    Returns detailed customer profitability profile, quadrant strategy, and top purchased products.
    """
    flt = _build_filter(period=period, date_from=date_from, date_to=date_to)
    result = default_customer_service.get_customer_details(customer_id=customer_id, filters=flt)
    if not result.get('customer'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Customer #{customer_id} profitability record not found for the selected period',
        )
    return result


@router.get('/quadrants/{quadrant_code}/playbook')
def get_quadrant_playbook(quadrant_code: str):
    """
    Returns executive strategic guidance and action items for a given quadrant (Q1, Q2, Q3, Q4).
    """
    return default_customer_service.get_quadrant_playbook(quadrant_code)


# ---------------------------------------------------------------------------
# Delivery Route Fulfillment Analytics
# ---------------------------------------------------------------------------

@router.get('/delivery/summary', response_model=DeliveryFulfillmentSummaryResponse)
def get_delivery_fulfillment_summary(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
    delivery_route: Optional[str] = Query(None, description='Filter by delivery route name'),
    customer_id: Optional[int] = Query(None, description='Filter by destination customer ID'),
    sales_rep_id: Optional[int] = Query(None, description='Filter by sales representative ID'),
):
    """
    Returns delivery route fulfillment statistics, On-Time Delivery (OTD) rates %,
    route completion rates, freight costs per delivery, and quantity variances.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
        customer_id=customer_id,
        sales_rep_id=sales_rep_id,
    )
    return default_delivery_service.get_delivery_fulfillment_summary(filters=flt)


@router.get('/delivery/warehouses', response_model=List[WarehouseDeliveryMetricItem])
def get_warehouse_delivery_efficiency(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    warehouse_id: Optional[int] = Query(None, description='Filter by specific warehouse ID'),
):
    """
    Returns fulfillment and dispatch efficiency broken down by origin warehouse.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
    )
    return default_delivery_service.get_warehouse_efficiency(filters=flt)


@router.get('/delivery/destinations', response_model=List[CustomerDestinationMetricItem])
def get_customer_destination_metrics(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
    delivery_route: Optional[str] = Query(None, description='Filter by delivery route'),
    customer_id: Optional[int] = Query(None, description='Filter by destination customer ID'),
    limit: int = Query(50, ge=1, le=200, description='Number of destination records to return'),
):
    """
    Returns delivery volume, on-time rates, and freight costs by customer destination.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
        customer_id=customer_id,
    )
    return default_delivery_service.get_customer_destination_metrics(filters=flt, limit=limit)


@router.get('/delivery/variances', response_model=List[DeliveryVarianceLineItem])
def get_delivery_fulfillment_variances(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
    delivery_route: Optional[str] = Query(None, description='Filter by delivery route'),
    limit: int = Query(100, ge=1, le=500, description='Number of variance line items to return'),
):
    """
    Returns line items where quantity delivered/shipped differs from quantity ordered.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )
    return default_delivery_service.get_delivery_fulfillment_variances(filters=flt, limit=limit)


@router.get('/delivery/gauges')
def get_delivery_kpi_gauges(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Filter start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='Filter end date (YYYY-MM-DD)'),
    warehouse_id: Optional[int] = Query(None, description='Filter by origin warehouse ID'),
    delivery_route: Optional[str] = Query(None, description='Filter by delivery route'),
):
    """
    Returns dashboard gauge ratings for OTD and completion rates against company targets.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )
    return default_delivery_service.get_delivery_kpi_gauges(filters=flt)
