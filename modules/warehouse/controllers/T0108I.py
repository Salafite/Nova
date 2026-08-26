"""
Nova ERP — Stock Transfers REST Controller (T0108I)
Multi-warehouse transfer orders, in-transit stock management,
dispatch & receipt workflows, and transit loss accounting.
"""
import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, status

from modules.warehouse.models.stock_transfer import (
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferResponse,
    StockTransferLineCreate,
    StockTransferLineUpdate,
    StockTransferLineResponse,
    StockTransferDispatch,
    StockTransferReceive,
)
from modules.warehouse.services.stock_transfer_service import (
    StockTransferService,
    TRANSFER_REPO,
    TRANSFER_LINE_REPO,
)
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

logger = logging.getLogger(__name__)

# Primary domain service for Stock Transfers
service = StockTransferService(repo=TRANSFER_REPO, line_repo=TRANSFER_LINE_REPO)

# Standard CRUD router (mounted at /api/T0108I)
router = create_crud_router(
    '/api/T0108I',
    'T0108 - Stock Transfers',
    service,
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferResponse,
)


def _set_tenant_from_user(user: dict) -> None:
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)


# ---------------------------------------------------------------------------
# In-Transit & Detailed Query Endpoints
# ---------------------------------------------------------------------------

@router.get('/in-transit', response_model=List[StockTransferResponse])
def get_in_transit_transfers(user: dict = Depends(get_current_user)):
    """
    List all active stock transfers currently In Transit across the logistics network.
    """
    _set_tenant_from_user(user)
    return service.list_in_transit()


@router.get('/{id}/detail', response_model=StockTransferResponse)
def get_transfer_detail(id: int, user: dict = Depends(get_current_user)):
    """
    Retrieve full transfer document details including itemized lines, product names,
    SKUs, warehouse names, carrier details, and transit progress metrics.
    """
    _set_tenant_from_user(user)
    result = service.get_transfer_with_lines(id)
    if not result:
        check_record_ownership(service, id, user, 'T0108', 'GET')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")
    return result


# ---------------------------------------------------------------------------
# Transfer Lifecycle Actions: Dispatch, Receive, Cancel
# ---------------------------------------------------------------------------

@router.post('/{id}/dispatch', response_model=StockTransferResponse)
def dispatch_transfer(
    id: int,
    body: Optional[StockTransferDispatch] = None,
    user: dict = Depends(get_current_user),
):
    """
    Dispatches inventory from the source warehouse:
    - Deducts available stock at source warehouse.
    - Increments in_transit_qty at destination warehouse.
    - Logs 'Transfer Out' stock movements.
    - Transitions order status to 'In Transit'.
    """
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    try:
        disp_data = body.model_dump(exclude_unset=True) if body else {}
        if not disp_data.get('dispatched_by') and isinstance(user, dict) and user.get('id'):
            disp_data['dispatched_by'] = user.get('id')
        return service.dispatch_transfer(id, disp_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Failed to dispatch transfer #{id}: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Dispatch failed: {str(e)}")


@router.post('/{id}/receive', response_model=StockTransferResponse)
def receive_transfer(
    id: int,
    body: Optional[StockTransferReceive] = None,
    user: dict = Depends(get_current_user),
):
    """
    Receives inventory at the destination warehouse:
    - Decrements in_transit_qty at destination warehouse.
    - Increments on-hand inventory at destination warehouse.
    - Logs 'Transfer In' stock movements.
    - Records transit damage / discrepancies as 'Transfer Loss' movements with reason codes.
    - Updates order status to 'Received' or 'Partially Received'.
    """
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    try:
        rec_data = body.model_dump(exclude_unset=True) if body else {}
        if not rec_data.get('received_by') and isinstance(user, dict) and user.get('id'):
            rec_data['received_by'] = user.get('id')
        return service.receive_transfer(id, rec_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Failed to receive transfer #{id}: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Receipt failed: {str(e)}")


@router.post('/{id}/cancel', response_model=StockTransferResponse)
def cancel_transfer(
    id: int,
    body: Optional[dict] = None,
    user: dict = Depends(get_current_user),
):
    """
    Cancels a stock transfer order:
    - If 'In Transit': Reverses source stock deductions, clears in-transit stock, restores batches.
    - If 'Draft' or 'Pending': Transitions status to 'Cancelled'.
    - If already 'Received': Rejects cancellation.
    """
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    reason = (body or {}).get('reason') or (body or {}).get('notes')
    try:
        return service.cancel_transfer(id, reason=reason)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Failed to cancel transfer #{id}: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Cancellation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Line Items Management (Draft / Pending Transfers)
# ---------------------------------------------------------------------------

@router.post('/{id}/lines', response_model=StockTransferLineResponse, status_code=status.HTTP_201_CREATED)
def add_transfer_line(
    id: int,
    body: StockTransferLineCreate,
    user: dict = Depends(get_current_user),
):
    """Add a new line item to a Draft/Pending transfer order."""
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    return service.add_line(id, body)


@router.put('/{id}/lines/{line_id}', response_model=StockTransferLineResponse)
def update_transfer_line(
    id: int,
    line_id: int,
    body: StockTransferLineUpdate,
    user: dict = Depends(get_current_user),
):
    """Update an existing line item on a Draft/Pending transfer order."""
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'PUT')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    return service.update_line(line_id, body)


@router.delete('/{id}/lines/{line_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer_line(
    id: int,
    line_id: int,
    user: dict = Depends(get_current_user),
):
    """Remove a line item from a Draft/Pending transfer order."""
    _set_tenant_from_user(user)
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0108', 'DELETE')
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Stock transfer #{id} not found")

    service.delete_line(line_id)
    return None
