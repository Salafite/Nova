from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, timezone
import uuid
from fastapi import HTTPException, status

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.purchasing.models.purchase_return import (
    AttachmentUploadRequest,
    QuarantineStatus,
    RMADisposition,
)


class PurchaseReturnLineService(CrudService):
    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        return_repo: Optional[CrudRepository] = None,
        batch_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or CrudRepository(
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
        ))
        self.return_repo = return_repo
        self.batch_repo = batch_repo
        self.product_repo = product_repo

    def _get_return_repo(self) -> CrudRepository:
        if self.return_repo is not None:
            return self.return_repo
        return CrudRepository(
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
        )

    def _get_batch_repo(self) -> CrudRepository:
        if self.batch_repo is not None:
            return self.batch_repo
        return CrudRepository(
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

    def _get_product_repo(self) -> CrudRepository:
        if self.product_repo is not None:
            return self.product_repo
        return CrudRepository(
            'T0003',
            business_columns=[
                'id',
                'code',
                'name',
                'category_id',
                'uom_id',
                'purchase_price',
                'selling_price',
                'is_active',
            ],
        )

    def _enrich_line_payload(self, payload: dict) -> dict:
        data = dict(payload)
        qty = float(data.get('qty', 0))
        unit_price = float(data.get('unit_price', 0))
        data['qty'] = qty
        data['unit_price'] = unit_price
        data['line_total'] = round(qty * unit_price, 2)

        batch_id = data.get('batch_id')
        batch_num = data.get('batch_number')
        product_id = data.get('product_id')

        # Batch resolution
        batch_repo = self._get_batch_repo()
        if batch_id:
            try:
                b_rec = batch_repo.get(batch_id)
                if b_rec:
                    if not batch_num and b_rec.get('batch_number'):
                        data['batch_number'] = b_rec.get('batch_number')
                    if not data.get('expiry_date') and b_rec.get('expiry_date'):
                        data['expiry_date'] = b_rec.get('expiry_date')
                    if not product_id and b_rec.get('product_id'):
                        data['product_id'] = b_rec.get('product_id')
                        product_id = b_rec.get('product_id')
            except Exception:
                pass
        elif batch_num:
            try:
                filters = {'batch_number': batch_num}
                if product_id:
                    filters['product_id'] = product_id
                matched = batch_repo.list(filters)
                if matched:
                    b_rec = matched[0]
                    data['batch_id'] = b_rec.get('id')
                    if not data.get('expiry_date') and b_rec.get('expiry_date'):
                        data['expiry_date'] = b_rec.get('expiry_date')
                    if not product_id and b_rec.get('product_id'):
                        data['product_id'] = b_rec.get('product_id')
                        product_id = b_rec.get('product_id')
            except Exception:
                pass

        # Product name resolution
        if product_id and (not data.get('product_name') or not str(data.get('product_name')).strip()):
            try:
                p_repo = self._get_product_repo()
                p_rec = p_repo.get(product_id)
                if p_rec and p_rec.get('name'):
                    data['product_name'] = p_rec.get('name')
            except Exception:
                pass

        if not data.get('product_name'):
            data['product_name'] = f"Product #{product_id}" if product_id else "Returned Item"

        # Defaults
        if not data.get('quarantine_status'):
            data['quarantine_status'] = QuarantineStatus.QUARANTINE.value
        if not data.get('disposition'):
            data['disposition'] = RMADisposition.RETURN_TO_VENDOR.value
        if 'photos' in data and data['photos'] is None:
            data['photos'] = []
        elif 'photos' not in data:
            data['photos'] = []

        return data

    def create(self, payload: dict) -> dict:
        enriched = self._enrich_line_payload(payload)
        return_id = enriched.get('return_id')
        if not return_id:
            raise ValueError("return_id is required to create a purchase return line")

        # Auto assign line_number if not provided or 0
        if not enriched.get('line_number'):
            try:
                existing_lines = self.get_by_return_id(return_id)
                max_ln = max([l.get('line_number', 0) for l in existing_lines] or [0])
                enriched['line_number'] = max_ln + 1
            except Exception:
                enriched['line_number'] = 1

        created = super().create(enriched)
        self._recalculate_return_total(return_id)
        return created

    def update(self, id_val, payload: dict) -> dict:
        old = self.repo.get(id_val)
        if not old:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Return line #{id_val} not found")

        data = dict(payload)
        if 'qty' in data or 'unit_price' in data:
            qty = float(data.get('qty', old.get('qty', 0)))
            price = float(data.get('unit_price', old.get('unit_price', 0)))
            data['qty'] = qty
            data['unit_price'] = price
            data['line_total'] = round(qty * price, 2)

        # Batch lookup if batch_id changed
        if 'batch_id' in data and data['batch_id'] and data['batch_id'] != old.get('batch_id'):
            try:
                b_rec = self._get_batch_repo().get(data['batch_id'])
                if b_rec:
                    if 'batch_number' not in data and b_rec.get('batch_number'):
                        data['batch_number'] = b_rec.get('batch_number')
                    if 'expiry_date' not in data and b_rec.get('expiry_date'):
                        data['expiry_date'] = b_rec.get('expiry_date')
            except Exception:
                pass

        updated = super().update(id_val, data)
        return_id = updated.get('return_id') or old.get('return_id')
        if return_id:
            self._recalculate_return_total(return_id)
        return updated

    def delete(self, id_val) -> dict:
        old = self.repo.get(id_val)
        res = super().delete(id_val)
        if old and old.get('return_id'):
            self._recalculate_return_total(old.get('return_id'))
        return res

    def _recalculate_return_total(self, return_id: Optional[int]):
        if not return_id:
            return
        try:
            lines = self.get_by_return_id(return_id)
            total = sum(float(l.get('line_total') if l.get('line_total') is not None else (float(l.get('qty', 0)) * float(l.get('unit_price', 0)))) for l in lines)
            self._get_return_repo().update(return_id, {'total_amount': round(total, 2)})
        except Exception:
            pass

    def get_by_return_id(self, return_id: int) -> List[Dict[str, Any]]:
        all_lines = self.repo.list({'return_id': return_id})
        filtered = [l for l in all_lines if l.get('return_id') == return_id and l.get('is_active', True)]
        filtered.sort(key=lambda x: (x.get('line_number', 0), x.get('id', 0)))
        return filtered

    def get_by_batch_id(self, batch_id: int) -> List[Dict[str, Any]]:
        all_lines = self.repo.list({'batch_id': batch_id})
        filtered = [l for l in all_lines if l.get('batch_id') == batch_id and l.get('is_active', True)]
        return filtered

    def get_by_batch_number(self, batch_number: str) -> List[Dict[str, Any]]:
        all_lines = self.repo.list()
        filtered = [l for l in all_lines if l.get('batch_number') == batch_number and l.get('is_active', True)]
        return filtered

    def bulk_create(self, return_id: int, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ret_repo = self._get_return_repo()
        parent_return = ret_repo.get(return_id)
        if not parent_return:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Purchase Return #{return_id} not found")

        created_lines = []
        for idx, line_payload in enumerate(lines, start=1):
            line_dict = dict(line_payload)
            line_dict['return_id'] = return_id
            if not line_dict.get('line_number'):
                line_dict['line_number'] = idx
            created = self.create(line_dict)
            created_lines.append(created)

        self._recalculate_return_total(return_id)
        return created_lines

    def add_photo(
        self,
        line_id: int,
        attachment: Union[Dict[str, Any], AttachmentUploadRequest],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        line = self.repo.get(line_id)
        if not line:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Return line #{line_id} not found")

        att_data = attachment.model_dump() if hasattr(attachment, 'model_dump') else dict(attachment)
        photo_id = att_data.get('id') or f"att_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        new_photo = {
            'id': photo_id,
            'filename': att_data.get('filename') or f"photo_{photo_id}.jpg",
            'url': att_data.get('url'),
            'thumbnail_url': att_data.get('thumbnail_url') or att_data.get('url'),
            'data_base64': att_data.get('data_base64'),
            'content_type': att_data.get('content_type') or 'image/jpeg',
            'size_bytes': att_data.get('size_bytes'),
            'description': att_data.get('description'),
            'uploaded_at': now_iso,
            'uploaded_by': user_id or att_data.get('uploaded_by'),
            'line_id': line_id,
        }

        photos = list(line.get('photos') or [])
        photos.append(new_photo)
        self.repo.update(line_id, {'photos': photos})
        return new_photo

    def get_photos(self, line_id: int) -> List[Dict[str, Any]]:
        line = self.repo.get(line_id)
        if not line:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Return line #{line_id} not found")
        return list(line.get('photos') or [])

    def delete_photo(self, line_id: int, photo_id: str) -> Dict[str, Any]:
        line = self.repo.get(line_id)
        if not line:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Return line #{line_id} not found")

        photos = list(line.get('photos') or [])
        initial_len = len(photos)
        photos = [p for p in photos if p.get('id') != photo_id]
        if len(photos) == initial_len:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Photo #{photo_id} not found on line #{line_id}")

        self.repo.update(line_id, {'photos': photos})
        return {'success': True, 'photo_id': photo_id, 'remaining_photos': len(photos)}

    def update_quarantine_status(self, line_id: int, quarantine_status: str, sync_batch: bool = True) -> Dict[str, Any]:
        line = self.repo.get(line_id)
        if not line:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Return line #{line_id} not found")

        updated_line = self.repo.update(line_id, {'quarantine_status': quarantine_status})

        if sync_batch and line.get('batch_id'):
            try:
                self._get_batch_repo().update(line['batch_id'], {'status': quarantine_status})
            except Exception:
                pass

        return updated_line

