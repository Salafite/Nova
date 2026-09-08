from typing import Optional, List, Dict, Any
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

