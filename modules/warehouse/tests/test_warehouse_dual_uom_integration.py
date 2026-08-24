import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from modules.warehouse.services.pick_list_service import PickListService
from modules.warehouse.controllers import T0101I


class InMemoryRepo:
    """In-memory CRUD repository for deterministic integration testing."""
    def __init__(self, table_name, items=None):
        self.table_name = table_name
        self.items = {item['id']: dict(item) for item in (items or [])}
        self._next_id = max(self.items.keys(), default=0) + 1

    def get(self, id_val, conn=None, **kwargs):
        item = self.items.get(id_val)
        return dict(item) if item else None

    def list(self, filters=None, limit=1000, order_by=None, offset=0, conn=None, **kwargs):
        results = list(self.items.values())
        if filters:
            for k, v in filters.items():
                results = [r for r in results if r.get(k) == v]
        if order_by and isinstance(order_by, str):
            results.sort(key=lambda x: (x.get(order_by) is None, x.get(order_by)))
        return [dict(r) for r in results[offset:offset + limit]]

    def create(self, payload, conn=None, **kwargs):
        new_id = payload.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        record = dict(payload, id=new_id)
        self.items[new_id] = record
        return dict(record)

    def update(self, id_val, payload, conn=None, **kwargs):
        if id_val not in self.items:
            return None
        self.items[id_val].update(payload)
        return dict(self.items[id_val])

    def delete(self, id_val, conn=None, **kwargs):
        return self.items.pop(id_val, None) is not None


