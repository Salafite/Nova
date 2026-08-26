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

    def test_pagination_response_headers_first_page(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 1, 'name': 'Item 1'}]
        mock_service.count.return_value = 150

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
            resp = client.get('/api/test-items/?limit=50&offset=0&order_by=name', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '150'
            assert resp.headers.get('X-Page-Limit') == '50'
            assert resp.headers.get('X-Page-Offset') == '0'

            link_header = resp.headers.get('Link')
            assert link_header is not None
            assert 'rel="first"' in link_header
            assert 'rel="next"' in link_header
            assert 'rel="last"' in link_header
            assert 'rel="prev"' not in link_header

            # Verify specific target URLs in Link header
            assert '<http://testserver/api/test-items/?order_by=name&limit=50&offset=0>; rel="first"' in link_header
            assert '<http://testserver/api/test-items/?order_by=name&limit=50&offset=50>; rel="next"' in link_header
            assert '<http://testserver/api/test-items/?order_by=name&limit=50&offset=100>; rel="last"' in link_header

    def test_pagination_response_headers_middle_page(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 51, 'name': 'Item 51'}]
        mock_service.count.return_value = 150

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
            resp = client.get('/api/test-items/?limit=50&offset=50', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '150'
            assert resp.headers.get('X-Page-Limit') == '50'
            assert resp.headers.get('X-Page-Offset') == '50'

            link_header = resp.headers.get('Link')
            assert link_header is not None
            assert '<http://testserver/api/test-items/?limit=50&offset=0>; rel="first"' in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=0>; rel="prev"' in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=100>; rel="next"' in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=100>; rel="last"' in link_header

    def test_pagination_response_headers_last_page(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 101, 'name': 'Item 101'}]
        mock_service.count.return_value = 150

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
            resp = client.get('/api/test-items/?limit=50&offset=100', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '150'
            assert resp.headers.get('X-Page-Limit') == '50'
            assert resp.headers.get('X-Page-Offset') == '100'

            link_header = resp.headers.get('Link')
            assert link_header is not None
            assert 'rel="first"' in link_header
            assert 'rel="prev"' in link_header
            assert 'rel="last"' in link_header
            assert 'rel="next"' not in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=0>; rel="first"' in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=50>; rel="prev"' in link_header
            assert '<http://testserver/api/test-items/?limit=50&offset=100>; rel="last"' in link_header

    def test_pagination_response_headers_single_page(self):
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo
        mock_service.list.return_value = [{'id': 1, 'name': 'Item 1'}]
        mock_service.count.return_value = 25

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
            resp = client.get('/api/test-items/?limit=50&offset=0', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '25'
            assert resp.headers.get('X-Page-Limit') == '50'
            assert resp.headers.get('X-Page-Offset') == '0'

            link_header = resp.headers.get('Link')
            assert link_header is not None
            assert 'rel="first"' in link_header
            assert 'rel="last"' in link_header
            assert 'rel="prev"' not in link_header
            assert 'rel="next"' not in link_header


class TestPaginationDirectHelpers:
    def test_build_pagination_links_direct(self):
        from modules.core.controllers.base import build_pagination_links

        url = "http://localhost:8070/api/T0001I?order_by=sku"
        link_header = build_pagination_links(url, total_count=120, limit=50, offset=50)

        assert '<http://localhost:8070/api/T0001I?order_by=sku&limit=50&offset=0>; rel="first"' in link_header
        assert '<http://localhost:8070/api/T0001I?order_by=sku&limit=50&offset=0>; rel="prev"' in link_header
        assert '<http://localhost:8070/api/T0001I?order_by=sku&limit=50&offset=100>; rel="next"' in link_header
        assert '<http://localhost:8070/api/T0001I?order_by=sku&limit=50&offset=100>; rel="last"' in link_header

    def test_apply_pagination_headers_direct(self):
        from fastapi import Response
        from starlette.datastructures import URL
        from modules.core.controllers.base import apply_pagination_headers

        response = Response()
        request_mock = MagicMock()
        request_mock.url = URL("http://localhost:8070/api/T0010I")

        apply_pagination_headers(response, request_mock, total_count=75, limit=25, offset=25)

        assert response.headers["X-Total-Count"] == "75"
        assert response.headers["X-Page-Limit"] == "25"
        assert response.headers["X-Page-Offset"] == "25"
        assert "rel=\"first\"" in response.headers["Link"]
        assert "rel=\"prev\"" in response.headers["Link"]
        assert "rel=\"next\"" in response.headers["Link"]
        assert "rel=\"last\"" in response.headers["Link"]
