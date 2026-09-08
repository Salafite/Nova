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
    def __init__(self, repo: CrudRepository):
        super().__init__(repo)
        self.stock_service = StockMovementService()

    def _get_lines_repo(self) -> CrudRepository:
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

    def _get_lines(self, return_id: int) -> List[Dict[str, Any]]:
        repo = self._get_lines_repo()
        return repo.list(filters={'return_id': return_id})

    def _generate_return_number(self) -> str:
        prefix = datetime.now().strftime('RMA-%Y%m-')
        existing = self.repo.list()
        count = len(existing) + 1
        return f"{prefix}{count:04d}"

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
        Validates line items and updates approved metadata.
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

