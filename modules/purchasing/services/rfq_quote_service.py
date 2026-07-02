from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository


class RFQQuoteService(CrudService):
    def create(self, payload: dict):
        line_id = payload.get('line_id')
        if line_id and (not payload.get('total_price') or payload.get('total_price') == 0):
            line_repo = CrudRepository('T0072', business_columns=['id', 'rfq_id', 'qty'])
            line = line_repo.get(line_id)
            if line:
                qty = line.get('qty', 0)
                unit_price = payload.get('unit_price', 0)
                payload['total_price'] = qty * unit_price
        return super().create(payload)

    def update(self, id_val, payload: dict):
        if 'unit_price' in payload or 'total_price' in payload:
            if payload.get('total_price') == 0:
                old = self.repo.get(id_val)
                line_id = old.get('line_id') if old else None
                if not line_id and 'line_id' in payload:
                    line_id = payload['line_id']
                if line_id:
                    line_repo = CrudRepository('T0072', business_columns=['id', 'rfq_id', 'qty'])
                    line = line_repo.get(line_id)
                    if line:
                        qty = line.get('qty', 0)
                        unit_price = payload.get('unit_price', old.get('unit_price', 0))
                        payload['total_price'] = qty * unit_price
        return super().update(id_val, payload)
