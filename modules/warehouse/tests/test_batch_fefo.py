import pytest
from unittest.mock import MagicMock, patch
import modules.core.controllers
from modules.warehouse.services.batch_number_service import BatchNumberService
from modules.warehouse.services.goods_receipt_service import GoodsReceiptService


class TestGoodsReceiptBatchCapture:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.service = GoodsReceiptService(self.mock_repo)
        self.service.stock_service = MagicMock()
        self.service.line_repo = MagicMock()
        self.service.po_repo = MagicMock()
        self.service.batch_repo = MagicMock()

    def test_goods_receipt_create_completed_registers_batch(self):
        self.mock_repo.create.return_value = {'id': 10, 'warehouse_id': 2, 'status': 'Completed'}
        self.mock_repo.get.return_value = {'id': 10, 'warehouse_id': 2, 'status': 'Completed'}
        self.service.line_repo.list.return_value = [
            {
                'id': 1, 'receipt_id': 10, 'product_id': 101, 'product_name': 'Organic Milk 1L',
                'batch_number': 'LOT-MILK-100', 'manufacturing_date': '2026-01-10', 'expiry_date': '2026-07-10',
                'qty_received': 50.0
            }
        ]
        self.service.batch_repo.list.return_value = []

        self.service.create({'status': 'Completed', 'warehouse_id': 2})

        self.service.batch_repo.create.assert_called_once_with({
            'product_id': 101,
            'batch_number': 'LOT-MILK-100',
            'manufacturing_date': '2026-01-10',
            'expiry_date': '2026-07-10',
            'quantity': 50.0,
            'warehouse_id': 2,
            'status': 'Available'
        })

    def test_goods_receipt_completed_updates_existing_batch(self):
        self.mock_repo.get.return_value = {'id': 10, 'warehouse_id': 2, 'status': 'Completed'}
        self.service.line_repo.list.return_value = [
            {
                'id': 1, 'receipt_id': 10, 'product_id': 101,
                'batch_number': 'LOT-MILK-100', 'manufacturing_date': '2026-01-10', 'expiry_date': '2026-07-10',
                'qty_received': 30.0
            }
        ]
        self.service.batch_repo.list.return_value = [
            {
                'id': 5, 'product_id': 101, 'batch_number': 'LOT-MILK-100', 'quantity': 20.0, 'status': 'Partially Used'
            }
        ]

        self.service._register_batches(10)

        self.service.batch_repo.update.assert_called_once_with(5, {
            'quantity': 50.0,
            'status': 'Available',
            'manufacturing_date': '2026-01-10',
            'expiry_date': '2026-07-10',
            'warehouse_id': 2
        })

    def test_goods_receipt_draft_does_not_register_batch(self):
        self.mock_repo.create.return_value = {'id': 10, 'status': 'Draft'}
        self.service.create({'status': 'Draft'})
        self.service.batch_repo.create.assert_not_called()
        self.service.batch_repo.update.assert_not_called()

    def test_goods_receipt_missing_expiry_date_validation(self):
        self.mock_repo.create.return_value = {'id': 10, 'warehouse_id': 2, 'status': 'Completed'}
        self.mock_repo.get.return_value = {'id': 10, 'warehouse_id': 2, 'status': 'Draft'}
        self.service.line_repo.list.return_value = [
            {
                'id': 1, 'receipt_id': 10, 'product_id': 101, 'product_name': 'Organic Milk 1L',
                'batch_number': 'LOT-NO-EXP', 'manufacturing_date': '2026-01-10', 'expiry_date': None,
                'qty_received': 50.0
            }
        ]
        with pytest.raises(ValueError) as exc_info:
            self.service.update(10, {'status': 'Completed'})
        assert "Expiration date is required for batch 'LOT-NO-EXP'" in str(exc_info.value)


