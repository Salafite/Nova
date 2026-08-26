"""
Nova ERP — Comprehensive Stock Transfer Backend Tests
Covers:
- Transfer creation, nested line initialization, number generation, validation errors
- Source stock deduction and in-transit inventory tracking during dispatch
- Receiving warehouse inventory addition and in-transit clearance
- Discrepancy & transit damage logging with reason codes (Transit Damage, Spillage, Theft, Expired, Shortage, Packaging Failure, Temp Deviation, Other)
- Transfer cancellation and stock reversal workflows
- Multi-tenant isolation and cross-tenant access protection
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, ANY
from fastapi import HTTPException

from modules.warehouse.services.stock_transfer_service import StockTransferService
from modules.warehouse.models.stock_transfer import (
    StockTransferCreate,
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferDispatch,
    StockTransferDispatchLine,
    StockTransferReceive,
    StockTransferReceiveLine,
    StockTransferLossDetail,
)
from modules.core.context import tenant_context, set_current_tenant, clear_current_tenant, get_current_tenant


# ---------------------------------------------------------------------------
# Test Fixtures & In-Memory Helpers
# ---------------------------------------------------------------------------

class InMemoryMockRepo:
    """In-memory repository simulator for multi-tenant transfer testing."""
    def __init__(self, table_name='T0108', initial_items=None):
        self.table_name = table_name
        self._items = {item['id']: dict(item) for item in (initial_items or [])}
        self._next_id = max(self._items.keys(), default=0) + 1

    def get(self, id_val, conn=None, **kwargs):
        item = self._items.get(id_val)
        if not item:
            return None
        current_tenant = get_current_tenant()
        if current_tenant is not None and item.get('business_id') is not None:
            if item.get('business_id') != current_tenant:
                return None
        return dict(item)

    def get_unscoped(self, id_val, conn=None, **kwargs):
        item = self._items.get(id_val)
        return dict(item) if item else None

    def list(self, filters=None, order_by=None, limit=100, offset=0, conn=None, **kwargs):
        res = list(self._items.values())
        current_tenant = get_current_tenant()
        if current_tenant is not None:
            res = [r for r in res if r.get('business_id') is None or r.get('business_id') == current_tenant]
        if filters:
            for k, v in filters.items():
                res = [r for r in res if r.get(k) == v]
        offset_val = offset if offset is not None else 0
        if limit is not None:
            return [dict(r) for r in res[offset_val:offset_val + limit]]
        return [dict(r) for r in res[offset_val:]]

    def create(self, payload, conn=None, **kwargs):
        new_id = payload.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        record = dict(payload, id=new_id)
        current_tenant = get_current_tenant()
        if current_tenant is not None and 'business_id' not in record:
            record['business_id'] = current_tenant
        self._items[new_id] = record
        return dict(record)

    def update(self, id_val, payload, conn=None, **kwargs):
        item = self._items.get(id_val)
        if not item:
            return None
        current_tenant = get_current_tenant()
        if current_tenant is not None and item.get('business_id') is not None:
            if item.get('business_id') != current_tenant:
                return None
        item.update(payload)
        return dict(item)

    def delete(self, id_val, conn=None, **kwargs):
        item = self._items.get(id_val)
        if not item:
            return False
        current_tenant = get_current_tenant()
        if current_tenant is not None and item.get('business_id') is not None:
            if item.get('business_id') != current_tenant:
                return False
        return self._items.pop(id_val, None) is not None


# ---------------------------------------------------------------------------
# 1. Stock Transfer Creation & Validation Tests
# ---------------------------------------------------------------------------

class TestStockTransferCreationAndValidation:
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

        self.wh_repo.get.side_effect = lambda wh_id, **kwargs: {
            1: {'id': 1, 'name': 'Central Cold Storage', 'warehouse_type': 'Central Hub', 'is_virtual': False},
            2: {'id': 2, 'name': 'East Regional Depot', 'warehouse_type': 'Regional DC', 'is_virtual': False},
            3: {'id': 3, 'name': 'West Retail Branch', 'warehouse_type': 'Branch Store', 'is_virtual': False},
        }.get(wh_id)

        self.product_repo.get.side_effect = lambda pid, **kwargs: {
            101: {'id': 101, 'name': 'Fresh Organic Milk 1L', 'sku': 'DAIRY-MLK-01'},
            102: {'id': 102, 'name': 'Artisan Butter 250g', 'sku': 'DAIRY-BTR-02'},
            103: {'id': 103, 'name': 'Aged Cheddar 500g', 'sku': 'DAIRY-CHD-03'},
        }.get(pid)

    def test_create_transfer_single_line_auto_number(self):
        self.transfer_repo.create.return_value = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': 'Weekly stock replenishment',
            'is_active': True,
        }
        self.transfer_repo.get.return_value = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': 'Weekly stock replenishment',
            'is_active': True,
        }
        self.line_repo.list.return_value = [
            {
                'id': 10,
                'transfer_id': 1,
                'product_id': 101,
                'qty_requested': 100.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 1,
                'is_active': True,
            }
        ]

        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=2,
            notes='Weekly stock replenishment',
            lines=[
                StockTransferLineCreate(product_id=101, qty_requested=100.0)
            ]
        )

        with patch('modules.warehouse.services.stock_transfer_service.generate_stock_transfer_number', return_value='TRF-00001'):
            res = self.service.create_transfer(payload)

        assert res['id'] == 1
        assert res['transfer_number'] == 'TRF-00001'
        assert res['status'] == 'Draft'
        assert res['source_warehouse_name'] == 'Central Cold Storage'
        assert res['destination_warehouse_name'] == 'East Regional Depot'
        assert res['total_requested_qty'] == 100.0
        assert len(res['lines']) == 1
        assert res['lines'][0]['product_name'] == 'Fresh Organic Milk 1L'

    def test_create_transfer_multi_line_with_batches(self):
        self.transfer_repo.create.return_value = {
            'id': 2,
            'transfer_number': 'TRF-00002',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 3,
            'status': 'Draft',
            'transfer_date': date.today(),
            'is_active': True,
        }
        self.transfer_repo.get.return_value = {
            'id': 2,
            'transfer_number': 'TRF-00002',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 3,
            'status': 'Draft',
            'transfer_date': date.today(),
            'is_active': True,
        }
        self.line_repo.list.return_value = [
            {'id': 20, 'transfer_id': 2, 'product_id': 101, 'qty_requested': 50.0, 'qty_dispatched': 0.0, 'qty_received': 0.0, 'qty_lost': 0.0, 'batch_id': 501, 'batch_number': 'LOT-M1', 'line_number': 1, 'is_active': True},
            {'id': 21, 'transfer_id': 2, 'product_id': 102, 'qty_requested': 30.0, 'qty_dispatched': 0.0, 'qty_received': 0.0, 'qty_lost': 0.0, 'batch_id': 502, 'batch_number': 'LOT-B2', 'line_number': 2, 'is_active': True},
            {'id': 22, 'transfer_id': 2, 'product_id': 103, 'qty_requested': 20.0, 'qty_dispatched': 0.0, 'qty_received': 0.0, 'qty_lost': 0.0, 'batch_id': None, 'batch_number': None, 'line_number': 3, 'is_active': True},
        ]

        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=3,
            lines=[
                StockTransferLineCreate(product_id=101, qty_requested=50.0, batch_id=501, batch_number='LOT-M1'),
                StockTransferLineCreate(product_id=102, qty_requested=30.0, batch_id=502, batch_number='LOT-B2'),
                StockTransferLineCreate(product_id=103, qty_requested=20.0),
            ]
        )

        with patch('modules.warehouse.services.stock_transfer_service.generate_stock_transfer_number', return_value='TRF-00002'):
            res = self.service.create_transfer(payload)

        assert res['lines_count'] == 3
        assert res['total_requested_qty'] == 100.0
        assert self.line_repo.create.call_count == 3

    def test_create_transfer_same_source_and_destination_rejected(self):
        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=1,
            lines=[StockTransferLineCreate(product_id=101, qty_requested=10.0)]
        )
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 400
        assert "must be different" in exc.value.detail

    def test_create_transfer_nonexistent_source_warehouse_rejected(self):
        payload = StockTransferCreate(
            source_warehouse_id=999,
            destination_warehouse_id=2,
            lines=[StockTransferLineCreate(product_id=101, qty_requested=10.0)]
        )
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 404
        assert "Source warehouse #999 not found" in exc.value.detail

    def test_create_transfer_nonexistent_destination_warehouse_rejected(self):
        payload = StockTransferCreate(
            source_warehouse_id=1,
            destination_warehouse_id=888,
            lines=[StockTransferLineCreate(product_id=101, qty_requested=10.0)]
        )
        with pytest.raises(HTTPException) as exc:
            self.service.create_transfer(payload)
        assert exc.value.status_code == 404
        assert "Destination warehouse #888 not found" in exc.value.detail

    def test_create_transfer_invalid_line_quantity_zero_rejected(self):
        payload = {
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'lines': [{'product_id': 101, 'qty_requested': 0}]
        }
        with patch('modules.warehouse.services.stock_transfer_service.generate_stock_transfer_number', return_value='TRF-00001'):
            with pytest.raises(HTTPException) as exc:
                self.service.create_transfer(payload)
        assert exc.value.status_code == 400
        assert "Requested quantity must be greater than 0" in exc.value.detail

    def test_draft_line_add_update_delete_lifecycle(self):
        # 1. Add line to Draft
        self.transfer_repo.get.return_value = {'id': 10, 'status': 'Draft'}
        self.line_repo.list.return_value = [{'id': 1}]
        self.line_repo.create.return_value = {'id': 2, 'transfer_id': 10, 'product_id': 102, 'qty_requested': 15.0, 'line_number': 2}
        added = self.service.add_line(10, {'product_id': 102, 'qty_requested': 15.0})
        assert added['id'] == 2

        # 2. Update line on Draft
        self.line_repo.get.return_value = {'id': 2, 'transfer_id': 10}
        self.line_repo.update.return_value = {'id': 2, 'transfer_id': 10, 'qty_requested': 25.0}
        updated = self.service.update_line(2, StockTransferLineUpdate(qty_requested=25.0))
        assert updated['qty_requested'] == 25.0

        # 3. Delete line on Draft
        self.line_repo.delete.return_value = True
        deleted = self.service.delete_line(2)
        assert deleted['success'] is True


# ---------------------------------------------------------------------------
# 2. Source Stock Deduction & In-Transit Tracking Tests (Dispatch)
# ---------------------------------------------------------------------------

class TestSourceStockDeductionAndInTransitTracking:
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

        self.transfer_draft = {
            'id': 100,
            'transfer_number': 'TRF-00100',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': date.today(),
            'notes': '',
            'is_active': True,
        }
        self.lines_data = [
            {
                'id': 1,
                'transfer_id': 100,
                'product_id': 101,
                'qty_requested': 60.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'batch_id': 77,
                'line_number': 1,
                'is_active': True,
            },
            {
                'id': 2,
                'transfer_id': 100,
                'product_id': 102,
                'qty_requested': 40.0,
                'qty_dispatched': 0.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'batch_id': None,
                'line_number': 2,
                'is_active': True,
            }
        ]

    def test_dispatch_transfer_deducts_source_and_increments_in_transit(self):
        state = dict(self.transfer_draft)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        def mock_update(tid, update_fields, **kwargs):
            state.update(update_fields)
            return dict(state)
        self.transfer_repo.update.side_effect = mock_update

        self.line_repo.list.return_value = [dict(l) for l in self.lines_data]
        self.batch_repo.get.return_value = {'id': 77, 'quantity': 100.0, 'status': 'Available'}

        dispatch_payload = StockTransferDispatch(
            carrier='SwiftFreight Logistics',
            tracking_number='TRK-998877',
            dispatched_by=3,
            notes='Dispatched on refrigerated truck #4',
        )

        res = self.service.dispatch_transfer(100, dispatch_payload)

        # 1. Verify status and header
        assert res['status'] == 'In Transit'
        assert state['carrier'] == 'SwiftFreight Logistics'
        assert state['tracking_number'] == 'TRK-998877'
        assert state['dispatched_by'] == 3

        # 2. Verify stock_service.transfer_dispatch calls
        assert self.stock_service.transfer_dispatch.call_count == 2
        calls = self.stock_service.transfer_dispatch.call_args_list

        # Call 1: Product 101 (60 units)
        assert calls[0].kwargs['product_id'] == 101
        assert calls[0].kwargs['source_warehouse_id'] == 1
        assert calls[0].kwargs['destination_warehouse_id'] == 2
        assert calls[0].kwargs['qty'] == 60.0
        assert calls[0].kwargs['reference_type'] == 'StockTransfer'
        assert calls[0].kwargs['reference_id'] == 100

        # Call 2: Product 102 (40 units)
        assert calls[1].kwargs['product_id'] == 102
        assert calls[1].kwargs['source_warehouse_id'] == 1
        assert calls[1].kwargs['destination_warehouse_id'] == 2
        assert calls[1].kwargs['qty'] == 40.0

        # 3. Verify batch deduction on source
        self.batch_repo.update.assert_called_once_with(77, {'quantity': 40.0, 'status': 'Partially Used'}, conn=ANY)

    def test_dispatch_transfer_with_itemized_dispatched_quantities(self):
        state = dict(self.transfer_draft)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        self.transfer_repo.update.side_effect = lambda tid, u, **kwargs: dict(state, **u)
        self.line_repo.list.return_value = [dict(l) for l in self.lines_data]

        # Dispatch partial: 50 instead of 60 for line 1, 35 instead of 40 for line 2
        dispatch_payload = StockTransferDispatch(
            dispatched_by=2,
            lines=[
                StockTransferDispatchLine(line_id=1, qty_dispatched=50.0),
                StockTransferDispatchLine(line_id=2, qty_dispatched=35.0),
            ]
        )

        res = self.service.dispatch_transfer(100, dispatch_payload)

        assert self.stock_service.transfer_dispatch.call_count == 2
        calls = self.stock_service.transfer_dispatch.call_args_list
        assert calls[0].kwargs['qty'] == 50.0
        assert calls[1].kwargs['qty'] == 35.0

    def test_dispatch_transfer_not_draft_status_rejected(self):
        self.transfer_repo.get.return_value = {**self.transfer_draft, 'status': 'In Transit'}
        with pytest.raises(HTTPException) as exc:
            self.service.dispatch_transfer(100)
        assert exc.value.status_code == 400
        assert "Status must be 'Draft' or 'Pending'" in exc.value.detail

    def test_dispatch_transfer_no_lines_rejected(self):
        self.transfer_repo.get.return_value = dict(self.transfer_draft)
        self.line_repo.list.return_value = []
        with pytest.raises(HTTPException) as exc:
            self.service.dispatch_transfer(100)
        assert exc.value.status_code == 400
        assert "no line items" in exc.value.detail


# ---------------------------------------------------------------------------
# 3. Receiving Inventory Addition & Receipt Workflows Tests
# ---------------------------------------------------------------------------

class TestReceivingInventoryAdditionAndReceiptWorkflows:
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
            'id': 105,
            'transfer_number': 'TRF-00105',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'carrier': 'ColdChain Express',
            'tracking_number': 'CCX-1234',
            'dispatched_at': datetime.now(),
            'dispatched_by': 1,
            'is_active': True,
        }
        self.lines_in_transit = [
            {
                'id': 50,
                'transfer_id': 105,
                'product_id': 101,
                'qty_requested': 80.0,
                'qty_dispatched': 80.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'batch_number': 'LOT-2026-X',
                'line_number': 1,
                'is_active': True,
            }
        ]

    def test_full_receipt_adds_destination_stock_and_clears_in_transit(self):
        state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        def mock_update(tid, u, **kwargs):
            state.update(u)
            return dict(state)
        self.transfer_repo.update.side_effect = mock_update

        self.line_repo.list.return_value = [dict(l) for l in self.lines_in_transit]
        self.batch_repo.list.return_value = []  # No existing batch at dest

        receive_payload = StockTransferReceive(
            received_by=7,
            notes='All goods verified intact and temperature compliant',
            lines=[
                StockTransferReceiveLine(line_id=50, qty_received=80.0, qty_lost=0.0)
            ]
        )

        res = self.service.receive_transfer(105, receive_payload)

        # 1. Stock service transfer_receive call
        self.stock_service.transfer_receive.assert_called_once_with(
            product_id=101,
            destination_warehouse_id=2,
            qty_received=80.0,
            qty_dispatched=80.0,
            source_warehouse_id=1,
            reference_type='StockTransfer',
            reference_id=105,
            description='Transfer Receipt: TRF-00105',
            user_id=7,
            conn=ANY,
        )

        # 2. No loss recorded
        self.stock_service.record_transfer_loss.assert_not_called()

        # 3. Status updated to Received
        assert state['status'] == 'Received'
        assert state['received_by'] == 7

        # 4. Destination batch registration
        self.batch_repo.create.assert_called_once()
        b_create_arg = self.batch_repo.create.call_args[0][0]
        assert b_create_arg['product_id'] == 101
        assert b_create_arg['warehouse_id'] == 2
        assert b_create_arg['quantity'] == 80.0
        assert b_create_arg['batch_number'] == 'LOT-2026-X'

    def test_receive_partial_without_loss_sets_partially_received(self):
        state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        def mock_update(tid, u, **kwargs):
            state.update(u)
            return dict(state)
        self.transfer_repo.update.side_effect = mock_update
        self.line_repo.list.return_value = [dict(l) for l in self.lines_in_transit]

        # Received 40 out of 80 dispatched, 0 lost (remaining 40 still unaccounted)
        receive_payload = StockTransferReceive(
            received_by=7,
            lines=[
                StockTransferReceiveLine(line_id=50, qty_received=40.0, qty_lost=0.0)
            ]
        )

        res = self.service.receive_transfer(105, receive_payload)

        assert state['status'] == 'Partially Received'
        self.stock_service.transfer_receive.assert_called_once_with(
            product_id=101,
            destination_warehouse_id=2,
            qty_received=40.0,
            qty_dispatched=80.0,
            source_warehouse_id=1,
            reference_type='StockTransfer',
            reference_id=105,
            description='Transfer Receipt: TRF-00105',
            user_id=7,
            conn=ANY,
        )

    def test_receive_transfer_not_in_transit_rejected(self):
        self.transfer_repo.get.return_value = {**self.transfer_in_transit, 'status': 'Draft'}
        with pytest.raises(HTTPException) as exc:
            self.service.receive_transfer(105)
        assert exc.value.status_code == 400
        assert "Status must be 'In Transit'" in exc.value.detail


# ---------------------------------------------------------------------------
# 4. Transit Discrepancies & Loss Reason Codes Tests
# ---------------------------------------------------------------------------

class TestTransitDiscrepanciesAndLossReasonCodes:
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
            'id': 200,
            'transfer_number': 'TRF-00200',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'dispatched_at': datetime.now(),
            'is_active': True,
        }

    @pytest.mark.parametrize("loss_reason,expected_note", [
        ("Transit Damage", "Box dropped and cartons crushed during offloading"),
        ("Spillage", "Liquid leaked from fractured container cap"),
        ("Theft", "Tamper evident seal broken on pallet #3"),
        ("Expired", "Past expiry date upon arrival"),
        ("Shortage", "Shipped quantity did not match invoice count"),
        ("Packaging Failure", "Torn outer packaging exposed goods"),
        ("Temperature Deviation", "Cooling failure during 12h transit route"),
        ("Other", "Custom discrepancy recorded"),
    ])
    def test_receive_with_all_discrepancy_reason_codes(self, loss_reason, expected_note):
        state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        self.transfer_repo.update.side_effect = lambda tid, u, **kwargs: dict(state, **u)

        lines = [
            {
                'id': 1,
                'transfer_id': 200,
                'product_id': 101,
                'qty_dispatched': 50.0,
                'qty_requested': 50.0,
                'qty_received': 0.0,
                'qty_lost': 0.0,
                'line_number': 1,
            }
        ]
        self.line_repo.list.return_value = [dict(l) for l in lines]

        # 42 units intact, 8 units lost with reason
        payload = StockTransferReceive(
            received_by=4,
            lines=[
                StockTransferReceiveLine(
                    line_id=1,
                    qty_received=42.0,
                    qty_lost=8.0,
                    loss_reason=loss_reason,
                    loss_notes=expected_note,
                )
            ]
        )

        res = self.service.receive_transfer(200, payload)

        # 1. Stock receive: 42 received, 50 dispatched cleared from in-transit
        self.stock_service.transfer_receive.assert_called_once_with(
            product_id=101,
            destination_warehouse_id=2,
            qty_received=42.0,
            qty_dispatched=50.0,
            source_warehouse_id=1,
            reference_type='StockTransfer',
            reference_id=200,
            description='Transfer Receipt: TRF-00200',
            user_id=4,
            conn=ANY,
        )

        # 2. Transfer loss recorded with reason and notes
        self.stock_service.record_transfer_loss.assert_called_once_with(
            product_id=101,
            warehouse_id=2,
            qty_lost=8.0,
            loss_reason=loss_reason,
            loss_notes=expected_note,
            reference_type='StockTransfer',
            reference_id=200,
            description='Transfer Discrepancy: TRF-00200',
            decrement_in_transit=False,
            user_id=4,
            conn=ANY,
        )

        # 3. Status is Received because 42 received + 8 lost = 50 dispatched (all accounted for)
        self.transfer_repo.update.assert_called()
        hdr_update = self.transfer_repo.update.call_args[0][1]
        assert hdr_update['status'] == 'Received'

    def test_receive_with_separate_losses_payload_structure(self):
        state = dict(self.transfer_in_transit)
        self.transfer_repo.get.side_effect = lambda tid, **kwargs: dict(state)
        self.transfer_repo.update.side_effect = lambda tid, u, **kwargs: dict(state, **u)

        lines = [
            {'id': 11, 'transfer_id': 200, 'product_id': 101, 'qty_dispatched': 100.0, 'line_number': 1},
            {'id': 12, 'transfer_id': 200, 'product_id': 102, 'qty_dispatched': 50.0, 'line_number': 2},
        ]
        self.line_repo.list.return_value = [dict(l) for l in lines]

        payload = StockTransferReceive(
            received_by=4,
            lines=[
                StockTransferReceiveLine(line_id=11, qty_received=90.0),
                StockTransferReceiveLine(line_id=12, qty_received=45.0),
            ],
            losses=[
                StockTransferLossDetail(line_id=11, product_id=101, qty_lost=10.0, loss_reason='Transit Damage', loss_notes='Broken pallet'),
                StockTransferLossDetail(line_id=12, product_id=102, qty_lost=5.0, loss_reason='Spillage', loss_notes='Leaking tub'),
            ]
        )

        res = self.service.receive_transfer(200, payload)

        assert self.stock_service.record_transfer_loss.call_count == 2
        calls = self.stock_service.record_transfer_loss.call_args_list

        assert calls[0].kwargs['product_id'] == 101
        assert calls[0].kwargs['qty_lost'] == 10.0
        assert calls[0].kwargs['loss_reason'] == 'Transit Damage'

        assert calls[1].kwargs['product_id'] == 102
        assert calls[1].kwargs['qty_lost'] == 5.0
        assert calls[1].kwargs['loss_reason'] == 'Spillage'


# ---------------------------------------------------------------------------
# 5. Stock Transfer Cancellation & Stock Restoration Tests
# ---------------------------------------------------------------------------

class TestStockTransferCancellation:
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

    def test_cancel_draft_transfer_does_not_call_stock_service(self):
        self.transfer_repo.get.return_value = {
            'id': 301,
            'transfer_number': 'TRF-00301',
            'status': 'Draft',
            'notes': 'Initial draft',
        }

        res = self.service.cancel_transfer(301, reason='Branch store revoked request')

        self.stock_service.cancel_transfer_dispatch.assert_not_called()
        self.transfer_repo.update.assert_called_once_with(
            301,
            {'status': 'Cancelled', 'notes': 'Initial draft [Cancelled: Branch store revoked request]'},
            conn=ANY
        )

    def test_cancel_in_transit_transfer_reverses_stock_and_batches(self):
        self.transfer_repo.get.return_value = {
            'id': 302,
            'transfer_number': 'TRF-00302',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'notes': '',
        }
        self.line_repo.list.return_value = [
            {'id': 1, 'transfer_id': 302, 'product_id': 101, 'qty_dispatched': 30.0, 'batch_id': 99}
        ]
        self.batch_repo.get.return_value = {'id': 99, 'quantity': 70.0, 'status': 'Partially Used'}

        res = self.service.cancel_transfer(302, reason='Highway closed due to blizzard - truck returned')

        # 1. Stock reversal called
        self.stock_service.cancel_transfer_dispatch.assert_called_once_with(
            product_id=101,
            source_warehouse_id=1,
            destination_warehouse_id=2,
            qty=30.0,
            reference_type='StockTransfer',
            reference_id=302,
            description='Transfer Cancelled: TRF-00302 (Highway closed due to blizzard - truck returned)',
            conn=ANY,
        )

        # 2. Batch quantity restored
        self.batch_repo.update.assert_called_once_with(
            99,
            {'quantity': 100.0, 'status': 'Available'},
            conn=ANY,
        )

        # 3. Header marked Cancelled
        assert self.transfer_repo.update.call_args[0][1]['status'] == 'Cancelled'

    def test_cancel_received_transfer_rejected(self):
        self.transfer_repo.get.return_value = {
            'id': 303,
            'transfer_number': 'TRF-00303',
            'status': 'Received',
        }
        with pytest.raises(HTTPException) as exc:
            self.service.cancel_transfer(303)
        assert exc.value.status_code == 400
        assert "already been received" in exc.value.detail


# ---------------------------------------------------------------------------
# 6. Multi-Tenant Isolation Tests
# ---------------------------------------------------------------------------

class TestStockTransferMultiTenantIsolation:
    def setup_method(self):
        self.transfer_repo = InMemoryMockRepo('T0108', [
            {
                'id': 1,
                'transfer_number': 'TRF-T1-001',
                'source_warehouse_id': 10,
                'destination_warehouse_id': 20,
                'status': 'In Transit',
                'business_id': 1,
                'is_active': True,
            },
            {
                'id': 2,
                'transfer_number': 'TRF-T2-002',
                'source_warehouse_id': 30,
                'destination_warehouse_id': 40,
                'status': 'Draft',
                'business_id': 2,
                'is_active': True,
            },
            {
                'id': 3,
                'transfer_number': 'TRF-T1-003',
                'source_warehouse_id': 10,
                'destination_warehouse_id': 20,
                'status': 'Draft',
                'business_id': 1,
                'is_active': True,
            }
        ])

        self.line_repo = InMemoryMockRepo('T0109', [
            {'id': 101, 'transfer_id': 1, 'product_id': 500, 'qty_requested': 50.0, 'qty_dispatched': 50.0, 'business_id': 1},
            {'id': 102, 'transfer_id': 2, 'product_id': 600, 'qty_requested': 30.0, 'qty_dispatched': 0.0, 'business_id': 2},
            {'id': 103, 'transfer_id': 3, 'product_id': 500, 'qty_requested': 25.0, 'qty_dispatched': 0.0, 'business_id': 1},
        ])

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

    def test_list_transfers_strictly_scoped_by_tenant(self):
        # Under Tenant 1
        with tenant_context(1):
            t1_list = self.service.list()
            assert len(t1_list) == 2
            assert all(t['business_id'] == 1 for t in t1_list)
            assert {t['id'] for t in t1_list} == {1, 3}

        # Under Tenant 2
        with tenant_context(2):
            t2_list = self.service.list()
            assert len(t2_list) == 1
            assert t2_list[0]['id'] == 2
            assert t2_list[0]['business_id'] == 2

    def test_get_transfer_cross_tenant_returns_none(self):
        # Tenant 1 tries to access Tenant 2's transfer #2
        with tenant_context(1):
            assert self.service.get(2) is None

        # Tenant 2 tries to access Tenant 1's transfer #1
        with tenant_context(2):
            assert self.service.get(1) is None

    def test_create_transfer_auto_injects_active_tenant_id(self):
        self.wh_repo.get.return_value = {'id': 10, 'name': 'WH'}

        with tenant_context(1):
            payload = {
                'source_warehouse_id': 10,
                'destination_warehouse_id': 20,
                'lines': [{'product_id': 500, 'qty_requested': 10.0}]
            }
            with patch('modules.warehouse.services.stock_transfer_service.generate_stock_transfer_number', return_value='TRF-T1-NEW'):
                created = self.service.create_transfer(payload)

            assert created['business_id'] == 1

        # Confirm it cannot be read under Tenant 2
        with tenant_context(2):
            assert self.service.get(created['id']) is None

    def test_list_in_transit_transfers_strictly_tenant_scoped(self):
        with tenant_context(1):
            in_transit = self.service.list_in_transit()
            assert len(in_transit) == 1
            assert in_transit[0]['id'] == 1
            assert in_transit[0]['status'] == 'In Transit'

        with tenant_context(2):
            # Tenant 2 has no In-Transit transfers
            in_transit = self.service.list_in_transit()
            assert len(in_transit) == 0

    def test_transfer_lines_tenant_scoping(self):
        with tenant_context(1):
            lines = self.line_repo.list()
            assert len(lines) == 2
            assert all(l['business_id'] == 1 for l in lines)

        with tenant_context(2):
            lines = self.line_repo.list()
            assert len(lines) == 1
            assert lines[0]['business_id'] == 2
