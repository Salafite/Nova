import logging
from typing import Optional, Dict, Any, List, Union
from datetime import date
from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    CustomerProfitabilityItem,
    QuadrantSummaryItem,
    CustomerProfitabilityResponse,
)
from ..repositories.customer_profitability_repo import (
    CustomerProfitabilityRepository,
    customer_profitability_repo as default_repo,
)
from .executive_analytics_service import resolve_date_range

logger = logging.getLogger(__name__)

# Strategic quadrant metadata and definitions
QUADRANTS_META = {
    'Q1': {
        'name': 'Core Stars',
        'code': 'Q1',
        'description': 'High Volume, High Margin - Strategic accounts driving company profitability and cash flow',
        'strategy': 'Protect and nurture relationship; prioritize service level, dedicate account management, and offer strategic pricing locks.',
    },
    'Q2': {
        'name': 'Volume Risks',
        'code': 'Q2',
        'description': 'High Volume, Low Margin - High volume drivers with margin dilution risk requiring price optimization',
        'strategy': 'Renegotiate contract pricing, curb non-standard discounts, optimize delivery batching, and improve route freight efficiency.',
    },
    'Q3': {
        'name': 'High Potential',
        'code': 'Q3',
        'description': 'Low Volume, High Margin - Highly profitable accounts with significant volume expansion potential',
        'strategy': 'Upsell and cross-sell complementary SKU categories; assign proactive sales rep outreach to scale order volume and wallet share.',
    },
    'Q4': {
        'name': 'Unprofitable / Drain',
        'code': 'Q4',
        'description': 'Low Volume, Low Margin - Low revenue and poor margins creating operational and fulfillment drain',
        'strategy': 'Enforce minimum order quantities (MOQ), pass through full delivery freight costs, and eliminate discretionary discounting.',
    },
}