class TestFEFOAllocation:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.service = BatchNumberService(self.mock_repo)


    def test_allocate_fefo_single_lot(self):
        self.mock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'batch_number': 'LOT-001', 'expiry_date': '2026-12-31',
             'quantity': 50.0, 'warehouse_id': 1, 'status': 'Available', 'manufacturing_date': '2026-01-01'}
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=20.0)
        assert len(allocations) == 1
        assert allocations[0]['batch_id'] == 1
        assert allocations[0]['batch_number'] == 'LOT-001'
        assert allocations[0]['quantity'] == 20.0
        assert allocations[0]['allocated_qty'] == 20.0
        assert allocations[0]['available_quantity'] == 50.0

    def test_allocate_fefo_multi_lot_ordering(self):
        # Earliest expiry first: LOT-B (2026-03-01) then LOT-A (2026-06-01) then LOT-C (2026-09-01)
        self.mock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'batch_number': 'LOT-A', 'expiry_date': '2026-06-01',
             'quantity': 10.0, 'warehouse_id': 1, 'status': 'Available'},
            {'id': 2, 'product_id': 101, 'batch_number': 'LOT-B', 'expiry_date': '2026-03-01',
             'quantity': 5.0, 'warehouse_id': 1, 'status': 'Available'},
            {'id': 3, 'product_id': 101, 'batch_number': 'LOT-C', 'expiry_date': '2026-09-01',
             'quantity': 20.0, 'warehouse_id': 1, 'status': 'Available'},
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=12.0)
        assert len(allocations) == 2
        # First allocation should be LOT-B (5 units)
        assert allocations[0]['batch_id'] == 2
        assert allocations[0]['batch_number'] == 'LOT-B'
        assert allocations[0]['quantity'] == 5.0
        # Second allocation should be LOT-A (7 units out of 10)
        assert allocations[1]['batch_id'] == 1
        assert allocations[1]['batch_number'] == 'LOT-A'
        assert allocations[1]['quantity'] == 7.0

    def test_allocate_fefo_null_expiry_last(self):
        # Batches with NULL expiry dates should sort after batches with valid expiry dates
        self.mock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'batch_number': 'LOT-NOEXP', 'expiry_date': None,
             'quantity': 10.0, 'warehouse_id': 1, 'status': 'Available'},
            {'id': 2, 'product_id': 101, 'batch_number': 'LOT-EXP', 'expiry_date': '2026-08-01',
             'quantity': 5.0, 'warehouse_id': 1, 'status': 'Available'},
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=8.0)
        assert len(allocations) == 2
        assert allocations[0]['batch_id'] == 2  # LOT-EXP first
        assert allocations[0]['quantity'] == 5.0
        assert allocations[1]['batch_id'] == 1  # LOT-NOEXP second
        assert allocations[1]['quantity'] == 3.0

    def test_allocate_fefo_same_expiry_id_asc(self):
        # Batches with same expiry date sort by id ASC
        self.mock_repo.list.return_value = [
            {'id': 5, 'product_id': 101, 'batch_number': 'LOT-5', 'expiry_date': '2026-05-01',
             'quantity': 10.0, 'warehouse_id': 1, 'status': 'Available'},
            {'id': 2, 'product_id': 101, 'batch_number': 'LOT-2', 'expiry_date': '2026-05-01',
             'quantity': 10.0, 'warehouse_id': 1, 'status': 'Available'},
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=15.0)
        assert len(allocations) == 2
        assert allocations[0]['batch_id'] == 2
        assert allocations[0]['quantity'] == 10.0
        assert allocations[1]['batch_id'] == 5
        assert allocations[1]['quantity'] == 5.0

    def test_allocate_fefo_filters_status_and_qty(self):
        self.mock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'batch_number': 'LOT-EXPIRED', 'expiry_date': '2025-01-01',
             'quantity': 10.0, 'warehouse_id': 1, 'status': 'Expired'},
            {'id': 2, 'product_id': 101, 'batch_number': 'LOT-DEPLETED', 'expiry_date': '2026-01-01',
             'quantity': 0.0, 'warehouse_id': 1, 'status': 'Available'},
            {'id': 3, 'product_id': 101, 'batch_number': 'LOT-GOOD', 'expiry_date': '2026-05-01',
             'quantity': 15.0, 'warehouse_id': 1, 'status': 'Available'},
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=10.0)
        assert len(allocations) == 1
        assert allocations[0]['batch_id'] == 3
        assert allocations[0]['quantity'] == 10.0

    def test_allocate_fefo_insufficient_stock(self):
        self.mock_repo.list.return_value = [
            {'id': 1, 'product_id': 101, 'batch_number': 'LOT-1', 'expiry_date': '2026-05-01',
             'quantity': 5.0, 'warehouse_id': 1, 'status': 'Available'},
        ]
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=10.0)
        assert len(allocations) == 1
        assert allocations[0]['quantity'] == 5.0

    def test_allocate_fefo_zero_or_negative_qty(self):
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=0)
        assert allocations == []
        allocations = self.service.allocate_fefo_lots(product_id=101, warehouse_id=1, qty_needed=-5)
        assert allocations == []


