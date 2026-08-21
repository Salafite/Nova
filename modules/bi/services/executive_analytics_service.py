import logging
from typing import Optional, Dict, Any, List, Union
from datetime import date, timedelta
from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    ExecutiveMarginSummary,
    CategoryMarginItem,
    CategoryMarginResponse,
    SkuMarginItem,
    SkuMarginResponse,
    PeriodMarginTrendItem,
    PeriodMarginTrendResponse,
)
from ..repositories.executive_analytics_repo import (
    ExecutiveAnalyticsRepository,
    executive_analytics_repo as default_repo,
)

logger = logging.getLogger(__name__)


def resolve_date_range(
    period: str = 'Monthly',
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[date, date]:
    """
    Resolves standard start and end dates based on period name if not explicitly provided.
    """
    today = date.today()
    if date_from and date_to:
        return date_from, date_to

    p = (period or 'Monthly').capitalize()
    if p == 'Daily':
        start = date_from or today
        end = date_to or today
    elif p == 'Weekly':
        start = date_from or (today - timedelta(days=today.weekday()))
        end = date_to or today
    elif p == 'Monthly':
        start = date_from or today.replace(day=1)
        end = date_to or today
    elif p == 'Quarterly':
        quarter = (today.month - 1) // 3
        start = date_from or date(today.year, quarter * 3 + 1, 1)
        end = date_to or today
    elif p == 'Ytd':
        start = date_from or date(today.year, 1, 1)
        end = date_to or today
    else:  # Custom or fallback
        start = date_from or today.replace(day=1)
        end = date_to or today

    return start, end


def resolve_prev_period(start_date: date, end_date: date) -> tuple[date, date]:
    """
    Computes an equivalent prior comparison window immediately preceding start_date.
    """
    duration = (end_date - start_date).days
    if duration < 0:
        duration = 0
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration)
    return prev_start, prev_end


