from modules.core.services.base import CrudService


class SalesReturnLineService(CrudService):
    def create(self, payload: dict):
        payload['line_total'] = payload.get('qty', 0) * payload.get('unit_price', 0)
        return super().create(payload)

    def update(self, id_val, payload: dict):
        if 'qty' in payload or 'unit_price' in payload:
            existing = self.repo.get(id_val)
            qty = payload.get('qty', existing.get('qty', 0))
            unit_price = payload.get('unit_price', existing.get('unit_price', 0))
            payload['line_total'] = qty * unit_price
        return super().update(id_val, payload)