class TestPickListFEFOGeneration:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_batch_service = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_wh_repo = MagicMock()

        from modules.warehouse.services.pick_list_service import PickListService
        self.service = PickListService(
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            batch_service=self.mock_batch_service,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            wh_repo=self.mock_wh_repo
        )

        self.mock_order_repo.get.return_value = {
            'id': 10,
            'order_number': 'SO-00010',
            'warehouse_id': 1,
            'customer_id': 50
        }
        self.mock_pl_repo.list.return_value = []
        self.mock_pl_repo.create.return_value = {
            'id': 100,
            'pick_list_number': 'PL-00001',
            'sales_order_id': 10,
            'warehouse_id': 1,
            'status': 'Pending'
        }
        self.mock_pl_repo.get.return_value = {
            'id': 100,
            'pick_list_number': 'PL-00001',
            'sales_order_id': 10,
            'warehouse_id': 1,
            'status': 'Pending'
        }

    def test_create_pick_list_fefo_single_lot(self):
        self.mock_line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 10, 'product_id': 201, 'product_name': 'Fresh Milk 1L', 'qty': 10.0, 'line_number': 1}
        ]
        self.mock_batch_service.allocate_fefo_lots.return_value = [
            {'batch_id': 5, 'batch_number': 'LOT-MILK-001', 'expiry_date': '2026-06-01', 'quantity': 10.0}
        ]

        created_items = []
        def mock_pli_create(payload):
            created_items.append(payload)
            return dict(payload, id=len(created_items))
        self.mock_pli_repo.create.side_effect = mock_pli_create
        self.mock_pli_repo.list.return_value = created_items

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00001'):
            result = self.service.create_from_order(10, warehouse_id=1)

        self.mock_batch_service.allocate_fefo_lots.assert_called_once_with(
            product_id=201,
            warehouse_id=1,
            qty_needed=10.0
        )
        assert len(created_items) == 1
        assert created_items[0]['batch_id'] == 5
        assert created_items[0]['batch_number'] == 'LOT-MILK-001'
        assert created_items[0]['expiry_date'] == '2026-06-01'
        assert created_items[0]['qty_ordered'] == 10.0
        assert created_items[0]['line_number'] == 1

    def test_create_pick_list_fefo_split_lots(self):
        # Order requests 15 units of Greek Yogurt; FEFO allocates across 2 batches
        self.mock_line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 10, 'product_id': 202, 'product_name': 'Greek Yogurt 500g', 'qty': 15.0, 'line_number': 1}
        ]
        self.mock_batch_service.allocate_fefo_lots.return_value = [
            {'batch_id': 11, 'batch_number': 'LOT-YOG-A', 'expiry_date': '2026-04-01', 'quantity': 10.0},
            {'batch_id': 12, 'batch_number': 'LOT-YOG-B', 'expiry_date': '2026-05-01', 'quantity': 5.0}
        ]

        created_items = []
        def mock_pli_create(payload):
            created_items.append(payload)
            return dict(payload, id=len(created_items))
        self.mock_pli_repo.create.side_effect = mock_pli_create
        self.mock_pli_repo.list.return_value = created_items

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00001'):
            result = self.service.create_from_order(10, warehouse_id=1)

        assert len(created_items) == 2
        # First lot item
        assert created_items[0]['batch_id'] == 11
        assert created_items[0]['batch_number'] == 'LOT-YOG-A'
        assert created_items[0]['expiry_date'] == '2026-04-01'
        assert created_items[0]['qty_ordered'] == 10.0
        assert created_items[0]['line_number'] == 1

        # Second lot item (split)
        assert created_items[1]['batch_id'] == 12
        assert created_items[1]['batch_number'] == 'LOT-YOG-B'
        assert created_items[1]['expiry_date'] == '2026-05-01'
        assert created_items[1]['qty_ordered'] == 5.0
        assert created_items[1]['line_number'] == 2

    def test_create_pick_list_fefo_partial_lot_and_unallocated(self):
        # Order requests 20 units; only 12 available in lots, 8 unallocated
        self.mock_line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 10, 'product_id': 203, 'product_name': 'Organic Eggs 12pk', 'qty': 20.0, 'line_number': 1}
        ]
        self.mock_batch_service.allocate_fefo_lots.return_value = [
            {'batch_id': 21, 'batch_number': 'LOT-EGG-1', 'expiry_date': '2026-04-15', 'quantity': 12.0}
        ]

        created_items = []
        def mock_pli_create(payload):
            created_items.append(payload)
            return dict(payload, id=len(created_items))
        self.mock_pli_repo.create.side_effect = mock_pli_create
        self.mock_pli_repo.list.return_value = created_items

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00001'):
            result = self.service.create_from_order(10, warehouse_id=1)

        assert len(created_items) == 2
        # Allocated lot portion
        assert created_items[0]['batch_id'] == 21
        assert created_items[0]['batch_number'] == 'LOT-EGG-1'
        assert created_items[0]['qty_ordered'] == 12.0
        assert created_items[0]['line_number'] == 1

        # Unallocated remainder portion
        assert created_items[1]['batch_id'] is None
        assert created_items[1]['batch_number'] is None
        assert created_items[1]['qty_ordered'] == 8.0
        assert created_items[1]['line_number'] == 2

    def test_create_pick_list_no_batches_non_perishable(self):
        # Non-batch product or product with zero lot records
        self.mock_line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 10, 'product_id': 301, 'product_name': 'Steel Storage Rack', 'qty': 2.0, 'line_number': 1}
        ]
        self.mock_batch_service.allocate_fefo_lots.return_value = []

        created_items = []
        def mock_pli_create(payload):
            created_items.append(payload)
            return dict(payload, id=len(created_items))
        self.mock_pli_repo.create.side_effect = mock_pli_create
        self.mock_pli_repo.list.return_value = created_items

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00001'):
            result = self.service.create_from_order(10, warehouse_id=1)

        assert len(created_items) == 1
        assert created_items[0]['batch_id'] is None
        assert created_items[0]['batch_number'] is None
        assert created_items[0]['expiry_date'] is None
        assert created_items[0]['qty_ordered'] == 2.0
        assert created_items[0]['line_number'] == 1