class CustomerProfitabilityService:
    def __init__(self, repo: Optional[CustomerProfitabilityRepository] = None):
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

    def get_customer_profitability_matrix(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        margin_threshold_pct: float = 15.0,
        revenue_threshold: Optional[float] = None,
        conn=None,
    ) -> CustomerProfitabilityResponse:
        """
        Classifies customer accounts into 4 strategic quadrants:
        - Q1: Core Stars (High Volume, High Margin)
        - Q2: Volume Risks (High Volume, Low Margin)
        - Q3: High Potential (Low Volume, High Margin)
        - Q4: Unprofitable / Drain (Low Volume, Low Margin)

        Computes customer gross profit $, margin %, order count, and AOV.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        raw_data = self.repo.get_customer_profitability_data(
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

        # Pre-process raw rows
        processed_rows: List[Dict[str, Any]] = []
        for r in raw_data:
            gross_sales = round(float(r.get('gross_sales', 0.0)), 2)
            discount_amount = round(float(r.get('discount_amount', 0.0)), 2)
            net_revenue = round(float(r.get('net_revenue', 0.0)), 2)
            cogs = round(float(r.get('cogs', 0.0)), 2)
            freight_cost = round(float(r.get('freight_cost', 0.0)), 2)
            gross_profit = round(float(r.get('gross_profit', 0.0)), 2)
            order_count = int(r.get('order_count', 0))

            margin_pct = round((gross_profit / net_revenue * 100.0), 2) if net_revenue > 0 else 0.0
            aov = round((net_revenue / order_count), 2) if order_count > 0 else 0.0

            processed_rows.append({
                'customer_id': int(r.get('customer_id')),
                'customer_code': r.get('customer_code'),
                'customer_name': r.get('customer_name', ''),
                'customer_group': r.get('customer_group', 'Retail'),
                'sales_rep_id': r.get('sales_rep_id'),
                'sales_rep_name': r.get('sales_rep_name'),
                'order_count': order_count,
                'gross_sales': gross_sales,
                'discount_amount': discount_amount,
                'net_revenue': net_revenue,
                'cogs': cogs,
                'freight_cost': freight_cost,
                'gross_profit': gross_profit,
                'gross_margin_pct': margin_pct,
                'average_order_value': aov,
            })

        # Calculate revenue volume threshold (median of net revenue across cohort if not provided)
        if revenue_threshold is not None:
            volume_threshold = float(revenue_threshold)
        elif processed_rows:
            revenues = sorted([row['net_revenue'] for row in processed_rows])
            n = len(revenues)
            if n % 2 == 1:
                median_rev = revenues[n // 2]
            else:
                median_rev = (revenues[n // 2 - 1] + revenues[n // 2]) / 2.0
            volume_threshold = round(median_rev, 2)
        else:
            volume_threshold = 0.0

        effective_margin_threshold = margin_threshold_pct

        # Classify each customer into one of 4 quadrants
        all_classified_customers: List[CustomerProfitabilityItem] = []
        for row in processed_rows:
            is_high_volume = row['net_revenue'] >= volume_threshold
            is_high_margin = row['gross_margin_pct'] >= effective_margin_threshold

            if is_high_volume and is_high_margin:
                q_code = 'Q1'
                q_name = QUADRANTS_META['Q1']['name']
                recommendation = (
                    f"Core Star account ({row['gross_margin_pct']}% margin, "
                    f"${row['net_revenue']:,.2f} net revenue). Protect relationship, prioritize fulfillment, "
                    "and offer strategic partnership pricing locks."
                )
            elif is_high_volume and not is_high_margin:
                q_code = 'Q2'
                q_name = QUADRANTS_META['Q2']['name']
                recommendation = (
                    f"Volume Risk account with {row['gross_margin_pct']}% margin on ${row['net_revenue']:,.2f} revenue. "
                    "Renegotiate contract pricing, curb non-standard discounts, and optimize delivery route freight."
                )
            elif not is_high_volume and is_high_margin:
                q_code = 'Q3'
                q_name = QUADRANTS_META['Q3']['name']
                recommendation = (
                    f"High Potential account ({row['gross_margin_pct']}% margin). "
                    "Assign dedicated sales rep outreach to expand order frequency and cross-sell high-margin SKU lines."
                )
            else:  # not is_high_volume and not is_high_margin
                q_code = 'Q4'
                q_name = QUADRANTS_META['Q4']['name']
                recommendation = (
                    f"Unprofitable/Drain account ({row['gross_margin_pct']}% margin). "
                    "Enforce minimum order quantities (MOQ), pass through full delivery freight costs, and eliminate discretionary discounting."
                )

            item = CustomerProfitabilityItem(
                customer_id=row['customer_id'],
                customer_code=row['customer_code'],
                customer_name=row['customer_name'],
                customer_group=row['customer_group'],
                sales_rep_id=row['sales_rep_id'],
                sales_rep_name=row['sales_rep_name'],
                order_count=row['order_count'],
                gross_sales=row['gross_sales'],
                discount_amount=row['discount_amount'],
                net_revenue=row['net_revenue'],
                cogs=row['cogs'],
                freight_cost=row['freight_cost'],
                gross_profit=row['gross_profit'],
                gross_margin_pct=row['gross_margin_pct'],
                average_order_value=row['average_order_value'],
                quadrant=q_name,
                quadrant_code=q_code,
                recommendation=recommendation,
            )
            all_classified_customers.append(item)

        # Compute summary metrics for each quadrant across all customers
        total_cohort_revenue = sum(c.net_revenue for c in all_classified_customers)
        total_cohort_profit = sum(c.gross_profit for c in all_classified_customers)

        quadrant_summaries: List[QuadrantSummaryItem] = []
        for q_code in ['Q1', 'Q2', 'Q3', 'Q4']:
            meta = QUADRANTS_META[q_code]
            q_members = [c for c in all_classified_customers if c.quadrant_code == q_code]
            q_count = len(q_members)
            q_rev = round(sum(c.net_revenue for c in q_members), 2)
            q_profit = round(sum(c.gross_profit for c in q_members), 2)
            q_avg_margin = round((q_profit / q_rev * 100.0), 2) if q_rev > 0 else 0.0
            q_rev_share = round((q_rev / total_cohort_revenue * 100.0), 2) if total_cohort_revenue > 0 else 0.0
            q_profit_share = round((q_profit / total_cohort_profit * 100.0), 2) if total_cohort_profit > 0 else 0.0

            quadrant_summaries.append(
                QuadrantSummaryItem(
                    quadrant=meta['name'],
                    quadrant_code=meta['code'],
                    description=meta['description'],
                    customer_count=q_count,
                    total_net_revenue=q_rev,
                    total_gross_profit=q_profit,
                    avg_margin_pct=q_avg_margin,
                    revenue_share_pct=q_rev_share,
                    profit_share_pct=q_profit_share,
                )
            )

        # Filter the returned customer list if specific quadrant or margin filters were requested
        filtered_customers = all_classified_customers
        if flt.quadrant:
            q_filter = flt.quadrant.strip().lower()
            filtered_customers = [
                c for c in filtered_customers
                if c.quadrant_code.lower() == q_filter
                or c.quadrant.lower() == q_filter
                or q_filter in c.quadrant.lower()
            ]

        if flt.min_margin_pct is not None:
            filtered_customers = [c for c in filtered_customers if c.gross_margin_pct >= flt.min_margin_pct]
        if flt.max_margin_pct is not None:
            filtered_customers = [c for c in filtered_customers if c.gross_margin_pct <= flt.max_margin_pct]

        return CustomerProfitabilityResponse(
            period=flt.period,
            date_from=start_date,
            date_to=end_date,
            total_customers=len(filtered_customers),
            revenue_median_threshold=volume_threshold,
            margin_threshold_pct=effective_margin_threshold,
            quadrants=quadrant_summaries,
            customers=filtered_customers,
        )

    def get_top_profitable_customers(
        self,
        limit: int = 10,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> List[CustomerProfitabilityItem]:
        """
        Returns top customers ranked by realized gross profit $.
        """
        resp = self.get_customer_profitability_matrix(filters=filters, conn=conn)
        sorted_customers = sorted(resp.customers, key=lambda c: c.gross_profit, reverse=True)
        return sorted_customers[:limit]

    def get_unprofitable_customers(
        self,
        limit: int = 10,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> List[CustomerProfitabilityItem]:
        """
        Returns lowest margin or negative gross profit customer accounts requiring intervention.
        """
        resp = self.get_customer_profitability_matrix(filters=filters, conn=conn)
        sorted_customers = sorted(resp.customers, key=lambda c: (c.gross_margin_pct, c.gross_profit))
        return sorted_customers[:limit]

    def get_customer_details(
        self,
        customer_id: int,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Retrieves detailed profitability breakdown and top purchased products for a specific customer.
        """
        flt, start_date, end_date = self._normalize_filter(filters)
        flt.customer_id = customer_id

        matrix_resp = self.get_customer_profitability_matrix(filters=flt, conn=conn)
        customer_item = next((c for c in matrix_resp.customers if c.customer_id == customer_id), None)

        top_products = self.repo.get_customer_top_products_data(
            customer_id=customer_id,
            date_from=start_date,
            date_to=end_date,
            limit=10,
            conn=conn,
        )

        return {
            'customer': customer_item,
            'top_products': top_products,
            'quadrant_strategy': QUADRANTS_META.get(customer_item.quadrant_code, {}) if customer_item else {},
        }

    def get_quadrant_playbook(self, quadrant_code: str) -> Dict[str, Any]:
        """
        Returns strategic optimization playbooks and guidelines for a given quadrant code.
        """
        code = (quadrant_code or 'Q1').upper()
        return QUADRANTS_META.get(code, QUADRANTS_META['Q1'])


# Default singleton instance
customer_profitability_service = CustomerProfitabilityService()
