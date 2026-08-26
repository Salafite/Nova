from typing import Optional
from fastapi import Request, Response, Query, Depends
from modules.crm.models.product_supplier import ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, apply_pagination_headers
from modules.core.services.base import CrudService
from modules.core.context import set_current_tenant
from packages.auth.deps import get_current_user

repo = CrudRepository('T0103', business_columns=['id', 'product_id', 'supplier_id', 'supplier_sku', 'unit_cost', 'lead_time_days', 'min_order_qty', 'is_preferred'])
service = CrudService(repo)

router = create_crud_router('/api/T0103I', 'T0103 - Product Suppliers', service,
                            ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse)

@router.get('/by-product/{product_id}')
def get_by_product(
    product_id: int,
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
    filters = {'product_id': product_id}
    items = repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset)
    total_count = repo.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return items

@router.get('/by-supplier/{supplier_id}')
def get_by_supplier(
    supplier_id: int,
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
    filters = {'supplier_id': supplier_id}
    items = repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset)
    total_count = repo.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return items
