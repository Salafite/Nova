from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

VALID_SALES_STATUS_TRANSITIONS = {
    'Draft': ['Confirmed', 'Cancelled'],
    'Pending': ['Confirmed', 'Cancelled'],
    'Confirmed': ['Shipped', 'Cancelled'],
    'Shipped': ['Delivered', 'Cancelled'],
    'Delivered': ['Invoiced'],
    'Invoiced': ['Paid', 'Cancelled'],
    'Paid': [],
    'Cancelled': [],
}

LINE_REPO = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])

class SalesOrderService(CrudService):
    def create(self, payload: dict):
        if not payload.get('grand_total') and payload.get('subtotal') is not None:
            payload['grand_total'] = payload.get('subtotal', 0) + payload.get('tax', 0)
        customer_id = payload.get('customer_id')
        if customer_id:
            customer_repo = CrudRepository('T0010', business_columns=['id', 'name', 'credit_limit', 'balance'])
            customer = customer_repo.get(customer_id)
            if customer:
                new_balance = customer.get('balance', 0) + payload.get('grand_total', 0)
                credit_limit = customer.get('credit_limit', 0)
                if credit_limit > 0 and new_balance > credit_limit:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Order would exceed credit limit ({customer.get("name")}: limit={credit_limit}, new balance={new_balance})')
        return super().create(payload)

    def _generate_invoice_number(self):
        inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number'])
        rows = inv_repo.list(order_by='id', limit=1)
        last_num = 0
        if rows:
            last_val = rows[0].get('invoice_number', 'INV-00000')
            try:
                last_num = int(last_val.split('-')[1])
            except (IndexError, ValueError):
                pass
        return f'INV-{last_num + 1:05d}'

    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_SALES_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid status transition: {old_status} -> {new_status}. Allowed: {allowed}')
                if new_status == 'Confirmed' and old_status in ('Draft', 'Pending'):
                    self._reserve_order_stock(id_val)
                elif new_status == 'Delivered' and old_status == 'Shipped':
                    self._create_invoice_from_order(id_val)
                elif new_status == 'Cancelled' and old_status in ('Draft', 'Pending', 'Confirmed'):
                    self._release_order_stock(id_val)
        return super().update(id_val, payload)

    def _create_invoice_from_order(self, order_id):
        order = self.repo.get(order_id)
        if not order:
            return
        inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes'])
        invoice_number = self._generate_invoice_number()
        inv_repo.create({
            'invoice_number': invoice_number,
            'invoice_type': 'Sales',
            'partner_id': order.get('customer_id'),
            'sales_order_id': order_id,
            'issue_date': order.get('order_date'),
            'due_date': order.get('order_date'),
            'total_amount': order.get('grand_total', 0),
            'status': 'Unpaid',
            'notes': f'Auto-generated from order {order.get("order_number")}',
        })
        customer_repo = CrudRepository('T0010', business_columns=['id', 'name', 'balance', 'credit_limit'])
        customer = customer_repo.get(order['customer_id'])
        if customer:
            new_balance = customer.get('balance', 0) + order.get('grand_total', 0)
            customer_repo.update(order['customer_id'], {'balance': new_balance})

    def _reserve_order_stock(self, order_id):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id)
        warehouse_id = order.get('warehouse_id') if order else None
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1)
            if warehouses:
                warehouse_id = warehouses[0]['id']
            else:
                from fastapi import HTTPException
                raise HTTPException(400, 'No active warehouse found for stock reservation')
        lines = LINE_REPO.list(filters={'sales_order_id': order_id})
        svc = StockMovementService()
        errors = []
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            try:
                svc.reserve_stock(product_id, warehouse_id, qty, 'sales_order', order_id)
            except Exception as e:
                errors.append(f'Product {product_id}: {str(e)}')
        if errors:
            raise Exception(f'Stock reservation partial failure: {"; ".join(errors)}')
        from modules.warehouse.services.pick_list_service import PickListService
        try:
            pl_service = PickListService()
            pl_service.create_from_order(order_id, warehouse_id)
        except Exception:
            pass

    def _release_order_stock(self, order_id):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id)
        warehouse_id = order.get('warehouse_id') if order else None
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1)
            if not warehouses:
                return
            warehouse_id = warehouses[0]['id']
        lines = LINE_REPO.list(filters={'sales_order_id': order_id})
        svc = StockMovementService()
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            svc.release_stock(product_id, warehouse_id, qty, 'sales_order', order_id)
