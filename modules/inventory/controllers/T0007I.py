from fastapi import APIRouter, Depends, HTTPException, Query, status
from modules.inventory.models.product import ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.core.context import get_current_tenant
from modules.core.services.permission_service import get_required_permission
from packages.auth.deps import get_current_user, require_permission
from packages.database.connection import get_connection, release_connection
from modules.inventory.services.barcode_service import find_product_uom_by_barcode

repo = CrudRepository('T0007', business_columns=[
    'id', 'product_id', 'base_uom_id', 'purchase_uom_id', 'sales_uom_id',
    'purchase_factor', 'sales_factor',
    'is_catch_weight', 'pricing_uom_id', 'nominal_weight', 'tolerance_pct', 'pricing_basis'
])
service = CrudService(repo)

perm = get_required_permission(prefix='/api/T0007I', tag='T0007 - Product UOM')
router = APIRouter(prefix='/api/T0007I', tags=['T0007 - Product UOM'], dependencies=[Depends(require_permission(perm))])


@router.get('/lookup-barcode')
def lookup_barcode(code: str = Query(..., description="Barcode string"), user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        uom_rec = find_product_uom_by_barcode(conn, code, tenant_id=tenant_id)
        if not uom_rec:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product UOM not found for barcode")
        return uom_rec
    finally:
        release_connection(conn)


@router.get('/by-barcode/{code}')
def get_by_barcode(code: str, user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        uom_rec = find_product_uom_by_barcode(conn, code, tenant_id=tenant_id)
        if not uom_rec:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product UOM not found for barcode")
        return uom_rec
    finally:
        release_connection(conn)


router = create_crud_router('/api/T0007I', 'T0007 - Product UOM', service,
                            ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse, router=router)

