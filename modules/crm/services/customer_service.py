from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

class CustomerService(CrudService):
    def delete(self, id_val):
        order_repo = CrudRepository('T0012', business_columns=['id', 'customer_id', 'status'])
        open_orders = order_repo.list(filters={'customer_id': id_val})
        active_orders = [o for o in open_orders if o.get('status') not in ('Cancelled', 'Paid')]
        if active_orders:
            from fastapi import HTTPException
            raise HTTPException(400, f'Cannot delete customer: {len(active_orders)} active order(s) exist')
        return super().delete(id_val)
