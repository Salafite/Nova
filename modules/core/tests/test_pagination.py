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


class TestPaginationCORSHeaders:
    def test_cors_exposed_headers_configured_in_main_app(self):
        from apps.api.main import app
        client = TestClient(app)

        # Send request with Origin header to trigger CORS middleware response headers
        resp = client.get('/api/health', headers={'Origin': 'http://localhost:5173'})
        assert resp.status_code == 200

        expose_headers = resp.headers.get('access-control-expose-headers', '')
        # Check all pagination headers are exposed to frontend
        assert 'X-Total-Count' in expose_headers or 'x-total-count' in expose_headers.lower()
        assert 'X-Page-Limit' in expose_headers or 'x-page-limit' in expose_headers.lower()
        assert 'X-Page-Offset' in expose_headers or 'x-page-offset' in expose_headers.lower()
        assert 'Link' in expose_headers or 'link' in expose_headers.lower()


class TestCustomTCodeControllerPagination:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_t0025i_settings_pagination(self):
        from modules.administration.controllers.T0025I import router, service

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['ADMIN_VIEW', '*'], 'business_id': 1}
        token = create_access_token(1, business_id=1)

        with patch('packages.auth.deps.get_user_by_id', return_value=user), \
             patch.object(service, 'list_by_group', return_value=[{'id': 1, 'setting_key': 'site_name', 'setting_value': 'Nova', 'description': 'Site', 'setting_group': 'General', 'is_active': True}]) as mock_list, \
             patch.object(service, 'count', return_value=75):
            resp = client.get('/api/T0025I/?limit=20&offset=40&order_by=setting_key', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '75'
            assert resp.headers.get('X-Page-Limit') == '20'
            assert resp.headers.get('X-Page-Offset') == '40'
            assert 'Link' in resp.headers
            assert 'rel="first"' in resp.headers['Link']
            assert 'rel="prev"' in resp.headers['Link']
            assert 'rel="next"' in resp.headers['Link']
            assert 'rel="last"' in resp.headers['Link']
            mock_list.assert_called_once_with(group=None, limit=20, offset=40, order_by='setting_key')

    def test_t0100i_module_registry_pagination(self):
        from modules.administration.controllers.T0100I import router, service

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['ADMIN_VIEW', '*'], 'business_id': 1}
        token = create_access_token(1, business_id=1)

        with patch('packages.auth.deps.get_user_by_id', return_value=user), \
             patch.object(service, 'list', return_value=[{'id': 1, 'module_key': 'crm', 'name': 'CRM', 'name_ar': None, 'description': None, 'description_ar': None, 'version': '1.0', 'author': None, 'icon': None, 'category': None, 'is_core': True, 'is_active': True, 'installed_at': None, 'dependencies': None}]) as mock_list, \
             patch.object(service, 'count', return_value=120):
            resp = client.get('/api/T0100I/?limit=10&offset=20&order_by=module_key', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '120'
            assert resp.headers.get('X-Page-Limit') == '10'
            assert resp.headers.get('X-Page-Offset') == '20'
            assert 'rel="first"' in resp.headers.get('Link', '')
            assert 'rel="prev"' in resp.headers.get('Link', '')
            assert 'rel="next"' in resp.headers.get('Link', '')
            assert 'rel="last"' in resp.headers.get('Link', '')
            mock_list.assert_called_once_with(limit=10, offset=20, order_by='module_key')

    def test_t0024i_categories_pagination(self):
        from modules.inventory.controllers.T0024I import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['PRODUCTS_VIEW', '*'], 'business_id': 1}
        token = create_access_token(1, business_id=1)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = (35,)
        mock_cur.fetchall.return_value = [('Beverages',), ('Snacks',)]

        with patch('packages.auth.deps.get_user_by_id', return_value=user), \
             patch('modules.inventory.controllers.T0024I.get_connection', return_value=mock_conn), \
             patch('modules.inventory.controllers.T0024I.release_connection'):
            resp = client.get('/api/categories/?limit=25&offset=0&order_by=name', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.json() == [{'name': 'Beverages'}, {'name': 'Snacks'}]
            assert resp.headers.get('X-Total-Count') == '35'
            assert resp.headers.get('X-Page-Limit') == '25'
            assert resp.headers.get('X-Page-Offset') == '0'
            assert 'rel="next"' in resp.headers.get('Link', '')

    def test_t0010i_customer_sub_endpoints_pagination(self):
        from modules.crm.controllers.T0010I import router, repo

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 1}
        token = create_access_token(1, business_id=1)

        with patch('packages.auth.deps.get_user_by_id', return_value=user), \
             patch.object(repo, 'get', return_value={'id': 5, 'name': 'Acme Corp'}), \
             patch('modules.crm.controllers.T0010I.CrudRepository') as mock_crud_cls:
            mock_pay_repo = MagicMock()
            mock_pay_repo.list.return_value = [{'id': 1, 'amount': 100.0}]
            mock_pay_repo.count.return_value = 45
            mock_crud_cls.return_value = mock_pay_repo

            resp = client.get('/api/T0010I/5/payments?limit=15&offset=0', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.headers.get('X-Total-Count') == '45'
            assert resp.headers.get('X-Page-Limit') == '15'
            assert resp.headers.get('X-Page-Offset') == '0'
            assert 'rel="next"' in resp.headers.get('Link', '')


