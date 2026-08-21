import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from modules.purchasing.services.demand_forecast_service import (
    DemandForecastService,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_SAFETY_MARGIN_DAYS,
    DEFAULT_TARGET_COVERAGE_DAYS,
    DEFAULT_LEAD_TIME_DAYS,
    DEFAULT_MIN_ORDER_QTY,
)


@pytest.fixture
def forecast_service():
    return DemandForecastService()


class TestDemandForecastService:
    def test_sales_velocity_calculation_with_mock_cursor(self, forecast_service):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock SQL return: product 101 sold 60 units in 30 days
        mock_cursor.fetchall.return_value = [
            {'product_id': 101, 'total_sold': 60.0, 'order_count': 5}
        ]

        with patch('modules.purchasing.services.demand_forecast_service.get_connection', return_value=mock_conn), \
             patch('modules.purchasing.services.demand_forecast_service.release_connection'):
            res = forecast_service.calculate_sales_velocity(product_id=101, days=30)

            assert 101 in res
            assert res[101]['daily_velocity'] == 2.0  # 60 / 30 = 2.0
            assert res[101]['total_sold'] == 60.0
            assert res[101]['order_count'] == 5

    def test_sales_velocity_fallback_to_repo(self, forecast_service):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB table error")

        ref_date = date(2026, 8, 20)
        today_str = ref_date.isoformat()
        past_str = (ref_date - timedelta(days=10)).isoformat()
        old_str = (ref_date - timedelta(days=40)).isoformat()

        # Mock sales orders
        forecast_service.sales_order_repo.list = MagicMock(return_value=[
            {'id': 1, 'order_date': today_str, 'status': 'Confirmed'},
            {'id': 2, 'order_date': past_str, 'status': 'Delivered'},
            {'id': 3, 'order_date': today_str, 'status': 'Cancelled'},  # Should be excluded
            {'id': 4, 'order_date': old_str, 'status': 'Confirmed'},     # Outside 30-day window
        ])

        # Mock sales lines
        forecast_service.sales_line_repo.list = MagicMock(return_value=[
            {'id': 1, 'sales_order_id': 1, 'product_id': 10, 'qty': 15.0},
            {'id': 2, 'sales_order_id': 2, 'product_id': 10, 'qty': 15.0},
            {'id': 3, 'sales_order_id': 3, 'product_id': 10, 'qty': 50.0},
            {'id': 4, 'sales_order_id': 4, 'product_id': 10, 'qty': 100.0},
        ])

        with patch('modules.purchasing.services.demand_forecast_service.get_connection', return_value=mock_conn), \
             patch('modules.purchasing.services.demand_forecast_service.release_connection'):
            res = forecast_service.calculate_sales_velocity(product_id=10, days=30, reference_date=ref_date)
            assert 10 in res
            assert res[10]['total_sold'] == 30.0  # 15 + 15 from valid orders
            assert res[10]['daily_velocity'] == 1.0  # 30 / 30 = 1.0

    def test_stock_levels_aggregation(self, forecast_service):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'product_id': 5, 'total_qty': 100.0, 'total_reserved_qty': 20.0, 'reorder_level': 30.0}
        ]

        with patch('modules.purchasing.services.demand_forecast_service.get_connection', return_value=mock_conn), \
             patch('modules.purchasing.services.demand_forecast_service.release_connection'):
            stocks = forecast_service.get_stock_levels(product_id=5)

            assert 5 in stocks
            assert stocks[5]['current_stock'] == 100.0
            assert stocks[5]['reserved_qty'] == 20.0
            assert stocks[5]['available_stock'] == 80.0
            assert stocks[5]['reorder_level'] == 30.0

    def test_preferred_supplier_retrieval(self, forecast_service):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'mapping_id': 1,
            'product_id': 5,
            'supplier_id': 2,
            'supplier_name': 'Acme Organic Supplies',
            'supplier_sku': 'ACM-ORG-05',
            'unit_cost': 12.50,
            'lead_time_days': 5,
            'min_order_qty': 50.0,
            'is_preferred': True,
        }

        with patch('modules.purchasing.services.demand_forecast_service.get_connection', return_value=mock_conn), \
             patch('modules.purchasing.services.demand_forecast_service.release_connection'):
            supplier = forecast_service.get_preferred_supplier(5)

            assert supplier is not None
            assert supplier['supplier_name'] == 'Acme Organic Supplies'
            assert supplier['lead_time_days'] == 5
            assert supplier['min_order_qty'] == 50.0
            assert supplier['unit_cost'] == 12.50

    def test_sku_forecast_restock_needed_with_moq_enforcement(self, forecast_service):
        # Product selling 10 units/day, 20 available stock, lead time 5 days, MOQ 100
        ref_date = date(2026, 8, 22)
        product = {'id': 1, 'name': 'Organic Olive Oil 1L', 'sku': 'OIL-ORG-01', 'cost_price': 8.0}

        forecast_service.calculate_sales_velocity = MagicMock(return_value={
            1: {'daily_velocity': 10.0, 'total_sold': 300.0, 'order_count': 20, 'days': 30}
        })
        forecast_service.get_stock_levels = MagicMock(return_value={
            1: {'current_stock': 25.0, 'reserved_qty': 5.0, 'available_stock': 20.0, 'reorder_level': 50.0}
        })
        forecast_service.get_preferred_supplier = MagicMock(return_value={
            'supplier_id': 3,
            'supplier_name': 'Mediterranean Importers',
            'supplier_sku': 'MED-OIL-01',
            'unit_cost': 8.50,
            'lead_time_days': 5,
            'min_order_qty': 500.0,  # High MOQ to test enforcement
            'is_preferred': True,
        })

        result = forecast_service.calculate_sku_forecast(product=product, reference_date=ref_date)

        assert result['product_id'] == 1
        assert result['velocity_30d'] == 10.0
        assert result['available_stock'] == 20.0
        assert result['days_of_inventory'] == 2.0  # 20 available / 10 daily = 2.0 days
        assert result['projected_stockout_date'] == (ref_date + timedelta(days=2)).isoformat()
        assert result['lead_time_days'] == 5
        assert result['min_order_qty'] == 500.0
        assert result['needs_restock'] is True
        # days_of_inventory (2.0) <= lead_time (5) -> CRITICAL
        assert result['urgency'] == 'CRITICAL'
        # Target stock = 10 * (5 + 30) + 70 safety buffer = 420. Raw needed = 400. MOQ is 500 -> suggested = 500
        assert result['suggested_order_qty'] == 500.0
        assert result['estimated_cost'] == 500.0 * 8.50
        assert 'CRITICAL RESTOCK' in result['rationale']
        assert 'MOQ' in result['rationale']

    def test_sku_forecast_healthy_stock(self, forecast_service):
        # Product selling 2 units/day, 200 available stock, lead time 5 days
        product = {'id': 2, 'name': 'Basmati Rice 5kg', 'sku': 'RICE-BAS-05', 'cost_price': 15.0}

        forecast_service.calculate_sales_velocity = MagicMock(return_value={
            2: {'daily_velocity': 2.0, 'total_sold': 60.0, 'order_count': 10, 'days': 30}
        })
        forecast_service.get_stock_levels = MagicMock(return_value={
            2: {'current_stock': 200.0, 'reserved_qty': 0.0, 'available_stock': 200.0, 'reorder_level': 20.0}
        })
        forecast_service.get_preferred_supplier = MagicMock(return_value={
            'supplier_id': 1,
            'supplier_name': 'Grain Corp',
            'unit_cost': 14.0,
            'lead_time_days': 5,
            'min_order_qty': 10.0,
        })

        result = forecast_service.calculate_sku_forecast(product=product)

        assert result['needs_restock'] is False
        assert result['urgency'] == 'HEALTHY'
        assert result['suggested_order_qty'] == 0.0
        assert result['days_of_inventory'] == 100.0  # 200 / 2.0 = 100 days
        assert 'no restock needed' in result['rationale']

    def test_sku_forecast_zero_sales(self, forecast_service):
        # Product with zero sales over 30 days
        product = {'id': 3, 'name': 'Seasonal Jam', 'sku': 'JAM-SEA-01', 'cost_price': 4.0}

        forecast_service.calculate_sales_velocity = MagicMock(return_value={
            3: {'daily_velocity': 0.0, 'total_sold': 0.0, 'order_count': 0, 'days': 30}
        })
        forecast_service.get_stock_levels = MagicMock(return_value={
            3: {'current_stock': 50.0, 'reserved_qty': 0.0, 'available_stock': 50.0, 'reorder_level': 10.0}
        })
        forecast_service.get_preferred_supplier = MagicMock(return_value=None)

        result = forecast_service.calculate_sku_forecast(product=product)

        assert result['velocity_30d'] == 0.0
        assert result['days_of_inventory'] == 999.0
        assert result['projected_stockout_date'] is None
        assert result['needs_restock'] is False
        assert result['urgency'] == 'HEALTHY'
        assert result['suggested_order_qty'] == 0.0
        assert result['lead_time_days'] == DEFAULT_LEAD_TIME_DAYS
        assert result['min_order_qty'] == DEFAULT_MIN_ORDER_QTY

    def test_sku_forecast_zero_inventory_out_of_stock(self, forecast_service):
        # Product with 5 units/day velocity, 0 stock available
        ref_date = date(2026, 8, 22)
        product = {'id': 4, 'name': 'Fresh Milk 1L', 'sku': 'MILK-01', 'cost_price': 1.20}

        forecast_service.calculate_sales_velocity = MagicMock(return_value={
            4: {'daily_velocity': 5.0, 'total_sold': 150.0, 'order_count': 30, 'days': 30}
        })
        forecast_service.get_stock_levels = MagicMock(return_value={
            4: {'current_stock': 0.0, 'reserved_qty': 0.0, 'available_stock': 0.0, 'reorder_level': 20.0}
        })
        forecast_service.get_preferred_supplier = MagicMock(return_value={
            'supplier_id': 2,
            'supplier_name': 'Dairy Best',
            'unit_cost': 1.10,
            'lead_time_days': 2,
            'min_order_qty': 50.0,
        })

        result = forecast_service.calculate_sku_forecast(product=product, reference_date=ref_date)

        assert result['available_stock'] == 0.0
        assert result['days_of_inventory'] == 0.0
        assert result['projected_stockout_date'] == ref_date.isoformat()
        assert result['needs_restock'] is True
        assert result['urgency'] == 'CRITICAL'
        assert result['suggested_order_qty'] >= 50.0  # At least MOQ

    def test_calculate_all_forecasts_sorting(self, forecast_service):
        # 3 products: 1 healthy, 1 critical, 1 high urgency
        forecast_service.product_repo.list = MagicMock(return_value=[
            {'id': 1, 'name': 'Prod 1', 'sku': 'P1', 'is_active': True},
            {'id': 2, 'name': 'Prod 2', 'sku': 'P2', 'is_active': True},
            {'id': 3, 'name': 'Prod 3', 'sku': 'P3', 'is_active': True},
            {'id': 4, 'name': 'Inactive Prod', 'sku': 'P4', 'is_active': False},
        ])

        def mock_calc_sku(product, **kwargs):
            p_id = product['id']
            if p_id == 1:
                return {'product_id': 1, 'urgency': 'HEALTHY', 'needs_restock': False, 'days_of_inventory': 100.0, 'velocity_30d': 1.0}
            elif p_id == 2:
                return {'product_id': 2, 'urgency': 'CRITICAL', 'needs_restock': True, 'days_of_inventory': 1.5, 'velocity_30d': 10.0}
            elif p_id == 3:
                return {'product_id': 3, 'urgency': 'HIGH', 'needs_restock': True, 'days_of_inventory': 6.0, 'velocity_30d': 4.0}
            return {}

        forecast_service.calculate_sku_forecast = MagicMock(side_effect=mock_calc_sku)

        all_results = forecast_service.calculate_all_forecasts()
        assert len(all_results) == 3  # Inactive skipped
        # Sorting: CRITICAL (prod 2) first, HIGH (prod 3) second, HEALTHY (prod 1) third
        assert all_results[0]['product_id'] == 2
        assert all_results[1]['product_id'] == 3
        assert all_results[2]['product_id'] == 1

        at_risk_only = forecast_service.calculate_all_forecasts(only_at_risk=True)
        assert len(at_risk_only) == 2
        assert at_risk_only[0]['product_id'] == 2
        assert at_risk_only[1]['product_id'] == 3
