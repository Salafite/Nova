from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository
from packages.auth.middleware import get_current_user

from fastapi import Depends

router = APIRouter(prefix='/api/adjustments', tags=['Stock Adjustments'], dependencies=[Depends(get_current_user)])

movement_svc = StockMovementService()
STOCK_REPO = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])
T0064_REPO = CrudRepository('T0064', business_columns=['id', 'product_id', 'warehouse_id', 'movement_type', 'reference_type', 'reference_id', 'qty_change', 'balance_after', 'description', 'movement_date'])


class AdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: int
    new_qty: float
    description: Optional[str] = None


@router.get('/')
def list_adjustments():
    return T0064_REPO.list(filters={'movement_type': 'ADJUSTMENT'})


@router.post('/', status_code=201)
def create_adjustment(body: AdjustmentCreate):
    stock_rows = STOCK_REPO.list(filters={'product_id': body.product_id, 'warehouse_id': body.warehouse_id})
    current_qty = stock_rows[0]['qty'] if stock_rows else 0
    diff = round(body.new_qty - current_qty, 2)
    if abs(diff) < 0.001:
        raise HTTPException(400, 'New quantity is the same as current quantity')
    return movement_svc.record_movement(
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        movement_type='ADJUSTMENT',
        qty_change=diff,
        description=body.description
    )
