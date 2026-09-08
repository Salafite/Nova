import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from modules.purchasing.services.purchase_return_service import PurchaseReturnService, VALID_RETURN_STATUS_TRANSITIONS
from modules.purchasing.models.purchase_return import RMAStatus


class TestPurchaseReturnServiceStateMachine:
    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def mock_invoice_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def service(self, mock_repo, mock_invoice_repo):
        svc = PurchaseReturnService(repo=mock_repo, invoice_repo=mock_invoice_repo)
        svc.stock_service = MagicMock()
        return svc

    def test_valid_transitions_map(self):
        assert VALID_RETURN_STATUS_TRANSITIONS[RMAStatus.DRAFT.value] == ['Approved', 'Cancelled']
        assert VALID_RETURN_STATUS_TRANSITIONS[RMAStatus.APPROVED.value] == ['Returned', 'Cancelled']
        assert VALID_RETURN_STATUS_TRANSITIONS[RMAStatus.RETURNED.value] == []
        assert VALID_RETURN_STATUS_TRANSITIONS[RMAStatus.CANCELLED.value] == []

    def test_create_sets_defaults(self, service, mock_repo):
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 1, **data}

        payload = {'supplier_id': 10}
        result = service.create(payload)

        assert result['status'] == RMAStatus.DRAFT.value
        assert result['return_number'].startswith('RMA-')
        assert 'return_date' in result

    def test_approve_return_success_with_debit_memo(self, service, mock_repo, mock_invoice_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Draft',
            'supplier_id': 10,
            'purchase_order_id': 5,
            'total_amount': 0.0,
            'notes': None,
            'debit_memo_id': None,
        }
        lines = [
            {'id': 1, 'return_id': 1, 'product_id': 101, 'product_name': 'Item A', 'qty': 5.0, 'unit_price': 10.0, 'line_total': 50.0},
            {'id': 2, 'return_id': 1, 'product_id': 102, 'product_name': 'Item B', 'qty': 2.0, 'unit_price': 25.0, 'line_total': 50.0},
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}
        mock_invoice_repo.create.return_value = {
            'id': 99,
            'invoice_number': 'DM-00001',
            'invoice_type': 'Debit Memo',
            'partner_id': 10,
            'purchase_return_id': 1,
            'total_amount': 100.0,
            'status': 'Unpaid',
        }

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.approve_return(1, approved_by=42, notes='Approved by QA')

            assert result['status'] == RMAStatus.APPROVED.value
            assert result['approved_by'] == 42
            assert result['approved_at'] is not None
            assert result['total_amount'] == 100.0
            assert result['debit_memo_id'] == 99
            assert 'Approved by QA' in result['notes']

            # Verify debit memo created with proper supplier, PO reference, and total amount
            assert mock_invoice_repo.create.called
            dm_payload = mock_invoice_repo.create.call_args[0][0]
            assert dm_payload['invoice_type'] == 'Debit Memo'
            assert dm_payload['partner_id'] == 10
            assert dm_payload['purchase_order_id'] == 5
            assert dm_payload['purchase_return_id'] == 1
            assert dm_payload['total_amount'] == 100.0
            assert dm_payload['status'] == 'Unpaid'

    def test_approve_return_skips_debit_memo_when_disabled(self, service, mock_repo, mock_invoice_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Draft',
            'supplier_id': 10,
            'total_amount': 0.0,
            'notes': None,
            'debit_memo_id': None,
        }
        lines = [
            {'id': 1, 'return_id': 1, 'product_id': 101, 'product_name': 'Item A', 'qty': 5.0, 'unit_price': 10.0, 'line_total': 50.0},
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.approve_return(1, approved_by=42, create_debit_memo=False)

            assert result['status'] == RMAStatus.APPROVED.value
            assert result.get('debit_memo_id') is None
            assert not mock_invoice_repo.create.called

    def test_approve_return_does_not_duplicate_existing_debit_memo(self, service, mock_repo, mock_invoice_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Draft',
            'supplier_id': 10,
            'total_amount': 50.0,
            'notes': None,
            'debit_memo_id': 77,  # already has debit memo
        }
        lines = [
            {'id': 1, 'return_id': 1, 'product_id': 101, 'product_name': 'Item A', 'qty': 5.0, 'unit_price': 10.0, 'line_total': 50.0},
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.approve_return(1, approved_by=42, create_debit_memo=True)

            assert result['status'] == RMAStatus.APPROVED.value
            assert not mock_invoice_repo.create.called

    def test_create_debit_memo_for_return_direct(self, service, mock_invoice_repo):
        return_rec = {
            'id': 10,
            'return_number': 'RMA-202609-0010',
            'supplier_id': 25,
            'purchase_order_id': 12,
            'return_date': '2026-09-08',
            'total_amount': 250.0,
            'business_id': 2,
        }
        lines = [
            {'id': 1, 'return_id': 10, 'qty': 10.0, 'unit_price': 25.0, 'line_total': 250.0},
        ]
        mock_invoice_repo.create.side_effect = lambda data: {'id': 50, **data}

        dm = service.create_debit_memo_for_return(return_rec, lines)
        assert dm['id'] == 50
        assert dm['invoice_type'] == 'Debit Memo'
        assert dm['partner_id'] == 25
        assert dm['purchase_order_id'] == 12
        assert dm['purchase_return_id'] == 10
        assert dm['total_amount'] == 250.0
        assert dm['status'] == 'Unpaid'
        assert dm['business_id'] == 2

    def test_get_debit_memo_lookup(self, service, mock_repo, mock_invoice_repo):
        mock_repo.get.return_value = {'id': 1, 'debit_memo_id': 88}
        mock_invoice_repo.get.return_value = {'id': 88, 'invoice_type': 'Debit Memo', 'total_amount': 150.0}

        dm = service.get_debit_memo(1)
        assert dm is not None
        assert dm['id'] == 88
        assert dm['total_amount'] == 150.0

    def test_approve_return_fails_when_no_lines(self, service, mock_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Draft',
            'supplier_id': 10,
        }
        mock_repo.get.return_value = existing_return

        with patch.object(service, '_get_lines', return_value=[]):
            with pytest.raises(HTTPException) as exc_info:
                service.approve_return(1)
            assert exc_info.value.status_code == 400
            assert 'no line items' in exc_info.value.detail.lower()

    def test_approve_return_fails_when_not_draft(self, service, mock_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Approved',
            'supplier_id': 10,
        }
        mock_repo.get.return_value = existing_return

        with pytest.raises(HTTPException) as exc_info:
            service.approve_return(1)
        assert exc_info.value.status_code == 400
        assert 'cannot approve' in exc_info.value.detail.lower()

    def test_complete_return_success(self, service, mock_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Approved',
            'supplier_id': 10,
        }
        lines = [
            {'id': 1, 'return_id': 1, 'product_id': 101, 'product_name': 'Item A', 'qty': 5.0},
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.complete_return(1, notes='Shipped back')

            assert result['status'] == RMAStatus.RETURNED.value
            assert service.stock_service.record_movement.called
            call_kwargs = service.stock_service.record_movement.call_args[1]
            assert call_kwargs['product_id'] == 101
            assert call_kwargs['qty_change'] == -5.0
            assert call_kwargs['movement_type'] == 'Purchase Return'

    def test_complete_return_fails_when_not_approved(self, service, mock_repo):
        existing_return = {
            'id': 1,
            'return_number': 'RMA-202609-0001',
            'status': 'Draft',
            'supplier_id': 10,
        }
        mock_repo.get.return_value = existing_return

        with pytest.raises(HTTPException) as exc_info:
            service.complete_return(1)
        assert exc_info.value.status_code == 400
        assert 'cannot complete return' in exc_info.value.detail.lower()

    def test_cancel_return_from_draft_and_approved(self, service, mock_repo):
        draft_return = {'id': 1, 'status': 'Draft', 'notes': None}
        mock_repo.get.return_value = draft_return
        mock_repo.update.side_effect = lambda id_val, data: {**draft_return, **data}

        result = service.cancel_return(1, reason='Vendor agreed to partial credit on invoice')
        assert result['status'] == RMAStatus.CANCELLED.value
        assert 'Vendor agreed to partial credit' in result['notes']

        approved_return = {'id': 2, 'status': 'Approved', 'notes': None}
        mock_repo.get.return_value = approved_return
        mock_repo.update.side_effect = lambda id_val, data: {**approved_return, **data}

        result2 = service.cancel_return(2, reason='Cancelled by supervisor')
        assert result2['status'] == RMAStatus.CANCELLED.value

    def test_cancel_return_fails_when_terminal(self, service, mock_repo):
        returned_return = {'id': 1, 'status': 'Returned'}
        mock_repo.get.return_value = returned_return

        with pytest.raises(HTTPException) as exc_info:
            service.cancel_return(1, reason='Too late')
        assert exc_info.value.status_code == 400
        assert 'cannot cancel' in exc_info.value.detail.lower()

    def test_invalid_status_transition_via_update(self, service, mock_repo):
        existing_return = {'id': 1, 'status': 'Draft'}
        mock_repo.get.return_value = existing_return

        with pytest.raises(HTTPException) as exc_info:
            service.update(1, {'status': 'Returned'})
        assert exc_info.value.status_code == 400
        assert 'invalid purchase return status transition' in exc_info.value.detail.lower()

    def test_nonexistent_return_raises_404(self, service, mock_repo):
        mock_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.approve_return(999)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            service.update(999, {'status': 'Approved'})
        assert exc_info.value.status_code == 404

    def test_quarantine_inventory_for_return_direct(self, service):
        service.batch_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.grn_repo = MagicMock()
        service.stock_service = MagicMock()

        return_rec = {
            'id': 5,
            'return_number': 'RMA-202609-0005',
            'goods_receipt_id': 12,
        }
        lines = [
            {
                'id': 101,
                'return_id': 5,
                'product_id': 201,
                'product_name': 'Organic Apples',
                'qty': 15.0,
                'batch_id': 33,
                'batch_number': 'LOT-APPLES-001',
                'reason_code': 'damaged',
            },
        ]
        service.grn_repo.get.return_value = {'id': 12, 'warehouse_id': 3}
        service.batch_repo.get.return_value = {'id': 33, 'status': 'Available', 'notes': 'Fresh harvest'}

        quarantined = service.quarantine_inventory_for_return(return_rec, lines)

        assert len(quarantined) == 1
        assert quarantined[0]['product_id'] == 201
        assert quarantined[0]['batch_id'] == 33
        assert quarantined[0]['quarantine_status'] == 'Quarantine'

        # Verify batch status updated in T0088
        service.batch_repo.update.assert_called_once()
        batch_update_args = service.batch_repo.update.call_args
        assert batch_update_args[0][0] == 33
        assert batch_update_args[0][1]['status'] == 'Quarantine'
        assert 'Quarantined via RMA RMA-202609-0005' in batch_update_args[0][1]['notes']

        # Verify line quarantine_status updated in T0082
        service.lines_repo.update.assert_called_once_with(101, {'quarantine_status': 'Quarantine'})

        # Verify stock movement recorded in T0064 with warehouse_id=3 and negative qty
        service.stock_service.record_movement.assert_called_once()
        sm_args = service.stock_service.record_movement.call_args[1]
        assert sm_args['product_id'] == 201
        assert sm_args['warehouse_id'] == 3
        assert sm_args['movement_type'] == 'Quarantine Write-Down'
        assert sm_args['qty_change'] == -15.0
        assert sm_args['reference_type'] == 'PurchaseReturn'
        assert sm_args['reference_id'] == 5
        assert 'RMA Quarantine Write-Down' in sm_args['description']

    def test_approve_return_quarantines_batches_and_records_stock_movements(self, service, mock_repo, mock_invoice_repo):
        service.batch_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.grn_repo = MagicMock()
        service.stock_service = MagicMock()

        existing_return = {
            'id': 7,
            'return_number': 'RMA-202609-0007',
            'status': 'Draft',
            'supplier_id': 15,
            'purchase_order_id': 8,
            'goods_receipt_id': 20,
            'total_amount': 0.0,
            'notes': None,
            'debit_memo_id': None,
        }
        lines = [
            {
                'id': 50,
                'return_id': 7,
                'product_id': 301,
                'product_name': 'Milk Cartons',
                'qty': 20.0,
                'unit_price': 5.0,
                'line_total': 100.0,
                'batch_id': 45,
                'batch_number': 'LOT-MILK-99',
                'reason_code': 'expired',
            }
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}
        service.grn_repo.get.return_value = {'id': 20, 'warehouse_id': 2}
        service.batch_repo.get.return_value = {'id': 45, 'status': 'Available', 'notes': None}
        mock_invoice_repo.create.return_value = {'id': 101, 'invoice_type': 'Debit Memo'}

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.approve_return(7, approved_by=10, quarantine_inventory=True)

            assert result['status'] == RMAStatus.APPROVED.value
            assert result['total_amount'] == 100.0

            # Batch quarantined
            service.batch_repo.update.assert_called_once_with(
                45,
                {'status': 'Quarantine', 'notes': 'Quarantined via RMA RMA-202609-0007'}
            )
            # Line quarantine status updated
            service.lines_repo.update.assert_called_once_with(
                50,
                {'quarantine_status': 'Quarantine'}
            )
            # Salable inventory written down
            service.stock_service.record_movement.assert_called_once()
            sm_kwargs = service.stock_service.record_movement.call_args[1]
            assert sm_kwargs['product_id'] == 301
            assert sm_kwargs['qty_change'] == -20.0
            assert sm_kwargs['movement_type'] == 'Quarantine Write-Down'

    def test_approve_return_skips_quarantine_when_disabled(self, service, mock_repo, mock_invoice_repo):
        service.batch_repo = MagicMock()
        service.stock_service = MagicMock()

        existing_return = {
            'id': 8,
            'return_number': 'RMA-202609-0008',
            'status': 'Draft',
            'supplier_id': 15,
            'total_amount': 50.0,
            'notes': None,
            'debit_memo_id': None,
        }
        lines = [
            {'id': 51, 'return_id': 8, 'product_id': 301, 'qty': 10.0, 'unit_price': 5.0, 'line_total': 50.0}
        ]
        mock_repo.get.return_value = existing_return
        mock_repo.update.side_effect = lambda id_val, data: {**existing_return, **data}
        mock_invoice_repo.create.return_value = {'id': 102, 'invoice_type': 'Debit Memo'}

        with patch.object(service, '_get_lines', return_value=lines):
            result = service.approve_return(8, quarantine_inventory=False)

            assert result['status'] == RMAStatus.APPROVED.value
            assert not service.batch_repo.update.called
            assert not service.stock_service.record_movement.called

    def test_quarantine_inventory_handles_batch_number_lookup(self, service):
        service.batch_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.grn_repo = MagicMock()
        service.stock_service = MagicMock()

        return_rec = {'id': 9, 'return_number': 'RMA-202609-0009'}
        lines = [
            {
                'id': 55,
                'return_id': 9,
                'product_id': 401,
                'product_name': 'Frozen Berries',
                'qty': 8.0,
                'batch_id': None,
                'batch_number': 'LOT-BERRIES-44',
            }
        ]
        service.batch_repo.list.return_value = [
            {'id': 77, 'batch_number': 'LOT-BERRIES-44', 'status': 'Available', 'warehouse_id': 4}
        ]

        quarantined = service.quarantine_inventory_for_return(return_rec, lines)
        assert len(quarantined) == 1
        service.batch_repo.update.assert_called_once_with(
            77,
            {'status': 'Quarantine', 'notes': 'Quarantined via RMA RMA-202609-0009'}
        )
        service.stock_service.record_movement.assert_called_once()
        sm_kwargs = service.stock_service.record_movement.call_args[1]
        assert sm_kwargs['product_id'] == 401
        assert sm_kwargs['warehouse_id'] == 4
        assert sm_kwargs['qty_change'] == -8.0

