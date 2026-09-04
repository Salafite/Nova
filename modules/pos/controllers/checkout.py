from datetime import datetime
from typing import List, Optional
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
    PosCustomerLookup,
    PosBarcodeLookupResponse,
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

        # 6. Post revenue and tax to accounting ledger (T0027 Journal Entry & T0089 Lines)
        if tenant_id is not None:
            cur.execute(
                """
                INSERT INTO "Nova".t0027 (entry_date, reference, description, status, business_id)
                VALUES (CURRENT_DATE, %s, %s, 'Posted', %s)
                RETURNING id
                """,
                (order_number, f"POS Sale Revenue #{order_number}", tenant_id)
            )
        else:
            cur.execute(
                """
                INSERT INTO "Nova".t0027 (entry_date, reference, description, status)
                VALUES (CURRENT_DATE, %s, %s, 'Posted')
                RETURNING id
                """,
                (order_number, f"POS Sale Revenue #{order_number}")
            )
        try:
            je_row = cur.fetchone()
            je_id = je_row['id'] if (je_row and isinstance(je_row, dict) and 'id' in je_row) else order_id
        except Exception:
            je_id = order_id

        if tenant_id is not None:
            cur.execute(
                """
                INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number, business_id)
                VALUES (%s, 1010, %s, %s, 0.0, 1, %s)
                """,
                (je_id, f"POS Payment - {order_number}", grand_total, tenant_id)
            )
            cur.execute(
                """
                INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number, business_id)
                VALUES (%s, 4010, %s, 0.0, %s, 2, %s)
                """,
                (je_id, f"POS Sales Revenue - {order_number}", subtotal, tenant_id)
            )
            if tax > 0:
                cur.execute(
                    """
                    INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number, business_id)
                    VALUES (%s, 2020, %s, 0.0, %s, 3, %s)
                    """,
                    (je_id, f"POS Sales Tax - {order_number}", tax, tenant_id)
                )
        else:
            cur.execute(
                """
                INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number)
                VALUES (%s, 1010, %s, %s, 0.0, 1)
                """,
                (je_id, f"POS Payment - {order_number}", grand_total)
            )
            cur.execute(
                """
                INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number)
                VALUES (%s, 4010, %s, 0.0, %s, 2)
                """,
                (je_id, f"POS Sales Revenue - {order_number}", subtotal)
            )
            if tax > 0:
                cur.execute(
                    """
                    INSERT INTO "Nova".t0089 (journal_entry_id, account_id, description, debit, credit, line_number)
                    VALUES (%s, 2020, %s, 0.0, %s, 3)
                    """,
                    (je_id, f"POS Sales Tax - {order_number}", tax)
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


@router.get('/customers', response_model=List[PosCustomerLookup])
def get_pos_customers(q: str = "", limit: int = 10):
    tenant_id = get_current_tenant()
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if tenant_id is not None:
            if q:
                cur.execute(
                    'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 WHERE (name ILIKE %s OR phone ILIKE %s) AND business_id = %s LIMIT %s',
                    (f"%{q}%", f"%{q}%", tenant_id, limit)
                )
            else:
                cur.execute(
                    'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 WHERE business_id = %s ORDER BY id LIMIT %s',
                    (tenant_id, limit)
                )
        else:
            if q:
                cur.execute(
                    'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 WHERE name ILIKE %s OR phone ILIKE %s LIMIT %s',
                    (f"%{q}%", f"%{q}%", limit)
                )
            else:
                cur.execute(
                    'SELECT id, name, phone, email, customer_group, credit_limit, current_balance FROM "Nova".t0010 ORDER BY id LIMIT %s',
                    (limit,)
                )
        rows = cur.fetchall()
        return [PosCustomerLookup(**dict(row)) for row in rows]
    finally:
        release_connection(conn)


@router.get('/barcode/{code}', response_model=PosBarcodeLookupResponse)
def lookup_barcode(code: str):
    tenant_id = get_current_tenant()
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if tenant_id is not None:
            cur.execute(
                """
                SELECT p.id as product_id, p.code as product_code, b.barcode, p.name as product_name, p.price as unit_price, p.uom
                FROM "Nova".t0003 p
                LEFT JOIN "Nova".t0004 b ON p.id = b.product_id
                WHERE (b.barcode = %s OR p.code = %s) AND p.business_id = %s
                LIMIT 1
                """,
                (code, code, tenant_id)
            )
        else:
            cur.execute(
                """
                SELECT p.id as product_id, p.code as product_code, b.barcode, p.name as product_name, p.price as unit_price, p.uom
                FROM "Nova".t0003 p
                LEFT JOIN "Nova".t0004 b ON p.id = b.product_id
                WHERE b.barcode = %s OR p.code = %s
                LIMIT 1
                """,
                (code, code)
            )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Barcode or SKU '{code}' not found")
        
        prod_id = row['product_id']
        if tenant_id is not None:
            cur.execute(
                'SELECT COALESCE(SUM(qty), 0) as stock FROM "Nova".t0009 WHERE product_id = %s AND business_id = %s',
                (prod_id, tenant_id)
            )
        else:
            cur.execute(
                'SELECT COALESCE(SUM(qty), 0) as stock FROM "Nova".t0009 WHERE product_id = %s',
                (prod_id,)
            )
        stock_row = cur.fetchone()
        stock_qty = float(stock_row['stock']) if stock_row else 0.0

        return PosBarcodeLookupResponse(
            product_id=row['product_id'],
            product_code=row['product_code'] or str(row['product_id']),
            barcode=row['barcode'] or code,
            product_name=row['product_name'],
            unit_price=float(row['unit_price'] or 0.0),
            uom=row['uom'] or 'PCS',
            stock_qty=stock_qty
        )
    finally:
        release_connection(conn)


@router.get('/receipt/{order_id}', response_model=PosReceiptData)
def get_receipt(order_id: int):
    tenant_id = get_current_tenant()
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if tenant_id is not None:
            cur.execute(
                'SELECT id, order_number, order_date, customer_id, warehouse_id, subtotal, tax, grand_total, notes FROM "Nova".t0012 WHERE id = %s AND business_id = %s',
                (order_id, tenant_id)
            )
        else:
            cur.execute(
                'SELECT id, order_number, order_date, customer_id, warehouse_id, subtotal, tax, grand_total, notes FROM "Nova".t0012 WHERE id = %s',
                (order_id,)
            )
        order_row = cur.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail=f"Order ID {order_id} not found")

        if tenant_id is not None:
            cur.execute(
                'SELECT product_id, product_name, qty, unit_price, line_total FROM "Nova".t0013 WHERE sales_order_id = %s AND business_id = %s ORDER BY line_number',
                (order_id, tenant_id)
            )
        else:
            cur.execute(
                'SELECT product_id, product_name, qty, unit_price, line_total FROM "Nova".t0013 WHERE sales_order_id = %s ORDER BY line_number',
                (order_id,)
            )
        item_rows = cur.fetchall()

        customer_name = "Walk-in Customer"
        cust_id = order_row.get('customer_id')
        if cust_id:
            if tenant_id is not None:
                cur.execute('SELECT name FROM "Nova".t0010 WHERE id = %s AND business_id = %s', (cust_id, tenant_id))
            else:
                cur.execute('SELECT name FROM "Nova".t0010 WHERE id = %s', (cust_id,))
            c_row = cur.fetchone()
            if c_row and c_row.get('name'):
                customer_name = c_row['name']

        receipt_items = [
            PosReceiptItem(
                product_id=row['product_id'],
                product_name=row['product_name'],
                qty=float(row['qty']),
                unit_price=float(row['unit_price']),
                line_total=float(row['line_total'])
            ) for row in item_rows
        ]

        grand_total = float(order_row['grand_total'])
        subtotal = float(order_row['subtotal'])
        tax = float(order_row['tax'])

        return PosReceiptData(
            order_id=order_row['id'],
            order_number=order_row['order_number'],
            order_date=str(order_row['order_date']),
            customer_name=customer_name,
            customer_id=cust_id,
            warehouse_id=order_row['warehouse_id'],
            items=receipt_items,
            subtotal=subtotal,
            tax=tax,
            grand_total=grand_total,
            amount_tendered=grand_total,
            change_due=0.0,
            payments=[PosPaymentSplit(payment_method="Cash", amount=grand_total)],
            cashier_name="Cashier",
            business_name="Nova Wholesale Depot"
        )
    finally:
        release_connection(conn)

