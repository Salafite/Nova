from modules.core.services.base import CrudService


class BatchNumberService(CrudService):
    def create(self, payload: dict):
        existing = self.repo.list(filters={
            'product_id': payload.get('product_id'),
            'batch_number': payload.get('batch_number')
        })
        if existing:
            raise ValueError(f"Batch number '{payload.get('batch_number')}' already exists for this product")
        payload.setdefault('status', 'Available')
        return super().create(payload)

    def adjustQuantity(self, id_val, qty: float):
        batch = self.get(id_val)
        if not batch:
            raise ValueError('Batch not found')
        new_qty = batch['quantity'] + qty
        if new_qty < 0:
            raise ValueError('Resulting quantity cannot be below 0')
        payload = {'quantity': new_qty}
        if new_qty == 0:
            payload['status'] = 'Depleted'
        elif batch['quantity'] > 0 and new_qty > 0 and batch['status'] not in ('Expired',):
            payload['status'] = 'Available' if batch.get('quantity', 0) == 0 else 'Partially Used'
        return self.update(id_val, payload)
