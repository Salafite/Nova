from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository


class DeliveryService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.stock_service = StockMovementService()
        self.line_repo = CrudRepository('T0078', business_columns=['id', 'delivery_id', 'sales_order_line_id', 'product_id', 'product_name', 'qty_shipped', 'qty_ordered', 'uom_id', 'line_number'])

    def create(self, payload: dict):
        result = super().create(payload)
        if result and payload.get('status') == 'Shipped':
            self._record_stock_movements(result['id'])
        return result

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        result = super().update(id_val, payload)
        if old and payload.get('status') == 'Shipped' and old.get('status') != 'Shipped':
            self._record_stock_movements(id_val)
        return result

    def _record_stock_movements(self, delivery_id):
        lines = self.line_repo.list(filters={'delivery_id': delivery_id})
        for line in lines:
            if line.get('product_id'):
                self.stock_service.record_movement(
                    product_id=line['product_id'],
                    warehouse_id=1,
                    movement_type='Delivery',
                    qty_change=-abs(line.get('qty_shipped', 0)),
                    reference_type='Delivery',
                    reference_id=delivery_id,
                    description=f'Delivery: {line.get("product_name", "")}',
                )
