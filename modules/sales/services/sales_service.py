import logging
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_invoice_number
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

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
    def create(self, payload: dict, conn=None):
        if not payload.get('grand_total') and payload.get('subtotal') is not None:
            payload['grand_total'] = payload.get('subtotal', 0) + payload.get('tax', 0)
        customer_id = payload.get('customer_id')
        if customer_id:
            customer_repo = CrudRepository('T0010', business_columns=['id', 'name', 'credit_limit', 'balance'])
            customer = customer_repo.get(customer_id, conn=conn)
            if customer:
                new_balance = customer.get('balance', 0) + payload.get('grand_total', 0)
                credit_limit = customer.get('credit_limit', 0)
                if credit_limit > 0 and new_balance > credit_limit:
                    from fastapi import HTTPException
                    logger.warning(
                        f"Order creation rejected for customer {customer.get('name')} (id {customer_id}): "
                        f"credit limit {credit_limit} exceeded by new balance {new_balance}"
                    )
                    raise HTTPException(400, f'Order would exceed credit limit ({customer.get("name")}: limit={credit_limit}, new balance={new_balance})')
        return super().create(payload, conn=conn)

    def _generate_invoice_number(self, conn=None):
        return generate_invoice_number(conn=conn)

    def update(self, id_val, payload: dict, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            old = self.repo.get(id_val, conn=conn)
            if old and 'status' in payload:
                old_status = old.get('status')
                new_status = payload['status']
                if old_status != new_status:
                    allowed = VALID_SALES_STATUS_TRANSITIONS.get(old_status, [])
                    if new_status not in allowed:
                        logger.warning(f"Invalid status transition attempted for sales order {id_val}: {old_status} -> {new_status}")
                        from fastapi import HTTPException
                        raise HTTPException(400, f'Invalid status transition: {old_status} -> {new_status}. Allowed: {allowed}')
                    logger.info(f"Sales order {id_val} transition requested: {old_status} -> {new_status}")
                    if new_status == 'Confirmed' and old_status in ('Draft', 'Pending'):
                        self._reserve_order_stock(id_val, conn=conn)
                    elif new_status == 'Delivered' and old_status == 'Shipped':
                        self._create_invoice_from_order(id_val, conn=conn)
                    elif new_status == 'Cancelled' and old_status in ('Draft', 'Pending', 'Confirmed'):
                        self._release_order_stock(id_val, conn=conn)
            result = super().update(id_val, payload, conn=conn)
            if should_release:
                conn.commit()
            return result
        except Exception as e:
            if should_release:
                try:
                    conn.rollback()
                    logger.info(f"Transaction rolled back for sales order {id_val} update: {e}")
                except Exception as rb_err:
                    logger.error(f"Error during transaction rollback for sales order {id_val}: {rb_err}")
            raise
        finally:
            if should_release:
                release_connection(conn)

    def _create_invoice_from_order(self, order_id, conn=None):
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot create invoice: Sales order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")
        inv_repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes'])
        try:
            invoice_number = self._generate_invoice_number(conn=conn)
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
            }, conn=conn)
            logger.info(f"Successfully created invoice {invoice_number} for sales order {order_id}")
        except Exception as e:
            logger.error(f"Failed to create invoice for sales order {order_id}: {e}")
            raise RuntimeError(f"Failed to create invoice for sales order {order_id}: {e}") from e

        customer_id = order.get('customer_id')
        if customer_id:
            try:
                customer_repo = CrudRepository('T0010', business_columns=['id', 'name', 'balance', 'credit_limit'])
                customer = customer_repo.get(customer_id, conn=conn)
                if customer:
                    new_balance = customer.get('balance', 0) + order.get('grand_total', 0)
                    customer_repo.update(customer_id, {'balance': new_balance}, conn=conn)
                    logger.info(f"Updated customer {customer_id} balance to {new_balance}")
            except Exception as e:
                logger.error(f"Failed to update customer balance for customer {customer_id}: {e}")
                raise RuntimeError(f"Failed to update customer balance for customer {customer_id}: {e}") from e

    def _reserve_order_stock(self, order_id, conn=None):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.error(f"Cannot reserve stock: Sales order {order_id} not found")
            raise ValueError(f"Sales order {order_id} not found")
        warehouse_id = order.get('warehouse_id')
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1, conn=conn)
            if warehouses:
                warehouse_id = warehouses[0]['id']
            else:
                logger.error(f"Cannot reserve stock for sales order {order_id}: No active warehouse found")
                from fastapi import HTTPException
                raise HTTPException(400, 'No active warehouse found for stock reservation')
        lines = LINE_REPO.list(filters={'sales_order_id': order_id}, conn=conn)
        svc = StockMovementService()
        errors = []
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            try:
                svc.reserve_stock(product_id, warehouse_id, qty, 'sales_order', order_id, conn=conn)
            except Exception as e:
                logger.warning(f"Failed to reserve stock for product {product_id} (qty {qty}) on order {order_id}: {e}")
                errors.append(f'Product {product_id}: {str(e)}')
        if errors:
            error_msg = f'Stock reservation partial failure: {"; ".join(errors)}'
            logger.error(f"Sales order {order_id} stock reservation failed: {error_msg}")
            raise RuntimeError(error_msg)
        from modules.warehouse.services.pick_list_service import PickListService
        try:
            pl_service = PickListService()
            pl_service.create_from_order(order_id, warehouse_id, conn=conn)
            logger.info(f"Successfully generated pick list for sales order {order_id} in warehouse {warehouse_id}")
        except Exception as e:
            logger.error(f"Failed to create pick list for sales order {order_id}: {e}")
            raise RuntimeError(f"Failed to create pick list for sales order {order_id}: {e}") from e

    def _release_order_stock(self, order_id, conn=None):
        from modules.inventory.services.stock_movement import StockMovementService
        order = self.repo.get(order_id, conn=conn)
        if not order:
            logger.warning(f"Cannot release stock: Sales order {order_id} not found")
            return
        warehouse_id = order.get('warehouse_id')
        if not warehouse_id:
            warehouse_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = warehouse_repo.list(filters={'is_active': True}, limit=1, conn=conn)
            if not warehouses:
                logger.warning(f"No active warehouse found when releasing stock for sales order {order_id}")
                return
            warehouse_id = warehouses[0]['id']
        lines = LINE_REPO.list(filters={'sales_order_id': order_id}, conn=conn)
        svc = StockMovementService()
        errors = []
        for line in lines:
            product_id = line.get('product_id')
            qty = line.get('qty', 0)
            if not product_id or qty <= 0:
                continue
            try:
                svc.release_stock(product_id, warehouse_id, qty, 'sales_order', order_id, conn=conn)
            except Exception as e:
                logger.warning(f"Failed to release stock for product {product_id} (qty {qty}) on order {order_id}: {e}")
                errors.append(f'Product {product_id}: {str(e)}')
        if errors:
            error_msg = f'Stock release partial failure: {"; ".join(errors)}'
            logger.error(f"Sales order {order_id} stock release failed: {error_msg}")
            raise RuntimeError(error_msg)


