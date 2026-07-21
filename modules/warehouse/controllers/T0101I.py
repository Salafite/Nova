from fastapi import HTTPException
from modules.warehouse.models import PickListCreate, PickListUpdate, PickListResponse
from modules.warehouse.services.pick_list_service import PickListService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService

repo = CrudRepository('T0101', business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'])
service = CrudService(repo)

router = create_crud_router('/api/T0101I', 'T0101 - Pick Lists', service,
                            PickListCreate, PickListUpdate, PickListResponse)

pl_service = PickListService()
pli_repo = CrudRepository('T0102', business_columns=['id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name', 'qty_ordered', 'qty_picked', 'line_number'])

@router.get('/{id}/detail')
def get_pick_list_detail(id: int):
    result = pl_service.get_with_items(id)
    if not result:
        raise HTTPException(404, 'Pick list not found')
    return result

@router.post('/{id}/start')
def start_picking(id: int):
    try:
        result = pl_service.start_picking(id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/pick-item/{item_id}')
def pick_item(id: int, item_id: int, body: dict):
    qty_picked = body.get('qty_picked', 0)
    try:
        result = pl_service.pick_item(item_id, qty_picked)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/complete')
def complete_picking(id: int):
    try:
        result = pl_service.complete_picking(id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
