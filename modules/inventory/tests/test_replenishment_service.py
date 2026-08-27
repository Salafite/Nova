"""
Nova ERP — Inter-Branch Replenishment Service Unit Tests
Comprehensive unit tests covering:
- Deficit detection against reorder points and safety stock thresholds
- In-transit inventory accounting in effective stock calculations
- Priority level assignments (Critical, High, Normal, Low)
- Optimal source warehouse matching (Central Hubs, Regional DCs, surplus stock)
- Filter options (by destination warehouse, product, category, priority, min_deficit)
- One-click multi-branch Stock Transfer order generation and grouping
- Network inventory health overview KPIs
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from modules.inventory.services.replenishment_service import ReplenishmentService
from modules.warehouse.models.stock_transfer import (
    ReplenishmentGenerateRequest,
    ReplenishmentGenerateItem,
)


class TestReplenishmentServiceSuggestions:
    def setup_method(self):
        self.stock_repo = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.transfer_service = MagicMock()
        self.stock_movement_service = MagicMock()

        self.service = ReplenishmentService(
            stock_repo=self.stock_repo,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            transfer_service=self.transfer_service,
            stock_movement_service=self.stock_movement_service,
        )

        # Standard test warehouses
        self.warehouses = [
            {'id': 1, 'name': 'Central Main Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False, 'is_active': True},
            {'id': 2, 'name': 'Regional DC East', 'warehouse_type': 'Regional DC', 'is_virtual': False, 'is_active': True},
            {'id': 3, 'name': 'Branch Store North', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
            {'id': 4, 'name': 'Branch Store South', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
            {'id': 99, 'name': 'In-Transit Virtual Location', 'warehouse_type': 'In-Transit Virtual', 'is_virtual': True, 'is_active': True},
        ]
        self.wh_repo.list.return_value = self.warehouses
        self.wh_repo.get.side_effect = lambda wid, **kwargs: next((w for w in self.warehouses if w['id'] == wid), None)

        # Standard test products
        self.products = [
            {'id': 101, 'name': 'Organic Milk 1L', 'sku': 'MLK-001', 'category': 'Dairy', 'is_active': True},
            {'id': 102, 'name': 'Cheddar Cheese 500g', 'sku': 'CHS-002', 'category': 'Dairy', 'is_active': True},
            {'id': 103, 'name': 'Sourdough Bread', 'sku': 'BRD-003', 'category': 'Bakery', 'is_active': True},
        ]
        self.product_repo.list.return_value = self.products
        self.product_repo.get.side_effect = lambda pid, **kwargs: next((p for p in self.products if p['id'] == pid), None)

    def test_critical_out_of_stock_deficit_detected(self):
        """Zero stock at branch warehouse with positive reorder point should trigger Critical priority."""
        self.stock_repo.list.return_value = [
            # Central hub has surplus stock
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 50.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Branch Store North has 0 stock, reorder level 40
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 40.0},
        ]

        result = self.service.get_replenishment_suggestions(warehouse_id=3)

        assert result['total_suggestions'] == 1
        assert result['critical_count'] == 1
        item = result['items'][0]
        assert item['product_id'] == 101
        assert item['product_code'] == 'MLK-001'
        assert item['destination_warehouse_id'] == 3
        assert item['destination_warehouse_name'] == 'Branch Store North'
        assert item['available_stock'] == 0.0
        assert item['reorder_point'] == 40.0
        assert item['safety_stock'] == 20.0
        assert item['priority'] == 'Critical'
        assert item['source_warehouse_id'] == 1
        assert item['source_warehouse_name'] == 'Central Main Hub'
        assert item['source_available_stock'] == 450.0  # 500 - 50
        # Target stock = 40 + 20 (safety) = 60, suggested = 60 - 0 = 60
        assert item['suggested_transfer_qty'] == 60.0

    def test_in_transit_inventory_reduces_replenishment_deficit(self):
        """In-transit shipments reduce effective deficit and prevent over-replenishment."""
        self.stock_repo.list.return_value = [
            # Central hub
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 300.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            # Branch Store North: on-hand 5, reserved 0, in-transit 30, reorder 40
            # Available = 5, In-transit = 30, Effective = 35 < Reorder (40)
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 5.0, 'reserved_qty': 0.0, 'in_transit_qty': 30.0, 'reorder_level': 40.0},
        ]

        result = self.service.get_replenishment_suggestions(warehouse_id=3)

        assert result['total_suggestions'] == 1
        item = result['items'][0]
        assert item['current_stock'] == 5.0
        assert item['in_transit_stock'] == 30.0
        assert item['available_stock'] == 5.0
        # Effective = 35. Target = 40 + 20 = 60. Suggested = 60 - 35 = 25.0
        assert item['suggested_transfer_qty'] == 25.0
        assert item['priority'] == 'Critical'  # available 5.0 < safety 20.0

    def test_sufficient_effective_stock_skips_suggestion(self):
        """When on-hand + in-transit stock satisfies reorder point, no suggestion is generated."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 300.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            # Branch Store North: on-hand 15, in-transit 30 (effective = 45 > reorder 40)
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 15.0, 'reserved_qty': 0.0, 'in_transit_qty': 30.0, 'reorder_level': 40.0},
        ]

        result = self.service.get_replenishment_suggestions(warehouse_id=3)

        assert result['total_suggestions'] == 0
        assert len(result['items']) == 0

    def test_virtual_warehouse_excluded_from_replenishment_destination(self):
        """Virtual locations (e.g. In-Transit virtual location) must not be evaluated as destinations."""
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_replenishment_suggestions(warehouse_id=99)
        assert exc_info.value.status_code == 400
        assert "virtual warehouse" in str(exc_info.value.detail).lower()

    def test_nonexistent_warehouse_raises_404(self):
        """Evaluating a non-existent warehouse raises HTTP 404."""
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_replenishment_suggestions(warehouse_id=999)
        assert exc_info.value.status_code == 404

    def test_filtering_by_category_and_product(self):
        """Filtering by category and product ID restricts suggestions accurately."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 30.0},
            {'id': 3, 'product_id': 102, 'warehouse_id': 1, 'qty': 200.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 20.0},
            {'id': 4, 'product_id': 102, 'warehouse_id': 3, 'qty': 2.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 25.0},
            {'id': 5, 'product_id': 103, 'warehouse_id': 1, 'qty': 100.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 10.0},
            {'id': 6, 'product_id': 103, 'warehouse_id': 3, 'qty': 1.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 20.0},
        ]

        # Filter by product_id
        self.product_repo.list.return_value = [self.products[0]]
        res_prod = self.service.get_replenishment_suggestions(product_id=101)
        assert res_prod['total_suggestions'] == 1
        assert res_prod['items'][0]['product_id'] == 101

        # Filter by category
        self.product_repo.list.return_value = [self.products[0], self.products[1]]
        res_cat = self.service.get_replenishment_suggestions(category='Dairy')
        assert res_cat['total_suggestions'] == 2
        for itm in res_cat['items']:
            assert itm['product_id'] in (101, 102)

    def test_priority_filtering(self):
        """Suggestions can be filtered specifically by priority level."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            # Critical (available 0 < safety 15)
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 30.0},
            # High (effective 12 < reorder 25 * 0.5 = 12.5, available 12 >= safety 12.5 -> actually available 12 < safety 12.5 -> Critical)
            # Let's set reorder 20, safety 10, available 12, effective 12 (effective 12 < reorder 20 -> Normal)
            {'id': 3, 'product_id': 102, 'warehouse_id': 3, 'qty': 12.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 20.0},
        ]

        # Get only Normal priority
        res_norm = self.service.get_replenishment_suggestions(priority='Normal')
        assert all(it['priority'] == 'Normal' for it in res_norm['items'])

    def test_reorder_level_zero_or_negative_skipped(self):
        """Products with zero or negative reorder levels do not trigger replenishment suggestions."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Zero reorder level
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 0.0},
            # Negative reorder level
            {'id': 3, 'product_id': 102, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': -5.0},
        ]

        result = self.service.get_replenishment_suggestions(warehouse_id=3)
        assert result['total_suggestions'] == 0
        assert len(result['items']) == 0

    def test_min_deficit_threshold_filtering(self):
        """When min_deficit is specified, suggestions with smaller deficits are excluded."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Deficit = 40 - 35 = 5.0
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 35.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 40.0},
            # Deficit = 50 - 10 = 40.0
            {'id': 3, 'product_id': 102, 'warehouse_id': 3, 'qty': 10.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
        ]

        # Filter with min_deficit = 10.0 -> item 101 (deficit 5) excluded, item 102 (deficit 40) included
        result = self.service.get_replenishment_suggestions(warehouse_id=3, min_deficit=10.0)
        assert result['total_suggestions'] == 1
        assert result['items'][0]['product_id'] == 102

    def test_custom_safety_stock_and_target_coverage_tuning(self):
        """Custom safety_stock_ratio and target_coverage_multiplier alter calculations accurately."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Reorder level 100, available 60, in-transit 0 -> effective 60
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 60.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
        ]

        # Custom: safety_ratio = 0.8 (safety = 80), target_coverage = 2.0 (target = max(100+80, 100*2) = 200)
        # Suggested transfer = 200 - 60 = 140
        result = self.service.get_replenishment_suggestions(
            warehouse_id=3,
            safety_stock_ratio=0.8,
            target_coverage_multiplier=2.0,
        )

        assert result['total_suggestions'] == 1
        item = result['items'][0]
        assert item['safety_stock'] == 80.0
        assert item['suggested_transfer_qty'] == 140.0
        assert item['priority'] == 'Critical'  # available 60 < safety 80

    def test_inactive_products_and_warehouses_excluded(self):
        """Inactive products and inactive warehouses are excluded from replenishment calculations."""
        self.wh_repo.list.return_value = [
            {'id': 1, 'name': 'Central Main Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False, 'is_active': True},
            {'id': 3, 'name': 'Branch Store North', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': False},  # Inactive
        ]
        self.product_repo.list.return_value = [
            {'id': 101, 'name': 'Organic Milk 1L', 'sku': 'MLK-001', 'category': 'Dairy', 'is_active': False},  # Inactive
        ]

        result = self.service.get_replenishment_suggestions()
        assert result['total_suggestions'] == 0

    def test_suggestions_sorting_by_priority_and_deficit(self):
        """Suggestions are sorted in order: Critical -> High -> Normal -> Low, then by deficit descending."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Critical: available 0 < safety 25, deficit 100
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # Normal: effective 70 < reorder 100 (safety 25), deficit 30
            {'id': 3, 'product_id': 102, 'warehouse_id': 3, 'qty': 70.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            # High: effective 35 < reorder 100 * 0.5 (safety 25), deficit 65 (available 35 >= safety 25)
            {'id': 4, 'product_id': 103, 'warehouse_id': 3, 'qty': 35.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
        ]
        self.product_repo.list.return_value = self.products

        result = self.service.get_replenishment_suggestions(warehouse_id=3, safety_stock_ratio=0.25)
        priorities = [it['priority'] for it in result['items']]
        assert priorities[0] == 'Critical'
        assert priorities[1] == 'High'
        assert priorities[2] == 'Normal'


class TestSourceWarehouseMatching:
    def setup_method(self):
        self.stock_repo = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.transfer_service = MagicMock()

        self.service = ReplenishmentService(
            stock_repo=self.stock_repo,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            transfer_service=self.transfer_service,
        )

        self.warehouses = [
            {'id': 1, 'name': 'Central Main Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False, 'is_active': True},
            {'id': 2, 'name': 'Regional DC East', 'warehouse_type': 'Regional DC', 'is_virtual': False, 'is_active': True},
            {'id': 3, 'name': 'Branch Store North', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
            {'id': 4, 'name': 'Branch Store South', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
        ]
        self.wh_repo.list.return_value = self.warehouses
        self.product_repo.list.return_value = [{'id': 101, 'name': 'Milk', 'sku': 'MLK-1', 'is_active': True}]

    def test_preferred_source_warehouse_selection(self):
        """When a valid preferred source warehouse is requested and has stock, it is prioritized."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 1000.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 300.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            {'id': 3, 'product_id': 101, 'warehouse_id': 3, 'qty': 5.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
        ]

        res = self.service.get_replenishment_suggestions(warehouse_id=3, source_warehouse_id=2)
        assert res['total_suggestions'] == 1
        item = res['items'][0]
        assert item['source_warehouse_id'] == 2
        assert item['source_warehouse_name'] == 'Regional DC East'
        assert item['source_available_stock'] == 300.0

    def test_central_hub_surplus_preferred_over_regional_dc(self):
        """Central Hubs with surplus above reorder level are matched first when no preferred source given."""
        self.stock_repo.list.return_value = [
            # Central Hub has 800 surplus (1000 - 200)
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 1000.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 200.0},
            # Regional DC East has 150 surplus (200 - 50)
            {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 200.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            # Branch Store North has shortage
            {'id': 3, 'product_id': 101, 'warehouse_id': 3, 'qty': 2.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 30.0},
        ]

        res = self.service.get_replenishment_suggestions(warehouse_id=3)
        assert res['total_suggestions'] == 1
        item = res['items'][0]
        assert item['source_warehouse_id'] == 1
        assert item['source_warehouse_name'] == 'Central Main Hub'
        assert item['source_available_stock'] == 1000.0

    def test_zero_network_stock_fallback_handling(self):
        """When no warehouse in the network has available stock, suggestion still generates with note and 0 source avail."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            {'id': 3, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 40.0},
        ]

        res = self.service.get_replenishment_suggestions(warehouse_id=3)
        assert res['total_suggestions'] == 1
        item = res['items'][0]
        assert item['source_available_stock'] == 0.0
        assert item['source_warehouse_id'] == 1  # Falls back to central hub


class TestOneClickTransferGeneration:
    def setup_method(self):
        self.stock_repo = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.transfer_service = MagicMock()

        self.service = ReplenishmentService(
            stock_repo=self.stock_repo,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            transfer_service=self.transfer_service,
        )

        self.warehouses = [
            {'id': 1, 'name': 'Central Main Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False, 'is_active': True},
            {'id': 2, 'name': 'Regional DC East', 'warehouse_type': 'Regional DC', 'is_virtual': False, 'is_active': True},
            {'id': 3, 'name': 'Branch Store North', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
            {'id': 4, 'name': 'Branch Store South', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
        ]
        self.wh_repo.list.return_value = self.warehouses
        self.product_repo.list.return_value = [
            {'id': 101, 'name': 'Organic Milk 1L', 'sku': 'MLK-001', 'is_active': True},
            {'id': 102, 'name': 'Cheddar Cheese 500g', 'sku': 'CHS-002', 'is_active': True},
        ]

    def test_generate_transfers_from_explicit_items_grouping(self):
        """Items for multiple destinations are grouped into separate transfer documents per (source, destination) pair."""
        # Setup mock transfer service creation
        transfer_counter = [101]

        def mock_create_transfer(data, **kwargs):
            tid = transfer_counter[0]
            transfer_counter[0] += 1
            return {
                'id': tid,
                'transfer_number': f'TRF-00{tid}',
                'source_warehouse_id': data['source_warehouse_id'],
                'destination_warehouse_id': data['destination_warehouse_id'],
                'status': 'Draft',
                'lines': data.get('lines', []),
            }

        self.transfer_service.create_transfer.side_effect = mock_create_transfer

        request_payload = {
            'notes': 'Weekly automated inter-branch replenishment',
            'carrier': 'Nova Logistics FastTrack',
            'items': [
                # Pair 1: Hub 1 -> Branch 3 (2 items)
                {'product_id': 101, 'source_warehouse_id': 1, 'destination_warehouse_id': 3, 'suggested_transfer_qty': 50.0},
                {'product_id': 102, 'source_warehouse_id': 1, 'destination_warehouse_id': 3, 'suggested_transfer_qty': 30.0},
                # Pair 2: Hub 1 -> Branch 4 (1 item)
                {'product_id': 101, 'source_warehouse_id': 1, 'destination_warehouse_id': 4, 'suggested_transfer_qty': 40.0},
            ]
        }

        result = self.service.generate_transfers(request_payload)

        assert result['transfers_created'] == 2
        assert len(result['transfer_ids']) == 2
        assert result['transfer_numbers'] == ['TRF-00101', 'TRF-00102']
        assert self.transfer_service.create_transfer.call_count == 2

        # Verify call arguments
        calls = self.transfer_service.create_transfer.call_args_list
        # Call 1: lines count = 2
        assert calls[0][0][0]['source_warehouse_id'] == 1
        assert calls[0][0][0]['destination_warehouse_id'] == 3
        assert len(calls[0][0][0]['lines']) == 2
        assert calls[0][0][0]['carrier'] == 'Nova Logistics FastTrack'

        # Call 2: lines count = 1
        assert calls[1][0][0]['source_warehouse_id'] == 1
        assert calls[1][0][0]['destination_warehouse_id'] == 4
        assert len(calls[1][0][0]['lines']) == 1

    def test_generate_transfers_auto_calculates_when_items_omitted(self):
        """When items is omitted, service auto-calculates recommendations and creates transfers."""
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 100.0},
            {'id': 2, 'product_id': 101, 'warehouse_id': 3, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 40.0},
        ]

        self.transfer_service.create_transfer.return_value = {
            'id': 105,
            'transfer_number': 'TRF-00105',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 3,
            'status': 'Draft',
        }

        request_payload = {
            'destination_warehouse_id': 3,
            'notes': 'Auto restock for branch 3',
        }

        result = self.service.generate_transfers(request_payload)

        assert result['transfers_created'] == 1
        assert result['transfer_ids'] == [105]
        assert result['transfer_numbers'] == ['TRF-00105']

    def test_generate_transfers_empty_skips_cleanly(self):
        """When no items or deficits exist, returns 0 transfers created."""
        self.stock_repo.list.return_value = []
        result = self.service.generate_transfers({'items': []})
        assert result['transfers_created'] == 0
        assert result['transfer_ids'] == []
        assert result['transfers'] == []

    def test_generate_transfers_skips_invalid_identical_source_dest(self):
        """Items where source and destination warehouse are identical are safely ignored."""
        self.transfer_service.create_transfer.return_value = {'id': 1, 'transfer_number': 'TRF-00001'}

        payload = {
            'items': [
                {'product_id': 101, 'source_warehouse_id': 1, 'destination_warehouse_id': 1, 'suggested_transfer_qty': 20.0},
            ]
        }
        result = self.service.generate_transfers(payload)
        assert result['transfers_created'] == 0
        assert self.transfer_service.create_transfer.call_count == 0

    def test_generate_transfers_with_pydantic_schema_object(self):
        """Passing ReplenishmentGenerateRequest Pydantic object works seamlessly."""
        self.transfer_service.create_transfer.return_value = {
            'id': 201,
            'transfer_number': 'TRF-00201',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 3,
            'status': 'Draft',
            'lines': [{'product_id': 101, 'qty_requested': 25.0}],
        }

        req = ReplenishmentGenerateRequest(
            source_warehouse_id=1,
            destination_warehouse_id=3,
            carrier="Nova Fleet Express",
            notes="Pydantic schema test transfer",
            items=[
                ReplenishmentGenerateItem(
                    product_id=101,
                    source_warehouse_id=1,
                    destination_warehouse_id=3,
                    suggested_transfer_qty=25.0,
                )
            ],
        )

        result = self.service.generate_transfers(req)
        assert result['transfers_created'] == 1
        assert result['transfer_ids'] == [201]
        assert result['transfer_numbers'] == ['TRF-00201']
        assert self.transfer_service.create_transfer.call_count == 1

    def test_generate_transfers_zero_quantity_items_skipped(self):
        """Items with zero or negative suggested quantities are ignored during transfer generation."""
        payload = {
            'items': [
                {'product_id': 101, 'source_warehouse_id': 1, 'destination_warehouse_id': 3, 'suggested_transfer_qty': 0.0},
                {'product_id': 102, 'source_warehouse_id': 1, 'destination_warehouse_id': 3, 'suggested_transfer_qty': -10.0},
            ]
        }
        result = self.service.generate_transfers(payload)
        assert result['transfers_created'] == 0
        assert self.transfer_service.create_transfer.call_count == 0


class TestStockHealthSummary:
    def setup_method(self):
        self.stock_repo = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.transfer_service = MagicMock()

        self.service = ReplenishmentService(
            stock_repo=self.stock_repo,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            transfer_service=self.transfer_service,
        )

        self.wh_repo.list.return_value = [
            {'id': 1, 'name': 'Central Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False, 'is_active': True},
            {'id': 2, 'name': 'Branch North', 'warehouse_type': 'Retail Branch', 'is_virtual': False, 'is_active': True},
            {'id': 99, 'name': 'Virtual', 'warehouse_type': 'In-Transit Virtual', 'is_virtual': True, 'is_active': True},
        ]
        self.product_repo.list.return_value = [
            {'id': 101, 'name': 'Milk', 'sku': 'MLK', 'is_active': True},
            {'id': 102, 'name': 'Cheese', 'sku': 'CHS', 'is_active': True},
        ]
        self.stock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 500.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 50.0},
            # Deficit item
            {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 0.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0, 'reorder_level': 20.0},
        ]
        self.transfer_service.list_in_transit.return_value = [{'id': 50, 'status': 'In Transit'}]

    def test_get_stock_health_summary(self):
        summary = self.service.get_stock_health_summary()
        assert summary['total_products'] == 2
        assert summary['total_warehouses'] == 2  # Non-virtual
        assert summary['total_deficits'] == 1
        assert summary['critical_deficits'] == 1
        assert summary['active_in_transit_transfers'] == 1
        assert 'generated_at' in summary
