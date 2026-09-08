from typing import Optional
from modules.core.repositories.base import CrudRepository


class CrudService:
    def __init__(self, repo: CrudRepository):
        self.repo = repo

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None, business_id: Optional[int] = None, for_update: bool = False):
        extra_kwargs = {'for_update': True} if for_update else {}
        if conn is not None:
            if business_id is not None:
                return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, conn=conn, business_id=business_id, **extra_kwargs)
            return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, conn=conn, **extra_kwargs)
        if business_id is not None:
            return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, business_id=business_id, **extra_kwargs)
        return self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, **extra_kwargs)

    def get(self, id_val, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.get(id_val, conn=conn, business_id=business_id)
            return self.repo.get(id_val, conn=conn)
        if business_id is not None:
            return self.repo.get(id_val, business_id=business_id)
        return self.repo.get(id_val)

    def get_unscoped(self, id_val):
        return self.repo.get_unscoped(id_val)

    def get_for_update(self, id_val, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.get_for_update(id_val, conn=conn, business_id=business_id)
            return self.repo.get_for_update(id_val, conn=conn)
        if business_id is not None:
            return self.repo.get_for_update(id_val, business_id=business_id)
        return self.repo.get_for_update(id_val)

    def get_many_for_update(self, id_vals: list, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.get_many_for_update(id_vals, conn=conn, business_id=business_id)
            return self.repo.get_many_for_update(id_vals, conn=conn)
        if business_id is not None:
            return self.repo.get_many_for_update(id_vals, business_id=business_id)
        return self.repo.get_many_for_update(id_vals)

    def create(self, payload: dict, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.create(payload, conn=conn, business_id=business_id)
            return self.repo.create(payload, conn=conn)
        if business_id is not None:
            return self.repo.create(payload, business_id=business_id)
        return self.repo.create(payload)

    def update(self, id_val, payload: dict, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.update(id_val, payload, conn=conn, business_id=business_id)
            return self.repo.update(id_val, payload, conn=conn)
        if business_id is not None:
            return self.repo.update(id_val, payload, business_id=business_id)
        return self.repo.update(id_val, payload)

    def count(self, filters: dict = None, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.count(filters=filters, conn=conn, business_id=business_id)
            return self.repo.count(filters=filters, conn=conn)
        if business_id is not None:
            return self.repo.count(filters=filters, business_id=business_id)
        return self.repo.count(filters=filters)

    def delete(self, id_val, conn=None, business_id: Optional[int] = None):
        if conn is not None:
            if business_id is not None:
                return self.repo.delete(id_val, conn=conn, business_id=business_id)
            return self.repo.delete(id_val, conn=conn)
        if business_id is not None:
            return self.repo.delete(id_val, business_id=business_id)
        return self.repo.delete(id_val)
