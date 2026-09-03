from fastapi import APIRouter, Depends, HTTPException, Query, status
from modules.inventory.models import BarcodeCreate, BarcodeUpdate, BarcodeResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.core.context import get_current_tenant
from modules.core.services.permission_service import get_required_permission
from packages.auth.deps import get_current_user, require_permission
from packages.database.connection import get_connection, release_connection
from modules.inventory.services.barcode_service import find_barcode_record

repo = CrudRepository('T0004', business_columns=['id', 'product_id', 'barcode', 'barcode_type', 'is_primary'])
service = CrudService(repo)

perm = get_required_permission(prefix='/api/T0004I', tag='T0004 - Barcodes')
router = APIRouter(prefix='/api/T0004I', tags=['T0004 - Barcodes'], dependencies=[Depends(require_permission(perm))])


@router.get('/lookup-barcode')
def lookup_barcode(code: str = Query(..., description="Barcode string"), user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        rec = find_barcode_record(conn, code, tenant_id=tenant_id)
        if not rec:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Barcode not found")
        return rec
    finally:
        release_connection(conn)


@router.get('/by-barcode/{code}')
def get_by_barcode(code: str, user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        rec = find_barcode_record(conn, code, tenant_id=tenant_id)
        if not rec:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Barcode not found")
        return rec
    finally:
        release_connection(conn)


router = create_crud_router('/api/T0004I', 'T0004 - Barcodes', service,
                            BarcodeCreate, BarcodeUpdate, BarcodeResponse, router=router)

