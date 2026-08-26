"""
Nova ERP — Unit & Integration Tests for Stock Transfer Controllers (T0108I & T0109I)
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from modules.warehouse.controllers.T0108I import router as t0108_router, service as t0108_service
from modules.warehouse.controllers.T0109I import router as t0109_router, service as t0109_service
from packages.auth.deps import get_current_user


@pytest.fixture
def test_app_and_client():
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {
        'id': 10,
        'username': 'logistics_admin',
        'role': 'Admin',
        'business_id': 1,
        'permissions': ['*'],
    }
    app.include_router(t0108_router)
    app.include_router(t0109_router)
    return app, TestClient(app)


class TestStockTransferHeaderControllerT0108I:
    """Test suite for T0108I Stock Transfers Controller."""

    def test_list_stock_transfers(self, test_app_and_client):
        _, client = test_app_and_client
        mock_list = [
            {'id': 1, 'transfer_number': 'TRF-00001', 'source_warehouse_id': 1, 'destination_warehouse_id': 2, 'status': 'Draft'},
            {'id': 2, 'transfer_number': 'TRF-00002', 'source_warehouse_id': 1, 'destination_warehouse_id': 3, 'status': 'In Transit'},
        ]
        with patch.object(t0108_service.repo, 'list', return_value=mock_list):
            resp = client.get('/api/T0108I/')
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]['transfer_number'] == 'TRF-00001'

    def test_get_stock_transfer_by_id(self, test_app_and_client):
        _, client = test_app_and_client
        mock_trf = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': '2026-08-26',
            'is_active': True,
        }
        with patch.object(t0108_service, 'get', return_value=mock_trf):
            resp = client.get('/api/T0108I/1')
            assert resp.status_code == 200
            data = resp.json()
            assert data['id'] == 1
            assert data['transfer_number'] == 'TRF-00001'

    def test_get_stock_transfer_not_found(self, test_app_and_client):
        _, client = test_app_and_client
        with patch.object(t0108_service, 'get', return_value=None):
            with patch.object(t0108_service.repo, 'get_unscoped', return_value=None):
                resp = client.get('/api/T0108I/999')
                assert resp.status_code == 404

    def test_create_stock_transfer(self, test_app_and_client):
        _, client = test_app_and_client
        mock_created = {
            'id': 5,
            'transfer_number': 'TRF-00005',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Draft',
            'transfer_date': '2026-08-26',
            'is_active': True,
            'lines': [
                {'id': 10, 'transfer_id': 5, 'product_id': 101, 'qty_requested': 50.0, 'qty_dispatched': 0, 'qty_received': 0, 'qty_lost': 0, 'is_active': True}
            ],
            'total_requested_qty': 50.0,
            'total_dispatched_qty': 0,
            'total_received_qty': 0,
            'total_lost_qty': 0,
            'lines_count': 1,
        }
        payload = {
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'lines': [
                {'product_id': 101, 'qty_requested': 50.0}
            ]
        }
        with patch.object(t0108_service, 'create_transfer', return_value=mock_created):
            resp = client.post('/api/T0108I/', json=payload)
            assert resp.status_code == 201
            data = resp.json()
            assert data['id'] == 5
            assert data['transfer_number'] == 'TRF-00005'
            assert data['total_requested_qty'] == 50.0

    def test_get_in_transit_transfers(self, test_app_and_client):
        _, client = test_app_and_client
        mock_in_transit = [
            {
                'id': 2,
                'transfer_number': 'TRF-00002',
                'source_warehouse_id': 1,
                'destination_warehouse_id': 2,
                'status': 'In Transit',
                'transfer_date': '2026-08-26',
                'carrier': 'FastFreight Logistics',
                'tracking_number': 'FF-883921',
                'is_active': True,
            }
        ]
        with patch.object(t0108_service, 'list_in_transit', return_value=mock_in_transit):
            resp = client.get('/api/T0108I/in-transit')
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]['status'] == 'In Transit'
            assert data[0]['carrier'] == 'FastFreight Logistics'

    def test_get_transfer_detail_enriched(self, test_app_and_client):
        _, client = test_app_and_client
        mock_detailed = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'source_warehouse_name': 'Central Cold Storage',
            'destination_warehouse_id': 2,
            'destination_warehouse_name': 'Regional DC North',
            'status': 'In Transit',
            'transfer_date': '2026-08-26',
            'carrier': 'ColdChain Express',
            'tracking_number': 'CC-10293',
            'is_active': True,
            'lines': [
                {
                    'id': 1,
                    'transfer_id': 1,
                    'product_id': 101,
                    'product_code': 'PROD-001',
                    'product_name': 'Aged Cheddar Cheese',
                    'qty_requested': 100.0,
                    'qty_dispatched': 100.0,
                    'qty_received': 0.0,
                    'qty_lost': 0.0,
                    'batch_number': 'LOT-2026-01',
                    'line_number': 1,
                    'is_active': True,
                }
            ],
            'total_requested_qty': 100.0,
            'total_dispatched_qty': 100.0,
            'total_received_qty': 0.0,
            'total_lost_qty': 0.0,
            'lines_count': 1,
        }
        with patch.object(t0108_service, 'get_transfer_with_lines', return_value=mock_detailed):
            resp = client.get('/api/T0108I/1/detail')
            assert resp.status_code == 200
            data = resp.json()
            assert data['source_warehouse_name'] == 'Central Cold Storage'
            assert data['destination_warehouse_name'] == 'Regional DC North'
            assert len(data['lines']) == 1
            assert data['lines'][0]['product_name'] == 'Aged Cheddar Cheese'

    def test_dispatch_transfer_action(self, test_app_and_client):
        _, client = test_app_and_client
        mock_existing = {'id': 1, 'status': 'Draft', 'transfer_number': 'TRF-00001'}
        mock_dispatched = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'In Transit',
            'transfer_date': '2026-08-26',
            'carrier': 'Express Logistics',
            'tracking_number': 'TRK-99001',
            'dispatched_by': 10,
            'is_active': True,
            'total_dispatched_qty': 40.0,
            'total_requested_qty': 40.0,
            'lines_count': 1,
        }
        with patch.object(t0108_service, 'get', return_value=mock_existing):
            with patch.object(t0108_service, 'dispatch_transfer', return_value=mock_dispatched):
                payload = {
                    'carrier': 'Express Logistics',
                    'tracking_number': 'TRK-99001',
                }
                resp = client.post('/api/T0108I/1/dispatch', json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data['status'] == 'In Transit'
                assert data['carrier'] == 'Express Logistics'

    def test_receive_transfer_action(self, test_app_and_client):
        _, client = test_app_and_client
        mock_existing = {'id': 1, 'status': 'In Transit', 'transfer_number': 'TRF-00001'}
        mock_received = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Received',
            'transfer_date': '2026-08-26',
            'received_by': 10,
            'is_active': True,
            'total_requested_qty': 50.0,
            'total_dispatched_qty': 50.0,
            'total_received_qty': 48.0,
            'total_lost_qty': 2.0,
            'lines_count': 1,
        }
        with patch.object(t0108_service, 'get', return_value=mock_existing):
            with patch.object(t0108_service, 'receive_transfer', return_value=mock_received):
                payload = {
                    'lines': [
                        {
                            'product_id': 101,
                            'qty_received': 48.0,
                            'qty_lost': 2.0,
                            'loss_reason': 'Transit Damage',
                            'loss_notes': '2 cartons damaged by forklift during transit',
                        }
                    ]
                }
                resp = client.post('/api/T0108I/1/receive', json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data['status'] == 'Received'
                assert data['total_received_qty'] == 48.0
                assert data['total_lost_qty'] == 2.0

    def test_cancel_transfer_action(self, test_app_and_client):
        _, client = test_app_and_client
        mock_existing = {'id': 1, 'status': 'Draft', 'transfer_number': 'TRF-00001'}
        mock_cancelled = {
            'id': 1,
            'transfer_number': 'TRF-00001',
            'source_warehouse_id': 1,
            'destination_warehouse_id': 2,
            'status': 'Cancelled',
            'transfer_date': '2026-08-26',
            'notes': '[Cancelled: Order no longer needed]',
            'is_active': True,
        }
        with patch.object(t0108_service, 'get', return_value=mock_existing):
            with patch.object(t0108_service, 'cancel_transfer', return_value=mock_cancelled):
                payload = {'reason': 'Order no longer needed'}
                resp = client.post('/api/T0108I/1/cancel', json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data['status'] == 'Cancelled'

    def test_add_and_delete_line_sub_routes(self, test_app_and_client):
        _, client = test_app_and_client
        mock_existing = {'id': 1, 'status': 'Draft', 'transfer_number': 'TRF-00001'}
        mock_created_line = {
            'id': 12,
            'transfer_id': 1,
            'product_id': 102,
            'qty_requested': 25.0,
            'qty_dispatched': 0.0,
            'qty_received': 0.0,
            'qty_lost': 0.0,
            'line_number': 2,
            'is_active': True,
        }
        with patch.object(t0108_service, 'get', return_value=mock_existing):
            with patch.object(t0108_service, 'add_line', return_value=mock_created_line):
                resp = client.post('/api/T0108I/1/lines', json={'product_id': 102, 'qty_requested': 25.0})
                assert resp.status_code == 201
                data = resp.json()
                assert data['id'] == 12
                assert data['qty_requested'] == 25.0

            with patch.object(t0108_service, 'delete_line', return_value={'success': True}):
                resp = client.delete('/api/T0108I/1/lines/12')
                assert resp.status_code == 204


class TestStockTransferLinesControllerT0109I:
    """Test suite for T0109I Stock Transfer Lines Controller."""

    def test_list_lines(self, test_app_and_client):
        _, client = test_app_and_client
        mock_lines = [
            {'id': 1, 'transfer_id': 1, 'product_id': 101, 'qty_requested': 50.0, 'qty_dispatched': 50.0, 'qty_received': 50.0, 'qty_lost': 0.0, 'is_active': True},
            {'id': 2, 'transfer_id': 1, 'product_id': 102, 'qty_requested': 30.0, 'qty_dispatched': 30.0, 'qty_received': 28.0, 'qty_lost': 2.0, 'loss_reason': 'Transit Damage', 'is_active': True},
        ]
        with patch.object(t0109_service.repo, 'list', return_value=mock_lines):
            resp = client.get('/api/T0109I/')
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[1]['loss_reason'] == 'Transit Damage'

    def test_get_line_by_id(self, test_app_and_client):
        _, client = test_app_and_client
        mock_line = {
            'id': 1,
            'transfer_id': 1,
            'product_id': 101,
            'qty_requested': 50.0,
            'qty_dispatched': 50.0,
            'qty_received': 50.0,
            'qty_lost': 0.0,
            'is_active': True,
        }
        with patch.object(t0109_service, 'get', return_value=mock_line):
            resp = client.get('/api/T0109I/1')
            assert resp.status_code == 200
            data = resp.json()
            assert data['id'] == 1
            assert data['qty_requested'] == 50.0

    def test_create_line(self, test_app_and_client):
        _, client = test_app_and_client
        mock_created = {
            'id': 3,
            'transfer_id': 1,
            'product_id': 103,
            'qty_requested': 15.0,
            'qty_dispatched': 0.0,
            'qty_received': 0.0,
            'qty_lost': 0.0,
            'is_active': True,
        }
        with patch.object(t0109_service, 'create', return_value=mock_created):
            payload = {'transfer_id': 1, 'product_id': 103, 'qty_requested': 15.0}
            resp = client.post('/api/T0109I/', json=payload)
            assert resp.status_code == 201
            data = resp.json()
            assert data['id'] == 3
            assert data['qty_requested'] == 15.0
