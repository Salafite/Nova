from modules.core.services.base import CrudService


class OpportunityLineService(CrudService):
    def create(self, payload: dict):
        qty = float(payload.get('qty', 1))
        unit_price = float(payload.get('unit_price', 0))
        payload['line_total'] = qty * unit_price
        return super().create(payload)

    def update(self, id_val, payload: dict):
        if 'qty' in payload or 'unit_price' in payload:
            existing = self.get(id_val)
            if existing:
                qty = float(payload.get('qty', existing['qty']))
                unit_price = float(payload.get('unit_price', existing['unit_price']))
                payload['line_total'] = qty * unit_price
        return super().update(id_val, payload)
