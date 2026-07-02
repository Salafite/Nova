from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository

VALID_PO_STATUS_TRANSITIONS = {
    'Pending': ['Approved', 'Cancelled'],
    'Approved': ['Shipped', 'Cancelled'],
    'Shipped': ['Partially Received', 'Received', 'Cancelled'],
    'Partially Received': ['Received', 'Cancelled'],
    'Received': ['Closed'],
    'Closed': [],
    'Cancelled': [],
}

class PurchaseOrderService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.stock_service = StockMovementService()

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_PO_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid PO status transition: {old_status} -> {new_status}. Allowed: {allowed}')
        result = super().update(id_val, payload)
        if old and payload.get('status') == 'Received' and old.get('status') != 'Received':
            lines = self._get_lines(id_val)
            for line in lines:
                if line.get('product_id'):
                    self.stock_service.record_movement(
                        product_id=line['product_id'],
                        warehouse_id=1,
                        movement_type='Purchase',
                        qty_change=line.get('qty', 0),
                        reference_type='PurchaseOrder',
                        reference_id=id_val,
                        description=f'PO Receive: {line.get("product_name", "")}',
                    )
        return result

    def _get_lines(self, po_id):
        repo = CrudRepository('T0015', business_columns=['id', 'purchase_order_id', 'product_id', 'product_name', 'qty'])
        return repo.list(filters={'purchase_order_id': po_id})

    def convert_from_rfq(self, rfq_id, vendor_id):
        rfq_repo = CrudRepository('T0071', business_columns=['id', 'rfq_number', 'title', 'description', 'status'])
        rfq = rfq_repo.get(rfq_id)
        if not rfq:
            from fastapi import HTTPException
            raise HTTPException(404, 'RFQ not found')
        if rfq.get('status') != 'Open':
            from fastapi import HTTPException
            raise HTTPException(400, 'Only Open RFQs can be converted to purchase orders')

        rfq_line_repo = CrudRepository('T0072', business_columns=['id', 'rfq_id', 'product_id', 'description', 'qty', 'uom_id', 'line_number'])
        lines = rfq_line_repo.list(filters={'rfq_id': rfq_id})

        rfq_quote_repo = CrudRepository('T0074', business_columns=['id', 'rfq_id', 'vendor_id', 'line_id', 'unit_price', 'total_price'])
        quotes = rfq_quote_repo.list(filters={'rfq_id': rfq_id, 'vendor_id': vendor_id})
        quote_map = {q['line_id']: q for q in quotes}

        po_num = 'PO-' + str(self.repo.list().__len__() + 1).zfill(3)
        grand_total = sum(quote_map.get(l['id'], {}).get('total_price', 0) or l.get('qty', 0) * 0 for l in lines)
        po = self.repo.create({
            'order_number': po_num,
            'supplier_id': vendor_id,
            'total': grand_total,
            'status': 'Pending',
            'notes': 'Converted from RFQ ' + rfq.get('rfq_number', '') + ': ' + (rfq.get('title', '') or ''),
            'converted_rfq_id': rfq_id,
        })

        po_line_repo = CrudRepository('T0015', business_columns=['id', 'purchase_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total', 'line_number'])
        for i, line in enumerate(lines):
            quote = quote_map.get(line['id'], {})
            unit_price = quote.get('unit_price', 0)
            qty = line.get('qty', 0)
            po_line_repo.create({
                'purchase_order_id': po['id'],
                'product_id': line.get('product_id'),
                'product_name': line.get('description', ''),
                'uom_id': line.get('uom_id'),
                'qty': qty,
                'unit_price': unit_price,
                'line_total': qty * unit_price,
                'line_number': i + 1,
            })

        rfq_vendor_repo = CrudRepository('T0073', business_columns=['id', 'rfq_id', 'vendor_id', 'status'])
        rfv = rfq_vendor_repo.list(filters={'rfq_id': rfq_id, 'vendor_id': vendor_id})
        for v in rfv:
            rfq_vendor_repo.update(v['id'], {'status': 'Quoted'})
        rfq_repo.update(rfq_id, {'status': 'Closed'})
        return po
