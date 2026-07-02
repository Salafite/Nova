from modules.core.services.base import CrudService

class RequisitionLineService(CrudService):
    def create(self, payload: dict):
        if not payload.get('total_price') or payload.get('total_price') == 0:
            qty = payload.get('qty', 0)
            price = payload.get('unit_price', 0)
            payload['total_price'] = qty * price
        return super().create(payload)

    def update(self, id_val, payload: dict):
        if 'qty' in payload or 'unit_price' in payload:
            old = self.repo.get(id_val)
            if old:
                qty = payload.get('qty', old.get('qty', 0))
                price = payload.get('unit_price', old.get('unit_price', 0))
                payload['total_price'] = qty * price
        return super().update(id_val, payload)
