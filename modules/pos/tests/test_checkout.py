import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from modules.pos.controllers.checkout import process_pos_checkout
from modules.pos.models.pos import (
    PosCheckoutRequest,
    PosCartItem,
    PosPaymentSplit
)

@patch("modules.pos.controllers.checkout.get_connection")
@patch("modules.pos.controllers.checkout.get_current_tenant")
def test_checkout_split_payments_inventory(mock_get_current_tenant, mock_get_connection):
    mock_get_current_tenant.return_value = 1
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    
    # Mock sequence and stock rows
    mock_cur.fetchone.side_effect = [
        {'cnt': 0}, # order sequence
        {'id': 99}, # order_id inserted
        {'id': 1001, 'qty': 50.0}, # stock row for item 1
        {'id': 1002, 'qty': 10.0}  # stock row for item 2
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
