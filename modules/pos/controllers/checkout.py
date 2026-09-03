from datetime import datetime
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException

from packages.auth.deps import require_permission
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant
from modules.pos.models.pos import (
    PosCheckoutRequest,
    PosCheckoutResponse,
    PosPaymentSplit,
    PosReceiptData,
    PosReceiptItem,
)

router = APIRouter(prefix='/api/pos', tags=['POS'], dependencies=[Depends(require_permission('POS_VIEW'))])


def process_pos_checkout(request: PosCheckoutRequest) -> PosCheckoutResponse:
    if not request.cart_items:
        raise HTTPException(status_code=400, detail="Cart items cannot be empty")

    tenant_id = request.business_id if request.business_id is not None else get_current_tenant()

    subtotal = round(sum(item.qty * item.unit_price for item in request.cart_items), 2)
    tax = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + tax, 2)

    # Process payments breakdown
    payments = request.payments if request.payments else [
        PosPaymentSplit(payment_method=request.payment_method or "Cash", amount=grand_total)
    ]
    total_tendered = request.amount_tendered if request.amount_tendered is not None else round(sum(p.amount for p in payments), 2)
    if total_tendered < grand_total:
        total_tendered = grand_total
    change_due = round(max(0.0, total_tendered - grand_total), 2)

    cust_id = request.customer_id if request.customer_id is not None else 1

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Generate order_number POS-YYYYMMDD-XXXX using counter
        today_str = datetime.now().strftime('%Y%m%d')
        if tenant_id is not None:
            cur.execute(
                'SELECT COUNT(*) AS cnt FROM "Nova".t0012 WHERE order_number LIKE %s AND business_id = %s',
                (f"POS-{today_str}-%", tenant_id)
            )
        else:
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

        if tenant_id is not None:
            cur.execute(
                """
                INSERT INTO "Nova".t0012 (order_number, customer_id, warehouse_id, subtotal, tax, grand_total, status, order_date, notes, business_id)
                VALUES (%s, %s, %s, %s, %s, %s, 'Paid', CURRENT_DATE, %s, %s)
                RETURNING id
                """,
                (order_number, cust_id, request.warehouse_id, subtotal, tax, grand_total, notes_content, tenant_id)
            )
        else:
            cur.execute(
                """
                INSERT INTO "Nova".t0012 (order_number, customer_id, warehouse_id, subtotal, tax, grand_total, status, order_date, notes)
                VALUES (%s, %s, %s, %s, %s, %s, 'Paid', CURRENT_DATE, %s)
                RETURNING id
                """,
                (order_number, cust_id, request.warehouse_id, subtotal, tax, grand_total, notes_content)
            )
        order_row = cur.fetchone()
        order_id = order_row['id']

        # 4. Create order lines T0013
        for line_no, item in enumerate(request.cart_items, start=1):
            line_total = round(item.qty * item.unit_price, 2)
            if tenant_id is not None:
                cur.execute(
                    """
                    INSERT INTO "Nova".t0013 (sales_order_id, product_id, product_name, qty, unit_price, line_total, line_number, business_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (order_id, item.product_id, item.product_name, item.qty, item.unit_price, line_total, line_no, tenant_id)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO "Nova".t0013 (sales_order_id, product_id, product_name, qty, unit_price, line_total, line_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (order_id, item.product_id, item.product_name, item.qty, item.unit_price, line_total, line_no)
                )

        # 5. Adjust stock T0009 and record movement T0064 atomically
        for item in request.cart_items:
            if tenant_id is not None:
                cur.execute(
                    'SELECT id, qty FROM "Nova".t0009 WHERE product_id = %s AND warehouse_id = %s AND business_id = %s',
                    (item.product_id, request.warehouse_id, tenant_id)
                )
            else:
                cur.execute(
                    'SELECT id, qty FROM "Nova".t0009 WHERE product_id = %s AND warehouse_id = %s',
                    (item.product_id, request.warehouse_id)
                )
            stock_row = cur.fetchone()
            if stock_row:
                current_qty = float(stock_row['qty'] or 0)
                new_balance = max(0.0, current_qty - item.qty)
                if tenant_id is not None:
                    cur.execute(
                        'UPDATE "Nova".t0009 SET qty = %s WHERE id = %s AND business_id = %s',
                        (new_balance, stock_row['id'], tenant_id)
                    )
                else:
                    cur.execute(
                        'UPDATE "Nova".t0009 SET qty = %s WHERE id = %s',
                        (new_balance, stock_row['id'])
                    )
            else:
                new_balance = 0.0
                if tenant_id is not None:
                    cur.execute(
                        'INSERT INTO "Nova".t0009 (product_id, warehouse_id, qty, business_id) VALUES (%s, %s, %s, %s)',
                        (item.product_id, request.warehouse_id, new_balance, tenant_id)
                    )
                else:
                    cur.execute(
                        'INSERT INTO "Nova".t0009 (product_id, warehouse_id, qty) VALUES (%s, %s, %s)',
                        (item.product_id, request.warehouse_id, new_balance)
                    )

            if tenant_id is not None:
                cur.execute(
                    """
                    INSERT INTO "Nova".t0064 (product_id, warehouse_id, movement_type, reference_type, reference_id, qty_change, balance_after, description, business_id)
                    VALUES (%s, %s, 'Sale', 'pos_order', %s, %s, %s, %s, %s)
                    """,
                    (item.product_id, request.warehouse_id, order_id, -item.qty, new_balance, f"POS Sale #{order_id}", tenant_id)
                )
            else:
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

    receipt_items = [
        PosReceiptItem(
            product_id=item.product_id,
            product_name=item.product_name,
            qty=item.qty,
            unit_price=item.unit_price,
            line_total=round(item.qty * item.unit_price, 2)
        ) for item in request.cart_items
    ]

    receipt_data = PosReceiptData(
        order_id=order_id,
        order_number=order_number,
        order_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        customer_name=request.customer_name,
        customer_id=cust_id,
        warehouse_id=request.warehouse_id,
        items=receipt_items,
        subtotal=subtotal,
        tax=tax,
        grand_total=grand_total,
        amount_tendered=total_tendered,
        change_due=change_due,
        payments=payments,
        cashier_name="Cashier",
        business_name="Nova Wholesale Depot"
    )

    return PosCheckoutResponse(
        success=True,
        order_id=order_id,
        order_number=order_number,
        subtotal=subtotal,
        tax=tax,
        grand_total=grand_total,
        amount_tendered=total_tendered,
        change_due=change_due,
        payments=payments,
        receipt=receipt_data,
        message=f"POS order {order_number} created successfully"
    )


@router.post('/checkout', response_model=PosCheckoutResponse)
def checkout(request: PosCheckoutRequest):
    return process_pos_checkout(request)
