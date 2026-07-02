from datetime import date, timedelta
from fastapi import APIRouter, Depends
from modules.inventory.models import ProductCreate, ProductUpdate, ProductResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from packages.auth.deps import get_current_user
from packages.database.connection import get_connection, release_connection
import psycopg2.extras

repo = CrudRepository('T0003', business_columns=['id', 'name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'image_url', 'is_phantom', 'last_transaction_date', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0003I', 'T0003 - Products', service,
                            ProductCreate, ProductUpdate, ProductResponse)

@router.post('/scan-phantoms')
def scan_phantoms(user: dict = Depends(get_current_user)):
    cutoff = date.today() - timedelta(days=365)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
