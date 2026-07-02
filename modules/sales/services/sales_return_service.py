from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository


class SalesReturnService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.stock_service = StockMovementService()
        self.line_repo = CrudRepository('T0080', business_columns=['id', 'return_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'uom_id', 'line_number'])

    def create(self, payload: dict):
        result = super().create(payload)
        if result and payload.get('status') == 'Received':
            self._record_stock_movements(result['id'])
        return result

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        result = super().update(id_val, payload)
        if old and payload.get('status') == 'Received' and old.get('status') != 'Received':
            self._record_stock_movements(id_val)
        return result

    def _record_stock_movements(self, return_id):
        lines = self.line_repo.list(filters={'return_id': return_id})
        for line in lines:
            if line.get('product_id'):
                self.stock_service.record_movement(
                    product_id=line['product_id'],
                    warehouse_id=1,
                    movement_type='Sales Return',
                    qty_change=abs(line.get('qty', 0)),
                    reference_type='Sales Return',
                    reference_id=return_id,
                    description=f'Sales Return: {line.get("product_name", "")}',
                )