class TestWarehouseDualUOMIntegration:
    """Integration test suite for warehouse dual UOM picking and scale weighing."""

    def setup_method(self):
        # Master data: Products with dual UOM
        self.products = [
            {
                'id': 101,
                'name': 'Parmigiano Reggiano Wheel (40kg nom)',
                'sku': 'CHEESE-PARM-40',
                'is_catch_weight': True,
                'pricing_uom_id': 2,  # kg
                'nominal_weight': 40.0,
                'tolerance_pct': 5.0,
                'price': 600.0,  # $15/kg nominal
            },
            {
                'id': 102,
                'name': 'Artisan White Cheddar Block (20kg nom)',
                'sku': 'CHEESE-CHED-20',
                'is_catch_weight': True,
                'pricing_uom_id': 2,  # kg
                'nominal_weight': 20.0,
                'tolerance_pct': 10.0,
                'price': 240.0,  # $12/kg nominal
            },
            {
                'id': 103,
                'name': 'Extra Virgin Olive Oil 5L Tin',
                'sku': 'OIL-EVOO-5L',
                'is_catch_weight': False,
                'pricing_uom_id': None,
                'nominal_weight': None,
                'tolerance_pct': None,
                'price': 45.0,
            },
            {
                'id': 104,
                'name': 'Strict Zero Tolerance Prosciutto (10kg)',
                'sku': 'MEAT-PROSC-10',
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'nominal_weight': 10.0,
                'tolerance_pct': 0.0,  # Exact weight required
                'price': 250.0,
            },
        ]

        self.uoms = [
            {'id': 1, 'uom_code': 'CASE', 'name': 'Case / Box'},
            {'id': 2, 'uom_code': 'kg', 'name': 'Kilogram'},
            {'id': 3, 'uom_code': 'EA', 'name': 'Each'},
        ]

        self.sales_orders = [
            {
                'id': 5001,
                'order_number': 'SO-2026-001',
                'customer_id': 200,
                'warehouse_id': 1,
                'status': 'Pending',
                'subtotal': 1725.0,
                'tax': 0.0,
                'grand_total': 1725.0,
            }
        ]

        self.sales_lines = [
            {
                'id': 6001,
                'sales_order_id': 5001,
                'product_id': 101,
                'product_name': 'Parmigiano Reggiano Wheel (40kg nom)',
                'qty': 2.0,  # 2 wheels = 80kg nominal
                'unit_price': 600.0,
                'line_total': 1200.0,
                'line_number': 1,
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'unit_price_pricing_uom': 15.0,
                'nominal_weight': 80.0,
                'catch_weight_actual': None,
            },
            {
                'id': 6002,
                'sales_order_id': 5001,
                'product_id': 102,
                'product_name': 'Artisan White Cheddar Block (20kg nom)',
                'qty': 2.0,  # 2 blocks = 40kg nominal
                'unit_price': 240.0,
                'line_total': 480.0,
                'line_number': 2,
                'is_catch_weight': True,
                'pricing_uom_id': 2,
                'unit_price_pricing_uom': 12.0,
                'nominal_weight': 40.0,
                'catch_weight_actual': None,
            },
            {
                'id': 6003,
                'sales_order_id': 5001,
                'product_id': 103,
                'product_name': 'Extra Virgin Olive Oil 5L Tin',
                'qty': 1.0,
                'unit_price': 45.0,
                'line_total': 45.0,
                'line_number': 3,
                'is_catch_weight': False,
                'nominal_weight': None,
                'catch_weight_actual': None,
            },
        ]

        self.product_repo = InMemoryRepo('T0003', self.products)
        self.uom_repo = InMemoryRepo('T0007', self.uoms)
        self.order_repo = InMemoryRepo('T0012', self.sales_orders)
        self.line_repo = InMemoryRepo('T0013', self.sales_lines)
        self.pl_repo = InMemoryRepo('T0101', [])
        self.pli_repo = InMemoryRepo('T0102', [])

        self.batch_service = MagicMock()
        self.batch_service.allocate_fefo_lots.return_value = []

        self.service = PickListService(
            repo=self.pl_repo,
            pli_repo=self.pli_repo,
            order_repo=self.order_repo,
            line_repo=self.line_repo,
            product_repo=self.product_repo,
            uom_repo=self.uom_repo,
            batch_service=self.batch_service,
        )

    def test_full_pick_list_creation_from_dual_uom_order(self):
        """Test pick list generation propagates dual UOM parameters correctly to items."""
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-2026-001'):
            pkl = self.service.create_from_order(sales_order_id=5001, warehouse_id=1)

        assert pkl is not None
        assert pkl['sales_order_id'] == 5001
        assert pkl['warehouse_id'] == 1

        items = self.pli_repo.list(filters={'pick_list_id': pkl['id']})
        assert len(items) == 3

        # Item 1: Parmigiano (2 cases @ 40kg = 80kg nominal, 5% tol)
        it1 = next(i for i in items if i['product_id'] == 101)
        assert it1['qty_ordered'] == 2.0
        assert it1['nominal_weight'] == 80.0
        assert it1['tolerance_pct'] == 5.0
        assert it1['catch_weight_uom'] == 'kg'
        assert it1['tolerance_status'] == 'Not Applicable'
        assert it1['supervisor_approved'] is False

        # Item 2: Cheddar (2 cases @ 20kg = 40kg nominal, 10% tol)
        it2 = next(i for i in items if i['product_id'] == 102)
        assert it2['qty_ordered'] == 2.0
        assert it2['nominal_weight'] == 40.0
        assert it2['tolerance_pct'] == 10.0
        assert it2['catch_weight_uom'] == 'kg'

        # Item 3: Olive Oil (standard item, no catch weight)
        it3 = next(i for i in items if i['product_id'] == 103)
        assert it3['qty_ordered'] == 1.0
        assert it3['nominal_weight'] is None
        assert it3['tolerance_pct'] is None
        assert it3['tolerance_status'] == 'Not Applicable'

    def test_scale_weighing_within_tolerance_all_items_completes_smoothly(self):
        """When all catch-weight items are weighed within tolerance limits, picking completes without discrepancy."""
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-2026-001'):
            pkl = self.service.create_from_order(sales_order_id=5001, warehouse_id=1)

        items = self.pli_repo.list(filters={'pick_list_id': pkl['id']})
        it1 = next(i for i in items if i['product_id'] == 101)
        it2 = next(i for i in items if i['product_id'] == 102)
        it3 = next(i for i in items if i['product_id'] == 103)

        # Pick Item 1: 78.4kg on 80.0kg nominal (-2.0% variance <= 5% tol)
        res1 = self.service.pick_item(
            item_id=it1['id'],
            qty_picked=2.0,
            catch_weight_actual=78.4,
            catch_weight_uom='kg',
        )
        assert res1['tolerance_status'] == 'Within Tolerance'
        assert res1['tolerance_variance_pct'] == -2.0

        # Pick Item 2: 42.8kg on 40.0kg nominal (+7.0% variance <= 10% tol)
        res2 = self.service.pick_item(
            item_id=it2['id'],
            qty_picked=2.0,
            catch_weight_actual=42.8,
            catch_weight_uom='kg',
        )
        assert res2['tolerance_status'] == 'Within Tolerance'
        assert res2['tolerance_variance_pct'] == 7.0

        # Pick Item 3: Standard item (no scale weight)
        res3 = self.service.pick_item(
            item_id=it3['id'],
            qty_picked=1.0,
        )
        assert res3['tolerance_status'] == 'Not Applicable'

        # Check discrepancies: should be empty
        discrepancies = self.service.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 0

        # Complete picking: should succeed
        res_complete = self.service.complete_picking(pkl['id'])
        assert res_complete['status'] == 'Completed'
        assert res_complete['has_discrepancies'] is False

        # Order status should now be 'Shipped'
        updated_order = self.order_repo.get(5001)
        assert updated_order['status'] == 'Shipped'

    def test_scale_weighing_out_of_tolerance_blocks_completion_until_approved(self):
        """When an item exceeds tolerance limits, picking completion is blocked until supervisor approves."""
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-2026-001'):
            pkl = self.service.create_from_order(sales_order_id=5001, warehouse_id=1)

        items = self.pli_repo.list(filters={'pick_list_id': pkl['id']})
        it1 = next(i for i in items if i['product_id'] == 101)
        it2 = next(i for i in items if i['product_id'] == 102)
        it3 = next(i for i in items if i['product_id'] == 103)

        # Item 1: 86.4kg on 80.0kg nominal (+8.0% variance > 5% tol) -> Out of Tolerance
        res1 = self.service.pick_item(
            item_id=it1['id'],
            qty_picked=2.0,
            catch_weight_actual=86.4,
            catch_weight_uom='kg',
        )
        assert res1['tolerance_status'] == 'Out of Tolerance'
        assert res1['tolerance_variance_pct'] == 8.0

        # Item 2: Within tolerance (40.0kg nominal, 40.0kg actual = 0.0%)
        self.service.pick_item(
            item_id=it2['id'],
            qty_picked=2.0,
            catch_weight_actual=40.0,
        )

        # Item 3: Standard item
        self.service.pick_item(
            item_id=it3['id'],
            qty_picked=1.0,
        )

        # Check discrepancies
        discrepancies = self.service.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 1
        assert discrepancies[0]['id'] == it1['id']
        assert discrepancies[0]['tolerance_status'] == 'Out of Tolerance'

        # Attempt to complete picking: must raise ValueError and not change order status
        with pytest.raises(ValueError, match="Unapproved catch-weight tolerance discrepancies exist"):
            self.service.complete_picking(pkl['id'])

        order_before_approval = self.order_repo.get(5001)
        assert order_before_approval['status'] == 'Pending'

        # Supervisor approves tolerance discrepancy
        approval_res = self.service.approve_tolerance(
            pick_list_id=pkl['id'],
            item_id=it1['id'],
            supervisor_id=99,
            supervisor_notes="Overweight Parmigiano wheel inspected and approved by QA Lead",
        )
        assert approval_res['has_discrepancies'] is False
        assert approval_res['discrepancy_count'] == 0

        # Verify item record has approval metadata
        updated_it1 = self.pli_repo.get(it1['id'])
        assert updated_it1['supervisor_approved'] is True
        assert updated_it1['supervisor_approved_by'] == 99
        assert updated_it1['tolerance_status'] == 'Approved'
        assert updated_it1['supervisor_notes'] == "Overweight Parmigiano wheel inspected and approved by QA Lead"

        # Complete picking now succeeds
        res_complete = self.service.complete_picking(pkl['id'])
        assert res_complete['status'] == 'Completed'
        assert self.order_repo.get(5001)['status'] == 'Shipped'

    def test_bulk_supervisor_approval_multiple_discrepancies(self):
        """Test approving multiple discrepancies in a single bulk operation."""
        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-2026-001'):
            pkl = self.service.create_from_order(sales_order_id=5001, warehouse_id=1)

        items = self.pli_repo.list(filters={'pick_list_id': pkl['id']})
        it1 = next(i for i in items if i['product_id'] == 101)
        it2 = next(i for i in items if i['product_id'] == 102)

        # Both items out of tolerance
        self.service.pick_item(item_id=it1['id'], qty_picked=2.0, catch_weight_actual=88.0)  # +10% > 5%
        self.service.pick_item(item_id=it2['id'], qty_picked=2.0, catch_weight_actual=34.0)  # -15% > 10%

        discrepancies = self.service.check_pick_list_discrepancies(pkl['id'])
        assert len(discrepancies) == 2

        # Bulk approve all discrepancies on pick list without specifying item IDs
        bulk_res = self.service.approve_tolerance(
            pick_list_id=pkl['id'],
            supervisor_id=42,
            supervisor_notes="Bulk approved by Warehouse Manager",
        )
        assert bulk_res['has_discrepancies'] is False
        assert bulk_res['discrepancy_count'] == 0

        for it_id in [it1['id'], it2['id']]:
            rec = self.pli_repo.get(it_id)
            assert rec['supervisor_approved'] is True
            assert rec['tolerance_status'] == 'Approved'
            assert rec['supervisor_approved_by'] == 42

    def test_exact_tolerance_boundaries(self):
        """Test exact tolerance threshold boundaries (+/- tol%)."""
        # Nominal 100kg, 5.0% tolerance
        # Exactly +5.0% (105.0kg) -> Within Tolerance
        var_pos, status_pos = self.service.evaluate_tolerance(100.0, 105.0, 5.0)
        assert var_pos == 5.0
        assert status_pos == "Within Tolerance"

        # Exactly -5.0% (95.0kg) -> Within Tolerance
        var_neg, status_neg = self.service.evaluate_tolerance(100.0, 95.0, 5.0)
        assert var_neg == -5.0
        assert status_neg == "Within Tolerance"

        # 105.01kg -> +5.01% -> Out of Tolerance
        var_over, status_over = self.service.evaluate_tolerance(100.0, 105.01, 5.0)
        assert var_over == 5.01
        assert status_over == "Out of Tolerance"

        # 94.99kg -> -5.01% -> Out of Tolerance
        var_under, status_under = self.service.evaluate_tolerance(100.0, 94.99, 5.0)
        assert var_under == -5.01
        assert status_under == "Out of Tolerance"

    def test_zero_tolerance_product(self):
        """Test strict zero tolerance product requires exact scale match."""
        # Product 104 has tolerance_pct = 0.0
        var1, status1 = self.service.evaluate_tolerance(10.0, 10.0, 0.0)
        assert var1 == 0.0
        assert status1 == "Within Tolerance"

        var2, status2 = self.service.evaluate_tolerance(10.0, 10.1, 0.0)
        assert var2 == 1.0
        assert status2 == "Out of Tolerance"
