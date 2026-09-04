import contextlib
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from modules.inventory.services.stock_movement import (
    StockMovementService,
    _get_stock,
    _get_or_create_stock,
    STOCK_REPO,
)


@pytest.fixture(autouse=True)
def mock_db_transaction():
    with patch('modules.inventory.services.stock_movement.db_transaction', side_effect=lambda conn=None: contextlib.nullcontext(conn)):
        yield


@pytest.fixture
def svc():
    return StockMovementService()


class TestStockMovementServiceTransfers:

    def test_transfer_dispatch_success(self, svc):
        source_stock = {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 50.0, 'reserved_qty': 10.0, 'in_transit_qty': 0.0}
        dest_stock = {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 5.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0}

        def mock_list(filters=None, conn=None, **kwargs):
            if filters.get('warehouse_id') == 1:
                return [source_stock]
            elif filters.get('warehouse_id') == 2:
                return [dest_stock]
            return []

        with patch.object(STOCK_REPO, 'list', side_effect=mock_list), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_movement_create:

            mock_movement_create.return_value = {
                'id': 10,
                'product_id': 101,
                'warehouse_id': 1,
                'movement_type': 'Transfer Out',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': -20.0,
                'balance_after': 30.0,
                'description': 'Transfer Out 20.0 to warehouse #2 (Transfer #500)'
            }

            result = svc.transfer_dispatch(
                product_id=101,
                source_warehouse_id=1,
                destination_warehouse_id=2,
                qty=20.0,
                reference_type='StockTransfer',
                reference_id=500
            )

            assert result is not None
            assert result['movement_type'] == 'Transfer Out'
            assert result['qty_change'] == -20.0
            assert result['balance_after'] == 30.0

            # Verify source stock update: qty = 50 - 20 = 30
            mock_stock_update.assert_any_call(1, {'qty': 30.0, 'reserved_qty': 10.0}, conn=None)
            # Verify dest stock update: in_transit_qty = 0 + 20 = 20
            mock_stock_update.assert_any_call(2, {'in_transit_qty': 20.0}, conn=None)

            # Verify movement creation
            mock_movement_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 1,
                'movement_type': 'Transfer Out',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': -20.0,
                'balance_after': 30.0,
                'description': 'Transfer Out 20.0 to warehouse #2 (Transfer #500)'
            }, conn=None)

    def test_transfer_dispatch_invalid_qty(self, svc):
        with pytest.raises(HTTPException) as exc:
            svc.transfer_dispatch(
                product_id=101,
                source_warehouse_id=1,
                destination_warehouse_id=2,
                qty=0
            )
        assert exc.value.status_code == 400
        assert 'greater than 0' in exc.value.detail

    def test_transfer_dispatch_no_source_stock(self, svc):
        with patch.object(STOCK_REPO, 'list', return_value=[]):
            with pytest.raises(HTTPException) as exc:
                svc.transfer_dispatch(
                    product_id=101,
                    source_warehouse_id=1,
                    destination_warehouse_id=2,
                    qty=10.0
                )
            assert exc.value.status_code == 400
            assert 'No stock record' in exc.value.detail

    def test_transfer_dispatch_insufficient_available_stock(self, svc):
        source_stock = {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 50.0, 'reserved_qty': 45.0, 'in_transit_qty': 0.0}
        with patch.object(STOCK_REPO, 'list', return_value=[source_stock]):
            with pytest.raises(HTTPException) as exc:
                svc.transfer_dispatch(
                    product_id=101,
                    source_warehouse_id=1,
                    destination_warehouse_id=2,
                    qty=10.0  # available is 5.0 (50 - 45)
                )
            assert exc.value.status_code == 400
            assert 'Insufficient stock' in exc.value.detail

    def test_transfer_dispatch_creates_destination_stock_if_missing(self, svc):
        source_stock = {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 50.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0}
        created_dest = {'id': 99, 'product_id': 101, 'warehouse_id': 2, 'qty': 0, 'reserved_qty': 0, 'in_transit_qty': 0, 'reorder_level': 0}

        def mock_list(filters=None, conn=None, **kwargs):
            if filters.get('warehouse_id') == 1:
                return [source_stock]
            return []

        with patch.object(STOCK_REPO, 'list', side_effect=mock_list), \
             patch.object(STOCK_REPO, 'create', return_value=created_dest) as mock_stock_create, \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_movement_create:

            svc.transfer_dispatch(
                product_id=101,
                source_warehouse_id=1,
                destination_warehouse_id=2,
                qty=15.0,
                reference_id=101
            )

            mock_stock_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 2,
                'qty': 0,
                'reserved_qty': 0,
                'in_transit_qty': 0,
                'reorder_level': 0
            }, conn=None)
            mock_stock_update.assert_any_call(99, {'in_transit_qty': 15.0}, conn=None)

    def test_transfer_receive_full(self, svc):
        dest_stock = {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 10.0, 'reserved_qty': 0.0, 'in_transit_qty': 25.0}

        with patch.object(STOCK_REPO, 'list', return_value=[dest_stock]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_movement_create:

            mock_movement_create.return_value = {
                'id': 20,
                'product_id': 101,
                'warehouse_id': 2,
                'movement_type': 'Transfer In',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': 25.0,
                'balance_after': 35.0,
                'description': 'Transfer In 25.0 at warehouse #2 (Transfer #500)'
            }

            result = svc.transfer_receive(
                product_id=101,
                destination_warehouse_id=2,
                qty_received=25.0,
                reference_id=500
            )

            assert result is not None
            assert result['movement_type'] == 'Transfer In'
            assert result['qty_change'] == 25.0

            # Destination stock: qty becomes 10 + 25 = 35, in_transit becomes 25 - 25 = 0
            mock_stock_update.assert_called_once_with(2, {'qty': 35.0, 'in_transit_qty': 0.0}, conn=None)
            mock_movement_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 2,
                'movement_type': 'Transfer In',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': 25.0,
                'balance_after': 35.0,
                'description': 'Transfer In 25.0 at warehouse #2 (Transfer #500)'
            }, conn=None)

    def test_transfer_receive_partial_with_dispatched_deduction(self, svc):
        dest_stock = {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 10.0, 'reserved_qty': 0.0, 'in_transit_qty': 30.0}

        with patch.object(STOCK_REPO, 'list', return_value=[dest_stock]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create'):

            # Received 25 out of 30 dispatched (5 lost or discrepant)
            svc.transfer_receive(
                product_id=101,
                destination_warehouse_id=2,
                qty_received=25.0,
                qty_dispatched=30.0,
                reference_id=500
            )

            # In transit reduced by 30 (to 0), qty increased by 25 (to 35)
            mock_stock_update.assert_called_once_with(2, {'qty': 35.0, 'in_transit_qty': 0.0}, conn=None)

    def test_transfer_receive_negative_qty_raises(self, svc):
        with pytest.raises(HTTPException) as exc:
            svc.transfer_receive(
                product_id=101,
                destination_warehouse_id=2,
                qty_received=-5.0
            )
        assert exc.value.status_code == 400
        assert 'cannot be negative' in exc.value.detail

    def test_record_transfer_loss(self, svc):
        dest_stock = {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 35.0, 'in_transit_qty': 5.0}

        with patch.object(STOCK_REPO, 'list', return_value=[dest_stock]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_movement_create:

            mock_movement_create.return_value = {
                'id': 30,
                'product_id': 101,
                'warehouse_id': 2,
                'movement_type': 'Transfer Loss',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': -5.0,
                'balance_after': 35.0,
                'description': 'Transfer Loss: 5.0 units | Reason: Transit Damage | Notes: Box crushed'
            }

            result = svc.record_transfer_loss(
                product_id=101,
                warehouse_id=2,
                qty_lost=5.0,
                loss_reason='Transit Damage',
                loss_notes='Box crushed',
                reference_id=500,
                decrement_in_transit=True
            )

            assert result is not None
            assert result['movement_type'] == 'Transfer Loss'
            assert result['qty_change'] == -5.0

            # In transit decremented from 5 to 0
            mock_stock_update.assert_called_once_with(2, {'in_transit_qty': 0.0}, conn=None)
            mock_movement_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 2,
                'movement_type': 'Transfer Loss',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': -5.0,
                'balance_after': 35.0,
                'description': 'Transfer Loss: 5.0 units | Reason: Transit Damage | Notes: Box crushed'
            }, conn=None)

    def test_record_transfer_loss_zero_qty(self, svc):
        result = svc.record_transfer_loss(
            product_id=101,
            warehouse_id=2,
            qty_lost=0.0
        )
        assert result is None

    def test_cancel_transfer_dispatch(self, svc):
        source_stock = {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 30.0, 'reserved_qty': 0.0, 'in_transit_qty': 0.0}
        dest_stock = {'id': 2, 'product_id': 101, 'warehouse_id': 2, 'qty': 10.0, 'reserved_qty': 0.0, 'in_transit_qty': 20.0}

        def mock_list(filters=None, conn=None, **kwargs):
            if filters.get('warehouse_id') == 1:
                return [source_stock]
            elif filters.get('warehouse_id') == 2:
                return [dest_stock]
            return []

        with patch.object(STOCK_REPO, 'list', side_effect=mock_list), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_movement_create:

            result = svc.cancel_transfer_dispatch(
                product_id=101,
                source_warehouse_id=1,
                destination_warehouse_id=2,
                qty=20.0,
                reference_id=500
            )

            # Restores source stock 30 + 20 = 50
            mock_stock_update.assert_any_call(1, {'qty': 50.0}, conn=None)
            # Clears dest in transit 20 - 20 = 0
            mock_stock_update.assert_any_call(2, {'in_transit_qty': 0.0}, conn=None)

            mock_movement_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 1,
                'movement_type': 'Transfer Cancel',
                'reference_type': 'StockTransfer',
                'reference_id': 500,
                'qty_change': 20.0,
                'balance_after': 50.0,
                'description': 'Transfer Cancelled: restored 20.0 to warehouse #1 (Transfer #500)'
            }, conn=None)

    def test_get_stock_level(self, svc):
        stock_row = {'id': 1, 'product_id': 101, 'warehouse_id': 1, 'qty': 100.0, 'reserved_qty': 20.0, 'in_transit_qty': 15.0, 'reorder_level': 30.0}

        with patch.object(STOCK_REPO, 'list', return_value=[stock_row]):
            level = svc.get_stock_level(101, 1)
            assert level['qty'] == 100.0
            assert level['reserved_qty'] == 20.0
            assert level['in_transit_qty'] == 15.0
            assert level['available_qty'] == 80.0
            assert level['reorder_level'] == 30.0

        with patch.object(STOCK_REPO, 'list', return_value=[]):
            level = svc.get_stock_level(999, 999)
            assert level['qty'] == 0.0
            assert level['reserved_qty'] == 0.0
            assert level['in_transit_qty'] == 0.0
            assert level['available_qty'] == 0.0


