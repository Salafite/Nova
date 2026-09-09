from typing import Optional, Dict, Any, List, Union
from fastapi import Depends, HTTPException, status, Body
from modules.purchasing.services.purchase_return_line_service import PurchaseReturnLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import (
    PurchaseReturnLineCreate,
    PurchaseReturnLineUpdate,
    PurchaseReturnLineResponse,
    AttachmentUploadRequest,
    BulkReturnLinesCreate,
    QuarantineStatusUpdateRequest,
)
from packages.auth.deps import get_current_user
from modules.core.context import set_current_tenant

repo = CrudRepository(
    'T0082',
    business_columns=[
        'id',
        'return_id',
        'product_id',
        'product_name',
        'qty',
        'unit_price',
        'line_total',
        'uom_id',
        'batch_id',
        'batch_number',
        'expiry_date',
        'reason_code',
        'photos',
        'quarantine_status',
        'disposition',
        'line_number',
        'business_id',
        'is_active',
    ],
)
service = PurchaseReturnLineService(repo)
router = create_crud_router(
    '/api/T0082I',
    'T0082 - Purchase Return Lines',
    service,
    PurchaseReturnLineCreate,
    PurchaseReturnLineUpdate,
    PurchaseReturnLineResponse,
)


@router.get('/by-return/{return_id}')
def get_lines_by_return(
    return_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Get all line items for a specific Purchase Return (RMA).
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.get_by_return_id(return_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve lines for RMA #{return_id}: {e}")


@router.get('/by-batch/{batch_id}')
def get_lines_by_batch(
    batch_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Get all Purchase Return lines associated with a specific batch.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.get_by_batch_id(batch_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve lines for batch #{batch_id}: {e}")


@router.post('/bulk', status_code=status.HTTP_201_CREATED)
def bulk_create_return_lines(
    body: BulkReturnLinesCreate,
    user: dict = Depends(get_current_user),
):
    """
    Bulk create return line items for a Purchase Return / RMA and recalculate total.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        lines_data = [l.model_dump() if hasattr(l, 'model_dump') else dict(l) for l in body.lines]
        if b_id is not None:
            for l in lines_data:
                if 'business_id' not in l:
                    l['business_id'] = b_id
        return service.bulk_create(return_id=body.return_id, lines=lines_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to bulk create return lines: {e}")


@router.post('/{id}/photos', status_code=status.HTTP_201_CREATED)
def upload_line_photo(
    id: int,
    body: AttachmentUploadRequest,
    user: dict = Depends(get_current_user),
):
    """
    Upload an inspection photo or document to a specific return line item.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    user_id = user.get('id') if isinstance(user, dict) else None

    try:
        return service.add_photo(line_id=id, attachment=body, user_id=user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to upload photo for line #{id}: {e}")


@router.get('/{id}/photos')
def get_line_photos(
    id: int,
    user: dict = Depends(get_current_user),
):
    """
    List all inspection photos for a specific return line item.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.get_photos(line_id=id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve photos for line #{id}: {e}")


@router.delete('/{id}/photos/{photo_id}')
def delete_line_photo(
    id: int,
    photo_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Delete an inspection photo from a return line item.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.delete_photo(line_id=id, photo_id=photo_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete photo from line #{id}: {e}")


@router.put('/{id}/quarantine-status')
def update_line_quarantine_status(
    id: int,
    body: QuarantineStatusUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """
    Update the quarantine status of a return line and optionally sync with the linked batch in T0088.
    """
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)

    try:
        return service.update_quarantine_status(
            line_id=id,
            quarantine_status=body.quarantine_status,
            sync_batch=body.sync_batch,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to update quarantine status for line #{id}: {e}")

