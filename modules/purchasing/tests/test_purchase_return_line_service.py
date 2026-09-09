import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from modules.purchasing.services.purchase_return_line_service import PurchaseReturnLineService
from modules.purchasing.controllers.T0082I import router, service as controller_service
from packages.auth.deps import get_current_user


class TestPurchaseReturnLineService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_return_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_batch_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_product_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo, mock_return_repo, mock_batch_repo, mock_product_repo):
        return PurchaseReturnLineService(
            repo=mock_repo,
            return_repo=mock_return_repo,
            batch_repo=mock_batch_repo,
            product_repo=mock_product_repo,
        )

    def test_create_line_auto_calculates_line_total(self, service, mock_repo, mock_return_repo):
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 1, **data}
        mock_return_repo.get.return_value = {'id': 10, 'total_amount': 0.0}

        payload = {
            'return_id': 10,
            'product_name': 'Organic Tomatoes',
            'qty': 5.5,
            'unit_price': 12.0,
        }
        created = service.create(payload)

        assert created['id'] == 1
        assert created['line_total'] == 66.0
        assert created['quarantine_status'] == 'Quarantine'
        assert created['disposition'] == 'Return to Vendor'
        assert created['line_number'] == 1
        assert mock_return_repo.update.called

    def test_create_line_resolves_batch_details(self, service, mock_repo, mock_batch_repo, mock_return_repo):
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 2, **data}
        mock_batch_repo.get.return_value = {
            'id': 50,
            'batch_number': 'LOT-2026-0901',
            'expiry_date': '2026-09-30',
            'product_id': 101,
        }

        payload = {
            'return_id': 10,
            'product_name': 'Fresh Milk',
            'batch_id': 50,
            'qty': 10.0,
            'unit_price': 3.5,
        }
        created = service.create(payload)

        assert created['batch_number'] == 'LOT-2026-0901'
        assert created['expiry_date'] == '2026-09-30'
        assert created['product_id'] == 101
        assert created['line_total'] == 35.0

    def test_create_line_resolves_batch_from_batch_number(self, service, mock_repo, mock_batch_repo, mock_return_repo):
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 3, **data}
        mock_batch_repo.list.return_value = [{
            'id': 55,
            'batch_number': 'LOT-9988',
            'expiry_date': '2026-10-15',
            'product_id': 202,
        }]

        payload = {
            'return_id': 10,
            'batch_number': 'LOT-9988',
            'qty': 2.0,
            'unit_price': 50.0,
        }
        created = service.create(payload)

        assert created['batch_id'] == 55
        assert created['expiry_date'] == '2026-10-15'
        assert created['product_id'] == 202
        assert created['line_total'] == 100.0

    def test_create_line_resolves_product_name(self, service, mock_repo, mock_product_repo, mock_return_repo):
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 4, **data}
        mock_product_repo.get.return_value = {
            'id': 301,
            'name': 'Premium Greek Yogurt',
        }

        payload = {
            'return_id': 10,
            'product_id': 301,
            'qty': 4.0,
            'unit_price': 8.0,
        }
        created = service.create(payload)

        assert created['product_name'] == 'Premium Greek Yogurt'
        assert created['line_total'] == 32.0

    def test_update_line_recalculates_line_total_and_return_total(self, service, mock_repo, mock_return_repo):
        old_line = {
            'id': 1,
            'return_id': 10,
            'product_name': 'Apples',
            'qty': 2.0,
            'unit_price': 10.0,
            'line_total': 20.0,
            'is_active': True,
        }
        mock_repo.get.return_value = old_line
        mock_repo.update.side_effect = lambda id_val, data: {**old_line, **data}
        mock_repo.list.return_value = [{**old_line, 'qty': 5.0, 'line_total': 50.0}]

        updated = service.update(1, {'qty': 5.0})

        assert updated['qty'] == 5.0
        assert updated['line_total'] == 50.0
        assert mock_return_repo.update.called

    def test_delete_line_recalculates_return_total(self, service, mock_repo, mock_return_repo):
        existing_line = {
            'id': 1,
            'return_id': 10,
            'product_name': 'Apples',
            'qty': 2.0,
            'unit_price': 10.0,
            'line_total': 20.0,
            'is_active': True,
        }
        mock_repo.get.return_value = existing_line
        mock_repo.delete.return_value = {'id': 1, 'deleted': True}
        mock_repo.list.return_value = []

        res = service.delete(1)

        assert res['deleted'] is True
        mock_return_repo.update.assert_called_with(10, {'total_amount': 0.0})

    def test_get_by_return_id(self, service, mock_repo):
        lines = [
            {'id': 1, 'return_id': 10, 'line_number': 2, 'product_name': 'Item 2', 'is_active': True},
            {'id': 2, 'return_id': 10, 'line_number': 1, 'product_name': 'Item 1', 'is_active': True},
            {'id': 3, 'return_id': 99, 'line_number': 1, 'product_name': 'Other', 'is_active': True},
        ]
        mock_repo.list.return_value = lines

        result = service.get_by_return_id(10)

        assert len(result) == 2
        assert result[0]['line_number'] == 1
        assert result[1]['line_number'] == 2

    def test_get_by_batch_id(self, service, mock_repo):
        lines = [
            {'id': 1, 'return_id': 10, 'batch_id': 42, 'product_name': 'Item 1', 'is_active': True},
            {'id': 2, 'return_id': 11, 'batch_id': 42, 'product_name': 'Item 2', 'is_active': True},
            {'id': 3, 'return_id': 12, 'batch_id': 99, 'product_name': 'Item 3', 'is_active': True},
        ]
        mock_repo.list.return_value = lines

        result = service.get_by_batch_id(42)

        assert len(result) == 2
        assert all(l['batch_id'] == 42 for l in result)

    def test_bulk_create_lines(self, service, mock_repo, mock_return_repo):
        mock_return_repo.get.return_value = {'id': 10, 'total_amount': 0.0}
        mock_repo.list.return_value = []
        mock_repo.create.side_effect = lambda data: {'id': 1, **data}

        lines_to_create = [
            {'product_name': 'Item 1', 'qty': 2.0, 'unit_price': 15.0},
            {'product_name': 'Item 2', 'qty': 3.0, 'unit_price': 10.0},
        ]

        created = service.bulk_create(return_id=10, lines=lines_to_create)

        assert len(created) == 2
        assert created[0]['line_number'] == 1
        assert created[0]['line_total'] == 30.0
        assert created[1]['line_number'] == 2
        assert created[1]['line_total'] == 30.0

    def test_add_and_get_and_delete_line_photos(self, service, mock_repo):
        line = {
            'id': 1,
            'return_id': 10,
            'product_name': 'Item 1',
            'photos': [],
        }
        mock_repo.get.return_value = line
        mock_repo.update.side_effect = lambda id_val, data: {**line, **data}

        # Add photo
        photo_payload = {
            'filename': 'damage1.jpg',
            'url': 'https://s3.example.com/damage1.jpg',
            'description': 'Torn carton packaging',
        }
        added = service.add_photo(1, photo_payload, user_id=42)

        assert added['filename'] == 'damage1.jpg'
        assert added['uploaded_by'] == 42
        assert added['id'].startswith('att_')

        # Get photos
        line['photos'] = [added]
        photos = service.get_photos(1)
        assert len(photos) == 1
        assert photos[0]['filename'] == 'damage1.jpg'

        # Delete photo
        res = service.delete_photo(1, added['id'])
        assert res['success'] is True
        assert res['remaining_photos'] == 0

    def test_update_quarantine_status_with_batch_sync(self, service, mock_repo, mock_batch_repo):
        line = {
            'id': 1,
            'return_id': 10,
            'batch_id': 77,
            'quarantine_status': 'Quarantine',
        }
        mock_repo.get.return_value = line
        mock_repo.update.return_value = {**line, 'quarantine_status': 'Released'}

        updated = service.update_quarantine_status(1, quarantine_status='Released', sync_batch=True)

        assert updated['quarantine_status'] == 'Released'
        mock_batch_repo.update.assert_called_with(77, {'status': 'Released'})


