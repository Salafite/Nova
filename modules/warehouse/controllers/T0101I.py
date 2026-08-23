from fastapi import HTTPException
from modules.warehouse.models import PickListCreate, PickListUpdate, PickListResponse
from modules.warehouse.services.pick_list_service import PickListService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0101', business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'])
service = PickListService(repo)

router = create_crud_router('/api/T0101I', 'T0101 - Pick Lists', service,
                            PickListCreate, PickListUpdate, PickListResponse)

pl_service = service
pli_repo = CrudRepository('T0102', business_columns=[
    'id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name',
    'qty_ordered', 'qty_picked', 'line_number',
    'batch_id', 'batch_number', 'expiry_date', 'picked_batch_id', 'picked_batch_number',
    'catch_weight_actual', 'catch_weight_uom', 'nominal_weight', 'tolerance_pct',
    'tolerance_variance_pct', 'tolerance_status', 'supervisor_approved',
    'supervisor_approved_by', 'supervisor_approved_at', 'supervisor_notes'
])

@router.get('/{id}/detail')
def get_pick_list_detail(id: int):
    result = pl_service.get_with_items(id)
    if not result:
        raise HTTPException(404, 'Pick list not found')
    return result

@router.get('/{id}/items/{item_id}/available-batches')
def get_available_batches(id: int, item_id: int):
    try:
        return pl_service.get_available_batches_for_item(id, item_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.post('/{id}/start')
def start_picking(id: int):
    try:
        return pl_service.start_picking(id)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/pick-item/{item_id}')
def pick_item(id: int, item_id: int, body: dict):
    qty_picked = body.get('qty_picked', 0)
    picked_batch_id = body.get('picked_batch_id')
    picked_batch_number = body.get('picked_batch_number')
    try:
        return pl_service.pick_item(
            item_id=item_id,
            qty_picked=qty_picked,
            pick_list_id=id,
            picked_batch_id=picked_batch_id,
            picked_batch_number=picked_batch_number
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post('/{id}/complete')
def complete_picking(id: int):
    try:
        return pl_service.complete_picking(id)
    except ValueError as e:
        raise HTTPException(400, str(e))