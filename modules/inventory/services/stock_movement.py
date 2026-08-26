from typing import Optional
from fastapi import HTTPException
from modules.core.repositories.base import CrudRepository

STOCK_REPO = CrudRepository(
    'T0009',
    business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'in_transit_qty', 'reorder_level']
)


def _get_stock(product_id: int, warehouse_id: int, conn=None):
    rows = STOCK_REPO.list(filters={'product_id': product_id, 'warehouse_id': warehouse_id}, conn=conn)
    return rows[0] if rows else None


def _get_or_create_stock(product_id: int, warehouse_id: int, conn=None):
    stock = _get_stock(product_id, warehouse_id, conn=conn)
    if not stock:
        return STOCK_REPO.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'qty': 0,
            'reserved_qty': 0,
            'in_transit_qty': 0,
            'reorder_level': 0
        }, conn=conn)
    return stock


class StockMovementService:
    def __init__(self):
        self.repo = CrudRepository(
            'T0064',
            business_columns=[
                'id', 'product_id', 'warehouse_id', 'movement_type',
                'reference_type', 'reference_id', 'qty_change',
                'balance_after', 'description', 'movement_date'
            ]
        )

    def record_movement(
        self,
        product_id: int,
        warehouse_id: int,
        movement_type: str,
        qty_change: float,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        conn=None
    ):
        stock_rows = STOCK_REPO.list(filters={'product_id': product_id, 'warehouse_id': warehouse_id}, conn=conn)
        current_qty = stock_rows[0]['qty'] if stock_rows else 0
        new_balance = current_qty + qty_change
        if new_balance < 0:
            new_balance = 0
        if stock_rows:
            STOCK_REPO.update(stock_rows[0]['id'], {'qty': new_balance}, conn=conn)
        else:
            STOCK_REPO.create({
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'qty': new_balance,
                'reserved_qty': 0,
                'in_transit_qty': 0,
                'reorder_level': 0
            }, conn=conn)
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
        return self.repo.create(payload, conn=conn)

    def reserve_stock(
        self,
        product_id: int,
        warehouse_id: int,
        qty: float,
        reference_type: str = 'sales_order',
        reference_id: Optional[int] = None,
        conn=None
    ):
        stock = _get_stock(product_id, warehouse_id, conn=conn)
        if not stock:
            raise HTTPException(400, f'No stock record for product {product_id} in warehouse {warehouse_id}')
        available = stock['qty'] - stock.get('reserved_qty', 0)
        if available < qty:
            raise HTTPException(400, f'Insufficient stock for product {product_id}: available {available}, requested {qty}')
        new_reserved = stock.get('reserved_qty', 0) + qty
        STOCK_REPO.update(stock['id'], {'reserved_qty': new_reserved}, conn=conn)
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Reserve',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': 0,
            'balance_after': stock['qty'],
            'description': f'Reserved {qty} for {reference_type} #{reference_id}',
        }, conn=conn)

    def release_stock(
        self,
        product_id: int,
        warehouse_id: int,
        qty: float,
        reference_type: str = 'sales_order',
        reference_id: Optional[int] = None,
        conn=None
    ):
        stock = _get_stock(product_id, warehouse_id, conn=conn)
        if not stock:
            return None
        current_reserved = stock.get('reserved_qty', 0)
        new_reserved = max(0, current_reserved - qty)
        STOCK_REPO.update(stock['id'], {'reserved_qty': new_reserved}, conn=conn)
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Unreserve',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': 0,
            'balance_after': stock['qty'],
            'description': f'Released {qty} from {reference_type} #{reference_id}',
        }, conn=conn)

    def deduct_stock(
        self,
        product_id: int,
        warehouse_id: int,
        qty: float,
        reference_type: str = 'sales_order',
        reference_id: Optional[int] = None,
        conn=None
    ):
        stock = _get_stock(product_id, warehouse_id, conn=conn)
        if not stock:
            raise HTTPException(400, f'No stock record for product {product_id} in warehouse {warehouse_id}')
        current_reserved = stock.get('reserved_qty', 0)
        new_reserved = max(0, current_reserved - qty)
        new_qty = max(0, stock['qty'] - qty)
        STOCK_REPO.update(stock['id'], {'qty': new_qty, 'reserved_qty': new_reserved}, conn=conn)
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Deduct',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': -qty,
            'balance_after': new_qty,
            'description': f'Deducted {qty} for {reference_type} #{reference_id}',
        }, conn=conn)

    def transfer_dispatch(
        self,
        product_id: int,
        source_warehouse_id: int,
        destination_warehouse_id: int,
        qty: float,
        reference_type: str = 'StockTransfer',
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        conn=None
    ):
        """
        Dispatches inventory from source warehouse to in-transit:
        - Deducts stock from source warehouse
        - Increments in_transit_qty at destination warehouse
        - Logs 'Transfer Out' stock movement in T0064
        """
        if qty <= 0:
            raise HTTPException(400, 'Transfer dispatch quantity must be greater than 0')

        source_stock = _get_stock(product_id, source_warehouse_id, conn=conn)
        if not source_stock:
            raise HTTPException(400, f'No stock record for product {product_id} in warehouse {source_warehouse_id}')

        available = float(source_stock.get('qty', 0) or 0) - float(source_stock.get('reserved_qty', 0) or 0)
        if available < qty:
            raise HTTPException(
                400,
                f'Insufficient stock for product {product_id} in warehouse {source_warehouse_id}: '
                f'available {available}, requested {qty}'
            )

        # 1. Deduct source warehouse available stock
        current_source_qty = float(source_stock.get('qty', 0) or 0)
        new_source_qty = max(0.0, current_source_qty - float(qty))
        current_reserved = float(source_stock.get('reserved_qty', 0) or 0)
        new_source_reserved = min(current_reserved, new_source_qty)
        STOCK_REPO.update(source_stock['id'], {'qty': new_source_qty, 'reserved_qty': new_source_reserved}, conn=conn)

        # 2. Increment destination warehouse in_transit_qty
        dest_stock = _get_or_create_stock(product_id, destination_warehouse_id, conn=conn)
        current_in_transit = float(dest_stock.get('in_transit_qty', 0) or 0)
        new_in_transit = current_in_transit + float(qty)
        STOCK_REPO.update(dest_stock['id'], {'in_transit_qty': new_in_transit}, conn=conn)

        # 3. Log 'Transfer Out' movement for source warehouse
        desc = description or f'Transfer Out {qty} to warehouse #{destination_warehouse_id} (Transfer #{reference_id})'
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': source_warehouse_id,
            'movement_type': 'Transfer Out',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': -float(qty),
            'balance_after': new_source_qty,
            'description': desc,
        }, conn=conn)

    def transfer_receive(
        self,
        product_id: int,
        destination_warehouse_id: int,
        qty_received: float,
        qty_dispatched: Optional[float] = None,
        source_warehouse_id: Optional[int] = None,
        reference_type: str = 'StockTransfer',
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        conn=None
    ):
        """
        Receives inventory at destination warehouse:
        - Decrements in_transit_qty at destination warehouse
        - Adds received quantity to destination warehouse available stock
        - Logs 'Transfer In' stock movement in T0064
        """
        if qty_received < 0:
            raise HTTPException(400, 'Received quantity cannot be negative')

        # 1. Update destination warehouse stock & in_transit_qty
        dest_stock = _get_or_create_stock(product_id, destination_warehouse_id, conn=conn)
        current_dest_qty = float(dest_stock.get('qty', 0) or 0)
        current_in_transit = float(dest_stock.get('in_transit_qty', 0) or 0)

        in_transit_deduction = float(qty_dispatched) if qty_dispatched is not None else float(qty_received)
        new_in_transit = max(0.0, current_in_transit - in_transit_deduction)
        new_dest_qty = current_dest_qty + float(qty_received)

        STOCK_REPO.update(dest_stock['id'], {'qty': new_dest_qty, 'in_transit_qty': new_in_transit}, conn=conn)

        # 2. Log 'Transfer In' movement for destination warehouse
        desc = description or f'Transfer In {qty_received} at warehouse #{destination_warehouse_id} (Transfer #{reference_id})'
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': destination_warehouse_id,
            'movement_type': 'Transfer In',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': float(qty_received),
            'balance_after': new_dest_qty,
            'description': desc,
        }, conn=conn)

    def record_transfer_loss(
        self,
        product_id: int,
        warehouse_id: int,
        qty_lost: float,
        loss_reason: Optional[str] = None,
        loss_notes: Optional[str] = None,
        reference_type: str = 'StockTransfer',
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        decrement_in_transit: bool = False,
        user_id: Optional[int] = None,
        conn=None
    ):
        """
        Logs inventory loss or transit discrepancy:
        - Optionally decrements in_transit_qty at the specified warehouse
        - Logs 'Transfer Loss' stock movement in T0064 with reason code and notes
        """
        if qty_lost <= 0:
            return None

        # 1. Optionally decrement in_transit_qty if not already decremented during receive
        if decrement_in_transit:
            stock = _get_stock(product_id, warehouse_id, conn=conn)
            if stock:
                current_in_transit = float(stock.get('in_transit_qty', 0) or 0)
                new_in_transit = max(0.0, current_in_transit - float(qty_lost))
                STOCK_REPO.update(stock['id'], {'in_transit_qty': new_in_transit}, conn=conn)

        # 2. Balance after is current on-hand quantity at warehouse
        stock = _get_stock(product_id, warehouse_id, conn=conn)
        balance_after = float(stock.get('qty', 0) or 0) if stock else 0.0

        # 3. Format loss description with reason code and notes
        desc_parts = [description or f'Transfer Loss: {qty_lost} units']
        if loss_reason:
            desc_parts.append(f'Reason: {loss_reason}')
        if loss_notes:
            desc_parts.append(f'Notes: {loss_notes}')
        desc = ' | '.join(desc_parts)

        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'movement_type': 'Transfer Loss',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': -float(qty_lost),
            'balance_after': balance_after,
            'description': desc,
        }, conn=conn)

    def cancel_transfer_dispatch(
        self,
        product_id: int,
        source_warehouse_id: int,
        destination_warehouse_id: int,
        qty: float,
        reference_type: str = 'StockTransfer',
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        conn=None
    ):
        """
        Restores source warehouse inventory and clears destination in-transit inventory upon transfer cancellation.
        """
        # 1. Restore source stock
        source_stock = _get_or_create_stock(product_id, source_warehouse_id, conn=conn)
        current_source_qty = float(source_stock.get('qty', 0) or 0)
        new_source_qty = current_source_qty + float(qty)
        STOCK_REPO.update(source_stock['id'], {'qty': new_source_qty}, conn=conn)

        # 2. Decrement destination in_transit_qty
        dest_stock = _get_stock(product_id, destination_warehouse_id, conn=conn)
        if dest_stock:
            current_in_transit = float(dest_stock.get('in_transit_qty', 0) or 0)
            new_in_transit = max(0.0, current_in_transit - float(qty))
            STOCK_REPO.update(dest_stock['id'], {'in_transit_qty': new_in_transit}, conn=conn)

        # 3. Log movement
        desc = description or f'Transfer Cancelled: restored {qty} to warehouse #{source_warehouse_id} (Transfer #{reference_id})'
        return self.repo.create({
            'product_id': product_id,
            'warehouse_id': source_warehouse_id,
            'movement_type': 'Transfer Cancel',
            'reference_type': reference_type,
            'reference_id': reference_id,
            'qty_change': float(qty),
            'balance_after': new_source_qty,
            'description': desc,
        }, conn=conn)

    def get_stock_level(self, product_id: int, warehouse_id: int, conn=None) -> dict:
        """
        Returns full stock position including on-hand, reserved, in-transit, and available quantities.
        """
        stock = _get_stock(product_id, warehouse_id, conn=conn)
        if not stock:
            return {
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'qty': 0.0,
                'reserved_qty': 0.0,
                'in_transit_qty': 0.0,
                'available_qty': 0.0,
                'reorder_level': 0.0,
            }
        qty = float(stock.get('qty', 0) or 0)
        reserved = float(stock.get('reserved_qty', 0) or 0)
        in_transit = float(stock.get('in_transit_qty', 0) or 0)
        return {
            'id': stock.get('id'),
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'qty': qty,
            'reserved_qty': reserved,
            'in_transit_qty': in_transit,
            'available_qty': max(0.0, qty - reserved),
            'reorder_level': float(stock.get('reorder_level', 0) or 0),
        }

