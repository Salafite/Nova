from packages.ws.manager import inventory_manager, order_manager


async def inventory_changed(business_id: int, product_id: int, qty: float, warehouse_id: int = None):
    await inventory_manager.broadcast(
        f'inventory:{business_id}',
        'stock_updated',
        {'product_id': product_id, 'qty': qty, 'warehouse_id': warehouse_id},
    )


async def order_status_changed(business_id: int, order_id: int, order_number: str, status: str):
    await order_manager.broadcast(
        f'orders:{business_id}',
        'order_status_changed',
        {'order_id': order_id, 'order_number': order_number, 'status': status},
    )
