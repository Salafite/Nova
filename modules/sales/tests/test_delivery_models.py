from datetime import date, datetime
from modules.sales.models.delivery import (
    DeliveryCreate,
    DeliveryUpdate,
    DeliveryResponse,
)


def test_delivery_create_pod_cod_defaults():
    delivery = DeliveryCreate(
        delivery_number="DEL-00100",
        sales_order_id=1,
    )
    assert delivery.delivery_number == "DEL-00100"
    assert delivery.sales_order_id == 1
    assert delivery.recipient_signature is None
    assert delivery.delivery_photo_url is None
    assert delivery.pod_timestamp is None
    assert delivery.delivery_location is None
    assert delivery.payment_status == "Pending"
    assert delivery.cod_cash_amount == 0.0
    assert delivery.cod_check_amount == 0.0
    assert delivery.cod_check_number is None
    assert delivery.cod_check_bank is None
    assert delivery.driver_id is None


def test_delivery_create_with_pod_cod_fields():
    now = datetime.now()
    delivery = DeliveryCreate(
        delivery_number="DEL-00101",
        sales_order_id=2,
        recipient_signature="data:image/png;base64,iVBORw0KGgo...",
        delivery_photo_url="https://storage.nova.erp/photos/del101.jpg",
        pod_timestamp=now,
        delivery_location="37.7749,-122.4194",
        payment_status="Collected",
        cod_cash_amount=150.50,
        cod_check_amount=200.00,
        cod_check_number="CHK-9988",
        cod_check_bank="Chase Bank",
        driver_id=42,
    )
    assert delivery.recipient_signature == "data:image/png;base64,iVBORw0KGgo..."
    assert delivery.delivery_photo_url == "https://storage.nova.erp/photos/del101.jpg"
    assert delivery.pod_timestamp == now
    assert delivery.delivery_location == "37.7749,-122.4194"
    assert delivery.payment_status == "Collected"
    assert delivery.cod_cash_amount == 150.50
    assert delivery.cod_check_amount == 200.00
    assert delivery.cod_check_number == "CHK-9988"
    assert delivery.cod_check_bank == "Chase Bank"
    assert delivery.driver_id == 42


def test_delivery_update_pod_cod_fields():
    now = datetime.now()
    update_data = DeliveryUpdate(
        payment_status="In Transit",
        cod_cash_amount=75.00,
        driver_id=5,
        pod_timestamp=now,
    )
    assert update_data.payment_status == "In Transit"
    assert update_data.cod_cash_amount == 75.00
    assert update_data.driver_id == 5
    assert update_data.pod_timestamp == now
    assert update_data.recipient_signature is None


def test_delivery_response_pod_cod_fields():
    now = datetime.now()
    response = DeliveryResponse(
        id=10,
        delivery_number="DEL-00102",
        sales_order_id=3,
        delivery_date=date(2026, 9, 3),
        status="Delivered",
        created_at=now,
        updated_at=now,
        recipient_signature="sig_data",
        delivery_photo_url="url_data",
        pod_timestamp=now,
        delivery_location="Warehouse Dock B",
        payment_status="Reconciled",
        cod_cash_amount=500.0,
        cod_check_amount=0.0,
        driver_id=12,
    )
    assert response.id == 10
    assert response.recipient_signature == "sig_data"
    assert response.payment_status == "Reconciled"
    assert response.cod_cash_amount == 500.0
    assert response.driver_id == 12
