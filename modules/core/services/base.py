from typing import Optional
from modules.core.repositories.base import CrudRepository


class CrudService:
    def __init__(self, repo: CrudRepository):
        self.repo = repo

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, business_id=business_id)
        return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset)

    def get(self, id_val, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.get(id_val, business_id=business_id)
        return self.repo.get(id_val)

    def get_unscoped(self, id_val):
        return self.repo.get_unscoped(id_val)

    def create(self, payload: dict, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.create(payload, business_id=business_id)
        return self.repo.create(payload)

    def update(self, id_val, payload: dict, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.update(id_val, payload, business_id=business_id)
        return self.repo.update(id_val, payload)

    def count(self, filters: dict = None, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.count(filters=filters, business_id=business_id)
        return self.repo.count(filters=filters)

    def delete(self, id_val, business_id: Optional[int] = None):
        if business_id is not None:
            return self.repo.delete(id_val, business_id=business_id)
        return self.repo.delete(id_val)
