from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository

VALID_RETURN_STATUS_TRANSITIONS = {
    'Draft': ['Approved', 'Cancelled'],
    'Approved': ['Returned', 'Cancelled'],
    'Returned': [],
    'Cancelled': [],
}

class PurchaseReturnService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.stock_service = StockMovementService()

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_RETURN_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid Purchase Return status transition: {old_status} -> {new_status}. Allowed: {allowed}')
        result = super().update(id_val, payload)
        if old and payload.get('status') == 'Returned' and old.get('status') != 'Returned':
            lines = self._get_lines(id_val)
            for line in lines:
                if line.get('product_id'):
                    self.stock_service.record_movement(
                        product_id=line['product_id'],
                        warehouse_id=1,
                        movement_type='Purchase Return',
                        qty_change=-(line.get('qty', 0)),
                        reference_type='PurchaseReturn',
                        reference_id=id_val,
                        description=f'Purchase Return: {line.get("product_name", "")}',
                    )
        return result

    def _get_lines(self, return_id):
        repo = CrudRepository('T0082', business_columns=['id', 'return_id', 'product_id', 'product_name', 'qty'])
        return repo.list(filters={'return_id': return_id})
