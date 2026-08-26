from typing import Optional
from fastapi import Request, Response, Query, Depends
from modules.inventory.models.counts import CountItemCreate, CountItemUpdate, CountItemResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router, apply_pagination_headers
from modules.core.context import set_current_tenant
from packages.database.connection import get_connection, release_connection
from packages.auth.deps import get_current_user

BASE = '/api/T0106I'

repo = CrudRepository('T0106', business_columns=['id', 'count_id', 'product_id', 'expected_qty', 'counted_qty', 'notes'])
service = CrudService(repo)
router = create_crud_router(BASE, 'T0106 - Inventory Count Items', service,
                            CountItemCreate, CountItemUpdate, CountItemResponse)


@router.get('/by-count/{count_id}')
def get_items_by_count(
    count_id: int,
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
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM "Nova".t0106 WHERE count_id = %s', (count_id,))
        cnt_row = cur.fetchone()
        total_count = cnt_row[0] if cnt_row else 0

        order_clause = 'ORDER BY ci.id ASC'
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
            if order_col in ('id', 'expected_qty', 'counted_qty', 'notes'):
                order_clause = f'ORDER BY ci.{order_col} {"DESC" if desc else "ASC"}'
            elif order_col in ('product_name', 'name'):
                order_clause = f'ORDER BY p.name {"DESC" if desc else "ASC"}'
            elif order_col == 'sku':
                order_clause = f'ORDER BY p.sku {"DESC" if desc else "ASC"}'

        cur.execute(f"""
            SELECT ci.*, p.name as product_name, p.sku
            FROM "Nova".t0106 ci
            LEFT JOIN "Nova".t0003 p ON p.id = ci.product_id
            WHERE ci.count_id = %s
            {order_clause}
            LIMIT %s OFFSET %s
        """, (count_id, limit, offset))
        cols = [desc[0] for desc in cur.description]
        items = [dict(zip(cols, row)) for row in cur.fetchall()]

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
