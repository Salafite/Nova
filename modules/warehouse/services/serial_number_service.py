from modules.core.services.base import CrudService


class SerialNumberService(CrudService):
    def create(self, payload: dict):
        existing = self.repo.list(filters={'serial_number': payload.get('serial_number')})
        if existing:
            raise ValueError(f"Serial number '{payload.get('serial_number')}' already exists")
        payload.setdefault('status', 'In Stock')
        return super().create(payload)

    def markSold(self, id_val):
        return self.update(id_val, {'status': 'Sold'})

    def markReturned(self, id_val):
        return self.update(id_val, {'status': 'Returned'})
