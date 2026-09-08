from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, timezone
from fastapi import HTTPException

from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository
from modules.purchasing.models.purchase_return import RMAStatus, QuarantineStatus

VALID_RETURN_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    RMAStatus.DRAFT.value: [RMAStatus.APPROVED.value, RMAStatus.CANCELLED.value],
    RMAStatus.APPROVED.value: [RMAStatus.RETURNED.value, RMAStatus.CANCELLED.value],
    RMAStatus.RETURNED.value: [],
    RMAStatus.CANCELLED.value: [],
}


class PurchaseReturnService(CrudService):
    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        lines_repo: Optional[CrudRepository] = None,
        batch_repo: Optional[CrudRepository] = None,
        grn_repo: Optional[CrudRepository] = None,
        grn_line_repo: Optional[CrudRepository] = None,
        po_repo: Optional[CrudRepository] = None,
        po_line_repo: Optional[CrudRepository] = None,
        stock_service: Optional[Any] = None,
    ):
        super().__init__(repo or CrudRepository(
            'T0081',
            business_columns=[
                'id',
                'return_number',
                'purchase_order_id',
                'goods_receipt_id',
                'supplier_id',
                'debit_memo_id',
                'return_date',
                'status',
                'total_amount',
                'reason',
                'notes',
                'attachments',
                'approved_at',
                'approved_by',
                'business_id',
                'is_active',
            ],
        ))
        self.invoice_repo = invoice_repo or CrudRepository(
            'T0090',
            business_columns=[
                'id',
                'invoice_number',
                'invoice_type',
                'partner_id',
                'sales_order_id',
                'purchase_order_id',
                'purchase_return_id',
                'sales_rep_id',
                'payment_term_id',
                'issue_date',
                'due_date',
                'discount_due_date',
                'discount_percentage',
                'discount_days',
                'early_discount_amount',
                'total_amount',
                'freight_amount',
                'discount_amount',
                'status',
                'notes',
                'is_catch_weight',
                'nominal_total_weight',
                'actual_total_weight',
                'weight_adjustment_amount',
                'business_id',
                'is_active',
            ],
        )
        self.lines_repo = lines_repo
        self.batch_repo = batch_repo or CrudRepository(
            'T0088',
            business_columns=[
                'id',
                'product_id',
                'batch_number',
                'expiry_date',
                'manufacturing_date',
                'quantity',
                'warehouse_id',
                'status',
                'notes',
                'business_id',
                'is_active',
            ],
        )
        self.grn_repo = grn_repo or CrudRepository(
            'T0075',
            business_columns=[
                'id',
                'receipt_number',
                'purchase_order_id',
                'receipt_date',
                'warehouse_id',
                'status',
                'notes',
                'business_id',
                'is_active',
            ],
        )
        self.grn_line_repo = grn_line_repo
        self.po_repo = po_repo
        self.po_line_repo = po_line_repo
        self.stock_service = stock_service or StockMovementService()

    def _get_lines_repo(self) -> CrudRepository:
        if self.lines_repo is not None:
            return self.lines_repo
        return CrudRepository(
            'T0082',
            business_columns=[
                'id',
                'return_id',
                'product_id',
                'product_name',
                'qty',
                'unit_price',
                'line_total',
                'uom_id',
                'batch_id',
                'batch_number',
                'expiry_date',
                'reason_code',
                'photos',
                'quarantine_status',
                'disposition',
                'line_number',
                'business_id',
                'is_active',
            ],
        )

    def _get_grn_line_repo(self) -> CrudRepository:
        if self.grn_line_repo is not None:
            return self.grn_line_repo
        return CrudRepository(
            'T0076',
            business_columns=[
                'id',
                'receipt_id',
                'purchase_order_line_id',
                'product_id',
                'product_name',
                'qty_received',
                'qty_ordered',
                'uom_id',
                'line_number',
                'batch_number',
                'manufacturing_date',
                'expiry_date',
                'business_id',
                'is_active',
            ],
        )

    def _get_po_repo(self) -> CrudRepository:
        if self.po_repo is not None:
            return self.po_repo
        return CrudRepository(
            'T0014',
            business_columns=[
                'id',
                'order_number',
                'supplier_id',
                'order_date',
                'total',
                'status',
                'warehouse_id',
                'business_id',
                'is_active',
            ],
        )

    def _get_po_line_repo(self) -> CrudRepository:
        if self.po_line_repo is not None:
            return self.po_line_repo
        return CrudRepository(
            'T0015',
            business_columns=[
                'id',
                'purchase_order_id',
                'product_id',
                'product_name',
                'uom_id',
                'qty',
                'unit_price',
                'line_total',
                'line_number',
                'business_id',
                'is_active',
            ],
        )

    def _get_lines(self, return_id: int, conn=None) -> List[Dict[str, Any]]:
        repo = self._get_lines_repo()
        kwargs = {'conn': conn} if conn is not None else {}
        return repo.list(filters={'return_id': return_id}, **kwargs)

    def _generate_return_number(self, conn=None) -> str:
        try:
            from packages.database.sequence import generate_document_number
            return generate_document_number('seq_purchase_return_number', prefix='RMA', padding=5, conn=conn)
        except Exception:
            prefix = datetime.now().strftime('RMA-%Y%m-')
            existing = self.repo.list(conn=conn) if hasattr(self.repo, 'list') else []
            count = (len(existing) if isinstance(existing, list) else 0) + 1
            return f"{prefix}{count:04d}"

    def _generate_debit_memo_number(self, conn=None) -> str:
        try:
            from packages.database.sequence import generate_invoice_number
            return generate_invoice_number(conn=conn, prefix="DM")
        except Exception:
            prefix = datetime.now().strftime('DM-%Y%m-')
            existing = self.invoice_repo.list(filters={'invoice_type': 'Debit Memo'}, conn=conn) if hasattr(self.invoice_repo, 'list') else []
            count = (len(existing) if isinstance(existing, list) else 0) + 1
            return f"{prefix}{count:04d}"

    def create_debit_memo_for_return(
        self,
        return_record: dict,
        lines: Optional[List[dict]] = None,
        conn=None,
    ) -> dict:
        """
        Generates and posts a T0090 Debit Memo record linked to the supplier
        with calculated line item credits and accounting references.
        """
        return_id = return_record.get('id')
        if lines is None and return_id:
            lines = self._get_lines(return_id, conn=conn)
        lines = lines or []

        calculated_total = sum(
            float(l.get('line_total') or (float(l.get('qty', 0)) * float(l.get('unit_price', 0))))
            for l in lines
        )
        total_amount = float(return_record.get('total_amount') or calculated_total or 0.0)

        debit_memo_number = self._generate_debit_memo_number(conn=conn)
        issue_date = return_record.get('return_date') or date.today().isoformat()
        if isinstance(issue_date, date):
            issue_date = issue_date.isoformat()

        return_num = return_record.get('return_number', f"#{return_id}")
        debit_memo_payload = {
            'invoice_number': debit_memo_number,
            'invoice_type': 'Debit Memo',
            'partner_id': return_record.get('supplier_id'),
            'purchase_order_id': return_record.get('purchase_order_id'),
            'purchase_return_id': return_id,
            'issue_date': issue_date,
            'due_date': issue_date,
            'total_amount': total_amount,
            'discount_amount': 0.0,
            'freight_amount': 0.0,
            'status': 'Unpaid',
            'notes': f"Automated Debit Memo for Purchase Return (RMA) {return_num}".strip(),
        }
        if return_record.get('business_id'):
            debit_memo_payload['business_id'] = return_record.get('business_id')

        kwargs = {'conn': conn} if conn is not None else {}
        debit_memo = self.invoice_repo.create(debit_memo_payload, **kwargs)
        return debit_memo

    def get_debit_memo(self, return_id: int, conn=None) -> Optional[dict]:
        """
        Retrieves the linked debit memo record for a given purchase return / RMA.
        """
        record = self.repo.get(return_id, conn=conn) if conn else self.repo.get(return_id)
        if not record:
            return None
        debit_memo_id = record.get('debit_memo_id')
        kwargs = {'conn': conn} if conn is not None else {}
        if debit_memo_id:
            return self.invoice_repo.get(debit_memo_id, **kwargs)
        # Fallback to query by purchase_return_id
        memos = self.invoice_repo.list(filters={'purchase_return_id': return_id, 'invoice_type': 'Debit Memo'}, **kwargs)
        return memos[0] if memos else None

    def create(self, payload: dict) -> dict:
        if not payload.get('return_number'):
            payload['return_number'] = self._generate_return_number()
        if not payload.get('status'):
            payload['status'] = RMAStatus.DRAFT.value
        if not payload.get('return_date'):
            payload['return_date'] = date.today().isoformat()
        return super().create(payload)

    def update(self, id_val: int, payload: dict) -> dict:
        old = self.repo.get(id_val)
        if not old:
            raise HTTPException(404, f'Purchase return with id {id_val} not found')

        old_status = old.get('status')
        new_status = payload.get('status')

        if new_status and old_status != new_status:
            allowed = VALID_RETURN_STATUS_TRANSITIONS.get(old_status, [])
            if new_status not in allowed:
                raise HTTPException(
                    400,
                    f'Invalid Purchase Return status transition: {old_status} -> {new_status}. Allowed: {allowed}'
                )

            # Validation specific to transitioning to Approved
            if new_status == RMAStatus.APPROVED.value:
                lines = self._get_lines(id_val)
                if not lines or len(lines) == 0:
                    raise HTTPException(400, 'Cannot approve a Purchase Return (RMA) with no line items')
                if not payload.get('approved_at') and not old.get('approved_at'):
                    payload['approved_at'] = datetime.now(timezone.utc).isoformat()
                if 'total_amount' not in payload or payload.get('total_amount') is None or payload.get('total_amount') == 0:
                    calculated_total = sum(float(l.get('line_total') or (float(l.get('qty', 0)) * float(l.get('unit_price', 0)))) for l in lines)
                    if calculated_total > 0:
                        payload['total_amount'] = calculated_total

        elif old_status in [RMAStatus.RETURNED.value, RMAStatus.CANCELLED.value] and any(k for k in payload if k not in ['notes', 'is_active']):
            # Trying to mutate an already completed/cancelled return
            if new_status != old_status:
                raise HTTPException(
                    400,
                    f"Cannot modify purchase return in terminal '{old_status}' status"
                )

        result = super().update(id_val, payload)

        # Handle post-transition side effects
        if new_status == RMAStatus.RETURNED.value and old_status != RMAStatus.RETURNED.value:
            lines = self._get_lines(id_val)
            for line in lines:
                if line.get('product_id'):
                    qty = float(line.get('qty', 0))
                    self.stock_service.record_movement(
                        product_id=line['product_id'],
                        warehouse_id=1,
                        movement_type='Purchase Return',
                        qty_change=-qty,
                        reference_type='PurchaseReturn',
                        reference_id=id_val,
                        description=f'Purchase Return: {line.get("product_name", "")}',
                    )

        return result

    def quarantine_inventory_for_return(
        self,
        return_record: dict,
        lines: Optional[List[dict]] = None,
        conn=None,
    ) -> List[dict]:
        """
        Executes automated inventory quarantine write-down for an approved RMA:
        1. Updates linked batch records in T0088 to status='Quarantine'.
        2. Deducts salable inventory via T0064 stock movements ('Quarantine Write-Down').
        3. Updates return line items in T0082 to quarantine_status='Quarantine'.
        """
        return_id = return_record.get('id')
        if lines is None and return_id:
            lines = self._get_lines(return_id, conn=conn)
        lines = lines or []

        # Determine default warehouse from goods receipt or fallback to 1
        warehouse_id = 1
        grn_id = return_record.get('goods_receipt_id')
        if grn_id and self.grn_repo:
            try:
                kwargs = {'conn': conn} if conn is not None else {}
                grn = self.grn_repo.get(grn_id, **kwargs)
                if grn and grn.get('warehouse_id'):
                    warehouse_id = grn.get('warehouse_id')
            except Exception:
                warehouse_id = 1

        quarantined_items = []
        return_num = return_record.get('return_number', f"#{return_id}")

        for line in lines:
            product_id = line.get('product_id')
            qty = float(line.get('qty', 0) or 0)
            batch_id = line.get('batch_id')
            batch_number = line.get('batch_number')
            product_name = line.get('product_name') or (f"Product #{product_id}" if product_id else "Unknown")
            line_wh_id = warehouse_id

            # 1. Update linked batch in T0088 to 'Quarantine'
            if batch_id and self.batch_repo:
                try:
                    kwargs = {'conn': conn} if conn is not None else {}
                    batch = self.batch_repo.get(batch_id, **kwargs)
                    if batch:
                        if batch.get('warehouse_id'):
                            line_wh_id = batch.get('warehouse_id')
                        self.batch_repo.update(
                            batch_id,
                            {
                                'status': QuarantineStatus.QUARANTINE.value,
                                'notes': f"{batch.get('notes') or ''}\nQuarantined via RMA {return_num}".strip()
                            },
                            **kwargs
                        )
                except Exception:
                    pass
            elif batch_number and self.batch_repo:
                try:
                    kwargs = {'conn': conn} if conn is not None else {}
                    filters = {'batch_number': str(batch_number).strip()}
                    if product_id:
                        filters['product_id'] = product_id
                    batches = self.batch_repo.list(filters=filters, **kwargs)
                    for b in batches:
                        if b.get('warehouse_id'):
                            line_wh_id = b.get('warehouse_id')
                        self.batch_repo.update(
                            b['id'],
                            {
                                'status': QuarantineStatus.QUARANTINE.value,
                                'notes': f"{b.get('notes') or ''}\nQuarantined via RMA {return_num}".strip()
                            },
                            **kwargs
                        )
                except Exception:
                    pass

            # 2. Update line item quarantine_status in T0082
            if line.get('id'):
                try:
                    lines_repo = self._get_lines_repo()
                    kwargs = {'conn': conn} if conn is not None else {}
                    lines_repo.update(
                        line['id'],
                        {'quarantine_status': QuarantineStatus.QUARANTINE.value},
                        **kwargs
                    )
                except Exception:
                    pass

            # 3. Deduct salable inventory via T0064 Stock Movement
            movement_record = None
            if product_id and qty > 0 and self.stock_service:
                batch_str = f" (Batch: {batch_number})" if batch_number else ""
                reason_str = f" [{line.get('reason_code')}]" if line.get('reason_code') else ""
                desc = f"RMA Quarantine Write-Down: {product_name}{batch_str}{reason_str} - Return {return_num}"
                try:
                    movement_record = self.stock_service.record_movement(
                        product_id=product_id,
                        warehouse_id=line_wh_id,
                        movement_type='Quarantine Write-Down',
                        qty_change=-qty,
                        reference_type='PurchaseReturn',
                        reference_id=return_id,
                        description=desc,
                        conn=conn,
                    )
                except Exception:
                    pass

            quarantined_items.append({
                'line_id': line.get('id'),
                'product_id': product_id,
                'batch_id': batch_id,
                'batch_number': batch_number,
                'qty': qty,
                'quarantine_status': QuarantineStatus.QUARANTINE.value,
                'stock_movement': movement_record,
            })

        return quarantined_items

    def approve_return(
        self,
        id_val: int,
        approved_by: Optional[int] = None,
        notes: Optional[str] = None,
        create_debit_memo: bool = True,
        quarantine_inventory: bool = True,
    ) -> dict:
        """
        Transitions RMA from Draft -> Approved.
        Validates line items, automatically generates supplier debit memo (T0090),
        deducts salable inventory / quarantines batches, and updates approved metadata.
        """
        record = self.repo.get(id_val)
        if not record:
            raise HTTPException(404, f'Purchase return with id {id_val} not found')

        current_status = record.get('status')
        if current_status != RMAStatus.DRAFT.value:
            raise HTTPException(
                400,
                f"Cannot approve Purchase Return in '{current_status}' status. Must be '{RMAStatus.DRAFT.value}'."
            )

        lines = self._get_lines(id_val)
        if not lines or len(lines) == 0:
            raise HTTPException(400, 'Cannot approve a Purchase Return (RMA) with no line items')

        calculated_total = sum(
            float(l.get('line_total') or (float(l.get('qty', 0)) * float(l.get('unit_price', 0))))
            for l in lines
        )

        update_payload: Dict[str, Any] = {
            'status': RMAStatus.APPROVED.value,
            'approved_at': datetime.now(timezone.utc).isoformat(),
            'approved_by': approved_by,
        }
        if calculated_total > 0:
            update_payload['total_amount'] = calculated_total

        # Automated Debit Memo creation on approval
        debit_memo_id = record.get('debit_memo_id')
        if create_debit_memo and not debit_memo_id:
            return_dict_for_dm = dict(record)
            if calculated_total > 0:
                return_dict_for_dm['total_amount'] = calculated_total
            debit_memo = self.create_debit_memo_for_return(return_dict_for_dm, lines)
            if debit_memo and debit_memo.get('id'):
                debit_memo_id = debit_memo.get('id')
                update_payload['debit_memo_id'] = debit_memo_id

        # Automated Inventory Quarantine & Write-Down on approval
        if quarantine_inventory:
            return_dict_for_quarantine = dict(record)
            self.quarantine_inventory_for_return(return_dict_for_quarantine, lines)

        if notes:
            existing_notes = record.get('notes') or ''
            update_payload['notes'] = f"{existing_notes}\nApproval note: {notes}".strip()

        # Update record status and metadata
        updated_record = self.update(id_val, update_payload)

        return updated_record

    def complete_return(self, id_val: int, notes: Optional[str] = None) -> dict:
        """
        Transitions RMA from Approved -> Returned.
        Executes stock movements and completes lifecycle.
        """
        record = self.repo.get(id_val)
        if not record:
            raise HTTPException(404, f'Purchase return with id {id_val} not found')

        current_status = record.get('status')
        if current_status != RMAStatus.APPROVED.value:
            raise HTTPException(
                400,
                f"Cannot complete return for RMA in '{current_status}' status. Must be '{RMAStatus.APPROVED.value}'."
            )

        update_payload: Dict[str, Any] = {
            'status': RMAStatus.RETURNED.value,
        }
        if notes:
            existing_notes = record.get('notes') or ''
            update_payload['notes'] = f"{existing_notes}\nCompletion note: {notes}".strip()

        return self.update(id_val, update_payload)

    def cancel_return(self, id_val: int, reason: Optional[str] = None) -> dict:
        """
        Transitions RMA from Draft or Approved -> Cancelled.
        """
        record = self.repo.get(id_val)
        if not record:
            raise HTTPException(404, f'Purchase return with id {id_val} not found')

        current_status = record.get('status')
        if current_status not in [RMAStatus.DRAFT.value, RMAStatus.APPROVED.value]:
            raise HTTPException(
                400,
                f"Cannot cancel Purchase Return in '{current_status}' status. Only Draft or Approved returns can be cancelled."
            )

        update_payload: Dict[str, Any] = {
            'status': RMAStatus.CANCELLED.value,
        }
        if reason:
            existing_notes = record.get('notes') or ''
            update_payload['notes'] = f"{existing_notes}\nCancellation reason: {reason}".strip()

        return self.update(id_val, update_payload)

    def create_from_goods_receipt(
        self,
        grn_id: int,
        rejection_payload: Optional[Union[dict, Any]] = None,
        conn=None,
    ) -> dict:
        """
        Creates an RMA / Purchase Return record directly from a Goods Receipt (T0075/T0076)
        and dock-side quality rejections. Pre-fills supplier, PO reference, batch metadata,
        unit pricing, and quarantine line items.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        grn = self.grn_repo.get(grn_id, **kwargs)
        if not grn:
            raise HTTPException(404, f"Goods receipt with id {grn_id} not found")

        po_id = grn.get('purchase_order_id')
        supplier_id = None
        business_id = grn.get('business_id')
        return_date = date.today().isoformat()
        reason = None
        notes = None
        attachments = []
        payload_lines = None

        if rejection_payload:
            if isinstance(rejection_payload, dict):
                supplier_id = rejection_payload.get('supplier_id')
                if rejection_payload.get('purchase_order_id'):
                    po_id = rejection_payload.get('purchase_order_id')
                if rejection_payload.get('rejection_date') or rejection_payload.get('return_date'):
                    d = rejection_payload.get('rejection_date') or rejection_payload.get('return_date')
                    return_date = d.isoformat() if isinstance(d, date) else str(d)
                reason = rejection_payload.get('reason')
                notes = rejection_payload.get('notes')
                attachments = rejection_payload.get('attachments') or []
                payload_lines = rejection_payload.get('lines')
                if rejection_payload.get('business_id'):
                    business_id = rejection_payload.get('business_id')
            else:
                supplier_id = getattr(rejection_payload, 'supplier_id', None)
                p_po_id = getattr(rejection_payload, 'purchase_order_id', None)
                if p_po_id:
                    po_id = p_po_id
                d = getattr(rejection_payload, 'rejection_date', None) or getattr(rejection_payload, 'return_date', None)
                if d:
                    return_date = d.isoformat() if isinstance(d, date) else str(d)
                reason = getattr(rejection_payload, 'reason', None)
                notes = getattr(rejection_payload, 'notes', None)
                attachments = getattr(rejection_payload, 'attachments', None) or []
                payload_lines = getattr(rejection_payload, 'lines', None)
                b_id = getattr(rejection_payload, 'business_id', None)
                if b_id:
                    business_id = b_id

        # Lookup supplier from PO if not provided
        if not supplier_id and po_id:
            po_repo = self._get_po_repo()
            try:
                po = po_repo.get(po_id, **kwargs)
                if po and po.get('supplier_id'):
                    supplier_id = po.get('supplier_id')
            except Exception:
                pass

        if not supplier_id:
            raise HTTPException(400, "Supplier ID is required or cannot be determined from Goods Receipt / Purchase Order")

        if not reason:
            receipt_num = grn.get('receipt_number') or f"#{grn_id}"
            reason = f"Dock-side receiving rejection for Goods Receipt {receipt_num}"

        # Build lines
        lines_to_create = []
        po_line_repo = self._get_po_line_repo()

        if payload_lines and len(payload_lines) > 0:
            for item in payload_lines:
                if isinstance(item, dict):
                    pid = item.get('product_id')
                    pname = item.get('product_name') or (f"Product #{pid}" if pid else "Unknown Item")
                    qty = float(item.get('qty_rejected') or item.get('qty') or 1.0)
                    unit_price = float(item.get('unit_price') or 0.0)
                    uom_id = item.get('uom_id')
                    batch_id = item.get('batch_id')
                    batch_num = item.get('batch_number')
                    exp_date = item.get('expiry_date')
                    rcode = item.get('reason_code') or 'rejected'
                    photos = item.get('photos') or []
                    qstatus = item.get('quarantine_status') or 'Quarantine'
                    disp = item.get('disposition') or 'Return to Vendor'
                    rdetails = item.get('reason_details')
                else:
                    pid = getattr(item, 'product_id', None)
                    pname = getattr(item, 'product_name', None) or (f"Product #{pid}" if pid else "Unknown Item")
                    qty = float(getattr(item, 'qty_rejected', None) or getattr(item, 'qty', None) or 1.0)
                    unit_price = float(getattr(item, 'unit_price', None) or 0.0)
                    uom_id = getattr(item, 'uom_id', None)
                    batch_id = getattr(item, 'batch_id', None)
                    batch_num = getattr(item, 'batch_number', None)
                    exp_date = getattr(item, 'expiry_date', None)
                    rcode = getattr(item, 'reason_code', None) or 'rejected'
                    photos = getattr(item, 'photos', None) or []
                    qstatus = getattr(item, 'quarantine_status', None) or 'Quarantine'
                    disp = getattr(item, 'disposition', None) or 'Return to Vendor'
                    rdetails = getattr(item, 'reason_details', None)

                if isinstance(exp_date, date):
                    exp_date = exp_date.isoformat()

                if rdetails and rcode:
                    rcode_str = f"{rcode}: {rdetails}" if not str(rcode).endswith(f": {rdetails}") else str(rcode)
                else:
                    rcode_str = str(rcode)

                # If unit price not provided, lookup from PO line
                if unit_price <= 0 and po_id and pid:
                    try:
                        po_lines = po_line_repo.list(filters={'purchase_order_id': po_id, 'product_id': pid}, **kwargs)
                        if po_lines and po_lines[0].get('unit_price'):
                            unit_price = float(po_lines[0]['unit_price'])
                    except Exception:
                        pass

                # If batch_id not provided but batch_num exists, lookup from batch_repo
                if not batch_id and batch_num and self.batch_repo:
                    try:
                        b_filters = {'batch_number': str(batch_num).strip()}
                        if pid:
                            b_filters['product_id'] = pid
                        batches = self.batch_repo.list(filters=b_filters, **kwargs)
                        if batches:
                            batch_id = batches[0]['id']
                    except Exception:
                        pass

                line_total = qty * unit_price
                lines_to_create.append({
                    'product_id': pid,
                    'product_name': pname,
                    'qty': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                    'uom_id': uom_id,
                    'batch_id': batch_id,
                    'batch_number': batch_num,
                    'expiry_date': exp_date,
                    'reason_code': rcode_str,
                    'photos': photos,
                    'quarantine_status': qstatus,
                    'disposition': disp,
                })
        else:
            # Fallback: Create lines from all GRN line items in T0076
            grn_line_repo = self._get_grn_line_repo()
            grn_lines = grn_line_repo.list(filters={'receipt_id': grn_id}, **kwargs)
            if not grn_lines:
                raise HTTPException(400, f"Goods receipt {grn_id} has no line items to return")

            for grn_line in grn_lines:
                pid = grn_line.get('product_id')
                pname = grn_line.get('product_name') or (f"Product #{pid}" if pid else "Unknown Item")
                qty = float(grn_line.get('qty_received') or grn_line.get('qty_ordered') or 1.0)
                unit_price = 0.0
                if po_id and pid:
                    try:
                        po_lines = po_line_repo.list(filters={'purchase_order_id': po_id, 'product_id': pid}, **kwargs)
                        if po_lines and po_lines[0].get('unit_price'):
                            unit_price = float(po_lines[0]['unit_price'])
                    except Exception:
                        pass

                exp_date = grn_line.get('expiry_date')
                if isinstance(exp_date, date):
                    exp_date = exp_date.isoformat()

                batch_num = grn_line.get('batch_number')
                batch_id = None
                if batch_num and self.batch_repo:
                    try:
                        b_filters = {'batch_number': str(batch_num).strip()}
                        if pid:
                            b_filters['product_id'] = pid
                        batches = self.batch_repo.list(filters=b_filters, **kwargs)
                        if batches:
                            batch_id = batches[0]['id']
                    except Exception:
                        pass

                line_total = qty * unit_price
                lines_to_create.append({
                    'product_id': pid,
                    'product_name': pname,
                    'qty': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                    'uom_id': grn_line.get('uom_id'),
                    'batch_id': batch_id,
                    'batch_number': batch_num,
                    'expiry_date': exp_date,
                    'reason_code': 'rejected',
                    'photos': [],
                    'quarantine_status': 'Quarantine',
                    'disposition': 'Return to Vendor',
                })

        total_amount = sum(l['line_total'] for l in lines_to_create)
        return_number = self._generate_return_number(conn=conn)

        header_payload = {
            'return_number': return_number,
            'goods_receipt_id': grn_id,
            'purchase_order_id': po_id,
            'supplier_id': supplier_id,
            'return_date': return_date,
            'status': RMAStatus.DRAFT.value,
            'total_amount': total_amount,
            'reason': reason,
            'notes': notes,
            'attachments': attachments,
        }
        if business_id:
            header_payload['business_id'] = business_id

        created_return = self.repo.create(header_payload, **kwargs)
        return_id = created_return['id']

        lines_repo = self._get_lines_repo()
        created_lines = []
        for idx, line_data in enumerate(lines_to_create):
            line_data['return_id'] = return_id
            line_data['line_number'] = idx + 1
            if business_id:
                line_data['business_id'] = business_id
            c_line = lines_repo.create(line_data, **kwargs)
            created_lines.append(c_line)

        created_return['lines'] = created_lines
        return created_return

    def create_dock_rejection(
        self,
        rejection: Union[dict, Any],
        conn=None,
    ) -> dict:
        """
        Convenience wrapper for dock-side quality receiving rejection to create an RMA directly.
        """
        if isinstance(rejection, dict):
            grn_id = rejection.get('goods_receipt_id')
        else:
            grn_id = getattr(rejection, 'goods_receipt_id', None)

        if not grn_id:
            raise HTTPException(400, "goods_receipt_id is required for dock rejection RMA creation")

        return self.create_from_goods_receipt(grn_id=grn_id, rejection_payload=rejection, conn=conn)

