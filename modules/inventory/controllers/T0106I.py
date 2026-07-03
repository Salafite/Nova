from fastapi import APIRouter, Query
from modules.inventory.models.counts import CountItemCreate, CountItemUpdate, CountItemResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from packages.database.connection import get_connection, release_connection

BASE = '/api/T0106I'

repo = CrudRepository('T0106', business_columns=['id', 'count_id', 'product_id', 'expected_qty', 'counted_qty', 'notes'])
service = CrudService(repo)
router = create_crud_router(BASE, 'T0106 - Inventory Count Items', service,
                            CountItemCreate, CountItemUpdate, CountItemResponse)


@router.get('/by-count/{count_id}')
def get_items_by_count(count_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ci.*, p.name as product_name, p.sku
            FROM "Nova".t0106 ci
            LEFT JOIN "Nova".t0003 p ON p.id = ci.product_id
            WHERE ci.count_id = %s
            ORDER BY ci.id
        """, (count_id,))
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_connection(conn)
