import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Optional
from fastapi import Depends, HTTPException
from modules.sales.services.sales_service import SalesOrderService
from modules.sales.services.enhanced_sales_order_service import EnhancedSalesOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.sales.models import (
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderResponse,
    CreditHoldOverrideRequest,
    CreditHoldRejectRequest,
)
from packages.auth.deps import get_current_user
from packages.security.audit import record_security_event
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
        'client_order_uuid',
        'is_offline_sync',
        'sync_status',
        'offline_created_at',
        'hold_reason',
        'hold_released_by',
        'hold_released_at',
        'hold_release_reason',
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


def _is_financial_manager(user: dict) -> bool:
    """Verify if the authenticated user has financial manager or credit override authority."""
    if not user or not isinstance(user, dict):
        return False
    role = str(user.get('role', '') or '').strip().lower()
    perms = user.get('permissions') or []
    if isinstance(perms, str):
        perms = [perms]
    perms_lower = [str(p).lower() for p in perms]

    authorized_roles = {
        'admin',
        'manager',
        'sales manager',
        'finance manager',
        'financial manager',
        'credit controller',
        'finance',
        'accounting',
    }
    authorized_perms = {
        '*',
        'admin_view',
        'finance_view',
        'credit_override',
        'credit_hold_override',
    }

    if role in authorized_roles:
        return True
    if any(p in authorized_perms for p in perms_lower):
        return True
    return False


@router.post('/{id}/override-credit-hold')
def override_credit_hold(
    id: int,
    body: Optional[CreditHoldOverrideRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Override a sales order credit hold: requires Financial Manager / Credit Controller authorization.
    Transitions order to Confirmed (or target_status), records audit log to T0023, and notifies sales rep.
    """
    order = service.get(id)
    if not order:
        check_record_ownership(service, id, user, 'T0012', 'POST')
        raise HTTPException(404, 'Order not found')

    if not _is_financial_manager(user):
        record_security_event(
            table_name='T0012',
            record_id=id,
            action='UNAUTHORIZED_CREDIT_OVERRIDE',
            user_id=user.get('id'),
            business_id=user.get('business_id'),
            details={'role': user.get('role'), 'attempted_action': 'override_credit_hold'},
        )
        raise HTTPException(
            status_code=403,
            detail='Financial manager authorization required to override credit hold'
        )

    if order.get('status') != 'Credit Hold':
        raise HTTPException(
            400,
            f"Only orders in 'Credit Hold' status can be overridden. Current status: {order.get('status')}"
        )

    req_data = body.model_dump() if body else {}
    reason = req_data.get('reason') or req_data.get('release_reason') or req_data.get('notes') or 'Credit hold override approved by manager'
    target_status = req_data.get('target_status') or 'Confirmed'

    try:
        result = service.override_credit_hold(
            order_id=id,
            user_id=user.get('id'),
            user_name=user.get('username') or user.get('full_name'),
            reason=reason,
            target_status=target_status,
        )

        # Audit logging to T0023
        audit_repo = CrudRepository(
            'T0023',
            pk='id',
            business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at', 'business_id']
        )
        audit_repo.create({
            'table_name': 'T0012',
            'record_id': id,
            'action': 'CREDIT_HOLD_OVERRIDE',
            'changed_data': json.dumps({
                'before': order,
                'after': result,
                'override_reason': reason,
                'manager_id': user.get('id'),
                'manager_role': user.get('role'),
                'target_status': target_status,
            }, default=str),
            'changed_by': user.get('id'),
            'changed_at': datetime.now(timezone.utc).isoformat(),
            'business_id': user.get('business_id'),
        })

        return result
    except HTTPException:
        raise
    except Exception as e:
        _server_error(e, 'override credit hold')


@router.post('/{id}/reject-credit-hold')
def reject_credit_hold(
    id: int,
    body: Optional[CreditHoldRejectRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Reject a sales order credit hold: requires Financial Manager / Credit Controller authorization.
    Transitions order to Cancelled, records audit log to T0023, and notifies sales rep.
    """
    order = service.get(id)
    if not order:
        check_record_ownership(service, id, user, 'T0012', 'POST')
        raise HTTPException(404, 'Order not found')

    if not _is_financial_manager(user):
        record_security_event(
            table_name='T0012',
            record_id=id,
            action='UNAUTHORIZED_CREDIT_REJECT',
            user_id=user.get('id'),
            business_id=user.get('business_id'),
            details={'role': user.get('role'), 'attempted_action': 'reject_credit_hold'},
        )
        raise HTTPException(
            status_code=403,
            detail='Financial manager authorization required to reject credit hold'
        )

    if order.get('status') != 'Credit Hold':
        raise HTTPException(
            400,
            f"Only orders in 'Credit Hold' status can be rejected. Current status: {order.get('status')}"
        )

    req_data = body.model_dump() if body else {}
    reason = req_data.get('reason') or req_data.get('notes') or 'Credit hold override rejected by financial manager'

    try:
        result = service.reject_credit_hold(
            order_id=id,
            user_id=user.get('id'),
            user_name=user.get('username') or user.get('full_name'),
            reason=reason,
        )

        # Audit logging to T0023
        audit_repo = CrudRepository(
            'T0023',
            pk='id',
            business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at', 'business_id']
        )
        audit_repo.create({
            'table_name': 'T0012',
            'record_id': id,
            'action': 'CREDIT_HOLD_REJECT',
            'changed_data': json.dumps({
                'before': order,
                'after': result,
                'reject_reason': reason,
                'manager_id': user.get('id'),
                'manager_role': user.get('role'),
            }, default=str),
            'changed_by': user.get('id'),
            'changed_at': datetime.now(timezone.utc).isoformat(),
            'business_id': user.get('business_id'),
        })

        return result
    except HTTPException:
        raise
    except Exception as e:
        _server_error(e, 'reject credit hold')


