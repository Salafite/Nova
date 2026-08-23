from fastapi import Depends, HTTPException, status
from modules.sales.services.sales_return_service import SalesReturnService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, check_record_ownership
from modules.sales.models.sales_return import SalesReturnCreate, SalesReturnUpdate, SalesReturnResponse
from packages.auth.deps import get_current_user

repo = CrudRepository('T0079', business_columns=['id', 'return_number', 'sales_order_id', 'customer_id', 'return_date', 'status', 'reason', 'notes'])
service = SalesReturnService(repo)
router = create_crud_router('/api/T0079I', 'T0079 - Sales Returns', service,
                            SalesReturnCreate, SalesReturnUpdate, SalesReturnResponse)


@router.post('/{id}/approve')
def approve_return(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0079', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    if existing['status'] != 'Draft':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Only Draft returns can be approved')
    result = service.update(id, {'status': 'Approved'})
    return result


@router.post('/{id}/receive')
def receive_return(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0079', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    if existing['status'] != 'Approved':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Only Approved returns can be received')
    result = service.update(id, {'status': 'Received'})
    return result


@router.post('/{id}/cancel')
def cancel_return(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0079', 'POST')
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    if existing['status'] in ('Received', 'Cancelled'):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Cannot cancel a Received or already Cancelled return')
    result = service.update(id, {'status': 'Cancelled'})
    return result