class TestPickerLotSelectionAndDepletion:
    def setup_method(self):
        self.mock_pl_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_batch_service = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_line_repo = MagicMock()
        self.mock_wh_repo = MagicMock()

        from modules.warehouse.services.pick_list_service import PickListService
        self.service = PickListService(
            pl_repo=self.mock_pl_repo,
            pli_repo=self.mock_pli_repo,
            batch_service=self.mock_batch_service,
            order_repo=self.mock_order_repo,
            line_repo=self.mock_line_repo,
            wh_repo=self.mock_wh_repo
        )

    def test_get_available_batches_for_item(self):
        self.mock_pl_repo.get.return_value = {
            'id': 100,
            'warehouse_id': 1
        }
        self.mock_pli_repo.get.return_value = {
            'id': 5,
            'pick_list_id': 100,
            'product_id': 201
        }
        self.mock_batch_service.repo.list.return_value = [
            {'id': 1, 'product_id': 201, 'batch_number': 'LOT-A', 'expiry_date': '2026-10-01', 'quantity': 15.0, 'status': 'Available'},
            {'id': 2, 'product_id': 201, 'batch_number': 'LOT-B', 'expiry_date': '2026-05-01', 'quantity': 10.0, 'status': 'Available'},
            {'id': 3, 'product_id': 201, 'batch_number': 'LOT-C', 'expiry_date': '2026-03-01', 'quantity': 0.0, 'status': 'Available'},
            {'id': 4, 'product_id': 201, 'batch_number': 'LOT-D', 'expiry_date': '2026-01-01', 'quantity': 5.0, 'status': 'Expired'},
        ]

        result = self.service.get_available_batches_for_item(pick_list_id=100, item_id=5)
        # Should filter out quantity=0 and status=Expired, and sort by expiry_date ASC
        assert len(result) == 2
        assert result[0]['batch_number'] == 'LOT-B'
        assert result[1]['batch_number'] == 'LOT-A'

    def test_pick_item_with_batch_id_override(self):
        self.mock_pli_repo.get.return_value = {
            'id': 5,
            'pick_list_id': 100,
            'product_id': 201,
            'qty_ordered': 10.0,
            'batch_id': 1,
            'batch_number': 'LOT-A'
        }
        self.mock_batch_service.get.return_value = {
            'id': 2,
            'batch_number': 'LOT-B'
        }

        self.service.pick_item(item_id=5, qty_picked=10.0, picked_batch_id=2)

        self.mock_pli_repo.update.assert_called_once_with(5, {
            'qty_picked': 10.0,
            'picked_batch_id': 2,
            'picked_batch_number': 'LOT-B'
        })

    def test_pick_item_with_batch_number_barcode_override(self):
        self.mock_pli_repo.get.return_value = {
            'id': 5,
            'pick_list_id': 100,
            'product_id': 201,
            'qty_ordered': 10.0,
            'batch_id': 1,
            'batch_number': 'LOT-A'
        }
        self.mock_batch_service.repo.list.return_value = [
            {'id': 99, 'batch_number': 'LOT-BARCODE-99', 'product_id': 201}
        ]

        self.service.pick_item(item_id=5, qty_picked=10.0, picked_batch_number='LOT-BARCODE-99')

        self.mock_pli_repo.update.assert_called_once_with(5, {
            'qty_picked': 10.0,
            'picked_batch_number': 'LOT-BARCODE-99',
            'picked_batch_id': 99
        })

    def test_pick_item_rejects_item_from_another_pick_list(self):
        self.mock_pli_repo.get.return_value = {
            'id': 5,
            'pick_list_id': 100,
            'product_id': 201,
            'qty_ordered': 10.0
        }
        with pytest.raises(ValueError) as exc_info:
            self.service.pick_item(item_id=5, qty_picked=10.0, pick_list_id=999)
        assert 'not found in pick list 999' in str(exc_info.value)

    def test_pick_item_rejects_qty_above_ordered(self):
        self.mock_pli_repo.get.return_value = {
            'id': 5,
            'pick_list_id': 100,
            'product_id': 201,
            'qty_ordered': 10.0
        }
        with pytest.raises(ValueError) as exc_info:
            self.service.pick_item(item_id=5, qty_picked=12.0)
        assert 'exceeds ordered quantity' in str(exc_info.value)

    def test_complete_picking_deducts_stock(self):
        self.mock_pl_repo.get.return_value = {
            'id': 100,
            'sales_order_id': 10,
            'warehouse_id': 1,
            'status': 'In Progress'
        }
        self.mock_pli_repo.list.return_value = [
            {'id': 1, 'pick_list_id': 100, 'product_id': 201, 'qty_ordered': 10.0, 'qty_picked': 10.0, 'batch_id': 1},
            {'id': 2, 'pick_list_id': 100, 'product_id': 202, 'qty_ordered': 5.0, 'qty_picked': 5.0, 'batch_id': 2, 'picked_batch_id': 3}
        ]

        self.service.complete_picking(100)

        # Should deduct 10 from batch 1 (default suggested lot)
        assert any(c[0] == (1, -10.0) for c in self.mock_batch_service.adjustQuantity.call_args_list)
        # Should deduct 5 from batch 3 (overridden lot)
        assert any(c[0] == (3, -5.0) for c in self.mock_batch_service.adjustQuantity.call_args_list)

        assert self.mock_pl_repo.update.call_count == 1
        assert self.mock_pl_repo.update.call_args[0] == (100, {'status': 'Completed'})
        assert self.mock_order_repo.update.call_count == 1
        assert self.mock_order_repo.update.call_args[0] == (10, {'status': 'Shipped'})


