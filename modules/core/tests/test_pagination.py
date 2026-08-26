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


class TestRepositoryPaginationAndSanitization:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_sanitize_order_by_valid_columns(self):
        repo = CrudRepository('t0001', pk='id')

        # Single column neutral / default
        clause = repo._sanitize_order_by('name')
        assert clause == 'ORDER BY "name"'

        # Single column descending prefix with -
        clause = repo._sanitize_order_by('-name')
        assert clause == 'ORDER BY "name" DESC'

        # Single column ascending prefix with +
        clause = repo._sanitize_order_by('+name')
        assert clause == 'ORDER BY "name" ASC'

        # Single column with explicit desc
        clause = repo._sanitize_order_by('price desc')
        assert clause == 'ORDER BY "price" DESC'

        # Multiple columns
        clause = repo._sanitize_order_by('category asc, -created_at')
        assert clause == 'ORDER BY "category" ASC, "created_at" DESC'

    def test_sanitize_order_by_sql_injection_defense(self):
        repo = CrudRepository('t0001', pk='id')

        # Malicious SQL injection attempts with no valid identifier should fall back to safe "id" DESC
        pure_malicious_inputs = [
            'name; DROP TABLE users;--',
            'name UNION SELECT * FROM passwords',
            '1=1',
            'name OR 1=1',
            'id/**/AND/**/1=1',
            '(SELECT 1 FROM secret)',
            'name` --',
            'name; --',
            '; DROP TABLE t0001;',
            'name DESC; DELETE FROM t0001;',
        ]
        for bad_input in pure_malicious_inputs:
            clause = repo._sanitize_order_by(bad_input)
            assert clause == 'ORDER BY "id" DESC', f'Failed to sanitize: {bad_input}'

        # Mixed inputs: invalid/injected parts are safely stripped, valid parts retained
        mixed_clause = repo._sanitize_order_by('name, (SELECT 1 FROM secret)')
        assert mixed_clause == 'ORDER BY "name"'

    def test_sanitize_order_by_with_allowed_columns_whitelist(self):
        repo = CrudRepository('t0001', pk='id')
        allowed = {'name', 'sku', 'price', 'created_at'}

        # Allowed column passes
        assert repo._sanitize_order_by('sku asc', allowed_columns=allowed) == 'ORDER BY "sku" ASC'
        assert repo._sanitize_order_by('-price', allowed_columns=allowed) == 'ORDER BY "price" DESC'

        # Unallowed column is filtered out and defaults to safe id DESC
        assert repo._sanitize_order_by('secret_column', allowed_columns=allowed) == 'ORDER BY "id" DESC'
        assert repo._sanitize_order_by('-secret_column', allowed_columns=allowed) == 'ORDER BY "id" DESC'

    def test_repository_list_query_construction_with_pagination(self):
        repo = CrudRepository('t0001', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [{'id': 1, 'name': 'Item 1'}]

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            items = repo.list(limit=25, offset=50, order_by='name desc')

            assert len(items) == 1
            execute_args = mock_cur.execute.call_args
            query, params = execute_args[0]

            assert 'ORDER BY "name" DESC' in query
            assert 'LIMIT %s' in query
            assert 'OFFSET %s' in query
            assert params[-2:] == [25, 50]

    def test_repository_list_query_capping_max_500(self):
        repo = CrudRepository('t0001', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            # If a caller passes limit > 500 directly to repo.list, it gets capped to 500
            repo.list(limit=1000, offset=0)
            execute_args = mock_cur.execute.call_args
            query, params = execute_args[0]
            assert params[-2] == 500


class TestMultiTenantPaginationIsolation:
    def setup_method(self):
        clear_current_tenant()

    def teardown_method(self):
        clear_current_tenant()

    def test_tenant_filter_applied_to_both_list_and_count(self):
        from modules.core.context import set_current_tenant

        set_current_tenant(42)
        repo = CrudRepository('t0001', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [{'id': 1, 'name': 'Tenant 42 Item', 'business_id': 42}]
        mock_cur.fetchone.return_value = {'cnt': 10}

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            # List query
            items = repo.list(limit=50, offset=0)
            assert len(items) == 1
            list_query, list_params = mock_cur.execute.call_args[0]
            assert '"business_id" = %s' in list_query
            assert 42 in list_params

            # Count query
            count = repo.count()
            assert count == 10
            count_query, count_params = mock_cur.execute.call_args[0]
            assert '"business_id" = %s' in count_query
            assert 42 in count_params

    def test_no_cross_tenant_data_leakage_across_pages(self):
        """Verify that requests from Tenant A and Tenant B remain completely isolated across all pages."""
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0001'
        mock_repo.table_name = 't0001'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo

        # Simulate tenant-scoped service responses
        tenant_1_data = [{'id': i, 'name': f'Tenant 1 Item {i}'} for i in range(1, 101)]
        tenant_2_data = [{'id': i, 'name': f'Tenant 2 Item {i}'} for i in range(1, 31)]

        def mock_list_side_effect(limit=50, offset=0, order_by=None):
            from modules.core.context import get_current_tenant
            active_tenant = get_current_tenant()
            if active_tenant == 101:
                return tenant_1_data[offset:offset + limit]
            elif active_tenant == 202:
                return tenant_2_data[offset:offset + limit]
            return []

        def mock_count_side_effect(where=None, params=None):
            from modules.core.context import get_current_tenant
            active_tenant = get_current_tenant()
            if active_tenant == 101:
                return len(tenant_1_data)
            elif active_tenant == 202:
                return len(tenant_2_data)
            return 0

        mock_service.list.side_effect = mock_list_side_effect
        mock_service.count.side_effect = mock_count_side_effect

        router = create_crud_router(
            prefix='/api/test-items',
            tag='T0001 - Test Items',
            service=mock_service,
            response_model=ItemSchema
        )
        app.include_router(router)
        client = TestClient(app)

        user_tenant_1 = {'id': 1, 'username': 'user1', 'role': 'User', 'permissions': ['*'], 'business_id': 101}
        token_tenant_1 = create_access_token(1, business_id=101)

        user_tenant_2 = {'id': 2, 'username': 'user2', 'role': 'User', 'permissions': ['*'], 'business_id': 202}
        token_tenant_2 = create_access_token(2, business_id=202)

        # Tenant 1 queries page 1 (50 items)
        with patch('packages.auth.deps.get_user_by_id', return_value=user_tenant_1):
            resp1 = client.get('/api/test-items/?limit=50&offset=0', headers={'Authorization': f'Bearer {token_tenant_1}'})
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert len(data1) == 50
            assert data1[0]['name'] == 'Tenant 1 Item 1'
            assert resp1.headers.get('X-Total-Count') == '100'
            assert 'rel="next"' in resp1.headers.get('Link', '')

        # Tenant 1 queries page 2 (next 50 items)
        with patch('packages.auth.deps.get_user_by_id', return_value=user_tenant_1):
            resp2 = client.get('/api/test-items/?limit=50&offset=50', headers={'Authorization': f'Bearer {token_tenant_1}'})
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert len(data2) == 50
            assert data2[0]['name'] == 'Tenant 1 Item 51'
            assert data2[-1]['name'] == 'Tenant 1 Item 100'
            assert resp2.headers.get('X-Total-Count') == '100'
            assert 'rel="prev"' in resp2.headers.get('Link', '')
            assert 'rel="next"' not in resp2.headers.get('Link', '')

        # Tenant 2 queries page 1 (30 items total)
        with patch('packages.auth.deps.get_user_by_id', return_value=user_tenant_2):
            resp3 = client.get('/api/test-items/?limit=50&offset=0', headers={'Authorization': f'Bearer {token_tenant_2}'})
            assert resp3.status_code == 200
            data3 = resp3.json()
            assert len(data3) == 30
            assert data3[0]['name'] == 'Tenant 2 Item 1'
            assert data3[-1]['name'] == 'Tenant 2 Item 30'
            # Zero leakage of Tenant 1 data
            assert not any('Tenant 1' in item['name'] for item in data3)
            assert resp3.headers.get('X-Total-Count') == '30'
            # No next page for Tenant 2 since count <= limit
            assert 'rel="next"' not in resp3.headers.get('Link', '')

    def test_multi_tenant_pagination_stateful_across_all_pages_and_empty_pages(self):
        """Test multi-tenant pagination across page 1, middle page, partial last page, and out-of-bounds offset."""
        app = FastAPI()
        mock_repo = MagicMock(spec=CrudRepository)
        mock_repo.table = 'T0003'
        mock_repo.table_name = 't0003'
        mock_service = MagicMock(spec=CrudService)
        mock_service.repo = mock_repo

        # Shared table contains 125 items for Tenant 100, 35 items for Tenant 200, and 0 for Tenant 300
        tenant_100_items = [{'id': i, 'name': f'Tenant 100 Product {i}', 'business_id': 100} for i in range(1, 126)]
        tenant_200_items = [{'id': i + 500, 'name': f'Tenant 200 Product {i}', 'business_id': 200} for i in range(1, 36)]

        def mock_list(limit=50, offset=0, order_by=None):
            from modules.core.context import get_current_tenant
            active_tenant = get_current_tenant()
            if active_tenant == 100:
                data = list(tenant_100_items)
            elif active_tenant == 200:
                data = list(tenant_200_items)
            else:
                data = []
            if order_by and order_by.startswith('-'):
                data = list(reversed(data))
            return data[offset:offset + limit]

        def mock_count(where=None, params=None):
            from modules.core.context import get_current_tenant
            active_tenant = get_current_tenant()
            if active_tenant == 100:
                return len(tenant_100_items)
            elif active_tenant == 200:
                return len(tenant_200_items)
            return 0

        mock_service.list.side_effect = mock_list
        mock_service.count.side_effect = mock_count

        router = create_crud_router(
            prefix='/api/T0003I',
            tag='T0003 - Products',
            service=mock_service,
            response_model=ItemSchema
        )
        app.include_router(router)
        client = TestClient(app)

        user_100 = {'id': 1, 'username': 't100_admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 100}
        token_100 = create_access_token(1, business_id=100)

        user_200 = {'id': 2, 'username': 't200_admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 200}
        token_200 = create_access_token(2, business_id=200)

        user_300 = {'id': 3, 'username': 't300_admin', 'role': 'Admin', 'permissions': ['*'], 'business_id': 300}
        token_300 = create_access_token(3, business_id=300)

        # --- Tenant 100 Page 1 (offset 0, limit 50) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_100):
            r1 = client.get('/api/T0003I/?limit=50&offset=0', headers={'Authorization': f'Bearer {token_100}'})
            assert r1.status_code == 200
            d1 = r1.json()
            assert len(d1) == 50
            assert d1[0]['name'] == 'Tenant 100 Product 1'
            assert d1[-1]['name'] == 'Tenant 100 Product 50'
            assert r1.headers.get('X-Total-Count') == '125'
            assert r1.headers.get('X-Page-Limit') == '50'
            assert r1.headers.get('X-Page-Offset') == '0'
            assert 'rel="first"' in r1.headers.get('Link', '')
            assert 'rel="next"' in r1.headers.get('Link', '')
            assert 'rel="last"' in r1.headers.get('Link', '')
            assert 'rel="prev"' not in r1.headers.get('Link', '')

        # --- Tenant 100 Page 2 (offset 50, limit 50) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_100):
            r2 = client.get('/api/T0003I/?limit=50&offset=50', headers={'Authorization': f'Bearer {token_100}'})
            assert r2.status_code == 200
            d2 = r2.json()
            assert len(d2) == 50
            assert d2[0]['name'] == 'Tenant 100 Product 51'
            assert d2[-1]['name'] == 'Tenant 100 Product 100'
            assert r2.headers.get('X-Total-Count') == '125'
            assert 'rel="prev"' in r2.headers.get('Link', '')
            assert 'rel="next"' in r2.headers.get('Link', '')

        # --- Tenant 100 Page 3 (offset 100, limit 50, partial page of 25 items) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_100):
            r3 = client.get('/api/T0003I/?limit=50&offset=100', headers={'Authorization': f'Bearer {token_100}'})
            assert r3.status_code == 200
            d3 = r3.json()
            assert len(d3) == 25
            assert d3[0]['name'] == 'Tenant 100 Product 101'
            assert d3[-1]['name'] == 'Tenant 100 Product 125'
            assert r3.headers.get('X-Total-Count') == '125'
            assert 'rel="prev"' in r3.headers.get('Link', '')
            assert 'rel="next"' not in r3.headers.get('Link', '')

        # --- Tenant 100 Page 4 (offset 150 > total 125, should be empty, zero leak from Tenant 200) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_100):
            r4 = client.get('/api/T0003I/?limit=50&offset=150', headers={'Authorization': f'Bearer {token_100}'})
            assert r4.status_code == 200
            d4 = r4.json()
            assert len(d4) == 0
            assert r4.headers.get('X-Total-Count') == '125'
            assert 'rel="next"' not in r4.headers.get('Link', '')

        # --- Tenant 200 Page 1 (offset 0, limit 20) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_200):
            r200_1 = client.get('/api/T0003I/?limit=20&offset=0', headers={'Authorization': f'Bearer {token_200}'})
            assert r200_1.status_code == 200
            d200_1 = r200_1.json()
            assert len(d200_1) == 20
            assert d200_1[0]['name'] == 'Tenant 200 Product 1'
            assert r200_1.headers.get('X-Total-Count') == '35'
            assert 'rel="next"' in r200_1.headers.get('Link', '')

        # --- Tenant 200 Page 2 (offset 20, limit 20 -> 15 remaining) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_200):
            r200_2 = client.get('/api/T0003I/?limit=20&offset=20', headers={'Authorization': f'Bearer {token_200}'})
            assert r200_2.status_code == 200
            d200_2 = r200_2.json()
            assert len(d200_2) == 15
            assert d200_2[0]['name'] == 'Tenant 200 Product 21'
            assert d200_2[-1]['name'] == 'Tenant 200 Product 35'
            assert r200_2.headers.get('X-Total-Count') == '35'
            assert 'rel="next"' not in r200_2.headers.get('Link', '')

        # --- Tenant 300 (Empty Tenant) ---
        with patch('packages.auth.deps.get_user_by_id', return_value=user_300):
            r300 = client.get('/api/T0003I/?limit=50&offset=0', headers={'Authorization': f'Bearer {token_300}'})
            assert r300.status_code == 200
            d300 = r300.json()
            assert len(d300) == 0
            assert r300.headers.get('X-Total-Count') == '0'
            assert 'rel="next"' not in r300.headers.get('Link', '')

    def test_multi_tenant_pagination_sorting_isolation(self):
        """Verify sorting order under tenant context does not leak other tenants' data."""
        repo = CrudRepository('t0003', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [{'id': 5, 'name': 'Item E', 'business_id': 77}]

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            # With tenant context 77 and order_by '-name'
            from modules.core.context import tenant_context
            with tenant_context(77):
                repo.list(order_by='-name', limit=20, offset=0)

            query, params = mock_cur.execute.call_args[0]
            assert '"business_id" = %s' in query
            assert 'ORDER BY "name" DESC' in query
            assert 'LIMIT %s' in query
            assert 'OFFSET %s' in query
            assert params == [77, 20, 0]

    def test_multi_tenant_pagination_sql_injection_defense(self):
        """Verify that malicious order_by strings cannot inject SQL or bypass business_id scoping."""
        repo = CrudRepository('t0003', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            from modules.core.context import tenant_context
            with tenant_context(88):
                # Malicious SQL injection in order_by
                repo.list(order_by='name; DELETE FROM t0003; --', limit=25, offset=10)

            query, params = mock_cur.execute.call_args[0]
            # Must retain business_id filter
            assert '"business_id" = %s' in query
            assert 88 in params
            # Order by safely fell back to safe pk desc
            assert 'ORDER BY "id" DESC' in query
            assert params == [88, 25, 10]

    def test_non_tenant_table_pagination_exempt_from_tenant_scoping(self):
        """Verify that non-tenant tables (e.g. t0059) paginate without business_id filtering even when tenant is active."""
        repo = CrudRepository('t0059', pk='id')
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [{'id': 1, 'tenant_name': 'Tenant 1'}]
        mock_cur.fetchone.return_value = {'cnt': 5}

        with patch('modules.core.repositories.base.get_connection', return_value=mock_conn), \
             patch('modules.core.repositories.base.release_connection'):
            from modules.core.context import tenant_context
            with tenant_context(999):
                items = repo.list(limit=10, offset=0)
                count = repo.count()

            # Query must not contain business_id for T0059
            list_query, list_params = mock_cur.execute.call_args_list[0][0]
            assert '"business_id"' not in list_query
            assert 999 not in list_params
            assert list_params == [10, 0]

            count_query, count_params = mock_cur.execute.call_args_list[1][0]
            assert '"business_id"' not in count_query
            assert 999 not in count_params
            assert count == 5



