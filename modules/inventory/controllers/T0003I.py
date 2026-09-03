from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from modules.inventory.models import ProductCreate, ProductUpdate, ProductResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.core.context import get_current_tenant
from modules.core.services.permission_service import get_required_permission
from packages.auth.deps import get_current_user, require_permission
from packages.database.connection import get_connection, release_connection
from modules.inventory.services.barcode_service import find_product_by_barcode
import psycopg2.extras

repo = CrudRepository('T0003', business_columns=[
    'id', 'name', 'sku', 'barcode', 'description', 'type', 'price', 'cost_price',
    'category', 'brand', 'tax_rate', 'weight', 'volume', 'image_url',
    'is_purchasable', 'is_saleable', 'is_phantom', 'last_transaction_date', 'is_active',
    'is_catch_weight', 'pricing_uom_id', 'nominal_weight', 'tolerance_pct', 'pricing_basis'
])
service = CrudService(repo)

perm = get_required_permission(prefix='/api/T0003I', tag='T0003 - Products')
router = APIRouter(prefix='/api/T0003I', tags=['T0003 - Products'], dependencies=[Depends(require_permission(perm))])


@router.get('/lookup-barcode')
def lookup_barcode(code: str = Query(..., description="Barcode, SKU, EAN-13, UPC-A, Code 128, or GS1-128 GTIN"), user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        product = find_product_by_barcode(conn, code, tenant_id=tenant_id)
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found for barcode")
        return product
    finally:
        release_connection(conn)


@router.get('/by-barcode/{code}')
def get_by_barcode(code: str, user: dict = Depends(get_current_user)):
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        product = find_product_by_barcode(conn, code, tenant_id=tenant_id)
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found for barcode")
        return product
    finally:
        release_connection(conn)


router = create_crud_router('/api/T0003I', 'T0003 - Products', service,
                            ProductCreate, ProductUpdate, ProductResponse, router=router)


@router.post('/scan-phantoms')
def scan_phantoms(user: dict = Depends(get_current_user)):
    cutoff = date.today() - timedelta(days=365)
    tenant_id = user.get('business_id') if isinstance(user, dict) and user.get('business_id') else get_current_tenant()
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if tenant_id is not None:
                cur.execute("""
                    UPDATE "Nova".t0003 p
                    SET is_phantom = true,
                        last_transaction_date = (
                            SELECT MAX(so.order_date)
                            FROM "Nova".t0013 oi
                            JOIN "Nova".t0012 so ON so.id = oi.sales_order_id
                            WHERE oi.product_id = p.id
                        )
                    WHERE p.business_id = %s AND p.id IN (
                        SELECT p2.id FROM "Nova".t0003 p2
                        LEFT JOIN "Nova".t0013 oi2 ON oi2.product_id = p2.id
                        LEFT JOIN "Nova".t0012 so2 ON so2.id = oi2.sales_order_id
                        WHERE p2.business_id = %s
                        GROUP BY p2.id
                        HAVING COALESCE(MAX(so2.order_date), '1970-01-01'::date) < %s
                    )
                    RETURNING id, name, sku, is_phantom, last_transaction_date
                """, (tenant_id, tenant_id, cutoff))
            else:
                cur.execute("""
                    UPDATE "Nova".t0003 p
                    SET is_phantom = true,
                        last_transaction_date = (
                            SELECT MAX(so.order_date)
                            FROM "Nova".t0013 oi
                            JOIN "Nova".t0012 so ON so.id = oi.sales_order_id
                            WHERE oi.product_id = p.id
                        )
                    WHERE p.id IN (
                        SELECT p2.id FROM "Nova".t0003 p2
                        LEFT JOIN "Nova".t0013 oi2 ON oi2.product_id = p2.id
                        LEFT JOIN "Nova".t0012 so2 ON so2.id = oi2.sales_order_id
                        GROUP BY p2.id
                        HAVING COALESCE(MAX(so2.order_date), '1970-01-01'::date) < %s
                    )
                    RETURNING id, name, sku, is_phantom, last_transaction_date
                """, (cutoff,))
            flagged = [dict(r) for r in cur.fetchall()]
            conn.commit()
        return {'flagged_count': len(flagged), 'flagged_products': flagged}
    finally:
        release_connection(conn)