class TestPickListControllerEndpoints:
    def test_get_available_batches_controller(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.get_available_batches_for_item.return_value = [
            {'id': 1, 'batch_number': 'LOT-1', 'quantity': 10.0, 'expiry_date': '2026-05-01'}
        ]
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.get_available_batches(id=100, item_id=5)
        assert result == [
            {'id': 1, 'batch_number': 'LOT-1', 'quantity': 10.0, 'expiry_date': '2026-05-01'}
        ]
        mock_svc.get_available_batches_for_item.assert_called_once_with(100, 5)

    def test_get_available_batches_controller_not_found(self, monkeypatch):
        from modules.warehouse.controllers import T0101I
        from fastapi import HTTPException

        mock_svc = MagicMock()
        mock_svc.get_available_batches_for_item.side_effect = ValueError('Pick list item not found')
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0101I.get_available_batches(id=100, item_id=999)
        assert exc_info.value.status_code == 404
        assert 'Pick list item not found' in exc_info.value.detail

    def test_pick_item_controller_with_custom_batch(self, monkeypatch):
        from modules.warehouse.controllers import T0101I

        mock_svc = MagicMock()
        mock_svc.pick_item.return_value = {
            'id': 5,
            'qty_picked': 8.0,
            'picked_batch_id': 2,
            'picked_batch_number': 'LOT-B'
        }
        monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

        result = T0101I.pick_item(id=100, item_id=5, body={
            'qty_picked': 8.0,
            'picked_batch_id': 2,
            'picked_batch_number': 'LOT-B'
        })
        assert result['picked_batch_id'] == 2
        mock_svc.pick_item.assert_called_once_with(
            item_id=5,
            qty_picked=8.0,
            pick_list_id=100,
            picked_batch_id=2,
            picked_batch_number='LOT-B'
        )


class TestBatchRecallReport:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.mock_grn_line_repo = MagicMock()
        self.mock_grn_repo = MagicMock()
        self.mock_po_repo = MagicMock()
        self.mock_supplier_repo = MagicMock()
        self.mock_pli_repo = MagicMock()
        self.mock_pl_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_invoice_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_wh_repo = MagicMock()

        self.service = BatchNumberService(
            repo=self.mock_repo,
            grn_line_repo=self.mock_grn_line_repo,
            grn_repo=self.mock_grn_repo,
            po_repo=self.mock_po_repo,
            supplier_repo=self.mock_supplier_repo,
            pli_repo=self.mock_pli_repo,
            pl_repo=self.mock_pl_repo,
            order_repo=self.mock_order_repo,
            customer_repo=self.mock_customer_repo,
            invoice_repo=self.mock_invoice_repo,
            product_repo=self.mock_product_repo,
            wh_repo=self.mock_wh_repo
        )

    def test_get_recall_report_by_batch_id(self):
        self.mock_repo.get.return_value = {
            'id': 1,
            'batch_number': 'LOT-RECALL-01',
            'product_id': 100,
            'expiry_date': '2026-10-31',
            'manufacturing_date': '2026-01-01',
            'quantity': 25.0,
            'warehouse_id': 1,
            'status': 'Available',
            'notes': 'Contamination suspected'
        }
        self.mock_product_repo.get.return_value = {
            'id': 100,
            'name': 'Organic Almond Milk 1L',
            'sku': 'MILK-ALM-001',
            'category': 'Dairy Alternatives'
        }
        self.mock_wh_repo.get.return_value = {
            'id': 1,
            'name': 'Main Central Warehouse'
        }

        # Inbound receipt setup
        self.mock_grn_line_repo.list.return_value = [
            {'id': 10, 'receipt_id': 50, 'product_id': 100, 'batch_number': 'LOT-RECALL-01', 'qty_received': 100.0, 'manufacturing_date': '2026-01-01', 'expiry_date': '2026-10-31'}
        ]
        self.mock_grn_repo.get.return_value = {
            'id': 50, 'receipt_number': 'GRN-00050', 'purchase_order_id': 30, 'receipt_date': '2026-01-05', 'warehouse_id': 1, 'status': 'Completed'
        }
        self.mock_po_repo.get.return_value = {
            'id': 30, 'order_number': 'PO-00030', 'supplier_id': 12, 'status': 'Received'
        }
        self.mock_supplier_repo.get.return_value = {
            'id': 12, 'name': 'Organic Farms Ltd', 'email': 'supplier@farms.com', 'phone': '555-1234', 'category': 'Beverages'
        }

        # Outbound pick list items setup (2 different customers)
        self.mock_pli_repo.list.side_effect = lambda filters=None: [
            {'id': 201, 'pick_list_id': 501, 'product_id': 100, 'qty_ordered': 40.0, 'qty_picked': 40.0, 'batch_id': 1, 'batch_number': 'LOT-RECALL-01', 'picked_batch_id': 1, 'picked_batch_number': 'LOT-RECALL-01'},
            {'id': 202, 'pick_list_id': 502, 'product_id': 100, 'qty_ordered': 35.0, 'qty_picked': 35.0, 'batch_id': 1, 'batch_number': 'LOT-RECALL-01', 'picked_batch_id': 1, 'picked_batch_number': 'LOT-RECALL-01'}
        ] if filters and ('batch_id' in filters or 'batch_number' in filters) else []

        def mock_pl_get(id_val):
            if id_val == 501:
                return {'id': 501, 'pick_list_number': 'PL-00501', 'sales_order_id': 801, 'warehouse_id': 1, 'status': 'Completed'}
            elif id_val == 502:
                return {'id': 502, 'pick_list_number': 'PL-00502', 'sales_order_id': 802, 'warehouse_id': 1, 'status': 'Completed'}
            return None
        self.mock_pl_repo.get.side_effect = mock_pl_get

        def mock_order_get(id_val):
            if id_val == 801:
                return {'id': 801, 'order_number': 'SO-00801', 'customer_id': 1001, 'order_date': '2026-02-01', 'status': 'Shipped'}
            elif id_val == 802:
                return {'id': 802, 'order_number': 'SO-00802', 'customer_id': 1002, 'order_date': '2026-02-05', 'status': 'Shipped'}
            return None
        self.mock_order_repo.get.side_effect = mock_order_get

        def mock_customer_get(id_val):
            if id_val == 1001:
                return {'id': 1001, 'name': 'Acme Supermarket', 'email': 'buyer@acme.com', 'phone': '555-9001', 'group_name': 'Wholesale'}
            elif id_val == 1002:
                return {'id': 1002, 'name': 'Green Grocery Co', 'email': 'orders@greengrocery.com', 'phone': '555-9002', 'group_name': 'Retail'}
            return None
        self.mock_customer_repo.get.side_effect = mock_customer_get

        def mock_invoice_list(filters=None):
            if filters and filters.get('sales_order_id') == 801:
                return [{'id': 901, 'invoice_number': 'INV-00901', 'status': 'Paid'}]
            elif filters and filters.get('sales_order_id') == 802:
                return [{'id': 902, 'invoice_number': 'INV-00902', 'status': 'Issued'}]
            return []
        self.mock_invoice_repo.list.side_effect = mock_invoice_list

        report = self.service.get_recall_report(batch_id=1)

        # Verify batch metadata
        assert report['batch']['batch_number'] == 'LOT-RECALL-01'
        assert report['batch']['product_name'] == 'Organic Almond Milk 1L'
        assert report['batch']['product_sku'] == 'MILK-ALM-001'
        assert report['batch']['quantity'] == 25.0

        # Verify inbound trace (supplier & goods receipt)
        assert len(report['inbound_trace']) == 1
        inbound = report['inbound_trace'][0]
        assert inbound['receipt_number'] == 'GRN-00050'
        assert inbound['po_number'] == 'PO-00030'
        assert inbound['supplier_name'] == 'Organic Farms Ltd'
        assert inbound['supplier_email'] == 'supplier@farms.com'
        assert inbound['qty_received'] == 100.0

        # Verify outbound trace (orders, customers, pick lists)
        assert len(report['outbound_trace']) == 2
        assert report['outbound_trace'][0]['customer_name'] == 'Acme Supermarket'
        assert report['outbound_trace'][0]['sales_order_number'] == 'SO-00801'
        assert report['outbound_trace'][0]['invoice_number'] == 'INV-00901'
        assert report['outbound_trace'][1]['customer_name'] == 'Green Grocery Co'
        assert report['outbound_trace'][1]['sales_order_number'] == 'SO-00802'

        # Verify affected customers summary
        assert len(report['affected_customers']) == 2
        cust1 = next(c for c in report['affected_customers'] if c['customer_id'] == 1001)
        assert cust1['customer_name'] == 'Acme Supermarket'
        assert cust1['email'] == 'buyer@acme.com'
        assert cust1['phone'] == '555-9001'
        assert cust1['total_qty_picked'] == 40.0
        assert len(cust1['orders']) == 1
        assert cust1['orders'][0]['order_number'] == 'SO-00801'

        # Verify summary counts
        assert report['summary']['total_qty_received'] == 100.0
        assert report['summary']['total_qty_picked'] == 75.0
        assert report['summary']['current_quantity'] == 25.0
        assert report['summary']['total_affected_customers'] == 2
        assert report['summary']['total_affected_orders'] == 2
        assert report['summary']['total_inbound_receipts'] == 1
        assert report['summary']['total_outbound_pick_lists'] == 2

    def test_get_recall_report_missing_parameters_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            self.service.get_recall_report()
        assert 'Either batch_number or batch_id' in str(exc_info.value)

    def test_get_recall_report_nonexistent_batch_id_raises_error(self):
        self.mock_repo.get.return_value = None
        with pytest.raises(ValueError) as exc_info:
            self.service.get_recall_report(batch_id=999)
        assert 'Batch with ID 999 not found' in str(exc_info.value)

    def test_get_recall_report_nonexistent_batch_number_raises_error(self):
        self.mock_repo.list.return_value = []
        self.mock_grn_line_repo.list.return_value = []
        self.mock_pli_repo.list.return_value = []
        with pytest.raises(ValueError) as exc_info:
            self.service.get_recall_report(batch_number='NONEXISTENT-LOT')
        assert "Batch 'NONEXISTENT-LOT' not found" in str(exc_info.value)

    def test_get_recall_report_by_batch_number(self):
        self.mock_repo.list.return_value = [{
            'id': 1,
            'batch_number': 'LOT-RECALL-02',
            'product_id': 100,
            'expiry_date': '2026-10-31',
            'manufacturing_date': '2026-01-01',
            'quantity': 50.0,
            'warehouse_id': 1,
            'status': 'Available'
        }]
        self.mock_product_repo.get.return_value = {
            'id': 100,
            'name': 'Organic Milk 1L',
            'sku': 'MILK-001',
            'category': 'Dairy'
        }
        self.mock_grn_line_repo.list.return_value = []
        self.mock_pli_repo.list.return_value = []

        report = self.service.get_recall_report(batch_number='LOT-RECALL-02')
        assert report['batch']['batch_number'] == 'LOT-RECALL-02'
        assert report['batch']['product_name'] == 'Organic Milk 1L'
        assert report['batch']['quantity'] == 50.0



class TestBatchRecallControllerEndpoints:
    def test_get_recall_report_endpoint(self, monkeypatch):
        from modules.warehouse.controllers import T0088I

        mock_svc = MagicMock()
        mock_svc.get_recall_report.return_value = {
            'batch': {'batch_number': 'LOT-TEST-1'},
            'summary': {'total_affected_customers': 1},
            'affected_customers': [{'customer_name': 'Test Cust'}]
        }
        monkeypatch.setattr(T0088I, 'service', mock_svc)

        result = T0088I.get_batch_recall_report(batch_number='LOT-TEST-1')
        assert result['batch']['batch_number'] == 'LOT-TEST-1'
        mock_svc.get_recall_report.assert_called_once_with(
            batch_number='LOT-TEST-1',
            batch_id=None,
            product_id=None
        )

    def test_get_recall_report_endpoint_missing_params(self):
        from modules.warehouse.controllers import T0088I
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            T0088I.get_batch_recall_report()
        assert exc_info.value.status_code == 400

    def test_get_batch_trace_endpoint(self, monkeypatch):
        from modules.warehouse.controllers import T0088I

        mock_svc = MagicMock()
        mock_svc.get_recall_report.return_value = {
            'batch': {'id': 42, 'batch_number': 'LOT-42'}
        }
        monkeypatch.setattr(T0088I, 'service', mock_svc)

        result = T0088I.get_batch_trace(id=42)
        assert result['batch']['id'] == 42
        mock_svc.get_recall_report.assert_called_once_with(batch_id=42)

    def test_get_batch_trace_endpoint_not_found(self, monkeypatch):
        from modules.warehouse.controllers import T0088I
        from fastapi import HTTPException

        mock_svc = MagicMock()
        mock_svc.get_recall_report.side_effect = ValueError('Batch with ID 999 not found')
        monkeypatch.setattr(T0088I, 'service', mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            T0088I.get_batch_trace(id=999)
        assert exc_info.value.status_code == 404
        assert 'Batch with ID 999 not found' in exc_info.value.detail


class TestDatabaseSchemaSupport:
    def test_goods_receipt_line_schema_batch_fields(self):
        from modules.warehouse.models.warehouse import (
            GoodsReceiptLineCreate,
            GoodsReceiptLineUpdate,
            GoodsReceiptLineResponse
        )
        from datetime import date

        create_model = GoodsReceiptLineCreate(
            receipt_id=1,
            product_name='Test Product',
            qty_received=10.0,
            batch_number='LOT-123',
            manufacturing_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31)
        )
        assert create_model.batch_number == 'LOT-123'
        assert create_model.manufacturing_date == date(2026, 1, 1)
        assert create_model.expiry_date == date(2026, 12, 31)

        update_model = GoodsReceiptLineUpdate(
            batch_number='LOT-456',
            manufacturing_date=date(2026, 2, 1),
            expiry_date=date(2027, 1, 1)
        )
        assert update_model.batch_number == 'LOT-456'

        response_model = GoodsReceiptLineResponse(
            id=1,
            receipt_id=1,
            product_name='Test Product',
            qty_received=10.0,
            qty_ordered=10.0,
            line_number=1,
            batch_number='LOT-123',
            manufacturing_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31)
        )
        assert response_model.batch_number == 'LOT-123'
        assert response_model.expiry_date == date(2026, 12, 31)

    def test_batch_number_schema_fields(self):
        from modules.warehouse.models.serial_batch import (
            BatchNumberCreate,
            BatchNumberUpdate,
            BatchNumberResponse
        )
        from datetime import date

        batch_create = BatchNumberCreate(
            product_id=10,
            batch_number='BATCH-789',
            manufacturing_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            quantity=100.0,
            warehouse_id=2,
            status='Available'
        )
        assert batch_create.batch_number == 'BATCH-789'
        assert batch_create.expiry_date == date(2026, 12, 31)

        batch_update = BatchNumberUpdate(
            quantity=50.0,
            status='Partially Used'
        )
        assert batch_update.quantity == 50.0

        batch_response = BatchNumberResponse(
            id=100,
            product_id=10,
            batch_number='BATCH-789',
            manufacturing_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            quantity=100.0,
            warehouse_id=2,
            status='Available'
        )
        assert batch_response.id == 100
        assert batch_response.batch_number == 'BATCH-789'