class TestStockMovementServiceCoreMethods:

    def test_record_movement_existing(self, svc):
        stock_row = {'id': 1, 'qty': 20.0}
        with patch.object(STOCK_REPO, 'list', return_value=[stock_row]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_create:

            svc.record_movement(101, 1, 'Adjustment', 5.0)
            mock_stock_update.assert_called_once_with(1, {'qty': 25.0}, conn=None)
            mock_create.assert_called_once_with({
                'product_id': 101,
                'warehouse_id': 1,
                'movement_type': 'Adjustment',
                'reference_type': None,
                'reference_id': None,
                'qty_change': 5.0,
                'balance_after': 25.0,
                'description': None,
            }, conn=None)

    def test_reserve_stock(self, svc):
        stock_row = {'id': 1, 'qty': 20.0, 'reserved_qty': 5.0}
        with patch.object(STOCK_REPO, 'list', return_value=[stock_row]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_create:

            svc.reserve_stock(101, 1, 10.0, reference_id=12)
            mock_stock_update.assert_called_once_with(1, {'reserved_qty': 15.0}, conn=None)
            mock_create.assert_called_once()

    def test_release_stock(self, svc):
        stock_row = {'id': 1, 'qty': 20.0, 'reserved_qty': 15.0}
        with patch.object(STOCK_REPO, 'list', return_value=[stock_row]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_create:

            svc.release_stock(101, 1, 10.0, reference_id=12)
            mock_stock_update.assert_called_once_with(1, {'reserved_qty': 5.0}, conn=None)
            mock_create.assert_called_once()

    def test_deduct_stock(self, svc):
        stock_row = {'id': 1, 'qty': 20.0, 'reserved_qty': 5.0}
        with patch.object(STOCK_REPO, 'list', return_value=[stock_row]), \
             patch.object(STOCK_REPO, 'update') as mock_stock_update, \
             patch.object(svc.repo, 'create') as mock_create:

            svc.deduct_stock(101, 1, 10.0, reference_id=12)
            mock_stock_update.assert_called_once_with(1, {'qty': 10.0, 'reserved_qty': 0}, conn=None)
            mock_create.assert_called_once()
