import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from modules.bi.models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    ExecutiveMarginSummary,
    CategoryMarginResponse,
    SkuMarginResponse,
    PeriodMarginTrendResponse,
    CustomerProfitabilityResponse,
    DeliveryFulfillmentSummaryResponse,
    DeliveryRouteMetricItem,
    WarehouseDeliveryMetricItem,
    CustomerDestinationMetricItem,
    DeliveryVarianceLineItem,
)
from modules.bi.services.executive_analytics_service import (
    ExecutiveAnalyticsService,
    resolve_date_range,
    resolve_prev_period,
)
from modules.bi.repositories.executive_analytics_repo import ExecutiveAnalyticsRepository
from modules.bi.services.customer_profitability_service import CustomerProfitabilityService
from modules.bi.repositories.customer_profitability_repo import CustomerProfitabilityRepository
from modules.bi.services.delivery_analytics_service import DeliveryAnalyticsService
from modules.bi.repositories.delivery_analytics_repo import DeliveryAnalyticsRepository



class TestExecutiveAnalyticsService:
    def setup_method(self):
        self.mock_repo = MagicMock(spec=ExecutiveAnalyticsRepository)
        self.service = ExecutiveAnalyticsService(repo=self.mock_repo)

    def test_date_range_resolution_monthly(self):
        start, end = resolve_date_range('Monthly')
        today = date.today()
        assert start == today.replace(day=1)
        assert end == today

    def test_date_range_resolution_ytd(self):
        start, end = resolve_date_range('YTD')
        today = date.today()
        assert start == date(today.year, 1, 1)
        assert end == today

    def test_date_range_resolution_custom(self):
        d1 = date(2026, 1, 15)
        d2 = date(2026, 2, 20)
        start, end = resolve_date_range('Custom', date_from=d1, date_to=d2)
        assert start == d1
        assert end == d2

    def test_prev_period_resolution(self):
        start = date(2026, 8, 1)
        end = date(2026, 8, 31)
        prev_start, prev_end = resolve_prev_period(start, end)
        assert prev_end == date(2026, 7, 31)
        assert prev_start == date(2026, 7, 1)

    def test_get_margin_summary_math(self):
        # Setup mock return from repo
        self.mock_repo.get_margin_summary_data.side_effect = [
            # Current period
            {
                'total_orders': 10,
                'total_customers': 5,
                'gross_sales': 10000.0,
                'discount_amount': 500.0,
                'net_revenue': 9500.0,
                'cogs': 6000.0,
                'freight_cost': 400.0,
                'gross_profit': 3100.0,
                'low_margin_order_count': 2,
            },
            # Previous period
            {
                'total_orders': 8,
                'total_customers': 4,
                'gross_sales': 8000.0,
                'discount_amount': 400.0,
                'net_revenue': 7600.0,
                'cogs': 5000.0,
                'freight_cost': 300.0,
                'gross_profit': 2300.0,
                'low_margin_order_count': 1,
            },
        ]

        summary = self.service.get_margin_summary(ExecutiveAnalyticsFilter(period='Monthly'))

        assert isinstance(summary, ExecutiveMarginSummary)
        assert summary.gross_sales == 10000.0
        assert summary.discount_amount == 500.0
        assert summary.net_revenue == 9500.0
        assert summary.cogs == 6000.0
        assert summary.freight_cost == 400.0
        assert summary.gross_profit == 3100.0
        # Margin % = (3100 / 9500) * 100 = 32.63%
        assert summary.gross_margin_pct == 32.63
        assert summary.total_orders == 10
        assert summary.total_customers == 5
        assert summary.average_order_value == 950.0
        assert summary.low_margin_order_count == 2
        assert summary.prev_period_gross_profit == 2300.0
        # Growth = ((3100 - 2300) / 2300) * 100 = 34.78%
        assert summary.gross_profit_growth_pct == 34.78
        # Prev margin % = (2300 / 7600) * 100 = 30.26%
        assert summary.prev_period_margin_pct == 30.26

    def test_get_category_margins_with_low_margin_alert(self):
        self.mock_repo.get_category_margins_data.return_value = [
            {
                'category_name': 'Dairy & Cheese',
                'units_sold': 100.0,
                'order_count': 8,
                'gross_sales': 5000.0,
                'discount_amount': 200.0,
                'net_revenue': 4800.0,
                'cogs': 3000.0,
                'freight_cost': 200.0,
                'gross_profit': 1600.0,
            },
            {
                'category_name': 'Fresh Produce',
                'units_sold': 50.0,
                'order_count': 5,
                'gross_sales': 2000.0,
                'discount_amount': 100.0,
                'net_revenue': 1900.0,
                'cogs': 1600.0,
                'freight_cost': 100.0,
                'gross_profit': 200.0,  # Margin % = 200 / 1900 = 10.53% (< 15% alert)
            },
            {
                'category_name': 'Frozen Goods',
                'units_sold': 20.0,
                'order_count': 2,
                'gross_sales': 1000.0,
                'discount_amount': 50.0,
                'net_revenue': 950.0,
                'cogs': 850.0,
                'freight_cost': 50.0,
                'gross_profit': 50.0,  # Margin % = 50 / 950 = 5.26% (< 10% critical)
            },
        ]

        resp = self.service.get_category_margins(ExecutiveAnalyticsFilter(period='Monthly'))

        assert isinstance(resp, CategoryMarginResponse)
        assert resp.total_categories == 3
        assert resp.low_margin_category_count == 2

        dairy = resp.items[0]
        assert dairy.category_name == 'Dairy & Cheese'
        assert dairy.gross_margin_pct == 33.33
        assert dairy.is_low_margin is False
        assert dairy.status == 'Healthy'

        produce = resp.items[1]
        assert produce.category_name == 'Fresh Produce'
        assert produce.gross_margin_pct == 10.53
        assert produce.is_low_margin is True
        assert produce.status == 'Warning'

        frozen = resp.items[2]
        assert frozen.category_name == 'Frozen Goods'
        assert frozen.gross_margin_pct == 5.26
        assert frozen.is_low_margin is True
        assert frozen.status == 'Critical'

    def test_get_sku_margins(self):
        self.mock_repo.get_sku_margins_data.return_value = (
            [
                {
                    'product_id': 101,
                    'sku_code': 'MILK-001',
                    'product_name': 'Whole Milk 1L',
                    'category_name': 'Dairy',
                    'brand_name': 'Almarai',
                    'units_sold': 500.0,
                    'gross_sales': 2500.0,
                    'discount_amount': 100.0,
                    'net_revenue': 2400.0,
                    'cogs': 1800.0,
                    'freight_cost': 100.0,
                    'gross_profit': 500.0,
                }
            ],
            1,
        )

        resp = self.service.get_sku_margins(ExecutiveAnalyticsFilter(period='Monthly'))

        assert isinstance(resp, SkuMarginResponse)
        assert resp.total_skus == 1
        item = resp.items[0]
        assert item.product_id == 101
        assert item.sku_code == 'MILK-001'
        assert item.avg_selling_price == 5.0  # 2500 / 500
        assert item.unit_cost == 3.6  # 1800 / 500
        assert item.gross_margin_pct == 20.83  # 500 / 2400 * 100
        assert item.is_low_margin is False

    def test_get_period_margin_trends(self):
        self.mock_repo.get_period_margin_trends_data.return_value = [
            {
                'bucket_start': date(2026, 7, 1),
                'order_count': 15,
                'gross_sales': 15000.0,
                'discount_amount': 500.0,
                'net_revenue': 14500.0,
                'cogs': 10000.0,
                'freight_cost': 500.0,
                'gross_profit': 4000.0,
            },
            {
                'bucket_start': date(2026, 8, 1),
                'order_count': 20,
                'gross_sales': 20000.0,
                'discount_amount': 800.0,
                'net_revenue': 19200.0,
                'cogs': 13000.0,
                'freight_cost': 600.0,
                'gross_profit': 5600.0,
            },
        ]

        resp = self.service.get_period_margin_trends(period_type='Monthly')

        assert isinstance(resp, PeriodMarginTrendResponse)
        assert len(resp.items) == 2
        assert resp.items[0].period_key == '2026-07'
        assert resp.items[0].gross_margin_pct == 27.59
        assert resp.items[1].period_key == '2026-08'
        assert resp.items[1].gross_margin_pct == 29.17

    def test_get_low_margin_alerts(self):
        self.mock_repo.get_category_margins_data.return_value = [
            {
                'category_name': 'Low Margin Cat',
                'units_sold': 10.0,
                'order_count': 1,
                'gross_sales': 100.0,
                'discount_amount': 0.0,
                'net_revenue': 100.0,
                'cogs': 90.0,
                'freight_cost': 0.0,
                'gross_profit': 10.0,  # 10%
            }
        ]
        self.mock_repo.get_sku_margins_data.return_value = (
            [
                {
                    'product_id': 1,
                    'sku_code': 'SKU-LOW',
                    'product_name': 'Low Margin SKU',
                    'category_name': 'General',
                    'brand_name': 'BrandX',
                    'units_sold': 10.0,
                    'gross_sales': 100.0,
                    'discount_amount': 0.0,
                    'net_revenue': 100.0,
                    'cogs': 92.0,
                    'freight_cost': 0.0,
                    'gross_profit': 8.0,  # 8%
                }
            ],
            1,
        )

        alerts = self.service.get_low_margin_alerts(threshold_pct=15.0)

        assert alerts['threshold_pct'] == 15.0
        assert alerts['low_margin_categories_count'] == 1
        assert alerts['low_margin_skus_count'] == 1
        assert alerts['categories'][0].category_name == 'Low Margin Cat'
        assert alerts['skus'][0].sku_code == 'SKU-LOW'


