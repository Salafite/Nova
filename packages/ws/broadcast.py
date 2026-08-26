from packages.ws.manager import inventory_manager, order_manager


async def inventory_changed(business_id: int, product_id: int, qty: float, warehouse_id: int = None):
    await inventory_manager.broadcast(
        f'inventory:{business_id}',
        'stock_updated',
        {'product_id': product_id, 'qty': qty, 'warehouse_id': warehouse_id},
    )


async def order_status_changed(business_id: int, order_id: int, order_number: str, status: str, **kwargs):
    data = {'order_id': order_id, 'order_number': order_number, 'status': status}
    if kwargs:
        data.update({k: v for k, v in kwargs.items() if v is not None})
    await order_manager.broadcast(
        f'orders:{business_id}',
        'order_status_changed',
        data,
    )


async def order_credit_hold_placed(
    business_id: int,
    order_id: int,
    order_number: str,
    customer_id: int = None,
    customer_name: str = None,
    hold_reason: str = None,
    grand_total: float = None,
):
    await order_manager.broadcast(
        f'orders:{business_id}',
        'order_credit_hold',
        {
            'order_id': order_id,
            'order_number': order_number,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'hold_reason': hold_reason,
            'grand_total': grand_total,
            'status': 'Credit Hold',
        },
    )

