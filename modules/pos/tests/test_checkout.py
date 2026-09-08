import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from modules.pos.controllers.checkout import (
    process_pos_checkout,
    get_pos_customers,
    lookup_barcode,
    get_receipt,
)
from modules.pos.models.pos import (
    PosCheckoutRequest,
    PosCartItem,
    PosPaymentSplit,
)

@patch("modules.pos.controllers.checkout.get_connection")
@patch("modules.pos.controllers.checkout.get_current_tenant")
def test_checkout_split_payments_inventory(mock_get_current_tenant, mock_get_connection):
    mock_get_current_tenant.return_value = 1
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    
    # Mock sequence, order, stock rows, and journal entry row
    mock_cur.fetchone.side_effect = [
        {'cnt': 0},                 # order sequence
        {'id': 99},                 # order_id inserted
        {'id': 1001, 'qty': 50.0},   # stock row for item 1
        {'id': 1002, 'qty': 10.0},   # stock row for item 2
        {'id': 501}                 # journal entry id inserted
    ]
    
    request = PosCheckoutRequest(
        business_id=1,
        warehouse_id=10,
        customer_id=20,
        customer_name="John Doe",
        cart_items=[
            PosCartItem(product_id=1, product_name="Item 1", qty=2.0, unit_price=10.0),
            PosCartItem(product_id=2, product_name="Item 2", qty=1.0, unit_price=20.0)
        ],
        amount_tendered=50.0,
        payments=[
            PosPaymentSplit(payment_method="Cash", amount=20.0),
            PosPaymentSplit(payment_method="Card", amount=30.0)
        ]
    )
    
    response = process_pos_checkout(request)
    
    assert response.success is True
    assert response.subtotal == 40.0
    assert response.tax == 2.0
    assert response.grand_total == 42.0
    assert response.amount_tendered == 50.0
    assert response.change_due == 8.0
    assert len(response.payments) == 2
    assert response.payments[0].payment_method == "Cash"
    assert response.payments[0].amount == 20.0
    
    # Verify DB calls
    assert mock_conn.commit.called
    
    queries = [call.args[0] for call in mock_cur.execute.call_args_list]
    
    # Verify inventory deductions
    update_stock_queries = [q for q in queries if 'UPDATE "Nova".t0009 SET qty' in q]
    assert len(update_stock_queries) == 2
    
    movement_queries = [q for q in queries if 'INSERT INTO "Nova".t0064' in q]
    assert len(movement_queries) == 2

    # Verify accounting journal entry & lines
    je_queries = [q for q in queries if 'INSERT INTO "Nova".t0027' in q]
    assert len(je_queries) == 1
    je_line_queries = [q for q in queries if 'INSERT INTO "Nova".t0089' in q]
    assert len(je_line_queries) == 3


@patch("modules.pos.controllers.checkout.get_connection")
@patch("modules.pos.controllers.checkout.get_current_tenant")
def test_get_pos_customers(mock_get_current_tenant, mock_get_connection):
    mock_get_current_tenant.return_value = 1
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    mock_cur.fetchall.return_value = [
        {"id": 1, "name": "Wholesale Buyer Inc", "phone": "555-0100", "email": "buyer@wholesale.com", "customer_group": "Wholesale", "credit_limit": 5000.0, "current_balance": 1200.0}
    ]

    customers = get_pos_customers(q="Wholesale", limit=5)
    assert len(customers) == 1
    assert customers[0].id == 1
    assert customers[0].name == "Wholesale Buyer Inc"


@patch("modules.pos.controllers.checkout.get_connection")
@patch("modules.pos.controllers.checkout.get_current_tenant")
def test_lookup_barcode(mock_get_current_tenant, mock_get_connection):
    mock_get_current_tenant.return_value = 1
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        {"product_id": 10, "product_code": "PROD-001", "barcode": "1234567890123", "product_name": "Bulk Coffee Beans 1kg", "unit_price": 15.5, "uom": "KG"},
        {"stock": 100.0}
    ]

    result = lookup_barcode("1234567890123")
    assert result.product_id == 10
    assert result.barcode == "1234567890123"
    assert result.product_name == "Bulk Coffee Beans 1kg"
    assert result.unit_price == 15.5
    assert result.stock_qty == 100.0


@patch("modules.pos.controllers.checkout.get_connection")
@patch("modules.pos.controllers.checkout.get_current_tenant")
def test_get_receipt(mock_get_current_tenant, mock_get_connection):
    mock_get_current_tenant.return_value = 1
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        {"id": 99, "order_number": "POS-20260904-0001", "order_date": "2026-09-04 10:00:00", "customer_id": 1, "warehouse_id": 1, "subtotal": 100.0, "tax": 5.0, "grand_total": 105.0, "notes": ""},
        {"name": "Wholesale Buyer Inc"}
    ]
    mock_cur.fetchall.return_value = [
        {"product_id": 10, "product_name": "Bulk Coffee Beans 1kg", "qty": 2.0, "unit_price": 50.0, "line_total": 100.0}
    ]

    receipt = get_receipt(99)
    assert receipt.order_id == 99
    assert receipt.order_number == "POS-20260904-0001"
    assert receipt.customer_name == "Wholesale Buyer Inc"
    assert len(receipt.items) == 1
    assert receipt.grand_total == 105.0
