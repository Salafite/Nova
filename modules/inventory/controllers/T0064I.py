from typing import Optional
from pydantic import BaseModel
from modules.inventory.models.stock_movement import StockMovementCreate, StockMovementResponse
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0064', business_columns=['id', 'product_id', 'warehouse_id', 'movement_type', 'reference_type', 'reference_id', 'qty_change', 'balance_after', 'description', 'movement_date'])
service = CrudService(repo)
router = create_crud_router('/api/T0064I', 'T0064 - Stock Movements', service,
                            StockMovementCreate, None, StockMovementResponse)

movement_svc = StockMovementService()
STOCK_REPO = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])


class AdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: int
    new_qty: float
    description: Optional[str] = None


@router.get('/adjustments')
def list_adjustments():
    return service.list(filters={'movement_type': 'ADJUSTMENT'})


@router.post('/adjust', status_code=201)
def create_adjustment(body: AdjustmentCreate):
    stock_rows = STOCK_REPO.list(filters={'product_id': body.product_id, 'warehouse_id': body.warehouse_id})
    current_qty = stock_rows[0]['qty'] if stock_rows else 0
    diff = round(body.new_qty - current_qty, 2)
    if abs(diff) < 0.001:
        from fastapi import HTTPException
        raise HTTPException(400, 'New quantity is the same as current quantity — no adjustment needed')
    return movement_svc.record_movement(
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        movement_type='ADJUSTMENT',
        qty_change=diff,
        description=body.description
    )