class TestT0082IControllerEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'username': 'testuser', 'business_id': 1, 'role': 'Admin', 'permissions': ['*']}
        return TestClient(app)

    def test_get_lines_by_return_endpoint(self, client):
        mock_lines = [
            {'id': 1, 'return_id': 5, 'product_name': 'Item A', 'qty': 2.0, 'unit_price': 10.0, 'line_total': 20.0, 'is_active': True},
        ]
        with patch.object(controller_service, 'get_by_return_id', return_value=mock_lines):
            response = client.get('/api/T0082I/by-return/5')
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['product_name'] == 'Item A'

    def test_get_lines_by_batch_endpoint(self, client):
        mock_lines = [
            {'id': 1, 'return_id': 5, 'batch_id': 42, 'product_name': 'Item A', 'is_active': True},
        ]
        with patch.object(controller_service, 'get_by_batch_id', return_value=mock_lines):
            response = client.get('/api/T0082I/by-batch/42')
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['batch_id'] == 42

    def test_bulk_create_endpoint(self, client):
        mock_created = [
            {'id': 1, 'return_id': 5, 'product_name': 'Item 1', 'qty': 2.0, 'unit_price': 10.0, 'line_total': 20.0},
            {'id': 2, 'return_id': 5, 'product_name': 'Item 2', 'qty': 3.0, 'unit_price': 15.0, 'line_total': 45.0},
        ]
        with patch.object(controller_service, 'bulk_create', return_value=mock_created):
            response = client.post('/api/T0082I/bulk', json={
                'return_id': 5,
                'lines': [
                    {'product_name': 'Item 1', 'qty': 2.0, 'unit_price': 10.0},
                    {'product_name': 'Item 2', 'qty': 3.0, 'unit_price': 15.0},
                ],
            })
            assert response.status_code == 201
            data = response.json()
            assert len(data) == 2

    def test_upload_photo_endpoint(self, client):
        mock_photo = {
            'id': 'att_123',
            'filename': 'damage.jpg',
            'url': 'https://example.com/damage.jpg',
            'uploaded_by': 1,
            'line_id': 1,
        }
        with patch.object(controller_service, 'add_photo', return_value=mock_photo):
            response = client.post('/api/T0082I/1/photos', json={
                'filename': 'damage.jpg',
                'url': 'https://example.com/damage.jpg',
            })
            assert response.status_code == 201
            data = response.json()
            assert data['filename'] == 'damage.jpg'

    def test_get_photos_endpoint(self, client):
        mock_photos = [{'id': 'att_123', 'filename': 'damage.jpg'}]
        with patch.object(controller_service, 'get_photos', return_value=mock_photos):
            response = client.get('/api/T0082I/1/photos')
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

    def test_delete_photo_endpoint(self, client):
        with patch.object(controller_service, 'delete_photo', return_value={'success': True, 'photo_id': 'att_123'}):
            response = client.delete('/api/T0082I/1/photos/att_123')
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_update_quarantine_status_endpoint(self, client):
        mock_updated = {'id': 1, 'quarantine_status': 'Scrapped'}
        with patch.object(controller_service, 'update_quarantine_status', return_value=mock_updated):
            response = client.put('/api/T0082I/1/quarantine-status', json={
                'quarantine_status': 'Scrapped',
                'sync_batch': True,
            })
            assert response.status_code == 200
            data = response.json()
            assert data['quarantine_status'] == 'Scrapped'
