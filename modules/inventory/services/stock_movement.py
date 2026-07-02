from modules.core.repositories.base import CrudRepository

STOCK_REPO = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])

def _get_stock(product_id, warehouse_id):
    rows = STOCK_REPO.list(filters={'product_id': product_id, 'warehouse_id': warehouse_id})
    return rows[0] if rows else None

class StockMovementService:
    def __init__(self):
        self.repo = CrudRepository('T0064', business_columns=['id', 'product_id', 'warehouse_id', 'movement_type', 'reference_type', 'reference_id', 'qty_change', 'balance_after', 'description', 'movement_date'])

    def record_movement(self, product_id, warehouse_id, movement_type, qty_change, reference_type=None, reference_id=None, description=None, user_id=None):
        stock_rows = STOCK_REPO.list(filters={'product_id': product_id, 'warehouse_id': warehouse_id})
        current_qty = stock_rows[0]['qty'] if stock_rows else 0
        new_balance = current_qty + qty_change
        if new_balance < 0:
            new_balance = 0
        if stock_rows:
            STOCK_REPO.update(stock_rows[0]['id'], {'qty': new_balance})
        payload = {
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': movement_type,
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': qty_change,
            'balance_after': new_balance,
            'description': description,
        }
        return self.repo.create(payload)

    def reserve_stock(self, product_id, warehouse_id, qty, reference_type='sales_order', reference_id=None):
        stock = _get_stock(product_id, warehouse_id)
        if not stock:
            from fastapi import HTTPException
            raise HTTPException(400, f'No stock record for product {product_id} in warehouse {warehouse_id}')
        available = stock['qty'] - stock.get('reserved_qty', 0)
        if available < qty:
            from fastapi import HTTPException
            raise HTTPException(400, f'Insufficient stock for product {product_id}: available {available}, requested {qty}')
        new_reserved = stock.get('reserved_qty', 0) + qty
        STOCK_REPO.update(stock['id'], {'reserved_qty': new_reserved})
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Reserve',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': 0,
            'balance_after': stock['qty'],
            'description': f'Reserved {qty} for {reference_type} #{reference_id}',
        })

    def release_stock(self, product_id, warehouse_id, qty, reference_type='sales_order', reference_id=None):
        stock = _get_stock(product_id, warehouse_id)
        if not stock:
            return None
        current_reserved = stock.get('reserved_qty', 0)
        new_reserved = max(0, current_reserved - qty)
        STOCK_REPO.update(stock['id'], {'reserved_qty': new_reserved})
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Unreserve',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': 0,
            'balance_after': stock['qty'],
            'description': f'Released {qty} from {reference_type} #{reference_id}',
        })

    def deduct_stock(self, product_id, warehouse_id, qty, reference_type='sales_order', reference_id=None):
        stock = _get_stock(product_id, warehouse_id)
        if not stock:
            from fastapi import HTTPException
            raise HTTPException(400, f'No stock record for product {product_id} in warehouse {warehouse_id}')
        current_reserved = stock.get('reserved_qty', 0)
        new_reserved = max(0, current_reserved - qty)
        new_qty = max(0, stock['qty'] - qty)
        STOCK_REPO.update(stock['id'], {'qty': new_qty, 'reserved_qty': new_reserved})
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Deduct',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': -qty,
            'balance_after': new_qty,
            'description': f'Deducted {qty} for {reference_type} #{reference_id}',
        })