class TestCustomerProfitabilityService:
    def setup_method(self):
        self.mock_repo = MagicMock(spec=CustomerProfitabilityRepository)
        self.service = CustomerProfitabilityService(repo=self.mock_repo)

    def test_customer_profitability_matrix_classification(self):
        # 4 customers representing the 4 quadrants with median revenue = (10000 + 4000) / 2 = 7000
        # Q1: High Vol ($15,000), High Margin (30%)
        # Q2: High Vol ($10,000), Low Margin (10%)
        # Q3: Low Vol ($4,000), High Margin (25%)
        # Q4: Low Vol ($1,000), Low Margin (5%)
        self.mock_repo.get_customer_profitability_data.return_value = [
            {
                'customer_id': 1,
                'customer_code': 'CUST-0001',
                'customer_name': 'Grand Hotel & Resort',
                'customer_group': 'Hospitality',
                'sales_rep_id': 10,
                'sales_rep_name': 'Sarah Sales',
                'order_count': 5,
                'gross_sales': 16000.0,
                'discount_amount': 1000.0,
                'net_revenue': 15000.0,
                'cogs': 10000.0,
                'freight_cost': 500.0,
                'gross_profit': 4500.0,  # 30% margin
            },
            {
                'customer_id': 2,
                'customer_code': 'CUST-0002',
                'customer_name': 'Bulk Discount Mart',
                'customer_group': 'Wholesale',
                'sales_rep_id': 10,
                'sales_rep_name': 'Sarah Sales',
                'order_count': 8,
                'gross_sales': 11000.0,
                'discount_amount': 1000.0,
                'net_revenue': 10000.0,
                'cogs': 8500.0,
                'freight_cost': 500.0,
                'gross_profit': 1000.0,  # 10% margin
            },
            {
                'customer_id': 3,
                'customer_code': 'CUST-0003',
                'customer_name': 'Boutique Cafe',
                'customer_group': 'Restaurant',
                'sales_rep_id': 11,
                'sales_rep_name': 'Alex Agent',
                'order_count': 2,
                'gross_sales': 4200.0,
                'discount_amount': 200.0,
                'net_revenue': 4000.0,
                'cogs': 2800.0,
                'freight_cost': 200.0,
                'gross_profit': 1000.0,  # 25% margin
            },
            {
                'customer_id': 4,
                'customer_code': 'CUST-0004',
                'customer_name': 'Corner Kiosk',
                'customer_group': 'Retail',
                'sales_rep_id': 11,
                'sales_rep_name': 'Alex Agent',
                'order_count': 1,
                'gross_sales': 1050.0,
                'discount_amount': 50.0,
                'net_revenue': 1000.0,
                'cogs': 900.0,
                'freight_cost': 50.0,
                'gross_profit': 50.0,  # 5% margin
            },
        ]

        resp = self.service.get_customer_profitability_matrix(
            filters=ExecutiveAnalyticsFilter(period='Monthly'),
            margin_threshold_pct=15.0,
        )

        assert isinstance(resp, CustomerProfitabilityResponse)
        assert resp.total_customers == 4
        # Median threshold of [1000, 4000, 10000, 15000] = (4000 + 10000) / 2 = 7000
        assert resp.revenue_median_threshold == 7000.0
        assert resp.margin_threshold_pct == 15.0

        # Verify classifications
        c1 = next(c for c in resp.customers if c.customer_id == 1)
        assert c1.quadrant_code == 'Q1'
        assert c1.quadrant == 'Core Stars'
        assert c1.gross_margin_pct == 30.0
        assert c1.average_order_value == 3000.0  # 15000 / 5
        assert 'Core Star account' in c1.recommendation

        c2 = next(c for c in resp.customers if c.customer_id == 2)
        assert c2.quadrant_code == 'Q2'
        assert c2.quadrant == 'Volume Risks'
        assert c2.gross_margin_pct == 10.0
        assert c2.average_order_value == 1250.0  # 10000 / 8
        assert 'Volume Risk account' in c2.recommendation

        c3 = next(c for c in resp.customers if c.customer_id == 3)
        assert c3.quadrant_code == 'Q3'
        assert c3.quadrant == 'High Potential'
        assert c3.gross_margin_pct == 25.0
        assert c3.average_order_value == 2000.0  # 4000 / 2
        assert 'High Potential account' in c3.recommendation

        c4 = next(c for c in resp.customers if c.customer_id == 4)
        assert c4.quadrant_code == 'Q4'
        assert c4.quadrant == 'Unprofitable / Drain'
        assert c4.gross_margin_pct == 5.0
        assert c4.average_order_value == 1000.0  # 1000 / 1
        assert 'Unprofitable/Drain account' in c4.recommendation

        # Check quadrant summaries
        q1_summary = next(q for q in resp.quadrants if q.quadrant_code == 'Q1')
        assert q1_summary.customer_count == 1
        assert q1_summary.total_net_revenue == 15000.0
        assert q1_summary.total_gross_profit == 4500.0
        assert q1_summary.avg_margin_pct == 30.0

        q2_summary = next(q for q in resp.quadrants if q.quadrant_code == 'Q2')
        assert q2_summary.customer_count == 1
        assert q2_summary.total_net_revenue == 10000.0
        assert q2_summary.total_gross_profit == 1000.0

        q3_summary = next(q for q in resp.quadrants if q.quadrant_code == 'Q3')
        assert q3_summary.customer_count == 1
        assert q3_summary.total_net_revenue == 4000.0
        assert q3_summary.total_gross_profit == 1000.0

        q4_summary = next(q for q in resp.quadrants if q.quadrant_code == 'Q4')
        assert q4_summary.customer_count == 1
        assert q4_summary.total_net_revenue == 1000.0
        assert q4_summary.total_gross_profit == 50.0

    def test_customer_matrix_filtering_by_quadrant(self):
        self.mock_repo.get_customer_profitability_data.return_value = [
            {
                'customer_id': 1,
                'customer_code': 'CUST-0001',
                'customer_name': 'Customer 1',
                'order_count': 1,
                'gross_sales': 10000.0,
                'discount_amount': 0.0,
                'net_revenue': 10000.0,
                'cogs': 7000.0,
                'freight_cost': 0.0,
                'gross_profit': 3000.0,
            },
            {
                'customer_id': 2,
                'customer_code': 'CUST-0002',
                'customer_name': 'Customer 2',
                'order_count': 1,
                'gross_sales': 2000.0,
                'discount_amount': 0.0,
                'net_revenue': 2000.0,
                'cogs': 1900.0,
                'freight_cost': 0.0,
                'gross_profit': 100.0,
            },
        ]

        resp = self.service.get_customer_profitability_matrix(
            filters=ExecutiveAnalyticsFilter(quadrant='Q1', period='Monthly')
        )

        assert resp.total_customers == 1
        assert resp.customers[0].customer_id == 1
        assert resp.customers[0].quadrant_code == 'Q1'

    def test_top_and_unprofitable_customers_ranking(self):
        self.mock_repo.get_customer_profitability_data.return_value = [
            {
                'customer_id': 1,
                'customer_code': 'CUST-0001',
                'customer_name': 'Top Profit Cust',
                'order_count': 1,
                'gross_sales': 5000.0,
                'discount_amount': 0.0,
                'net_revenue': 5000.0,
                'cogs': 2000.0,
                'freight_cost': 0.0,
                'gross_profit': 3000.0,  # 60%
            },
            {
                'customer_id': 2,
                'customer_code': 'CUST-0002',
                'customer_name': 'Mid Profit Cust',
                'order_count': 1,
                'gross_sales': 4000.0,
                'discount_amount': 0.0,
                'net_revenue': 4000.0,
                'cogs': 3000.0,
                'freight_cost': 0.0,
                'gross_profit': 1000.0,  # 25%
            },
            {
                'customer_id': 3,
                'customer_code': 'CUST-0003',
                'customer_name': 'Drain Cust',
                'order_count': 1,
                'gross_sales': 1000.0,
                'discount_amount': 0.0,
                'net_revenue': 1000.0,
                'cogs': 980.0,
                'freight_cost': 0.0,
                'gross_profit': 20.0,  # 2%
            },
        ]

        top_custs = self.service.get_top_profitable_customers(limit=2)
        assert len(top_custs) == 2
        assert top_custs[0].customer_id == 1
        assert top_custs[0].gross_profit == 3000.0
        assert top_custs[1].customer_id == 2

        unprofitable = self.service.get_unprofitable_customers(limit=1)
        assert len(unprofitable) == 1
        assert unprofitable[0].customer_id == 3
        assert unprofitable[0].gross_margin_pct == 2.0

    def test_customer_details_with_top_products(self):
        self.mock_repo.get_customer_profitability_data.return_value = [
            {
                'customer_id': 1,
                'customer_code': 'CUST-0001',
                'customer_name': 'Grand Hotel',
                'customer_group': 'Hospitality',
                'order_count': 2,
                'gross_sales': 10000.0,
                'discount_amount': 500.0,
                'net_revenue': 9500.0,
                'cogs': 6000.0,
                'freight_cost': 200.0,
                'gross_profit': 3300.0,
            }
        ]
        self.mock_repo.get_customer_top_products_data.return_value = [
            {
                'product_id': 101,
                'sku_code': 'BEEF-001',
                'product_name': 'Ribeye Steak 5kg',
                'category_name': 'Meat & Poultry',
                'units_sold': 10.0,
                'gross_sales': 5000.0,
                'discount_amount': 250.0,
                'net_revenue': 4750.0,
                'cogs': 3000.0,
                'gross_profit': 1750.0,
            }
        ]

        details = self.service.get_customer_details(customer_id=1)

        assert details['customer'] is not None
        assert details['customer'].customer_id == 1
        assert details['customer'].customer_name == 'Grand Hotel'
        assert len(details['top_products']) == 1
        assert details['top_products'][0]['sku_code'] == 'BEEF-001'
        assert 'strategy' in details['quadrant_strategy']

    def test_quadrant_playbook(self):
        playbook_q1 = self.service.get_quadrant_playbook('Q1')
        assert playbook_q1['name'] == 'Core Stars'
        assert 'Protect and nurture' in playbook_q1['strategy']

        playbook_q2 = self.service.get_quadrant_playbook('Q2')
        assert playbook_q2['name'] == 'Volume Risks'

        playbook_q4 = self.service.get_quadrant_playbook('Q4')
        assert playbook_q4['name'] == 'Unprofitable / Drain'


