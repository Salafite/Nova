from fastapi import APIRouter, Depends
from packages.database.connection import get_connection, release_connection
from packages.auth.deps import get_current_user

router = APIRouter(prefix='/api/categories', tags=['Categories'],
                   dependencies=[Depends(get_current_user)])

@router.get('/')
def list_categories():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT DISTINCT category FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' ORDER BY category')
            return [{'name': r[0]} for r in cur.fetchall()]
    finally:
        release_connection(conn)

@router.get('/product-counts')
def category_product_counts():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT category, COUNT(*) as count FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' GROUP BY category ORDER BY category')
            return [{'name': r[0], 'product_count': r[1]} for r in cur.fetchall()]
    finally:
        release_connection(conn)

@router.put('/rename')
def rename_category(old_name: str, new_name: str):
    if not old_name or not new_name:
        from fastapi import HTTPException
        raise HTTPException(400, 'Both old_name and new_name are required')
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "Nova".t0003 SET category = %s WHERE category = %s', (new_name, old_name))
            conn.commit()
            return {'renamed': cur.rowcount, 'from': old_name, 'to': new_name}
    finally:
        release_connection(conn)
