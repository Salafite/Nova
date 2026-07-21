from datetime import datetime
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException

from packages.auth.deps import get_current_user
from packages.database.connection import get_connection, release_connection
from modules.pos.models.pos import PosCheckoutRequest, PosCheckoutResponse

router = APIRouter(prefix='/api/pos', tags=['POS'], dependencies=[Depends(get_current_user)])


def process_pos_checkout(request: PosCheckoutRequest) -> PosCheckoutResponse:
    if not request.cart_items:
        raise HTTPException(status_code=400, detail="Cart items cannot be empty")

    subtotal = round(sum(item.qty * item.unit_price for item in request.cart_items), 2)
    tax = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + tax, 2)

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Generate order_number POS-YYYYMMDD-XXXX using counter
        today_str = datetime.now().strftime('%Y%m%d')
        cur.execute(
            'SELECT COUNT(*) AS cnt FROM "Nova".t0012 WHERE order_number LIKE %s',
            (f"POS-{today_str}-%",)
        )
        row = cur.fetchone()
        seq_id = (row['cnt'] if row and 'cnt' in row else 0) + 1
        order_number = f"POS-{today_str}-{seq_id:04d}"

        # 3. Create sales order T0012
        notes_content = request.customer_name
        if request.notes:
            notes_content = f"{request.customer_name} - {request.notes}"

        cur.execute(
            """
            INSERT INTO "Nova".t0012 (order_number, customer_id, warehouse_id, subtotal, tax, grand_total, status, order_date, notes)
            VALUES (%s, 1, %s, %s, %s, %s, 'Paid', CURRENT_DATE, %s)
            RETURNING id
            """,
            (order_number, request.warehouse_id, subtotal, tax, grand_total, notes_content)
        )
        order_row = cur.fetchone()
        order_id = order_row['id']

        # 4. Create order lines T0013
        for line_no, item in enumerate(request.cart_items, start=1):
            line_total = round(item.qty * item.unit_price, 2)
            cur.execute(
                """
                INSERT INTO "Nova".t0013 (sales_order_id, product_id, product_name, qty, unit_price, line_total, line_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (order_id, item.product_id, item.product_name, item.qty, item.unit_price, line_total, line_no)
            )

        # 5. Adjust stock T0009 and record movement T0064 atomically
        for item in request.cart_items:
            cur.execute(
                'SELECT id, qty FROM "Nova".t0009 WHERE product_id = %s AND warehouse_id = %s',
                (item.product_id, request.warehouse_id)
            )
            stock_row = cur.fetchone()
            if stock_row:
                current_qty = float(stock_row['qty'] or 0)
                new_balance = max(0.0, current_qty - item.qty)
                cur.execute(
                    'UPDATE "Nova".t0009 SET qty = %s WHERE id = %s',
                    (new_balance, stock_row['id'])
                )
            else:
                new_balance = 0.0
                cur.execute(
                    'INSERT INTO "Nova".t0009 (product_id, warehouse_id, qty) VALUES (%s, %s, %s)',
                    (item.product_id, request.warehouse_id, new_balance)
                )

            cur.execute(
                """
                INSERT INTO "Nova".t0064 (product_id, warehouse_id, movement_type, reference_type, reference_id, qty_change, balance_after, description)
                VALUES (%s, %s, 'Sale', 'pos_order', %s, %s, %s, %s)
                """,
                (item.product_id, request.warehouse_id, order_id, -item.qty, new_balance, f"POS Sale #{order_id}")
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn)

    return PosCheckoutResponse(
        success=True,
        order_id=order_id,
        order_number=order_number,
        grand_total=grand_total,
        message=f"POS order {order_number} created successfully"
    )


@router.post('/checkout', response_model=PosCheckoutResponse)
def checkout(request: PosCheckoutRequest):
    return process_pos_checkout(request)
