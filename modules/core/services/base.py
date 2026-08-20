from modules.core.repositories.base import CrudRepository


class CrudService:
    def __init__(self, repo: CrudRepository):
        self.repo = repo

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None):
        if conn is not None:
            return self.repo.list(filters, order_by, limit, offset, conn=conn)
        return self.repo.list(filters, order_by, limit, offset)

    def get(self, id_val, conn=None):
        if conn is not None:
            return self.repo.get(id_val, conn=conn)
        return self.repo.get(id_val)

    def create(self, payload: dict, conn=None):
        if conn is not None:
            return self.repo.create(payload, conn=conn)
        return self.repo.create(payload)

    def update(self, id_val, payload: dict, conn=None):
        if conn is not None:
            return self.repo.update(id_val, payload, conn=conn)
        return self.repo.update(id_val, payload)

    def count(self, filters: dict = None, conn=None):
        if conn is not None:
            return self.repo.count(filters, conn=conn)
        return self.repo.count(filters)

    def delete(self, id_val, conn=None):
        if conn is not None:
            return self.repo.delete(id_val, conn=conn)
        return self.repo.delete(id_val)
