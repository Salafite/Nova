from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

VALID_QUOTE_STATUS_TRANSITIONS = {
    'Draft': ['Sent', 'Cancelled'],
    'Sent': ['Accepted', 'Rejected', 'Cancelled'],
    'Accepted': ['Converted', 'Cancelled'],
    'Converted': [],
    'Rejected': [],
    'Cancelled': [],
}

class QuotationService(CrudService):
    def create(self, payload: dict):
        if not payload.get('grand_total') and payload.get('subtotal') is not None:
            payload['grand_total'] = payload.get('subtotal', 0) + payload.get('tax', 0)
        return super().create(payload)

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_QUOTE_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid quotation status transition: {old_status} -> {new_status}. Allowed: {allowed}')
        if 'subtotal' in payload or 'tax' in payload:
            sub = payload.get('subtotal', old.get('subtotal', 0) if old else 0)
            tx = payload.get('tax', old.get('tax', 0) if old else 0)
            payload['grand_total'] = sub + tx
        return super().update(id_val, payload)

    def convert_to_order(self, quote_id):
        quote = self.repo.get(quote_id)
        if not quote:
            from fastapi import HTTPException
            raise HTTPException(404, 'Quotation not found')
        if quote.get('status') != 'Accepted':
            from fastapi import HTTPException
            raise HTTPException(400, 'Only accepted quotations can be converted to orders')
        order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'customer_id', 'subtotal', 'tax', 'grand_total', 'status', 'order_date', 'notes'])
        order_num = 'INV-' + str(order_repo.list().__len__() + 1).zfill(3)
        order = order_repo.create({
            'order_number': order_num,
            'customer_id': quote['customer_id'],
            'subtotal': quote.get('subtotal', 0),
            'tax': quote.get('tax', 0),
            'grand_total': quote.get('grand_total', 0),
            'status': 'Pending',
            'order_date': str(quote.get('quote_date', '')),
            'notes': 'Converted from quotation ' + quote.get('quote_number', ''),
        })
        self.repo.update(quote_id, {'status': 'Converted', 'converted_order_id': order['id']})
        return order
