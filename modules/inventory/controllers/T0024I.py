from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from packages.database.connection import get_connection, release_connection
from packages.auth.deps import require_permission, get_current_user
from modules.core.context import get_current_tenant, set_current_tenant
from modules.core.controllers.base import apply_pagination_headers

router = APIRouter(prefix='/api/categories', tags=['Categories'],
                   dependencies=[Depends(require_permission('PRODUCTS_VIEW'))])

@router.get('/')
def list_categories(
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
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute('SELECT COUNT(DISTINCT category) FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s', (tenant_id,))
            else:
                cur.execute('SELECT COUNT(DISTINCT category) FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\'')
            cnt_row = cur.fetchone()
            total_count = cnt_row[0] if cnt_row else 0

            order_clause = 'ORDER BY category ASC'
            if order_by:
                order_col = order_by.strip()
                desc = False
                if order_col.startswith('-'):
                    desc = True
                    order_col = order_col[1:]
                elif order_col.lower().endswith(' desc'):
                    desc = True
                    order_col = order_col[:-5].strip()
                elif order_col.lower().endswith(' asc'):
                    desc = False
                    order_col = order_col[:-4].strip()
                if order_col in ('category', 'name'):
                    order_clause = f'ORDER BY category {"DESC" if desc else "ASC"}'

            if tenant_id is not None:
                cur.execute(f'SELECT DISTINCT category FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s {order_clause} LIMIT %s OFFSET %s', (tenant_id, limit, offset))
            else:
                cur.execute(f'SELECT DISTINCT category FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' {order_clause} LIMIT %s OFFSET %s', (limit, offset))
            items = [{'name': r[0]} for r in cur.fetchall()]

            apply_pagination_headers(
                response=response,
                request=request,
                total_count=total_count,
                limit=limit,
                offset=offset,
            )
            return items
    finally:
        release_connection(conn)

@router.get('/product-counts')
def category_product_counts(
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
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute('SELECT COUNT(DISTINCT category) FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s', (tenant_id,))
            else:
                cur.execute('SELECT COUNT(DISTINCT category) FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\'')
            cnt_row = cur.fetchone()
            total_count = cnt_row[0] if cnt_row else 0

            order_clause = 'ORDER BY category ASC'
            if order_by:
                order_col = order_by.strip()
                desc = False
                if order_col.startswith('-'):
                    desc = True
                    order_col = order_col[1:]
                elif order_col.lower().endswith(' desc'):
                    desc = True
                    order_col = order_col[:-5].strip()
                elif order_col.lower().endswith(' asc'):
                    desc = False
                    order_col = order_col[:-4].strip()
                if order_col in ('category', 'name'):
                    order_clause = f'ORDER BY category {"DESC" if desc else "ASC"}'
                elif order_col in ('count', 'product_count'):
                    order_clause = f'ORDER BY count {"DESC" if desc else "ASC"}'

            if tenant_id is not None:
                cur.execute(f'SELECT category, COUNT(*) as count FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' AND business_id = %s GROUP BY category {order_clause} LIMIT %s OFFSET %s', (tenant_id, limit, offset))
            else:
                cur.execute(f'SELECT category, COUNT(*) as count FROM "Nova".t0003 WHERE category IS NOT NULL AND category != \'\' GROUP BY category {order_clause} LIMIT %s OFFSET %s', (limit, offset))
            items = [{'name': r[0], 'product_count': r[1]} for r in cur.fetchall()]

            apply_pagination_headers(
                response=response,
                request=request,
                total_count=total_count,
                limit=limit,
                offset=offset,
            )
            return items
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
