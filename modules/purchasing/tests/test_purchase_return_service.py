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

    def test_create_from_goods_receipt_with_explicit_lines(self, service, mock_repo):
        service.grn_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.po_repo = MagicMock()
        service.po_line_repo = MagicMock()
        service.batch_repo = MagicMock()

        grn_data = {
            'id': 100,
            'receipt_number': 'GRN-202609-001',
            'purchase_order_id': 20,
            'warehouse_id': 1,
            'business_id': 1,
        }
        service.grn_repo.get.return_value = grn_data
        service.po_repo.get.return_value = {'id': 20, 'supplier_id': 55}
        service.batch_repo.list.return_value = [{'id': 88, 'batch_number': 'LOT-123'}]

        mock_repo.create.side_effect = lambda data, **kw: {'id': 10, **data}
        service.lines_repo.create.side_effect = lambda data, **kw: {'id': 500, **data}

        rejection_payload = {
            'supplier_id': 55,
            'reason': 'Damaged boxes during unloading',
            'notes': 'Dock inspection supervisor signoff',
            'lines': [
                {
                    'product_id': 301,
                    'product_name': 'Avocados Grade A',
                    'qty_rejected': 10.0,
                    'unit_price': 15.0,
                    'batch_number': 'LOT-123',
                    'reason_code': 'damaged',
                    'reason_details': 'Crushed packaging',
                    'photos': [{'url': 'http://example.com/img1.jpg'}],
                }
            ],
            'attachments': [{'filename': 'bol_dock_copy.pdf'}],
        }

        result = service.create_from_goods_receipt(100, rejection_payload)

        assert result['id'] == 10
        assert result['status'] == RMAStatus.DRAFT.value
        assert result['goods_receipt_id'] == 100
        assert result['purchase_order_id'] == 20
        assert result['supplier_id'] == 55
        assert result['total_amount'] == 150.0
        assert result['reason'] == 'Damaged boxes during unloading'
        assert result['return_number'].startswith('RMA-')
        assert len(result['lines']) == 1

        line = result['lines'][0]
        assert line['return_id'] == 10
        assert line['product_id'] == 301
        assert line['qty'] == 10.0
        assert line['unit_price'] == 15.0
        assert line['line_total'] == 150.0
        assert line['batch_id'] == 88
        assert line['quarantine_status'] == 'Quarantine'
        assert line['disposition'] == 'Return to Vendor'
        assert 'damaged: Crushed packaging' in line['reason_code']

    def test_create_from_goods_receipt_fallback_to_grn_lines(self, service, mock_repo):
        service.grn_repo = MagicMock()
        service.grn_line_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.po_repo = MagicMock()
        service.po_line_repo = MagicMock()
        service.batch_repo = MagicMock()

        grn_data = {
            'id': 101,
            'receipt_number': 'GRN-202609-002',
            'purchase_order_id': 21,
            'warehouse_id': 1,
        }
        service.grn_repo.get.return_value = grn_data
        service.po_repo.get.return_value = {'id': 21, 'supplier_id': 60}
        service.grn_line_repo.list.return_value = [
            {
                'id': 1,
                'receipt_id': 101,
                'product_id': 401,
                'product_name': 'Tomatoes',
                'qty_received': 20.0,
                'uom_id': 2,
                'batch_number': 'LOT-TOM-01',
                'expiry_date': '2026-10-01',
            }
        ]
        service.po_line_repo.list.return_value = [{'product_id': 401, 'unit_price': 5.0}]
        service.batch_repo.list.return_value = []

        mock_repo.create.side_effect = lambda data, **kw: {'id': 11, **data}
        service.lines_repo.create.side_effect = lambda data, **kw: {'id': 501, **data}

        result = service.create_from_goods_receipt(101)

        assert result['id'] == 11
        assert result['supplier_id'] == 60
        assert result['total_amount'] == 100.0  # 20.0 * 5.0
        assert len(result['lines']) == 1
        assert result['lines'][0]['qty'] == 20.0
        assert result['lines'][0]['unit_price'] == 5.0
        assert result['lines'][0]['line_total'] == 100.0
        assert result['lines'][0]['batch_number'] == 'LOT-TOM-01'

    def test_create_from_goods_receipt_not_found_raises_404(self, service):
        service.grn_repo = MagicMock()
        service.grn_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.create_from_goods_receipt(999)
        assert exc_info.value.status_code == 404

    def test_create_from_goods_receipt_missing_supplier_raises_400(self, service):
        service.grn_repo = MagicMock()
        service.po_repo = MagicMock()
        service.grn_repo.get.return_value = {'id': 105, 'purchase_order_id': None}
        service.po_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.create_from_goods_receipt(105, {})
        assert exc_info.value.status_code == 400
        assert 'supplier id is required' in exc_info.value.detail.lower()

    def test_create_dock_rejection_convenience_method(self, service, mock_repo):
        service.grn_repo = MagicMock()
        service.lines_repo = MagicMock()
        service.po_repo = MagicMock()
        service.po_line_repo = MagicMock()
        service.batch_repo = MagicMock()

        grn_data = {'id': 102, 'purchase_order_id': 22}
        service.grn_repo.get.return_value = grn_data
        service.po_repo.get.return_value = {'id': 22, 'supplier_id': 70}
        mock_repo.create.side_effect = lambda data, **kw: {'id': 12, **data}
        service.lines_repo.create.side_effect = lambda data, **kw: {'id': 502, **data}

        dock_payload = {
            'goods_receipt_id': 102,
            'supplier_id': 70,
            'lines': [
                {
                    'product_id': 501,
                    'product_name': 'Cheese',
                    'qty_rejected': 5.0,
                    'unit_price': 12.0,
                    'reason_code': 'expired',
                }
            ],
        }

        result = service.create_dock_rejection(dock_payload)
        assert result['id'] == 12
        assert result['goods_receipt_id'] == 102
        assert result['total_amount'] == 60.0

    def test_format_reason_label_mappings(self):
        from modules.purchasing.services.purchase_return_service import format_reason_label
        assert format_reason_label('damaged') == 'Damaged Goods'
        assert format_reason_label('expired') == 'Expired Product'
        assert format_reason_label('rejected') == 'Receiving Rejected'
        assert format_reason_label('wrong_item') == 'Wrong Item / Mismatch'
        assert format_reason_label('qc_failed') == 'QC Inspection Failed'
        assert format_reason_label('defective') == 'Defective / Poor Quality'
        assert format_reason_label('over_delivery') == 'Over Delivery / Excess'
        assert format_reason_label('other') == 'Other Discrepancy'
        assert format_reason_label('damaged: broken seal') == 'Damaged Goods (broken seal)'
        assert format_reason_label(None) == 'Not Specified'
        assert format_reason_label('custom_reason') == 'Custom Reason'

    def test_get_return_slip_data_aggregates_all_metadata(self, service, mock_repo):
        service.supplier_repo = MagicMock()
        service.po_repo = MagicMock()
        service.grn_repo = MagicMock()
        service.invoice_repo = MagicMock()
        service.user_repo = MagicMock()
        service.tenant_repo = MagicMock()
        service.uom_repo = MagicMock()
        service.batch_repo = MagicMock()

        return_record = {
            'id': 10,
            'return_number': 'RMA-202609-00010',
            'return_date': '2026-09-08',
            'status': 'Approved',
            'supplier_id': 50,
            'purchase_order_id': 20,
            'goods_receipt_id': 30,
            'debit_memo_id': 40,
            'total_amount': 250.0,
            'reason': 'Damaged boxes and expired dairy products',
            'notes': 'Dock driver agreed to return',
            'approved_at': '2026-09-08T09:00:00Z',
            'approved_by': 99,
            'business_id': 1,
            'attachments': [{'id': 'att-1', 'url': 'https://cdn.example.com/dock-slip.jpg'}],
        }
        mock_repo.get.return_value = return_record

        lines = [
            {
                'id': 101,
                'return_id': 10,
                'line_number': 1,
                'product_id': 1001,
                'product_name': 'Organic Whole Milk 1L',
                'qty': 20.0,
                'unit_price': 5.0,
                'line_total': 100.0,
                'uom_id': 1,
                'batch_id': 501,
                'batch_number': 'LOT-MILK-99',
                'expiry_date': '2026-09-01',
                'reason_code': 'expired',
                'quarantine_status': 'Quarantine',
                'disposition': 'Return to Vendor',
                'photos': [{'id': 'photo-1', 'url': 'https://cdn.example.com/expired-carton.jpg'}],
            },
            {
                'id': 102,
                'return_id': 10,
                'line_number': 2,
                'product_id': 1002,
                'product_name': 'Greek Yogurt 500g',
                'qty': 30.0,
                'unit_price': 5.0,
                'line_total': 150.0,
                'uom_id': 2,
                'batch_id': 502,
                'batch_number': 'LOT-YOG-88',
                'expiry_date': '2026-09-15',
                'reason_code': 'damaged: broken foil seal',
                'quarantine_status': 'Quarantine',
                'disposition': 'Return to Vendor',
                'photos': [{'id': 'photo-2', 'url': 'https://cdn.example.com/broken-seal.jpg'}],
            },
        ]
        with patch.object(service, '_get_lines', return_value=lines):
            # Mock supplier lookup
            service.supplier_repo.get.return_value = {
                'id': 50,
                'name': 'Fresh Farms Dairy Ltd',
                'supplier_code': 'SUP-0050',
                'contact': 'Alice Smith',
                'phone': '+1-555-444-3322',
                'email': 'returns@freshfarms.example',
                'address': '450 Dairy Road, Greenfield, CA',
            }
            # Mock PO lookup
            service.po_repo.get.return_value = {'id': 20, 'order_number': 'PO-2026-0088'}
            # Mock GRN lookup
            service.grn_repo.get.return_value = {'id': 30, 'receipt_number': 'GRN-2026-0045'}
            # Mock Debit Memo lookup
            service.invoice_repo.get.return_value = {'id': 40, 'invoice_number': 'DM-2026-0012'}
            # Mock User lookup
            service.user_repo.get.return_value = {'id': 99, 'full_name': 'Sarah Quality Lead'}
            # Mock Tenant lookup
            service.tenant_repo.get.return_value = {'id': 1, 'tenant_name': 'Nova Organics Hub'}
            # Mock UOM lookup
            service.uom_repo.get.side_effect = lambda uom_id, **kw: {'id': uom_id, 'uom_code': 'CS' if uom_id == 1 else 'EA'}

            slip = service.get_return_slip_data(10)

            # Check header aggregation
            assert slip['return_id'] == 10
            assert slip['return_number'] == 'RMA-202609-00010'
            assert slip['status'] == 'Approved'
            assert slip['company_name'] == 'Nova Organics Hub'
            assert slip['supplier_name'] == 'Fresh Farms Dairy Ltd'
            assert slip['supplier_code'] == 'SUP-0050'
            assert slip['supplier_contact'] == 'Alice Smith'
            assert slip['supplier_phone'] == '+1-555-444-3322'
            assert slip['supplier_email'] == 'returns@freshfarms.example'
            assert slip['supplier_address'] == '450 Dairy Road, Greenfield, CA'
            assert slip['po_number'] == 'PO-2026-0088'
            assert slip['grn_number'] == 'GRN-2026-0045'
            assert slip['debit_memo_id'] == 40
            assert slip['debit_memo_number'] == 'DM-2026-0012'
            assert slip['approved_by_name'] == 'Sarah Quality Lead'
            assert slip['total_amount'] == 250.0
            assert 'Supplier acknowledgment verifies debit memo claims' in slip['acknowledgment_text']

            # Check lines aggregation
            assert len(slip['lines']) == 2
            line1 = slip['lines'][0]
            assert line1['product_name'] == 'Organic Whole Milk 1L'
            assert line1['qty'] == 20.0
            assert line1['uom'] == 'CS'
            assert line1['batch_number'] == 'LOT-MILK-99'
            assert line1['expiry_date'] == '2026-09-01'
            assert line1['reason_code'] == 'expired'
            assert line1['reason_label'] == 'Expired Product'
            assert line1['quarantine_status'] == 'Quarantine'

            line2 = slip['lines'][1]
            assert line2['uom'] == 'EA'
            assert line2['reason_label'] == 'Damaged Goods (broken foil seal)'

            # Check aggregated photo attachments
            assert len(slip['attachments']) == 3
            attachment_urls = [a.get('url') for a in slip['attachments']]
            assert 'https://cdn.example.com/dock-slip.jpg' in attachment_urls
            assert 'https://cdn.example.com/expired-carton.jpg' in attachment_urls
            assert 'https://cdn.example.com/broken-seal.jpg' in attachment_urls

    def test_get_return_slip_data_fallback_batch_lookup(self, service, mock_repo):
        service.supplier_repo = MagicMock()
        service.batch_repo = MagicMock()
        service.uom_repo = MagicMock()

        return_record = {
            'id': 15,
            'return_number': 'RMA-202609-00015',
            'return_date': '2026-09-08',
            'status': 'Approved',
            'supplier_id': 60,
            'total_amount': 50.0,
        }
        mock_repo.get.return_value = return_record
        service.supplier_repo.get.return_value = {'id': 60, 'name': 'Bakery Supplies'}

        # Line without explicit batch_number and expiry_date, but with batch_id
        lines = [
            {
                'id': 201,
                'return_id': 15,
                'product_id': 2001,
                'product_name': 'Flour 25kg',
                'qty': 2.0,
                'unit_price': 25.0,
                'line_total': 50.0,
                'batch_id': 888,
                'batch_number': None,
                'expiry_date': None,
                'reason_code': 'rejected',
            }
        ]
        service.batch_repo.get.return_value = {
            'id': 888,
            'batch_number': 'LOT-FLOUR-888',
            'expiry_date': '2027-01-01',
        }

        with patch.object(service, '_get_lines', return_value=lines):
            slip = service.get_return_slip_data(15)
            assert slip['lines'][0]['batch_number'] == 'LOT-FLOUR-888'
            assert slip['lines'][0]['expiry_date'] == '2027-01-01'
            assert slip['lines'][0]['reason_label'] == 'Receiving Rejected'

    def test_get_return_slip_data_not_found_raises_404(self, service, mock_repo):
        mock_repo.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            service.get_return_slip_data(9999)
        assert exc_info.value.status_code == 404

    def test_get_return_details_aggregates_line_and_header_info(self, service, mock_repo):
        service.supplier_repo = MagicMock()
        service.po_repo = MagicMock()
        service.grn_repo = MagicMock()
        service.invoice_repo = MagicMock()

        return_record = {
            'id': 30,
            'return_number': 'RMA-202609-00030',
            'supplier_id': 12,
            'purchase_order_id': 34,
            'goods_receipt_id': 56,
            'debit_memo_id': 78,
            'status': 'Approved',
        }
        mock_repo.get.return_value = return_record
        service.supplier_repo.get.return_value = {'id': 12, 'name': 'ABC Supplies'}
        service.po_repo.get.return_value = {'id': 34, 'order_number': 'PO-34'}
        service.grn_repo.get.return_value = {'id': 56, 'receipt_number': 'GRN-56'}
        service.invoice_repo.get.return_value = {'id': 78, 'invoice_number': 'DM-78'}

        lines = [{'id': 1, 'return_id': 30, 'product_name': 'Item X', 'qty': 10.0}]
        with patch.object(service, '_get_lines', return_value=lines):
            details = service.get_return_details(30)
            assert details['id'] == 30
            assert details['supplier_name'] == 'ABC Supplies'
            assert details['po_number'] == 'PO-34'
            assert details['grn_number'] == 'GRN-56'
            assert details['debit_memo_number'] == 'DM-78'
            assert len(details['lines']) == 1

    def test_add_attachment_to_header_success(self, service, mock_repo):
        return_rec = {
            'id': 1,
            'return_number': 'RMA-0001',
            'attachments': [],
        }
        mock_repo.get.return_value = return_rec
        mock_repo.update.return_value = return_rec

        att_data = {
            'filename': 'damage_photo.jpg',
            'url': 'https://storage.example.com/rma/photo1.jpg',
            'content_type': 'image/jpeg',
            'description': 'Crushed packaging at dock',
        }
        result = service.add_attachment(return_id=1, attachment=att_data, user_id=10)

        assert result['filename'] == 'damage_photo.jpg'
        assert result['url'] == 'https://storage.example.com/rma/photo1.jpg'
        assert result['uploaded_by'] == 10
        assert 'id' in result
        mock_repo.update.assert_called_once()
        update_call = mock_repo.update.call_args
        assert len(update_call[0][1]['attachments']) == 1

    def test_add_attachment_with_base64_calculates_size(self, service, mock_repo):
        return_rec = {
            'id': 2,
            'return_number': 'RMA-0002',
            'attachments': [],
        }
        mock_repo.get.return_value = return_rec

        b64_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        att_data = {
            'filename': 'inspection_base64.png',
            'content_type': 'image/png',
            'data_base64': b64_data,
        }
        result = service.add_attachment(return_id=2, attachment=att_data, user_id=12)

        assert result['filename'] == 'inspection_base64.png'
        assert result['content_type'] == 'image/png'
        assert result['size_bytes'] is not None and result['size_bytes'] > 0
        mock_repo.update.assert_called_once()

    def test_add_attachment_to_line_item(self, service, mock_repo):
        return_rec = {
            'id': 3,
            'return_number': 'RMA-0003',
            'attachments': [],
        }
        mock_repo.get.return_value = return_rec

        mock_lines_repo = MagicMock()
        service.lines_repo = mock_lines_repo
        line_rec = {
            'id': 101,
            'return_id': 3,
            'product_id': 45,
            'product_name': 'Fresh Apples',
            'photos': [],
        }
        mock_lines_repo.get.return_value = line_rec

        att_data = {
            'filename': 'bruised_apples.jpg',
            'url': 'https://storage.example.com/rma/apples.jpg',
            'line_id': 101,
        }
        result = service.add_attachment(return_id=3, attachment=att_data, line_id=101)

        assert result['line_id'] == 101
        assert result['product_id'] == 45
        assert result['product_name'] == 'Fresh Apples'
        mock_lines_repo.update.assert_called_once()
        update_call = mock_lines_repo.update.call_args
        assert len(update_call[0][1]['photos']) == 1

    def test_add_attachment_not_found_raises_404(self, service, mock_repo):
        mock_repo.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            service.add_attachment(return_id=999, attachment={'filename': 'x.jpg'})
        assert exc.value.status_code == 404

    def test_add_attachment_invalid_line_raises_404(self, service, mock_repo):
        mock_repo.get.return_value = {'id': 1, 'return_number': 'RMA-0001'}
        mock_lines_repo = MagicMock()
        service.lines_repo = mock_lines_repo
        mock_lines_repo.get.return_value = {'id': 99, 'return_id': 999}  # Mismatched return_id

        with pytest.raises(HTTPException) as exc:
            service.add_attachment(return_id=1, attachment={'filename': 'x.jpg'}, line_id=99)
        assert exc.value.status_code == 404

    def test_get_attachments_combines_header_and_lines(self, service, mock_repo):
        return_rec = {
            'id': 5,
            'return_number': 'RMA-0005',
            'attachments': [{'id': 'att_1', 'filename': 'doc.pdf'}],
        }
        mock_repo.get.return_value = return_rec

        lines = [
            {
                'id': 20,
                'return_id': 5,
                'product_id': 10,
                'product_name': 'Product 10',
                'photos': [{'id': 'att_2', 'filename': 'photo_p10.jpg'}],
            }
        ]
        with patch.object(service, '_get_lines', return_value=lines):
            atts = service.get_attachments(5)
            assert len(atts) == 2
            assert atts[0]['scope'] == 'header'
            assert atts[0]['id'] == 'att_1'
            assert atts[1]['scope'] == 'line'
            assert atts[1]['id'] == 'att_2'
            assert atts[1]['product_name'] == 'Product 10'

    def test_delete_attachment_from_header_and_line(self, service, mock_repo):
        return_rec = {
            'id': 6,
            'return_number': 'RMA-0006',
            'attachments': [{'id': 'att_hdr_1', 'filename': 'invoice.pdf'}],
        }
        mock_repo.get.return_value = return_rec

        # Delete header attachment
        del_res = service.delete_attachment(6, 'att_hdr_1')
        assert del_res['success'] is True
        assert del_res['deleted_id'] == 'att_hdr_1'
        mock_repo.update.assert_called_with(6, {'attachments': []})

        # Delete non-existent raises 404
        with patch.object(service, '_get_lines', return_value=[]):
            with pytest.raises(HTTPException) as exc:
                service.delete_attachment(6, 'non_existent_id')
            assert exc.value.status_code == 404




