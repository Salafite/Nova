from fastapi import APIRouter, Depends, HTTPException
from packages.database.connection import get_connection, release_connection
from packages.auth.deps import require_permission
from modules.core.context import get_current_tenant

router = APIRouter(prefix='/api/categories', tags=['Categories'],
                   dependencies=[Depends(require_permission('PRODUCTS_VIEW'))])

@router.get('/')
def list_categories():
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute('SELECT DISTINCT category FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s ORDER BY category', (tenant_id,))
            else:
                cur.execute('SELECT DISTINCT category FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' ORDER BY category')
            return [{'name': r[0]} for r in cur.fetchall()]
    finally:
        release_connection(conn)

@router.get('/product-counts')
def category_product_counts():
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute('SELECT category, COUNT(*) as count FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s GROUP BY category ORDER BY category', (tenant_id,))
            else:
                cur.execute('SELECT category, COUNT(*) as count FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' GROUP BY category ORDER BY category')
            return [{'name': r[0], 'product_count': r[1]} for r in cur.fetchall()]
    finally:
        release_connection(conn)

@router.put('/rename')
def rename_category(old_name: str = '', new_name: str = ''):
    if not old_name and not new_name:
        raise HTTPException(400, 'Either old_name or new_name must be provided')
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute('UPDATE "Nova".t0003 SET category = %s WHERE category = %s AND business_id = %s', (new_name, old_name, tenant_id))
            else:
                cur.execute('UPDATE "Nova".t0003 SET category = %s WHERE category = %s', (new_name, old_name))
            conn.commit()
            return {'renamed': cur.rowcount, 'from': old_name or '(empty)', 'to': new_name or '(empty)'}
    finally:
        release_connection(conn)