class ExecutiveAnalyticsService:
    def __init__(self, repo: Optional[ExecutiveAnalyticsRepository] = None):
        self.repo = repo or default_repo

    def _normalize_filter(
        self,
        filter_input: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None],
    ) -> tuple[ExecutiveAnalyticsFilter, date, date]:
        if filter_input is None:
            flt = ExecutiveAnalyticsFilter()
        elif isinstance(filter_input, dict):
            flt = ExecutiveAnalyticsFilter(**filter_input)
        else:
            flt = filter_input

        start_date, end_date = resolve_date_range(
            period=flt.period,
            date_from=flt.date_from,
            date_to=flt.date_to,
        )
        return flt, start_date, end_date

    def get_margin_summary(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> ExecutiveMarginSummary:
        """
        Computes executive margin KPIs including revenue, cogs, freight, gross profit $, margin %,
        and comparison against previous period.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        data = self.repo.get_margin_summary_data(
            date_from=start_date,
            date_to=end_date,
            category_name=None,
            product_id=flt.product_id,
            brand=flt.brand,
            sales_rep_id=flt.sales_rep_id,
            customer_id=flt.customer_id,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            conn=conn,
        )

        gross_sales = round(float(data.get('gross_sales', 0.0)), 2)
        discount_amount = round(float(data.get('discount_amount', 0.0)), 2)
        net_revenue = round(float(data.get('net_revenue', 0.0)), 2)
        cogs = round(float(data.get('cogs', 0.0)), 2)
        freight_cost = round(float(data.get('freight_cost', 0.0)), 2)
        gross_profit = round(float(data.get('gross_profit', 0.0)), 2)
        total_orders = int(data.get('total_orders', 0))
        total_customers = int(data.get('total_customers', 0))
        low_margin_order_count = int(data.get('low_margin_order_count', 0))

        gross_margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0
        average_order_value = round((net_revenue / total_orders), 2) if total_orders > 0 else 0.0

        # Prior period comparison
        prev_start, prev_end = resolve_prev_period(start_date, end_date)
        prev_data = self.repo.get_margin_summary_data(
            date_from=prev_start,
            date_to=prev_end,
            sales_rep_id=flt.sales_rep_id,
            customer_id=flt.customer_id,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            conn=conn,
        )

        prev_gross_profit = round(float(prev_data.get('gross_profit', 0.0)), 2)
        prev_net_rev = float(prev_data.get('net_revenue', 0.0))
        prev_margin_pct = round((prev_gross_profit / prev_net_rev * 100.0), 2) if prev_net_rev > 0 else 0.0

        if prev_gross_profit != 0:
            growth_pct = round(((gross_profit - prev_gross_profit) / abs(prev_gross_profit) * 100.0), 2)
        elif gross_profit != 0:
            growth_pct = 100.0
        else:
            growth_pct = 0.0

        return ExecutiveMarginSummary(
            period=flt.period,
            date_from=start_date,
            date_to=end_date,
            gross_sales=gross_sales,
            discount_amount=discount_amount,
            net_revenue=net_revenue,
            cogs=cogs,
            freight_cost=freight_cost,
            gross_profit=gross_profit,
            gross_margin_pct=gross_margin_pct,
            total_orders=total_orders,
            total_customers=total_customers,
            average_order_value=average_order_value,
            low_margin_order_count=low_margin_order_count,
            target_margin_pct=20.0,
            prev_period_gross_profit=prev_gross_profit,
            gross_profit_growth_pct=growth_pct,
            prev_period_margin_pct=prev_margin_pct,
        )

    def get_category_margins(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> CategoryMarginResponse:
        """
        Computes category margin breakdowns, revenue share, unit sales, and alert status (<15%).
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        rows = self.repo.get_category_margins_data(
            date_from=start_date,
            date_to=end_date,
            sales_rep_id=flt.sales_rep_id,
            customer_id=flt.customer_id,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            conn=conn,
        )

        total_net_rev = sum(float(r.get('net_revenue', 0.0)) for r in rows)

        items: List[CategoryMarginItem] = []
        low_margin_count = 0

        for r in rows:
            gross_sales = round(float(r.get('gross_sales', 0.0)), 2)
            discount_amount = round(float(r.get('discount_amount', 0.0)), 2)
            net_revenue = round(float(r.get('net_revenue', 0.0)), 2)
            cogs = round(float(r.get('cogs', 0.0)), 2)
            freight_cost = round(float(r.get('freight_cost', 0.0)), 2)
            gross_profit = round(float(r.get('gross_profit', 0.0)), 2)
            units_sold = round(float(r.get('units_sold', 0.0)), 2)
            order_count = int(r.get('order_count', 0))

            margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0
            rev_share = round((net_revenue / total_net_rev * 100.0), 2) if total_net_rev > 0 else 0.0
            is_low = margin_pct < 15.0

            if is_low:
                low_margin_count += 1

            if margin_pct < 10.0:
                status = 'Critical'
            elif margin_pct < 15.0:
                status = 'Warning'
            else:
                status = 'Healthy'

            # Margin threshold filters if specified
            if flt.min_margin_pct is not None and margin_pct < flt.min_margin_pct:
                continue
            if flt.max_margin_pct is not None and margin_pct > flt.max_margin_pct:
                continue

            items.append(
                CategoryMarginItem(
                    category_name=r.get('category_name', 'Unassigned'),
                    gross_sales=gross_sales,
                    discount_amount=discount_amount,
                    net_revenue=net_revenue,
                    cogs=cogs,
                    freight_cost=freight_cost,
                    gross_profit=gross_profit,
                    gross_margin_pct=margin_pct,
                    revenue_share_pct=rev_share,
                    units_sold=units_sold,
                    order_count=order_count,
                    is_low_margin=is_low,
                    status=status,
                )
            )

        return CategoryMarginResponse(
            period=flt.period,
            date_from=start_date,
            date_to=end_date,
            total_categories=len(items),
            low_margin_category_count=low_margin_count,
            items=items,
        )

    def get_sku_margins(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> SkuMarginResponse:
        """
        Computes SKU line-level margin analysis, average selling price (ASP), unit cost, and profit margins.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        rows, total_count = self.repo.get_sku_margins_data(
            date_from=start_date,
            date_to=end_date,
            product_id=flt.product_id,
            brand=flt.brand,
            sales_rep_id=flt.sales_rep_id,
            customer_id=flt.customer_id,
            warehouse_id=flt.warehouse_id,
            delivery_route=flt.delivery_route,
            limit=limit,
            offset=offset,
            conn=conn,
        )

        items: List[SkuMarginItem] = []
        low_margin_count = 0

        for r in rows:
            units_sold = round(float(r.get('units_sold', 0.0)), 2)
            gross_sales = round(float(r.get('gross_sales', 0.0)), 2)
            discount_amount = round(float(r.get('discount_amount', 0.0)), 2)
            net_revenue = round(float(r.get('net_revenue', 0.0)), 2)
            cogs = round(float(r.get('cogs', 0.0)), 2)
            freight_cost = round(float(r.get('freight_cost', 0.0)), 2)
            gross_profit = round(float(r.get('gross_profit', 0.0)), 2)

            margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0
            asp = round((gross_sales / units_sold), 2) if units_sold > 0 else 0.0
            unit_cost = round((cogs / units_sold), 2) if units_sold > 0 else 0.0
            is_low = margin_pct < 15.0

            if is_low:
                low_margin_count += 1

            if flt.min_margin_pct is not None and margin_pct < flt.min_margin_pct:
                continue
            if flt.max_margin_pct is not None and margin_pct > flt.max_margin_pct:
                continue

            items.append(
                SkuMarginItem(
                    product_id=int(r.get('product_id')),
                    sku_code=r.get('sku_code'),
                    product_name=r.get('product_name', ''),
                    category_id=None,
                    category_name=r.get('category_name'),
                    brand_name=r.get('brand_name'),
                    units_sold=units_sold,
                    avg_selling_price=asp,
                    unit_cost=unit_cost,
                    gross_sales=gross_sales,
                    discount_amount=discount_amount,
                    net_revenue=net_revenue,
                    cogs=cogs,
                    freight_cost=freight_cost,
                    gross_profit=gross_profit,
                    gross_margin_pct=margin_pct,
                    is_low_margin=is_low,
                )
            )

        return SkuMarginResponse(
            period=flt.period,
            date_from=start_date,
            date_to=end_date,
            total_skus=total_count,
            low_margin_sku_count=low_margin_count,
            items=items,
        )

    def get_period_margin_trends(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        period_type: Optional[str] = None,
        conn=None,
    ) -> PeriodMarginTrendResponse:
        """
        Computes sequential margin trends over daily, weekly, monthly, or quarterly intervals.
        """
        flt, start_date, end_date = self._normalize_filter(filters)
        chosen_period = period_type or flt.period or 'Monthly'

        rows = self.repo.get_period_margin_trends_data(
            date_from=start_date,
            date_to=end_date,
            period_type=chosen_period,
            product_id=flt.product_id,
            brand=flt.brand,
            sales_rep_id=flt.sales_rep_id,
            customer_id=flt.customer_id,
            warehouse_id=flt.warehouse_id,
            conn=conn,
        )

        items: List[PeriodMarginTrendItem] = []
        p_lower = chosen_period.lower()

        for r in rows:
            bucket_start: date = r['bucket_start']
            gross_sales = round(float(r.get('gross_sales', 0.0)), 2)
            discount_amount = round(float(r.get('discount_amount', 0.0)), 2)
            net_revenue = round(float(r.get('net_revenue', 0.0)), 2)
            cogs = round(float(r.get('cogs', 0.0)), 2)
            freight_cost = round(float(r.get('freight_cost', 0.0)), 2)
            gross_profit = round(float(r.get('gross_profit', 0.0)), 2)
            order_count = int(r.get('order_count', 0))
            margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0

            if p_lower == 'daily':
                key = bucket_start.strftime('%Y-%m-%d')
                label = bucket_start.strftime('%b %d, %Y')
                bucket_end = bucket_start
            elif p_lower == 'weekly':
                iso_year, iso_week, _ = bucket_start.isocalendar()
                key = f'{iso_year}-W{iso_week:02d}'
                label = f'Week {iso_week}, {iso_year}'
                bucket_end = bucket_start + timedelta(days=6)
            elif p_lower == 'quarterly':
                q = (bucket_start.month - 1) // 3 + 1
                key = f'{bucket_start.year}-Q{q}'
                label = f'Q{q} {bucket_start.year}'
                # Approximation of quarter end
                bucket_end = date(bucket_start.year, q * 3, 28)
            else:  # Monthly
                key = bucket_start.strftime('%Y-%m')
                label = bucket_start.strftime('%b %Y')
                # End of month
                next_month = bucket_start.replace(day=28) + timedelta(days=4)
                bucket_end = next_month - timedelta(days=next_month.day)

            items.append(
                PeriodMarginTrendItem(
                    period_key=key,
                    period_label=label,
                    start_date=bucket_start,
                    end_date=bucket_end,
                    gross_sales=gross_sales,
                    discount_amount=discount_amount,
                    net_revenue=net_revenue,
                    cogs=cogs,
                    freight_cost=freight_cost,
                    gross_profit=gross_profit,
                    gross_margin_pct=margin_pct,
                    order_count=order_count,
                )
            )

        return PeriodMarginTrendResponse(
            period_type=chosen_period,
            items=items,
        )

    def get_low_margin_alerts(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        threshold_pct: float = 15.0,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Returns an executive alert payload of product categories and individual SKUs that fall below
        the target gross margin threshold (default 15%).
        """
        cat_resp = self.get_category_margins(filters=filters, conn=conn)
        sku_resp = self.get_sku_margins(filters=filters, limit=500, offset=0, conn=conn)

        critical_categories = [c for c in cat_resp.items if c.gross_margin_pct < threshold_pct]
        critical_skus = [s for s in sku_resp.items if s.gross_margin_pct < threshold_pct]

        critical_categories.sort(key=lambda x: x.gross_margin_pct)
        critical_skus.sort(key=lambda x: x.gross_margin_pct)

        return {
            'threshold_pct': threshold_pct,
            'low_margin_categories_count': len(critical_categories),
            'low_margin_skus_count': len(critical_skus),
            'categories': critical_categories,
            'skus': critical_skus,
        }


# Default singleton instance
executive_analytics_service = ExecutiveAnalyticsService()
