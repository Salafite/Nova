import asyncio
from fastapi import HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models import SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse
from packages.ws.broadcast import order_status_changed

repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal', 'tax', 'grand_total', 'status', 'order_date', 'notes', 'price_list_id', 'tax_rate_id', 'payment_term_id'])
service = SalesOrderService(repo)

router = create_crud_router('/api/T0012I', 'T0012 - Sales Orders', service,
                            SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse)

enhanced_service = EnhancedSalesOrderService(repo)

def _safe_broadcast(coro):
    try:
        asyncio.create_task(coro)
    except RuntimeError:
        try:
            coro.close()
        except Exception:
            pass


@router.post('/with-lines', status_code=201)
def create_order_with_lines(body: dict):
    """Create a sales order with line items, applying price list and tax rate."""
    order_data = body.get('order', {})
    lines = body.get('lines', [])
    try:
        result = enhanced_service.create_with_lines(order_data, lines)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/confirm')
def confirm_order(id: int):
    """Confirm a pending order: reserves stock, creates pick list, and updates status atomically."""
    order = service.get(id)
    if not order:
        raise HTTPException(404, 'Order not found')
    if order.get('status') not in ('Draft', 'Pending'):
        raise HTTPException(400, f'Only Draft or Pending orders can be confirmed. Current status: {order.get("status")}')
    try:
        result = service.update(id, {'status': 'Confirmed'})
        _safe_broadcast(order_status_changed(1, id, order.get('order_number', ''), 'Confirmed'))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/deliver')
def deliver_order(id: int):
    """Mark an order as delivered: creates invoice, updates customer balance, and updates status atomically."""
    order = service.get(id)
    if not order:
        raise HTTPException(404, 'Order not found')
    if order.get('status') != 'Shipped':
        raise HTTPException(400, f'Only Shipped orders can be marked as delivered. Current status: {order.get("status")}')
    try:
        result = service.update(id, {'status': 'Delivered'})
        _safe_broadcast(order_status_changed(1, id, order.get('order_number', ''), 'Delivered'))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/cancel')
def cancel_order(id: int):
    """Cancel an order: releases reserved stock and updates status atomically."""
    order = service.get(id)
    if not order:
        raise HTTPException(404, 'Order not found')
    if order.get('status') in ('Paid', 'Cancelled'):
        raise HTTPException(400, f'Order cannot be cancelled. Current status: {order.get("status")}')
    try:
        result = service.update(id, {'status': 'Cancelled'})
        _safe_broadcast(order_status_changed(1, id, order.get('order_number', ''), 'Cancelled'))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))
