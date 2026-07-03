from datetime import date
from fastapi import APIRouter, HTTPException
from modules.inventory.models.counts import InventoryCountCreate, InventoryCountUpdate, InventoryCountResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from packages.database.connection import get_connection, release_connection

BASE = '/api/T0105I'

repo = CrudRepository('T0105', business_columns=['id', 'count_number', 'warehouse_id', 'count_date', 'status', 'notes'])
service = CrudService(repo)
router = create_crud_router(BASE, 'T0105 - Inventory Counts', service,
                            InventoryCountCreate, InventoryCountUpdate, InventoryCountResponse)


@router.post(f'{BASE}/{{id}}/populate')
def populate_items(id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT status FROM "Nova".t0105 WHERE id = %s', (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, 'Count not found')
        if row[0] != 'Draft':
            raise HTTPException(400, 'Can only populate Draft counts')

        cur.execute("""
            INSERT INTO "Nova".t0106 (count_id, product_id, expected_qty)
            SELECT %s, t0009.product_id, t0009.qty
            FROM "Nova".t0009
            WHERE t0009.qty > 0
              AND NOT EXISTS (
                SELECT 1 FROM "Nova".t0106
                WHERE t0106.count_id = %s AND t0106.product_id = t0009.product_id
              )
        """, (id, id))
        conn.commit()
        return {'populated': cur.rowcount}
    finally:
        release_connection(conn)


@router.post(f'{BASE}/{{id}}/complete')
def complete_count(id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT status FROM "Nova".t0105 WHERE id = %s', (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, 'Count not found')
        if row[0] != 'In Progress':
            raise HTTPException(400, 'Count must be In Progress to complete')

        cur.execute("""
            SELECT ci.id, ci.product_id, ci.expected_qty, ci.counted_qty
            FROM "Nova".t0106 ci
            WHERE ci.count_id = %s
        """, (id,))
        items = cur.fetchall()

        adjustments = 0
        for item_id, product_id, expected_qty, counted_qty in items:
            if counted_qty is None:
                continue
            diff = counted_qty - expected_qty
            if abs(diff) < 0.001:
                continue

            cur.execute("""
                UPDATE "Nova".t0009
                SET qty = qty + %s
                WHERE product_id = %s
            """, (diff, product_id))

            cur.execute("""
                INSERT INTO "Nova".t0064 (product_id, warehouse_id, qty_change, balance, movement_type, description, ref_type, ref_id)
                SELECT %s, t0105.warehouse_id, %s, COALESCE((SELECT qty FROM "Nova".t0009 WHERE t0009.product_id = %s), 0),
                       'ADJUSTMENT', 'Inventory count adjustment', 'T0105', %s
                FROM "Nova".t0105 WHERE t0105.id = %s
            """, (product_id, diff, product_id, id, id))
            adjustments += 1

        cur.execute('UPDATE "Nova".t0105 SET status = %s WHERE id = %s', ('Completed', id))
        conn.commit()
        return {'completed': True, 'adjustments': adjustments}
    finally:
        release_connection(conn)