class TestEndToEndFEFOWorkflow:
    """End-to-end workflow verification across inbound check-in, FEFO order reservation,
    picking completion, and recall trace execution."""

    def test_full_fefo_lifecycle(self):
        batch_repo = MagicMock()
        grn_repo = MagicMock()
        grn_line_repo = MagicMock()
        po_repo = MagicMock()
        supplier_repo = MagicMock()
        pl_repo = MagicMock()
        pli_repo = MagicMock()
        order_repo = MagicMock()
        line_repo = MagicMock()
        customer_repo = MagicMock()
        invoice_repo = MagicMock()
        product_repo = MagicMock()
        wh_repo = MagicMock()

        batch_service = BatchNumberService(
            repo=batch_repo,
            grn_line_repo=grn_line_repo,
            grn_repo=grn_repo,
            po_repo=po_repo,
            supplier_repo=supplier_repo,
            pli_repo=pli_repo,
            pl_repo=pl_repo,
            order_repo=order_repo,
            customer_repo=customer_repo,
            invoice_repo=invoice_repo,
            product_repo=product_repo,
            wh_repo=wh_repo
        )

        from modules.warehouse.services.goods_receipt_service import GoodsReceiptService
        from modules.warehouse.services.pick_list_service import PickListService

        grn_service = GoodsReceiptService(grn_repo)
        grn_service.line_repo = grn_line_repo
        grn_service.batch_repo = batch_repo

        pick_service = PickListService(
            pl_repo=pl_repo,
            pli_repo=pli_repo,
            batch_service=batch_service,
            order_repo=order_repo,
            line_repo=line_repo,
            wh_repo=wh_repo
        )

        # Step 1: Inbound Check-In - Goods Receipt registers batch
        grn_repo.get.return_value = {'id': 100, 'warehouse_id': 1, 'status': 'Completed'}
        grn_line_repo.list.return_value = [
            {
                'id': 1, 'receipt_id': 100, 'product_id': 500, 'product_name': 'Organic Cheese 250g',
                'batch_number': 'LOT-CHEESE-EARLY', 'manufacturing_date': '2026-01-01', 'expiry_date': '2026-06-01',
                'qty_received': 10.0
            }
        ]
        batch_repo.list.return_value = []

        grn_service._register_batches(100)

        batch_repo.create.assert_called_once_with({
            'product_id': 500,
            'batch_number': 'LOT-CHEESE-EARLY',
            'manufacturing_date': '2026-01-01',
            'expiry_date': '2026-06-01',
            'quantity': 10.0,
            'warehouse_id': 1,
            'status': 'Available'
        })

        # Step 2: FEFO Order Reservation with split lots
        batches_in_db = [
            {
                'id': 1, 'product_id': 500, 'batch_number': 'LOT-CHEESE-EARLY',
                'expiry_date': '2026-06-01', 'quantity': 10.0, 'warehouse_id': 1, 'status': 'Available'
            },
            {
                'id': 2, 'product_id': 500, 'batch_number': 'LOT-CHEESE-LATE',
                'expiry_date': '2026-09-01', 'quantity': 20.0, 'warehouse_id': 1, 'status': 'Available'
            }
        ]
        batch_repo.list.return_value = batches_in_db

        allocations = batch_service.allocate_fefo_lots(product_id=500, warehouse_id=1, qty_needed=15.0)

        assert len(allocations) == 2
        assert allocations[0]['batch_number'] == 'LOT-CHEESE-EARLY'
        assert allocations[0]['quantity'] == 10.0
        assert allocations[1]['batch_number'] == 'LOT-CHEESE-LATE'
        assert allocations[1]['quantity'] == 5.0

        # Step 3: Pick List Generation & Picking Completion
        order_repo.get.return_value = {'id': 200, 'order_number': 'SO-200', 'warehouse_id': 1, 'customer_id': 10}
        line_repo.list.return_value = [
            {'id': 1, 'sales_order_id': 200, 'product_id': 500, 'product_name': 'Organic Cheese 250g', 'qty': 15.0, 'line_number': 1}
        ]
        pl_repo.list.return_value = []
        pl_repo.create.return_value = {'id': 300, 'pick_list_number': 'PL-300', 'sales_order_id': 200, 'warehouse_id': 1, 'status': 'Pending'}
        pl_repo.get.return_value = {'id': 300, 'sales_order_id': 200, 'warehouse_id': 1, 'status': 'In Progress'}

        created_pli = []
        def mock_pli_create(payload):
            item = dict(payload, id=len(created_pli) + 1)
            created_pli.append(item)
            return item
        pli_repo.create.side_effect = mock_pli_create
        pli_repo.list.return_value = created_pli

        with patch('modules.warehouse.services.pick_list_service.generate_pick_list_number', return_value='PKL-00300'):
            pick_service.create_from_order(200, warehouse_id=1)

        assert len(created_pli) == 2
        assert created_pli[0]['batch_number'] == 'LOT-CHEESE-EARLY'
        assert created_pli[0]['qty_ordered'] == 10.0
        assert created_pli[1]['batch_number'] == 'LOT-CHEESE-LATE'
        assert created_pli[1]['qty_ordered'] == 5.0

        # Simulate picker marking items as picked
        def mock_pli_get(item_id, **kwargs):
            return next((i for i in created_pli if i['id'] == item_id), None)
        pli_repo.get.side_effect = mock_pli_get

        def mock_pli_update(item_id, payload, **kwargs):
            item = next((i for i in created_pli if i['id'] == item_id), None)
            if item:
                item.update(payload)
            return item
        pli_repo.update.side_effect = mock_pli_update

        def mock_batch_get(batch_id, **kwargs):
            return next((b for b in batches_in_db if b['id'] == batch_id), None)
        batch_repo.get.side_effect = mock_batch_get
        batch_repo.get_for_update.side_effect = mock_batch_get

        pick_service.pick_item(item_id=1, qty_picked=10.0, pick_list_id=300)
        pick_service.pick_item(item_id=2, qty_picked=5.0, pick_list_id=300)

        pick_service.complete_picking(300)

        assert order_repo.update.call_count == 1
        assert order_repo.update.call_args[0] == (200, {'status': 'Shipped'})

        # Step 4: Supplier Recall Trace Execution
        batch_repo.get.return_value = {
            'id': 1, 'batch_number': 'LOT-CHEESE-EARLY', 'product_id': 500,
            'expiry_date': '2026-06-01', 'manufacturing_date': '2026-01-01',
            'quantity': 0.0, 'warehouse_id': 1, 'status': 'Depleted'
        }
        product_repo.get.return_value = {'id': 500, 'name': 'Organic Cheese 250g', 'sku': 'CHEESE-001', 'category': 'Dairy'}
        wh_repo.get.return_value = {'id': 1, 'name': 'Main Warehouse'}
        grn_line_repo.list.return_value = [
            {'id': 1, 'receipt_id': 100, 'product_id': 500, 'batch_number': 'LOT-CHEESE-EARLY', 'qty_received': 10.0}
        ]
        grn_repo.get.return_value = {'id': 100, 'receipt_number': 'GRN-100', 'purchase_order_id': 50, 'receipt_date': '2026-01-02'}
        po_repo.get.return_value = {'id': 50, 'order_number': 'PO-050', 'supplier_id': 5}
        supplier_repo.get.return_value = {'id': 5, 'name': 'Cheese Producer Co', 'email': 'supplier@cheeseco.com', 'phone': '555-0199'}

        pli_repo.list.side_effect = lambda filters=None: [
            {'id': 1, 'pick_list_id': 300, 'product_id': 500, 'qty_ordered': 10.0, 'qty_picked': 10.0, 'batch_id': 1, 'batch_number': 'LOT-CHEESE-EARLY'}
        ]
        pl_repo.get.return_value = {'id': 300, 'pick_list_number': 'PL-300', 'sales_order_id': 200, 'warehouse_id': 1, 'status': 'Completed'}
        order_repo.get.return_value = {'id': 200, 'order_number': 'SO-200', 'customer_id': 10, 'order_date': '2026-01-15', 'status': 'Shipped'}
        customer_repo.get.return_value = {'id': 10, 'name': 'Gourmet Market', 'email': 'purchasing@gourmet.com', 'phone': '555-4321'}
        invoice_repo.list.return_value = [{'id': 70, 'invoice_number': 'INV-070', 'status': 'Paid'}]

        report = batch_service.get_recall_report(batch_id=1)

        assert report['batch']['batch_number'] == 'LOT-CHEESE-EARLY'
        assert len(report['inbound_trace']) == 1
        assert report['inbound_trace'][0]['supplier_name'] == 'Cheese Producer Co'
        assert len(report['outbound_trace']) == 1
        assert report['outbound_trace'][0]['customer_name'] == 'Gourmet Market'
        assert report['outbound_trace'][0]['sales_order_number'] == 'SO-200'
        assert report['summary']['total_affected_customers'] == 1
        assert report['summary']['total_affected_orders'] == 1







