from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository


class GoodsReceiptService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.stock_service = StockMovementService()
        self.line_repo = CrudRepository('T0076', business_columns=['id', 'receipt_id', 'purchase_order_line_id', 'product_id', 'product_name', 'qty_received', 'qty_ordered', 'uom_id', 'line_number'])
        self.po_repo = CrudRepository('T0014', business_columns=['id', 'order_number', 'supplier_id', 'total', 'status'])

    def create(self, payload: dict):
        result = super().create(payload)
        if result and payload.get('status') == 'Completed':
            self._record_stock_movements(result['id'])
            self._advance_po_status(result['id'])
        return result

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        result = super().update(id_val, payload)
        if old and payload.get('status') == 'Completed' and old.get('status') != 'Completed':
            self._record_stock_movements(id_val)
            self._advance_po_status(id_val)
        return result

    def _record_stock_movements(self, receipt_id):
        receipt = self.repo.get(receipt_id)
        warehouse_id = receipt.get('warehouse_id', 1) if receipt else 1
        lines = self.line_repo.list(filters={'receipt_id': receipt_id})
        for line in lines:
            if line.get('product_id'):
                self.stock_service.record_movement(
                    product_id=line['product_id'],
                    warehouse_id=warehouse_id,
                    movement_type='Goods Receipt',
                    qty_change=abs(line.get('qty_received', 0)),
                    reference_type='GoodsReceipt',
                    reference_id=receipt_id,
                    description=f'GRN: {line.get("product_name", "")}',
                )

    def _advance_po_status(self, receipt_id):
        receipt = self.repo.get(receipt_id)
        if not receipt:
            return
        po_id = receipt.get('purchase_order_id')
        if not po_id:
            return
        po = self.po_repo.get(po_id)
        if not po or po.get('status') in ('Received', 'Closed', 'Cancelled'):
            return

        po_line_repo = CrudRepository('T0015', business_columns=['id', 'purchase_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total'])
        po_lines = po_line_repo.list(filters={'purchase_order_id': po_id})
        if not po_lines:
            return

        all_grn_repo = CrudRepository('T0075', business_columns=['id', 'purchase_order_id', 'status'])
        all_grns = all_grn_repo.list(filters={'purchase_order_id': po_id, 'status': 'Completed'})

        total_qty_received = {}
        for grn in all_grns:
            grn_lines = self.line_repo.list(filters={'receipt_id': grn['id']})
            for line in grn_lines:
                pid = line.get('product_id')
                if pid:
                    total_qty_received[pid] = total_qty_received.get(pid, 0) + abs(line.get('qty_received', 0))

        all_received = all(
            total_qty_received.get(pl.get('product_id'), 0) >= abs(pl.get('qty', 0))
            for pl in po_lines if pl.get('product_id')
        )
        any_received = any(
            total_qty_received.get(pl.get('product_id'), 0) > 0
            for pl in po_lines if pl.get('product_id')
        )

        if all_received:
            self.po_repo.update(po_id, {'status': 'Received'})
        elif any_received:
            self.po_repo.update(po_id, {'status': 'Partially Received'})
