"""
Nova ERP — Stock Transfer Domain Service Unit Tests
Comprehensive unit tests for StockTransferService covering transfer creation,
line enrichment, dispatch, receive, loss tracking, cancellation, and line item management.
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, ANY
from fastapi import HTTPException

from modules.warehouse.services.stock_transfer_service import StockTransferService
from modules.warehouse.models.stock_transfer import (
    StockTransferCreate, StockTransferLineCreate, StockTransferDispatch,
    StockTransferDispatchLine, StockTransferReceive, StockTransferReceiveLine,
    StockTransferLossDetail, StockTransferLineUpdate
)


class TestStockTransferServiceCreation:
    def setup_method(self):
        self.transfer_repo = MagicMock()
        self.line_repo = MagicMock()
        self.stock_service = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.batch_repo = MagicMock()
        self.user_repo = MagicMock()

        self.service = StockTransferService(
            repo=self.transfer_repo,
            line_repo=self.line_repo,
            stock_service=self.stock_service,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            batch_repo=self.batch_repo,
            user_repo=self.user_repo,
        )

        # Default mock warehouses
        self.wh_repo.get.side_effect = lambda wh_id, **kwargs: {
            1: {'id': 1, 'name': 'Main Central Hub', 'warehouse_type': 'Central Hub', 'is_virtual': False},
            2: {'id': 2, 'name': 'North Branch DC', 'warehouse_type': 'Regional DC', 'is_virtual': False},
        }.get(wh_id)

    def test_create_transfer_success_with_nested_lines(self):
        # Setup mocks
        self.transfer_repo.create.return_value = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': 'Urgent restock',
            'is_active': True,
        }
        self.transfer_repo.get.return_value = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': 'Urgent restock',
            'is_active': True,
        }
        self.line_repo.list.return_value = [
            {
                'id': 1,
                'transfer_id': 101,
                'product_id': 10,
                'qty_requested': 50.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 1,
                'is_active': True,
            },
            {
                'id': 2,
                'transfer_id': 101,
                'product_id': 20,
                'qty_requested': 30.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 2,
                'is_active': True,
            }
        ]
        self.product_repo.get.side_effect = lambda pid, **kwargs: {
            10: {'id': 10, 'name': 'Whole Milk 1L', 'sku': 'MLK-001'},
            20: {'id': 20, 'name': 'Cheddar Cheese 500g', 'sku': 'CHS-002'},
        }.get(pid)

        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=2,
            notes='Urgent restock',
            lines=[
                StockTransferLineCreate(product_id=10, qty_requested=50.0),
                StockTransferLineCreate(product_id=20, qty_requested=30.0),
            ]
        )

        with patch('modules.warehouse.services.stock_transfer_service.generate_stock_transfer_number', return_value='TRF-00101'):
            result = self.service.create_transfer(payload)

        assert result is not None
        assert result['id'] == 101
        assert result['transfer_number'] == 'TRF-00101'
        assert result['status'] == 'Draft'
        assert result['source_warehouse_name'] == 'Main Central Hub'
        assert result['destination_warehouse_name'] == 'North Branch DC'
        assert result['total_requested_qty'] == 80.0
        assert result['lines_count'] == 2
        assert len(result['lines']) == 2
        assert result['lines'][0]['product_name'] == 'Whole Milk 1L'
        assert result['lines'][1]['product_name'] == 'Cheddar Cheese 500g'

        # Verify line repo create calls
        assert self.line_repo.create.call_count == 2

    def test_create_transfer_same_source_and_destination_raises_400(self):
        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=1,
            lines=[StockTransferLineCreate(product_id=10, qty_requested=10.0)]
        )
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 400
        assert "must be different" in exc.value.detail

    def test_create_transfer_invalid_source_warehouse_raises_404(self):
        self.wh_repo.get.side_effect = lambda wh_id, **kwargs: None if wh_id == 999 else {'id': 2, 'name': 'Branch'}
        payload = StockTransferCreate(
            source_warehouse_id=999,
            destination_warehouse_id=2,
            lines=[StockTransferLineCreate(product_id=10, qty_requested=10.0)]
        )
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 404
        assert "Source warehouse #999 not found" in exc.value.detail

    def test_create_transfer_invalid_line_qty_raises_400(self):
        payload = {
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'lines': [{'product_id': 10, 'qty_requested': 0}]
        }
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 400
        assert "Requested quantity must be greater than 0" in exc.value.detail


class TestStockTransferServiceDispatch:
    def setup_method(self):
        self.transfer_repo = MagicMock()
        self.line_repo = MagicMock()
        self.stock_service = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.batch_repo = MagicMock()
        self.user_repo = MagicMock()

        self.service = StockTransferService(
            repo=self.transfer_repo,
            line_repo=self.line_repo,
            stock_service=self.stock_service,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            batch_repo=self.batch_repo,
            user_repo=self.user_repo,
        )

        self.transfer_data = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': '',
            'is_active': True,
        }
        self.lines_data = [
            {
                'id': 11,
                'transfer_id': 101,
                'product_id': 10,
                'qty_requested': 40.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'batch_id': 501,
                'batch_number': 'LOT-2026-001',
                'line_number': 1,
                'is_active': True,
            }
        ]

    def test_dispatch_transfer_full_success(self):
        current_state = dict(self.transfer_data)
        def mock_get(tid, **kwargs):
            return dict(current_state)
        self.transfer_repo.get.side_effect = mock_get

        def mock_update(tid, update_fields, **kwargs):
            current_state.update(update_fields)
            return dict(current_state)
        self.transfer_repo.update.side_effect = mock_update

        self.line_repo.list.return_value = [dict(l) for l in self.lines_data]
        self.batch_repo.get.return_value = {'id': 501, 'quantity': 100.0, 'status': 'Available'}

        dispatch_payload = StockTransferDispatch(
            carrier='DHL Express',
            tracking_number='DHL-98765',
            dispatched_by=5,
            notes='Dispatched via express truck',
        )

        result = self.service.dispatch_transfer(101, dispatch_payload)

        assert result['status'] == 'In Transit'
        assert result['total_dispatched_qty'] == 40.0

        # Verify stock_service.transfer_dispatch was called
        self.stock_service.transfer_dispatch.assert_called_once()
        call_kwargs = self.stock_service.transfer_dispatch.call_args[1]
        assert call_kwargs['product_id'] == 10
        assert call_kwargs['source_warehouse_id'] == 1
        assert call_kwargs['destination_warehouse_id'] == 2
        assert call_kwargs['qty'] == 40.0
        assert call_kwargs['reference_type'] == 'StockTransfer'
        assert call_kwargs['reference_id'] == 101
        assert call_kwargs['user_id'] == 5

        # Verify batch deduction
        self.batch_repo.update.assert_called_once()
        args, kwargs = self.batch_repo.update.call_args
        assert args[0] == 501
        assert args[1]['quantity'] == 60.0

    def test_dispatch_transfer_wrong_status_raises_400(self):
        self.transfer_repo.get.return_value = {**self.transfer_data, 'status': 'In Transit'}
        with pytest.raises(HTTPException) as exc:
            self.service.dispatch_transfer(101)
        assert exc.value.status_code == 400
        assert "Status must be 'Draft' or 'Pending'" in exc.value.detail

    def test_dispatch_transfer_no_lines_raises_400(self):
        self.transfer_repo.get.return_value = dict(self.transfer_data)
        self.line_repo.list.return_value = []
        with pytest.raises(HTTPException) as exc:
            self.service.dispatch_transfer(101)
        assert exc.value.status_code == 400
        assert "no line items" in exc.value.detail


class TestStockTransferServiceReceive:
    def setup_method(self):
        self.transfer_repo = MagicMock()
        self.line_repo = MagicMock()
        self.stock_service = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.batch_repo = MagicMock()
        self.user_repo = MagicMock()

        self.service = StockTransferService(
            repo=self.transfer_repo,
            line_repo=self.line_repo,
            stock_service=self.stock_service,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            batch_repo=self.batch_repo,
            user_repo=self.user_repo,
        )

        self.transfer_in_transit = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'transfer_date': date.today(),
            'carrier': 'DHL Express',
            'tracking_number': 'DHL-98765',
            'dispatched_at': datetime.now(),
            'dispatched_by': 5,
            'notes': '',
            'is_active': True,
        }

    def test_receive_transfer_full_receipt(self):
        current_state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(current_state)
        def mock_update(tid, update_fields, **kwargs):
            current_state.update(update_fields)
            return dict(current_state)
        self.transfer_repo.update.side_effect = mock_update

        lines = [
            {
                'id': 11,
                'transfer_id': 101,
                'product_id': 10,
                'qty_requested': 50.0,
                'qty_dispatched': 50.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 1,
                'is_active': True,
            }
        ]
        self.line_repo.list.return_value = [dict(l) for l in lines]

        receive_payload = StockTransferReceive(
            received_by=8,
            notes='Received in good condition',
            lines=[StockTransferReceiveLine(line_id=11, qty_received=50.0, qty_lost=0.0)]
        )

        result = self.service.receive_transfer(101, receive_payload)

        # Verify stock_service.transfer_receive was called
        self.stock_service.transfer_receive.assert_called_once()
        kwargs = self.stock_service.transfer_receive.call_args[1]
        assert kwargs['product_id'] == 10
        assert kwargs['destination_warehouse_id'] == 2
        assert kwargs['qty_received'] == 50.0
        assert kwargs['qty_dispatched'] == 50.0

        # Verify loss was NOT recorded
        self.stock_service.record_transfer_loss.assert_not_called()

        # Verify header updated to Received
        self.transfer_repo.update.assert_called()
        update_payload = self.transfer_repo.update.call_args[0][1]
        assert update_payload['status'] == 'Received'

    def test_receive_transfer_with_transit_loss_and_discrepancy(self):
        current_state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(current_state)
        def mock_update(tid, update_fields, **kwargs):
            current_state.update(update_fields)
            return dict(current_state)
        self.transfer_repo.update.side_effect = mock_update

        lines = [
            {
                'id': 11,
                'transfer_id': 101,
                'product_id': 10,
                'qty_requested': 50.0,
                'qty_dispatched': 50.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 1,
                'is_active': True,
            }
        ]
        self.line_repo.list.return_value = [dict(l) for l in lines]

        # 45 units received intact, 5 units damaged during transit
        receive_payload = StockTransferReceive(
            received_by=8,
            lines=[
                StockTransferReceiveLine(
                    line_id=11,
                    qty_received=45.0,
                    qty_lost=5.0,
                    loss_reason='Transit Damage',
                    loss_notes='Crushed boxes during transit'
                )
            ]
        )

        result = self.service.receive_transfer(101, receive_payload)

        # Verify transfer_receive called with 45 received and 50 dispatched
        self.stock_service.transfer_receive.assert_called_once()
        tr_kwargs = self.stock_service.transfer_receive.call_args[1]
        assert tr_kwargs['qty_received'] == 45.0
        assert tr_kwargs['qty_dispatched'] == 50.0

        # Verify loss record called with 5 units damaged
        self.stock_service.record_transfer_loss.assert_called_once()
        loss_kwargs = self.stock_service.record_transfer_loss.call_args[1]
        assert loss_kwargs['product_id'] == 10
        assert loss_kwargs['warehouse_id'] == 2
        assert loss_kwargs['qty_lost'] == 5.0
        assert loss_kwargs['loss_reason'] == 'Transit Damage'
        assert loss_kwargs['loss_notes'] == 'Crushed boxes during transit'

    def test_receive_transfer_not_in_transit_raises_400(self):
        self.transfer_repo.get.return_value = {**self.transfer_in_transit, 'status': 'Draft'}
        with pytest.raises(HTTPException) as exc:
            self.service.receive_transfer(101)
        assert exc.value.status_code == 400
        assert "Status must be 'In Transit'" in exc.value.detail


class TestStockTransferServiceCancel:
    def setup_method(self):
        self.transfer_repo = MagicMock()
        self.line_repo = MagicMock()
        self.stock_service = MagicMock()
        self.wh_repo = MagicMock()
        self.product_repo = MagicMock()
        self.batch_repo = MagicMock()
        self.user_repo = MagicMock()

        self.service = StockTransferService(
            repo=self.transfer_repo,
            line_repo=self.line_repo,
            stock_service=self.stock_service,
            wh_repo=self.wh_repo,
            product_repo=self.product_repo,
            batch_repo=self.batch_repo,
            user_repo=self.user_repo,
        )

    def test_cancel_draft_transfer_success(self):
        self.transfer_repo.get.return_value = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'status': 'Draft',
            'notes': 'Initial order',
        }

        result = self.service.cancel_transfer(101, reason='Customer cancelled demand')

        # Stock cancellation should NOT be called since no stock moved
        self.stock_service.cancel_transfer_dispatch.assert_not_called()

        self.transfer_repo.update.assert_called_once()
        update_args = self.transfer_repo.update.call_args[0]
        assert update_args[0] == 101
        assert update_args[1]['status'] == 'Cancelled'
        assert 'Customer cancelled demand' in update_args[1]['notes']

    def test_cancel_in_transit_transfer_reverses_stock(self):
        self.transfer_repo.get.return_value = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'notes': '',
        }
        self.line_repo.list.return_value = [
            {'id': 1, 'transfer_id': 101, 'product_id': 10, 'qty_dispatched': 25.0, 'batch_id': 501}
        ]
        self.batch_repo.get.return_value = {'id': 501, 'quantity': 75.0, 'status': 'Partially Used'}

        result = self.service.cancel_transfer(101, reason='Truck breakdown - returned to depot')

        # Stock cancellation must be called
        self.stock_service.cancel_transfer_dispatch.assert_called_once()
        call_kwargs = self.stock_service.cancel_transfer_dispatch.call_args[1]
        assert call_kwargs['product_id'] == 10
        assert call_kwargs['source_warehouse_id'] == 1
        assert call_kwargs['destination_warehouse_id'] == 2
        assert call_kwargs['qty'] == 25.0
        assert call_kwargs['reference_type'] == 'StockTransfer'
        assert call_kwargs['reference_id'] == 101
        assert 'Truck breakdown - returned to depot' in call_kwargs['description']

        # Batch quantity restored
        self.batch_repo.update.assert_called_once()
        b_args = self.batch_repo.update.call_args[0]
        assert b_args[0] == 501
        assert b_args[1]['quantity'] == 100.0

        # Status updated to Cancelled
        assert self.transfer_repo.update.call_args[0][1]['status'] == 'Cancelled'

    def test_cancel_already_received_transfer_raises_400(self):
        self.transfer_repo.get.return_value = {
            'id': 101,
            'transfer_number': 'TRF-00101',
            'status': 'Received',
        }
        with pytest.raises(HTTPException) as exc:
            self.service.cancel_transfer(101)
        assert exc.value.status_code == 400
        assert "already been received" in exc.value.detail


class TestStockTransferServiceLineOperations:
    def setup_method(self):
        self.transfer_repo = MagicMock()
        self.line_repo = MagicMock()
        self.service = StockTransferService(repo=self.transfer_repo, line_repo=self.line_repo)

    def test_add_line_to_draft_transfer(self):
        self.transfer_repo.get.return_value = {'id': 101, 'status': 'Draft'}
        self.line_repo.list.return_value = [{'id': 1}]
        self.line_repo.create.return_value = {'id': 2, 'transfer_id': 101, 'product_id': 15, 'qty_requested': 20.0}

        line = self.service.add_line(101, {'product_id': 15, 'qty_requested': 20.0})
        assert line['id'] == 2
        assert self.line_repo.create.call_args[0][0]['line_number'] == 2

    def test_add_line_to_in_transit_transfer_raises_400(self):
        self.transfer_repo.get.return_value = {'id': 101, 'status': 'In Transit'}
        with pytest.raises(HTTPException) as exc:
            self.service.add_line(101, {'product_id': 15, 'qty_requested': 20.0})
        assert exc.value.status_code == 400
        assert "Cannot add line to transfer" in exc.value.detail

    def test_delete_line_from_draft_transfer(self):
        self.line_repo.get.return_value = {'id': 2, 'transfer_id': 101}
        self.transfer_repo.get.return_value = {'id': 101, 'status': 'Draft'}

        result = self.service.delete_line(2)
        assert result['success'] is True
        self.line_repo.delete.assert_called_once_with(2)