class TestDeliveryAnalyticsService:
    def setup_method(self):
        self.mock_repo = MagicMock(spec=DeliveryAnalyticsRepository)
        self.service = DeliveryAnalyticsService(repo=self.mock_repo)

    def test_get_delivery_fulfillment_summary(self):
        self.mock_repo.get_route_fulfillment_data.return_value = [
            {
                'delivery_route': 'North Metro Route',
                'warehouse_id': 1,
                'warehouse_name': 'Main DC',
                'total_deliveries': 20,
                'completed_deliveries': 18,
                'on_time_deliveries': 16,
                'delayed_deliveries': 2,
                'total_freight_cost': 1200.0,
                'total_qty_ordered': 1000.0,
                'total_qty_shipped': 980.0,
            },
            {
                'delivery_route': 'South Coastal Route',
                'warehouse_id': 2,
                'warehouse_name': 'Coastal Hub',
                'total_deliveries': 10,
                'completed_deliveries': 10,
                'on_time_deliveries': 8,
                'delayed_deliveries': 2,
                'total_freight_cost': 800.0,
                'total_qty_ordered': 500.0,
                'total_qty_shipped': 500.0,
            },
        ]
        self.mock_repo.get_delivery_summary_kpis.return_value = {
            'total_routes': 2,
            'total_deliveries': 30,
            'completed_deliveries': 28,
            'on_time_deliveries': 24,
            'delayed_deliveries': 4,
            'total_freight_cost': 2000.0,
        }

        resp = self.service.get_delivery_fulfillment_summary(
            filters=ExecutiveAnalyticsFilter(period='Monthly')
        )

        assert isinstance(resp, DeliveryFulfillmentSummaryResponse)
        assert resp.total_routes == 2
        assert resp.total_deliveries == 30
        assert resp.total_freight_cost == 2000.0
        # Overall on time rate = 24 / 28 * 100 = 85.71%
        assert resp.overall_on_time_rate == 85.71
        # Overall completion rate = 28 / 30 * 100 = 93.33%
        assert resp.overall_completion_rate == 93.33
        # Avg freight per order = 2000 / 30 = 66.67
        assert resp.avg_freight_cost_per_order == 66.67

        assert len(resp.routes) == 2
        r1 = resp.routes[0]
        assert r1.delivery_route == 'North Metro Route'
        assert r1.warehouse_name == 'Main DC'
        # OTD rate = 16 / 18 * 100 = 88.89%
        assert r1.on_time_delivery_rate == 88.89
        # Route completion rate = 18 / 20 * 100 = 90.0%
        assert r1.route_completion_rate == 90.0
        # Avg freight = 1200 / 20 = 60.0
        assert r1.avg_freight_per_delivery == 60.0
        # Variance = (980 - 1000) / 1000 * 100 = -2.0%
        assert r1.fulfillment_variance_pct == -2.0

        r2 = resp.routes[1]
        assert r2.delivery_route == 'South Coastal Route'
        assert r2.on_time_delivery_rate == 80.0
        assert r2.route_completion_rate == 100.0
        assert r2.avg_freight_per_delivery == 80.0
        assert r2.fulfillment_variance_pct == 0.0

    def test_get_warehouse_efficiency(self):
        self.mock_repo.get_warehouse_delivery_data.return_value = [
            {
                'warehouse_id': 1,
                'warehouse_name': 'Central Depot',
                'location': 'Riyadh',
                'total_deliveries': 50,
                'completed_deliveries': 48,
                'on_time_deliveries': 46,
                'delayed_deliveries': 2,
                'total_freight_cost': 2500.0,
                'total_qty_shipped': 5000.0,
            }
        ]

        result = self.service.get_warehouse_efficiency()

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, WarehouseDeliveryMetricItem)
        assert item.warehouse_id == 1
        assert item.warehouse_name == 'Central Depot'
        assert item.on_time_delivery_rate == 95.83  # 46 / 48 * 100
        assert item.route_completion_rate == 96.0  # 48 / 50 * 100
        assert item.avg_freight_per_delivery == 50.0  # 2500 / 50
        assert item.total_qty_shipped == 5000.0

    def test_get_customer_destination_metrics(self):
        self.mock_repo.get_customer_destination_delivery_data.return_value = [
            {
                'customer_id': 10,
                'customer_code': 'CUST-0010',
                'customer_name': 'Gourmet Bistro',
                'delivery_route': 'Downtown Core',
                'total_deliveries': 12,
                'completed_deliveries': 12,
                'on_time_deliveries': 11,
                'total_freight_cost': 600.0,
                'total_qty_shipped': 350.0,
            }
        ]

        result = self.service.get_customer_destination_metrics()

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, CustomerDestinationMetricItem)
        assert item.customer_id == 10
        assert item.customer_name == 'Gourmet Bistro'
        assert item.delivery_route == 'Downtown Core'
        assert item.on_time_delivery_rate == 91.67  # 11 / 12 * 100
        assert item.avg_freight_per_delivery == 50.0  # 600 / 12

    def test_get_delivery_fulfillment_variances(self):
        self.mock_repo.get_delivery_variance_details.return_value = [
            {
                'delivery_id': 101,
                'delivery_number': 'DEL-101',
                'delivery_route': 'East Route',
                'product_id': 5,
                'product_name': 'Organic Butter 250g',
                'qty_ordered': 100.0,
                'qty_shipped': 80.0,
                'variance_qty': -20.0,
                'status': 'Delivered',
            }
        ]

        variances = self.service.get_delivery_fulfillment_variances()

        assert len(variances) == 1
        v = variances[0]
        assert isinstance(v, DeliveryVarianceLineItem)
        assert v.delivery_id == 101
        assert v.product_name == 'Organic Butter 250g'
        assert v.qty_ordered == 100.0
        assert v.qty_shipped == 80.0
        assert v.variance_qty == -20.0
        assert v.variance_pct == -20.0  # (-20 / 100) * 100

    def test_get_delivery_kpi_gauges(self):
        self.mock_repo.get_route_fulfillment_data.return_value = []
        self.mock_repo.get_delivery_summary_kpis.return_value = {
            'total_routes': 3,
            'total_deliveries': 100,
            'completed_deliveries': 98,
            'on_time_deliveries': 96,
            'delayed_deliveries': 2,
            'total_freight_cost': 4500.0,
        }

        gauges = self.service.get_delivery_kpi_gauges()

        assert gauges['total_deliveries'] == 100
        # OTD % = 96 / 98 * 100 = 97.96%
        assert gauges['overall_on_time_rate'] == 97.96
        assert gauges['otd_rating'] == 'Excellent'
        # Completion % = 98 / 100 * 100 = 98.0%
        assert gauges['overall_completion_rate'] == 98.0
        assert gauges['completion_rating'] == 'Optimal'
        assert gauges['total_freight_cost'] == 4500.0
        assert gauges['avg_freight_cost_per_order'] == 45.0

    def test_empty_delivery_data_handling(self):
        self.mock_repo.get_route_fulfillment_data.return_value = []
        self.mock_repo.get_delivery_summary_kpis.return_value = {}

        resp = self.service.get_delivery_fulfillment_summary()

        assert isinstance(resp, DeliveryFulfillmentSummaryResponse)
        assert resp.total_deliveries == 0
        assert resp.overall_on_time_rate == 0.0
        assert resp.overall_completion_rate == 0.0
        assert resp.total_freight_cost == 0.0
        assert resp.avg_freight_cost_per_order == 0.0
        assert len(resp.routes) == 0

