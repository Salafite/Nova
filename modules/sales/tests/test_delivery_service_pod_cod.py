from datetime import date, datetime
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from modules.sales.services.delivery_service import DeliveryService


@pytest.fixture
def mock_delivery_repo():
    repo = MagicMock()
    # In-memory storage for mock repo
    db = {}

    def get(id_val, **kwargs):
        return db.get(id_val)

    def update(id_val, payload, **kwargs):
        if id_val not in db:
            return None
        db[id_val].update(payload)
        return dict(db[id_val])

    def list_fn(filters=None, **kwargs):
        filters = filters or {}
        results = []
        for item in db.values():
            match = True
            for k, v in filters.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                results.append(dict(item))
        return results

    repo.get.side_effect = get
    repo.update.side_effect = update
    repo.list.side_effect = list_fn
    repo._db = db
    return repo


def test_capture_pod_success(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    mock_delivery_repo._db[1] = {
        'id': 1,
        'delivery_number': 'DEL-001',
        'sales_order_id': 100,
        'status': 'Shipped',
        'recipient_signature': None,
        'delivery_photo_url': None,
        'delivery_location': None,
        'pod_timestamp': None,
    }

    now = datetime.now()
    result = service.capture_pod(
        delivery_id=1,
        signature='data:image/png;base64,abcdef...',
        photo_url='https://storage.nova.erp/photos/1.jpg',
        location='37.7749,-122.4194',
        timestamp=now,
    )

    assert result['id'] == 1
    assert result['status'] == 'Delivered'
    assert result['recipient_signature'] == 'data:image/png;base64,abcdef...'
    assert result['delivery_photo_url'] == 'https://storage.nova.erp/photos/1.jpg'
    assert result['delivery_location'] == '37.7749,-122.4194'
    assert result['pod_timestamp'] == now
    assert result['actual_delivery_date'] == now.date()


def test_capture_pod_not_found(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    with pytest.raises(HTTPException) as exc_info:
        service.capture_pod(delivery_id=999)
    assert exc_info.value.status_code == 404


def test_log_cod_collection_success(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    mock_delivery_repo._db[1] = {
        'id': 1,
        'delivery_number': 'DEL-001',
        'payment_status': 'Pending',
        'cod_cash_amount': 0.0,
        'cod_check_amount': 0.0,
    }

    result = service.log_cod_collection(
        delivery_id=1,
        cash_amount=150.00,
        check_amount=50.00,
        check_number='CHK-1001',
        check_bank='First National Bank',
    )

    assert result['payment_status'] == 'Collected'
    assert result['cod_cash_amount'] == 150.00
    assert result['cod_check_amount'] == 50.00
    assert result['cod_check_number'] == 'CHK-1001'
    assert result['cod_check_bank'] == 'First National Bank'


def test_log_cod_collection_custom_status(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    mock_delivery_repo._db[1] = {
        'id': 1,
        'delivery_number': 'DEL-001',
        'payment_status': 'Pending',
    }

    result = service.log_cod_collection(
        delivery_id=1,
        cash_amount=200.00,
        payment_status='In Transit',
    )

    assert result['payment_status'] == 'In Transit'
    assert result['cod_cash_amount'] == 200.00


def test_log_cod_collection_negative_amount_raises(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    mock_delivery_repo._db[1] = {'id': 1, 'payment_status': 'Pending'}
    with pytest.raises(HTTPException) as exc_info:
        service.log_cod_collection(delivery_id=1, cash_amount=-50.0)
    assert exc_info.value.status_code == 400


def test_get_driver_handover_report(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    today_str = date.today().strftime('%Y-%m-%d')
    mock_delivery_repo._db[1] = {
        'id': 1,
        'driver_id': 10,
        'delivery_date': today_str,
        'status': 'Delivered',
        'payment_status': 'Collected',
        'cod_cash_amount': 100.0,
        'cod_check_amount': 0.0,
    }
    mock_delivery_repo._db[2] = {
        'id': 2,
        'driver_id': 10,
        'delivery_date': today_str,
        'status': 'Delivered',
        'payment_status': 'Collected',
        'cod_cash_amount': 50.0,
        'cod_check_amount': 200.0,
    }

    report = service.get_driver_handover_report(driver_id=10, delivery_date=date.today())

    assert report['driver_id'] == 10
    assert report['total_deliveries'] == 2
    assert report['completed_deliveries'] == 2
    assert report['total_cash_collected'] == 150.0
    assert report['total_check_collected'] == 200.0
    assert report['total_collected'] == 350.0
    assert report['unreconciled_deliveries'] == 2


def test_reconcile_driver_cash_balanced(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    today_str = date.today().strftime('%Y-%m-%d')
    mock_delivery_repo._db[1] = {
        'id': 1,
        'driver_id': 10,
        'delivery_date': today_str,
        'status': 'Delivered',
        'payment_status': 'Collected',
        'cod_cash_amount': 100.0,
        'cod_check_amount': 50.0,
    }

    recon = service.reconcile_driver_cash(
        driver_id=10,
        delivery_date=date.today(),
        cash_submitted=100.0,
        check_submitted=50.0,
        notes='End of day check drop',
    )

    assert recon['is_balanced'] is True
    assert recon['status'] == 'Reconciled'
    assert recon['cash_discrepancy'] == 0.0
    assert recon['check_discrepancy'] == 0.0
    assert recon['reconciled_count'] == 1
    assert mock_delivery_repo._db[1]['payment_status'] == 'Reconciled'


def test_reconcile_driver_cash_discrepancy(mock_delivery_repo):
    service = DeliveryService(repo=mock_delivery_repo)
    today_str = date.today().strftime('%Y-%m-%d')
    mock_delivery_repo._db[1] = {
        'id': 1,
        'driver_id': 10,
        'delivery_date': today_str,
        'status': 'Delivered',
        'payment_status': 'Collected',
        'cod_cash_amount': 100.0,
        'cod_check_amount': 0.0,
    }

    recon = service.reconcile_driver_cash(
        driver_id=10,
        delivery_date=date.today(),
        cash_submitted=90.0,
        check_submitted=0.0,
    )

    assert recon['is_balanced'] is False
    assert recon['status'] == 'Discrepancy'
    assert recon['cash_discrepancy'] == -10.0
    assert recon['total_discrepancy'] == -10.0
