from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Body
from modules.purchasing.services.purchase_return_service import PurchaseReturnService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import (
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
    PurchaseReturnResponse,
    PurchaseReturnDetailResponse,
    RMAApprovalRequest,
    ReceivingRejectionCreate,
    ReturnSlipData,
)
from packages.auth.deps import get_current_user
from modules.core.context import set_current_tenant

repo = CrudRepository(
    'T0081',
    business_columns=[
        'id',
        'return_number',
        'purchase_order_id',
        'goods_receipt_id',
        'supplier_id',
        'debit_memo_id',
        'return_date',
        'status',
        'total_amount',
        'reason',
        'notes',
        'attachments',
        'approved_at',
        'approved_by',
        'business_id',
        'is_active',
    ],
)
service = PurchaseReturnService(repo)
router = create_crud_router(
    '/api/T0081I',
    'T0081 - Purchase Returns',
    service,
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
    PurchaseReturnResponse,
)


@router.post('/from-goods-receipt/{grn_id}', status_code=status.HTTP_201_CREATED)
def create_rma_from_goods_receipt(
    grn_id: int,
    body: Optional[Union[ReceivingRejectionCreate, Dict[str, Any]]] = None,
    user: dict = Depends(get_current_user),
):
    """
    Create an RMA / Purchase Return directly from a Goods Receipt (T0075/T0076)
    and dock-side quality rejections.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    payload = body.model_dump() if hasattr(body, 'model_dump') else (body or {})
    if b_id is not None and 'business_id' not in payload:
        payload['business_id'] = b_id

    try:
        return service.create_from_goods_receipt(grn_id=grn_id, rejection_payload=payload)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to create RMA from Goods Receipt: {e}")


@router.post('/dock-rejection', status_code=status.HTTP_201_CREATED)
def create_rma_from_dock_rejection(
    body: ReceivingRejectionCreate,
    user: dict = Depends(get_current_user),
):
    """
    Convenience endpoint for dock-side quality receiving rejection creating an RMA.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    payload = body.model_dump() if hasattr(body, 'model_dump') else body
    if b_id is not None and isinstance(payload, dict) and 'business_id' not in payload:
        payload['business_id'] = b_id

    try:
        return service.create_dock_rejection(rejection=payload)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to record dock rejection: {e}")


@router.post('/{id}/approve')
def approve_purchase_return(
    id: int,
    body: Optional[RMAApprovalRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Approve an RMA / Purchase Return (Draft -> Approved).
    Automatically posts a debit memo against supplier payables and isolates items in Quarantine status.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    approved_by = body.approved_by if body and body.approved_by is not None else (user.get('id') if isinstance(user, dict) else None)
    notes = body.notes if body else None
    create_debit_memo = body.create_debit_memo if body is not None else True
    quarantine_inventory = body.quarantine_inventory if body is not None else True

    try:
        return service.approve_return(
            id_val=id,
            approved_by=approved_by,
            notes=notes,
            create_debit_memo=create_debit_memo,
            quarantine_inventory=quarantine_inventory,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to approve RMA: {e}")


@router.post('/{id}/complete-return')
def complete_purchase_return(
    id: int,
    body: Optional[Dict[str, Any]] = None,
    user: dict = Depends(get_current_user),
):
    """
    Complete an approved RMA / Purchase Return (Approved -> Returned).
    Records stock movements and finalizes the return lifecycle.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    notes = body.get('notes') if isinstance(body, dict) else None

    try:
        return service.complete_return(id_val=id, notes=notes)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to complete RMA return: {e}")


@router.post('/{id}/cancel')
def cancel_purchase_return(
    id: int,
    body: Optional[Dict[str, Any]] = None,
    user: dict = Depends(get_current_user),
):
    """
    Cancel a Draft or Approved RMA / Purchase Return.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    reason = body.get('reason') or body.get('notes') if isinstance(body, dict) else None

    try:
        return service.cancel_return(id_val=id, reason=reason)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to cancel RMA: {e}")


@router.get('/{id}/details')
def get_purchase_return_details(
    id: int,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve comprehensive details for an RMA / Purchase Return including line items,
    supplier info, purchase order reference, goods receipt reference, and linked debit memo.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.get_return_details(return_id=id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to fetch RMA details: {e}")


@router.get('/{id}/slip-data')
def get_purchase_return_slip_data(
    id: int,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve aggregated data for generating printable supplier return slips with itemized
    reasons, batch numbers, debit memo links, driver sign-off blocks, and photo attachments.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.get_return_slip_data(return_id=id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to fetch RMA slip data: {e}")
