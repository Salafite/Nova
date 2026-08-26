from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.context import clear_current_tenant
from packages.auth.jwt import create_access_token


class ItemSchema(BaseModel):
    id: int
    name: str


class TestPaginationQueryParams:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_default_pagination_params(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 1, 'name': 'Item 1'}]

        router = create_crud_router(
            prefix='/api/test-items',
            tag='T0001 - Test Items',
            service=mock_service,
            response_model=ItemSchema
        )
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 10}
        token = create_access_token(1, business_id=10)

        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get('/api/test-items/', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.json() == [{'id': 1, 'name': 'Item 1'}]
            mock_service.list.assert_called_once_with(limit=50, offset=0, order_by=None)

    def test_custom_limit_and_offset_params(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 2, 'name': 'Item 2'}]

        router = create_crud_router(
            prefix='/api/test-items',
            tag='T0001 - Test Items',
            service=mock_service,
            response_model=ItemSchema
        )
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 10}
        token = create_access_token(1, business_id=10)

        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get('/api/test-items/?limit=25&offset=50&order_by=name', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            mock_service.list.assert_called_once_with(limit=25, offset=50, order_by='name')

    def test_limit_capping_max_500_or_validation(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = []

        router = create_crud_router(
            prefix='/api/test-items',
            tag='T0001 - Test Items',
            service=mock_service,
            response_model=ItemSchema
        )
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 10}
        token = create_access_token(1, business_id=10)

        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            # Limit > 500 is rejected with 422 Unprocessable Entity by FastAPI Query validation (le=500)
            resp = client.get('/api/test-items/?limit=1000', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 422

            # Limit < 1 is rejected with 422 Unprocessable Entity by FastAPI Query validation (ge=1)
            resp_negative = client.get('/api/test-items/?limit=0', headers={'Authorization': f'Bearer {token}'})
            assert resp_negative.status_code == 422

            # Limit = 500 is allowed
            resp_500 = client.get('/api/test-items/?limit=500', headers={'Authorization': f'Bearer {token}'})
            assert resp_500.status_code == 200
            mock_service.list.assert_called_with(limit=500, offset=0, order_by=None)
