import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from modules.warehouse.controllers import T0101I, T0102I


@pytest.fixture
def client(monkeypatch):
    from packages.auth.deps import get_current_user
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'username': 'test', 'role': 'Admin', 'permissions': ['*']}
    app.include_router(T0101I.router)
    app.include_router(T0102I.router)
    return TestClient(app)


def test_t0101i_pick_item_endpoint(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.pick_item.return_value = {
        'id': 10,
        'pick_list_id': 1,
        'qty_picked': 2.0,
        'catch_weight_actual': 41.5,
        'catch_weight_uom': 'kg',
        'tolerance_variance_pct': 3.75,
        'tolerance_status': 'Within Tolerance',
    }
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.post(
        '/api/T0101I/1/pick-item/10',
        json={
            'qty_picked': 2.0,
            'catch_weight_actual': 41.5,
            'catch_weight_uom': 'kg',
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == 10
    assert data['catch_weight_actual'] == 41.5
    assert data['tolerance_status'] == 'Within Tolerance'
    mock_svc.pick_item.assert_called_once_with(
        item_id=10,
        qty_picked=2.0,
        pick_list_id=1,
        picked_batch_id=None,
        picked_batch_number=None,
        catch_weight_actual=41.5,
        catch_weight_uom='kg',
        nominal_weight=40.0,
        tolerance_pct=5.0,
    )


def test_t0101i_pick_item_with_barcode(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.pick_item.return_value = {
        'id': 10,
        'pick_list_id': 1,
        'qty_picked': 1.0,
        'catch_weight_actual': 12.5,
        'catch_weight_uom': 'kg',
        'tolerance_status': 'Within Tolerance',
    }
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.post(
        '/api/T0101I/1/pick-item/10',
        json={
            'qty_picked': 1.0,
            'barcode': '(01)00614141000039(3102)001250(10)LOT123',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['catch_weight_actual'] == 12.5
    mock_svc.pick_item.assert_called_once_with(
        item_id=10,
        qty_picked=1.0,
        pick_list_id=1,
        picked_batch_id=None,
        picked_batch_number=None,
        barcode='(01)00614141000039(3102)001250(10)LOT123',
    )


def test_t0101i_get_discrepancies_endpoint(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.check_pick_list_discrepancies.return_value = [
        {
            'id': 10,
            'product_name': 'Aged Cheddar Block',
            'nominal_weight': 40.0,
            'catch_weight_actual': 45.0,
            'tolerance_variance_pct': 12.5,
            'tolerance_status': 'Out of Tolerance',
            'supervisor_approved': False,
        }
    ]
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.get('/api/T0101I/1/discrepancies')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['tolerance_status'] == 'Out of Tolerance'
    mock_svc.check_pick_list_discrepancies.assert_called_once_with(1)


def test_t0101i_approve_tolerance_endpoint(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.approve_tolerance.return_value = {
        'id': 1,
        'approved_count': 1,
        'item_ids': [10],
        'status': 'Approved',
        'message': 'Approved 1 discrepancy item(s)',
    }
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.post(
        '/api/T0101I/1/approve-tolerance',
        json={
            'item_id': 10,
            'supervisor_id': 5,
            'supervisor_notes': 'Customer requested heavy cut',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['approved_count'] == 1
    assert data['status'] == 'Approved'
    mock_svc.approve_tolerance.assert_called_once_with(
        pick_list_id=1,
        item_id=10,
        item_ids=None,
        supervisor_id=5,
        supervisor_notes='Customer requested heavy cut',
    )


def test_t0101i_approve_item_tolerance_endpoint(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.approve_item_tolerance.return_value = {
        'id': 1,
        'approved_count': 1,
        'item_ids': [10],
        'status': 'Approved',
    }
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.post(
        '/api/T0101I/1/items/10/approve-tolerance',
        json={
            'supervisor_id': 3,
            'supervisor_notes': 'Line approval granted',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'Approved'
    mock_svc.approve_item_tolerance.assert_called_once_with(
        pick_list_id=1,
        item_id=10,
        supervisor_id=3,
        supervisor_notes='Line approval granted',
    )


def test_t0101i_complete_picking_endpoint(client, monkeypatch):
    mock_svc = MagicMock()
    mock_svc.complete_picking.return_value = {
        'id': 1,
        'status': 'Completed',
        'has_discrepancies': False,
    }
    monkeypatch.setattr(T0101I, 'pl_service', mock_svc)

    response = client.post('/api/T0101I/1/complete')
    assert response.status_code == 200
    assert response.json()['status'] == 'Completed'


def test_t0102i_crud_endpoints(client, monkeypatch):
    mock_service = MagicMock()
    mock_service.list.return_value = [
        {
            'id': 1,
            'pick_list_id': 100,
            'sales_order_line_id': 10,
            'product_id': 50,
            'product_name': 'Parmigiano Reggiano',
            'qty_ordered': 1.0,
            'qty_picked': 1.0,
            'line_number': 1,
            'catch_weight_actual': 39.2,
            'catch_weight_uom': 'kg',
            'nominal_weight': 40.0,
            'tolerance_pct': 5.0,
            'tolerance_variance_pct': -2.0,
            'tolerance_status': 'Within Tolerance',
            'supervisor_approved': False,
        }
    ]
    mock_service.get.return_value = {
        'id': 1,
        'pick_list_id': 100,
        'sales_order_line_id': 10,
        'product_id': 50,
        'product_name': 'Parmigiano Reggiano',
        'qty_ordered': 1.0,
        'qty_picked': 1.0,
        'line_number': 1,
        'catch_weight_actual': 39.2,
        'catch_weight_uom': 'kg',
        'nominal_weight': 40.0,
        'tolerance_pct': 5.0,
        'tolerance_variance_pct': -2.0,
        'tolerance_status': 'Within Tolerance',
        'supervisor_approved': False,
    }
    mock_service.create.return_value = {
        'id': 2,
        'pick_list_id': 100,
        'product_id': 51,
        'qty_ordered': 2.0,
        'qty_picked': 0.0,
        'line_number': 2,
        'tolerance_status': 'Not Applicable',
        'supervisor_approved': False,
    }
    monkeypatch.setattr(T0102I.service, 'list', mock_service.list)
    monkeypatch.setattr(T0102I.service, 'get', mock_service.get)
    monkeypatch.setattr(T0102I.service, 'create', mock_service.create)
    monkeypatch.setattr(T0102I.service, 'count', MagicMock(return_value=1))

    # Test list
    res = client.get('/api/T0102I')
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]['catch_weight_actual'] == 39.2

    # Test get
    res = client.get('/api/T0102I/1')
    assert res.status_code == 200
    assert res.json()['catch_weight_actual'] == 39.2

    # Test create
    res = client.post('/api/T0102I', json={'pick_list_id': 100, 'product_id': 51, 'qty_ordered': 2.0})
    assert res.status_code == 201
    assert res.json()['id'] == 2
