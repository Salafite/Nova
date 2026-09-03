import math
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest

from modules.purchasing.services.demand_forecast_service import (
    DemandForecastService,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_SAFETY_MARGIN_DAYS,
    DEFAULT_TARGET_COVERAGE_DAYS,
)


class TestDemandForecastService:
    @pytest.fixture
    def service(self):
        with patch('modules.purchasing.services.demand_forecast_service.get_connection', side_effect=Exception('DB not connected')):
            svc = DemandForecastService()
            yield svc

    def test_calculate_sales_velocity_fallback_orders(self, service):
        ref_date = date(2026, 8, 20)
        # Mock valid and invalid sales orders
        mock_orders = [
            {'id': 1, 'order_date': '2026-08-10', 'status': 'Confirmed'},
            {'id': 2, 'order_date': '2026-08-01', 'status': 'Delivered'},
            {'id': 3, 'order_date': '2026-07-01', 'status': 'Confirmed'},  # Out of 30d window
            {'id': 4, 'order_date': '2026-08-15', 'status': 'Cancelled'},  # Cancelled
        ]
        mock_lines = [
            {'sales_order_id': 1, 'product_id': 101, 'qty': 30.0},
            {'sales_order_id': 2, 'product_id': 101, 'qty': 30.0},
            {'sales_order_id': 3, 'product_id': 101, 'qty': 100.0},
            {'sales_order_id': 4, 'product_id': 101, 'qty': 50.0},
            {'sales_order_id': 1, 'product_id': 102, 'qty': 15.0},
        ]

        with patch.object(service.sales_order_repo, 'list', return_value=mock_orders), \
             patch.object(service.sales_line_repo, 'list', return_value=mock_lines):
            velocities = service.calculate_sales_velocity(product_id=101, days=30, reference_date=ref_date)
            
            assert 101 in velocities
            assert velocities[101]['total_sold'] == 60.0
            assert velocities[101]['daily_velocity'] == 2.0  # 60 / 30

    def test_calculate_sales_velocity_zero_sales(self, service):
        ref_date = date(2026, 8, 20)
        with patch.object(service.sales_order_repo, 'list', return_value=[]), \
             patch.object(service.sales_line_repo, 'list', return_value=[]):
            velocities = service.calculate_sales_velocity(product_id=999, days=30, reference_date=ref_date)
            
            assert 999 in velocities
            assert velocities[999]['total_sold'] == 0.0
            assert velocities[999]['daily_velocity'] == 0.0

    def test_get_stock_levels_calculation(self, service):
        mock_stock = [
            {'product_id': 101, 'warehouse_id': 1, 'qty': 50.0, 'reserved_qty': 10.0, 'reorder_level': 20.0},
            {'product_id': 101, 'warehouse_id': 2, 'qty': 30.0, 'reserved_qty': 5.0, 'reorder_level': 10.0},
        ]
        with patch.object(service.stock_repo, 'list', return_value=mock_stock):
            stocks = service.get_stock_levels(product_id=101)
            
            assert 101 in stocks
            assert stocks[101]['current_stock'] == 80.0
            assert stocks[101]['reserved_qty'] == 15.0
            assert stocks[101]['available_stock'] == 65.0
            assert stocks[101]['reorder_level'] == 20.0

    def test_get_preferred_supplier_priority(self, service):
        mock_suppliers = [
            {'id': 1, 'product_id': 101, 'supplier_id': 10, 'is_preferred': False, 'unit_cost': 5.0, 'lead_time_days': 5, 'min_order_qty': 20},
            {'id': 2, 'product_id': 101, 'supplier_id': 20, 'is_preferred': True, 'unit_cost': 4.5, 'lead_time_days': 7, 'min_order_qty': 50},
        ]
        with patch.object(service.product_supplier_repo, 'list', return_value=mock_suppliers), \
             patch.object(service.supplier_repo, 'get', return_value={'id': 20, 'name': 'Preferred Supplier Corp'}):
            supplier = service.get_preferred_supplier(101)
            
            assert supplier is not None
            assert supplier['supplier_id'] == 20
            assert supplier['is_preferred'] is True
            assert supplier['min_order_qty'] == 50.0
            assert supplier['lead_time_days'] == 7

    def test_calculate_sku_forecast_critical_urgency_and_moq(self, service):
        ref_date = date(2026, 8, 20)
        product = {'id': 101, 'name': 'Organic Whole Milk', 'sku': 'MILK-001', 'cost_price': 3.0}

        # Daily velocity 10 units/day, available stock 20 units (2 days supply). Lead time is 5 days.
        with patch.object(service, 'calculate_sales_velocity', return_value={101: {'daily_velocity': 10.0, 'total_sold': 300.0, 'order_count': 15, 'days': 30}}), \
             patch.object(service, 'get_stock_levels', return_value={101: {'current_stock': 25.0, 'reserved_qty': 5.0, 'available_stock': 20.0, 'reorder_level': 50.0}}), \
             patch.object(service, 'get_preferred_supplier', return_value={'supplier_id': 5, 'supplier_name': 'Dairy Best', 'unit_cost': 2.5, 'lead_time_days': 5, 'min_order_qty': 500.0}):
            
            forecast = service.calculate_sku_forecast(product=product, reference_date=ref_date)

            assert forecast['needs_restock'] is True
            assert forecast['urgency'] == 'CRITICAL'  # 2 days of supply <= 5 days lead time
            assert forecast['days_of_inventory'] == 2.0
            assert forecast['projected_stockout_date'] == '2026-08-22'
            # Suggested qty must satisfy MOQ (500 units)
            assert forecast['suggested_order_qty'] >= 500.0
            assert forecast['estimated_cost'] == forecast['suggested_order_qty'] * 2.5
            assert "CRITICAL RESTOCK" in forecast['rationale']
            assert "Dairy Best" in forecast['rationale']

    def test_calculate_sku_forecast_healthy_no_restock(self, service):
        ref_date = date(2026, 8, 20)
        product = {'id': 102, 'name': 'Almond Flour', 'sku': 'FLOUR-002', 'cost_price': 10.0}

        # Velocity 1 unit/day, available stock 100 units (100 days supply). Reorder point is ~15 units.
        with patch.object(service, 'calculate_sales_velocity', return_value={102: {'daily_velocity': 1.0, 'total_sold': 30.0, 'order_count': 5, 'days': 30}}), \
             patch.object(service, 'get_stock_levels', return_value={102: {'current_stock': 100.0, 'reserved_qty': 0.0, 'available_stock': 100.0, 'reorder_level': 10.0}}), \
             patch.object(service, 'get_preferred_supplier', return_value={'supplier_id': 8, 'supplier_name': 'Grain Co', 'unit_cost': 8.0, 'lead_time_days': 7, 'min_order_qty': 20.0}):
            
            forecast = service.calculate_sku_forecast(product=product, reference_date=ref_date)

            assert forecast['needs_restock'] is False
            assert forecast['urgency'] == 'HEALTHY'
            assert forecast['suggested_order_qty'] == 0.0
            assert forecast['estimated_cost'] == 0.0
            assert "no restock needed" in forecast['rationale']

    def test_calculate_all_forecasts_sorting_and_filtering(self, service):
        ref_date = date(2026, 8, 20)
        products = [
            {'id': 1, 'name': 'Healthy Item', 'sku': 'H-01', 'is_active': True},
            {'id': 2, 'name': 'Critical Item', 'sku': 'C-02', 'is_active': True},
            {'id': 3, 'name': 'High Urgency Item', 'sku': 'HI-03', 'is_active': True},
            {'id': 4, 'name': 'Inactive Item', 'sku': 'IN-04', 'is_active': False},
        ]

        def mock_sku_forecast(product, **kwargs):
            p_id = product.get('id') if isinstance(product, dict) else product
            if p_id == 1:
                return {'product_id': 1, 'sku': 'H-01', 'urgency': 'HEALTHY', 'needs_restock': False, 'days_of_inventory': 50.0, 'velocity_30d': 1.0}
            elif p_id == 2:
                return {'product_id': 2, 'sku': 'C-02', 'urgency': 'CRITICAL', 'needs_restock': True, 'days_of_inventory': 1.0, 'velocity_30d': 10.0}
            elif p_id == 3:
                return {'product_id': 3, 'sku': 'HI-03', 'urgency': 'HIGH', 'needs_restock': True, 'days_of_inventory': 8.0, 'velocity_30d': 4.0}
            return {'product_id': p_id, 'urgency': 'HEALTHY', 'needs_restock': False}

        with patch.object(service.product_repo, 'list', return_value=products), \
             patch.object(service, 'calculate_sku_forecast', side_effect=mock_sku_forecast):
            
            # All active products
            all_res = service.calculate_all_forecasts(only_at_risk=False, reference_date=ref_date)
            assert len(all_res) == 3  # Inactive skipped
            assert all_res[0]['urgency'] == 'CRITICAL'
            assert all_res[1]['urgency'] == 'HIGH'
            assert all_res[2]['urgency'] == 'HEALTHY'

            # Only at risk products
            at_risk = service.calculate_all_forecasts(only_at_risk=True, reference_date=ref_date)
            assert len(at_risk) == 2
            assert at_risk[0]['sku'] == 'C-02'
            assert at_risk[1]['sku'] == 'HI-03'

    def test_get_stock_levels_with_sales_order_reservations(self, service):
        mock_stock = [
            {'product_id': 101, 'warehouse_id': 1, 'qty': 100.0, 'reserved_qty': 0.0, 'reorder_level': 30.0},
        ]
        mock_orders = [
            {'id': 10, 'warehouse_id': 1, 'status': 'Pending'},
            {'id': 11, 'warehouse_id': 1, 'status': 'Cancelled'},
        ]
        mock_lines = [
            {'sales_order_id': 10, 'product_id': 101, 'qty': 25.0},
            {'sales_order_id': 11, 'product_id': 101, 'qty': 50.0},  # Cancelled order should be ignored
        ]

        with patch.object(service.stock_repo, 'list', return_value=mock_stock), \
             patch.object(service.sales_order_repo, 'list', return_value=mock_orders), \
             patch.object(service.sales_line_repo, 'list', return_value=mock_lines):
            
            stocks = service.get_stock_levels(product_id=101)

            assert 101 in stocks
            assert stocks[101]['current_stock'] == 100.0
            assert stocks[101]['reserved_qty'] == 25.0
            assert stocks[101]['available_stock'] == 75.0

    def test_calculate_sku_forecast_with_sales_order_reservations_triggering_restock(self, service):
        ref_date = date(2026, 8, 20)
        product = {'id': 101, 'name': 'Butter', 'sku': 'BUTTER-001', 'cost_price': 4.0}

        # current_stock = 40, reserved_qty = 15 (due to SO reservation), net available_stock = 25. Reorder level = 30.
        with patch.object(service, 'calculate_sales_velocity', return_value={101: {'daily_velocity': 0.0, 'total_sold': 0.0, 'order_count': 0, 'days': 30}}), \
             patch.object(service, 'get_stock_levels', return_value={101: {'current_stock': 40.0, 'reserved_qty': 15.0, 'available_stock': 25.0, 'reorder_level': 30.0}}), \
             patch.object(service, 'get_preferred_supplier', return_value={'supplier_id': 3, 'supplier_name': 'Dairy Co', 'unit_cost': 3.5, 'lead_time_days': 5, 'min_order_qty': 10.0}):
            
            forecast = service.calculate_sku_forecast(product=product, reference_date=ref_date)

            assert forecast['current_stock'] == 40.0
            assert forecast['reserved_qty'] == 15.0
            assert forecast['available_stock'] == 25.0
            assert forecast['net_available_stock'] == 25.0
            assert forecast['reorder_level'] == 30.0
            # Since net available (25) <= reorder level (30), it triggers restock despite current stock (40) > reorder level (30)
            assert forecast['needs_restock'] is True

    def test_get_aggregated_supplier_draft_pos(self, service):
        ref_date = date(2026, 8, 20)
        mock_forecasts = [
            {
                'product_id': 101,
                'sku': 'MILK-001',
                'product_name': 'Whole Milk',
                'supplier_id': 2,
                'supplier_name': 'Dairy Farm Co',
                'needs_restock': True,
                'urgency': 'CRITICAL',
                'suggested_order_qty': 100.0,
                'unit_cost': 2.5,
                'estimated_cost': 250.0,
                'lead_time_days': 5,
                'min_order_qty': 50.0,
            },
            {
                'product_id': 102,
                'sku': 'CHEESE-001',
                'product_name': 'Cheddar Cheese',
                'supplier_id': 2,
                'supplier_name': 'Dairy Farm Co',
                'needs_restock': True,
                'urgency': 'HIGH',
                'suggested_order_qty': 40.0,
                'unit_cost': 5.0,
                'estimated_cost': 200.0,
                'lead_time_days': 7,
                'min_order_qty': 20.0,
            },
            {
                'product_id': 103,
                'sku': 'FLOUR-001',
                'product_name': 'Wheat Flour',
                'supplier_id': 5,
                'supplier_name': 'Grain Corp',
                'needs_restock': True,
                'urgency': 'MEDIUM',
                'suggested_order_qty': 50.0,
                'unit_cost': 10.0,
                'estimated_cost': 500.0,
                'lead_time_days': 3,
                'min_order_qty': 10.0,
            },
        ]

        with patch.object(service, 'calculate_all_forecasts', return_value=mock_forecasts):
            draft_pos = service.get_aggregated_supplier_draft_pos(reference_date=ref_date)

            assert len(draft_pos) == 2  # 2 distinct suppliers (Dairy Farm Co and Grain Corp)

            # Dairy Farm Co should be first because max_urgency is CRITICAL
            dairy_po = draft_pos[0]
            assert dairy_po['supplier_id'] == 2
            assert dairy_po['supplier_name'] == 'Dairy Farm Co'
            assert dairy_po['total_items'] == 2
            assert dairy_po['total_qty'] == 140.0
            assert dairy_po['total_estimated_cost'] == 450.0
            assert dairy_po['max_urgency'] == 'CRITICAL'
            assert dairy_po['lead_time_days'] == 7  # Max of 5 and 7
            assert dairy_po['expected_date'] == '2026-08-27'

            grain_po = draft_pos[1]
            assert grain_po['supplier_id'] == 5
            assert grain_po['supplier_name'] == 'Grain Corp'
            assert grain_po['total_items'] == 1
            assert grain_po['total_qty'] == 50.0
            assert grain_po['total_estimated_cost'] == 500.0
            assert grain_po['max_urgency'] == 'MEDIUM'
            assert grain_po['lead_time_days'] == 3
            assert grain_po['expected_date'] == '2026-08-23'

    def test_get_stock_levels_with_sales_order_reservations_warehouse_isolation(self, service):
        mock_stock = [
            {'product_id': 101, 'warehouse_id': 1, 'qty': 100.0, 'reserved_qty': 0.0, 'reorder_level': 30.0},
            {'product_id': 101, 'warehouse_id': 2, 'qty': 50.0, 'reserved_qty': 0.0, 'reorder_level': 10.0},
        ]
        mock_orders = [
            {'id': 10, 'warehouse_id': 1, 'status': 'Pending'},
            {'id': 20, 'warehouse_id': 2, 'status': 'Processing'},
        ]
        mock_lines = [
            {'sales_order_id': 10, 'product_id': 101, 'qty': 40.0},
            {'sales_order_id': 20, 'product_id': 101, 'qty': 10.0},
        ]

        with patch.object(service.stock_repo, 'list', side_effect=lambda filters=None, conn=None: [s for s in mock_stock if not filters or s.get('warehouse_id') == filters.get('warehouse_id')]), \
             patch.object(service.sales_order_repo, 'list', return_value=mock_orders), \
             patch.object(service.sales_line_repo, 'list', return_value=mock_lines):

            # Filtered by warehouse_id=1
            stocks_w1 = service.get_stock_levels(product_id=101, warehouse_id=1)
            assert 101 in stocks_w1
            assert stocks_w1[101]['current_stock'] == 100.0
            assert stocks_w1[101]['reserved_qty'] == 40.0
            assert stocks_w1[101]['available_stock'] == 60.0

    def test_calculate_sku_forecast_lead_time_demand_and_safety_buffer(self, service):
        ref_date = date(2026, 8, 20)
        product = {'id': 105, 'name': 'Coffee Beans 1kg', 'sku': 'COFFEE-001', 'cost_price': 15.0}

        # Daily velocity = 5 units/day, current stock = 50, reserved = 10 -> net available = 40.
        # Lead time = 10 days -> lead time demand = 50 units.
        # Safety margin = 7 days -> safety buffer = 35 units.
        # Calculated reorder point = 50 + 35 = 85 units.
        with patch.object(service, 'calculate_sales_velocity', return_value={105: {'daily_velocity': 5.0, 'total_sold': 150.0, 'order_count': 10, 'days': 30}}), \
             patch.object(service, 'get_stock_levels', return_value={105: {'current_stock': 50.0, 'reserved_qty': 10.0, 'available_stock': 40.0, 'reorder_level': 20.0}}), \
             patch.object(service, 'get_preferred_supplier', return_value={'supplier_id': 12, 'supplier_name': 'Roasters United', 'unit_cost': 12.0, 'lead_time_days': 10, 'min_order_qty': 100.0}):

            forecast = service.calculate_sku_forecast(
                product=product,
                safety_margin_days=7,
                target_coverage_days=30,
                reference_date=ref_date,
            )

            assert forecast['velocity_30d'] == 5.0
            assert forecast['available_stock'] == 40.0
            assert forecast['lead_time_days'] == 10
            assert forecast['reorder_point'] == 85.0  # max(20, 5*10 + 5*7) = 85.0
            assert forecast['needs_restock'] is True
            # Days of inventory = 40 / 5 = 8 days <= lead time (10 days) -> CRITICAL
            assert forecast['urgency'] == 'CRITICAL'
            assert forecast['min_order_qty'] == 100.0
            assert forecast['suggested_order_qty'] >= 100.0

    def test_get_aggregated_supplier_draft_pos_unassigned_supplier(self, service):
        ref_date = date(2026, 8, 20)
        mock_forecasts = [
            {
                'product_id': 201,
                'sku': 'NO-SUP-01',
                'product_name': 'Generic Item',
                'supplier_id': None,
                'supplier_name': None,
                'needs_restock': True,
                'urgency': 'HIGH',
                'suggested_order_qty': 25.0,
                'unit_cost': 10.0,
                'estimated_cost': 250.0,
                'lead_time_days': 7,
                'min_order_qty': 1.0,
            }
        ]

        with patch.object(service, 'calculate_all_forecasts', return_value=mock_forecasts):
            draft_pos = service.get_aggregated_supplier_draft_pos(reference_date=ref_date)
            assert len(draft_pos) == 1
            po = draft_pos[0]
            assert po['supplier_id'] is None
            assert po['supplier_name'] == 'Unassigned Supplier'
            assert po['total_items'] == 1
            assert po['total_qty'] == 25.0
            assert po['total_estimated_cost'] == 250.0

    def test_calculate_sku_forecast_zero_stock_critical(self, service):
        ref_date = date(2026, 8, 20)
        product = {'id': 301, 'name': 'Out of Stock Product', 'sku': 'OOS-001', 'cost_price': 8.0}

        with patch.object(service, 'calculate_sales_velocity', return_value={301: {'daily_velocity': 2.0, 'total_sold': 60.0, 'order_count': 6, 'days': 30}}), \
             patch.object(service, 'get_stock_levels', return_value={301: {'current_stock': 0.0, 'reserved_qty': 0.0, 'available_stock': 0.0, 'reorder_level': 10.0}}), \
             patch.object(service, 'get_preferred_supplier', return_value={'supplier_id': 4, 'supplier_name': 'Quick Supply', 'unit_cost': 7.5, 'lead_time_days': 3, 'min_order_qty': 10.0}):

            forecast = service.calculate_sku_forecast(product=product, reference_date=ref_date)

            assert forecast['available_stock'] == 0.0
            assert forecast['days_of_inventory'] == 0.0
            assert forecast['needs_restock'] is True
            assert forecast['urgency'] == 'CRITICAL'
            assert "0 units available" in forecast['rationale']




