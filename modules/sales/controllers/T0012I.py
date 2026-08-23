import asyncio
import logging
from fastapi import HTTPException
from fastapi import Depends, HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.sales.models import SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse
from packages.auth.deps import get_current_user
from packages.ws.broadcast import order_status_changed

logger = logging.getLogger(__name__)

repo = CrudRepository(
    'T0012',
    business_columns=[
        'id',
        'order_number',
        'customer_id',
        'warehouse_id',
        'subtotal',
        'tax',
        'grand_total',
        'freight_amount',
        'discount_amount',
        'sales_rep_id',
        'status',
        'order_date',
        'notes',
        'price_list_id',
        'tax_rate_id',
        'payment_term_id',
    ],
)
service = SalesOrderService(repo)

router = create_crud_router(
    '/api/T0012I',
    'T0012 - Sales Orders',
    service,
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderResponse,
)

enhanced_service = EnhancedSalesOrderService(repo)

_broadcast_tasks = set()


def _safe_broadcast(coro):
    """Schedule an async broadcast, honoring both async and sync (threadpool) contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Sync endpoint running in a threadpool thread: run the broadcast on its own loop.
        try:
            asyncio.run(coro)
        except Exception as e:
            logger.warning(f"Failed to run status broadcast: {e}")
        return
    task = loop.create_task(coro)
    _broadcast_tasks.add(task)
    task.add_done_callback(_broadcast_tasks.discard)


def _server_error(e: Exception, action: str):
    logger.error(f"Failed to {action}: {e}", exc_info=True)
    raise HTTPException(500, 'Internal server error') from e


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
        _server_error(e, 'create order with lines')

@router.post('/{id}/confirm')
def confirm_order(id: int, user: dict = Depends(get_current_user)):
    """Confirm a pending order: reserves stock and updates status."""
    order = service.get(id)
    if not order:
        check_record_ownership(service, id, user, 'T0012', 'POST')
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
        _server_error(e, 'confirm order')

@router.post('/{id}/deliver')
def deliver_order(id: int, user: dict = Depends(get_current_user)):
    """Mark an order as delivered: creates invoice, updates customer balance, and updates status atomically."""
    order = service.get(id)
    if not order:
        check_record_ownership(service, id, user, 'T0012', 'POST')
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
        _server_error(e, 'deliver order')

@router.post('/{id}/cancel')
def cancel_order(id: int, user: dict = Depends(get_current_user)):
    """Cancel an order: releases reserved stock."""
    order = service.get(id)
    if not order:
        check_record_ownership(service, id, user, 'T0012', 'POST')
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
        _server_error(e, 'cancel order')

@router.post('/{id}/recalculate-catch-weight')
def recalculate_order_catch_weight(id: int):
    """Recalculate sales order lines and totals based on actual catch-weights from warehouse picking."""
    order = service.get(id)
    if not order:
        raise HTTPException(404, 'Order not found')
    try:
        result = service.recalculate_order_catch_weight(id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        _server_error(e, 'recalculate order catch weight')

@router.get('/{id}/recalculate-preview')
def preview_order_catch_weight_recalculation(id: int):
    """Preview sales order recalculation without persisting changes."""
    order = service.get(id)
    if not order:
        raise HTTPException(404, 'Order not found')
    try:
        # Recalculate will return the full breakdown
        result = service.recalculate_order_catch_weight(id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        _server_error(e, 'preview order recalculation')

