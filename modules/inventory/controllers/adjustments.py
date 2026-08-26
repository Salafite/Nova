from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import apply_pagination_headers
from modules.core.context import set_current_tenant
from packages.auth.deps import require_permission, get_current_user

router = APIRouter(prefix='/api/adjustments', tags=['Stock Adjustments'], dependencies=[Depends(require_permission('INVENTORY_VIEW'))])

movement_svc = StockMovementService()
STOCK_REPO = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])
T0064_REPO = CrudRepository('T0064', business_columns=['id', 'product_id', 'warehouse_id', 'movement_type', 'reference_type', 'reference_id', 'qty_change', 'balance_after', 'description', 'movement_date'])


class AdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: int
    new_qty: float
    description: Optional[str] = None
    business_id: Optional[int] = None


@router.get('/')
def list_adjustments(
    response: Response,
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
    order_by: Optional[str] = Query(None, description="Field name to order results by"),
    user: dict = Depends(get_current_user),
):
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    filters = {'movement_type': 'ADJUSTMENT'}
    items = T0064_REPO.list(filters=filters, order_by=order_by, limit=limit, offset=offset)
    total_count = T0064_REPO.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return items


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
