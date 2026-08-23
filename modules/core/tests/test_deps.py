from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import pytest


class TestGetCurrentUser:
    def test_returns_user_on_valid_token(self, valid_token, sample_user):
        from packages.auth.deps import get_current_user
        creds = MagicMock()
        creds.credentials = valid_token
        with patch('packages.auth.deps.get_user_by_id', return_value=sample_user):
            user = get_current_user(creds)
        assert user['id'] == 1
        assert user['username'] == 'testuser'

    def test_raises_on_invalid_token(self):
        from packages.auth.deps import get_current_user
        creds = MagicMock()
        creds.credentials = 'invalid.token.here'
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds)
        assert exc.value.status_code == 401

    def test_raises_on_user_not_found(self, valid_token):
        from packages.auth.deps import get_current_user
        creds = MagicMock()
        creds.credentials = valid_token
        with patch('packages.auth.deps.get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc:
                get_current_user(creds)
            assert exc.value.status_code == 401

    def test_raises_on_refresh_token_used_as_access(self, valid_refresh_token):
        from packages.auth.deps import get_current_user
        creds = MagicMock()
        creds.credentials = valid_refresh_token
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds)
        assert exc.value.status_code == 401
        assert 'Invalid token type' in str(exc.value.detail)

    def test_populates_tenant_context_from_token(self, sample_user):
        from packages.auth.deps import get_current_user
        from packages.auth.jwt import create_access_token
        from modules.core.context import get_current_tenant, clear_current_tenant

        clear_current_tenant()
        assert get_current_tenant() is None

        token = create_access_token(1, business_id=42)
        creds = MagicMock()
        creds.credentials = token
        with patch('packages.auth.deps.get_user_by_id', return_value=sample_user):
            user = get_current_user(creds)
            assert user['id'] == 1
            assert get_current_tenant() == 42
        clear_current_tenant()

    def test_populates_tenant_context_from_user_dict_fallback(self):
        from packages.auth.deps import get_current_user
        from packages.auth.jwt import create_access_token
        from modules.core.context import get_current_tenant, clear_current_tenant

        clear_current_tenant()
        assert get_current_tenant() is None

        token = create_access_token(1)  # token without business_id
        user_with_tenant = {
            'id': 1,
            'username': 'tenantuser',
            'role': 'Admin',
            'business_id': 77,
        }
        creds = MagicMock()
        creds.credentials = token
        with patch('packages.auth.deps.get_user_by_id', return_value=user_with_tenant):
            user = get_current_user(creds)
            assert user['id'] == 1
            assert get_current_tenant() == 77
        clear_current_tenant()


class TestRequirePermission:
    def test_admin_wildcard_permission_allowed(self, sample_user):
        from packages.auth.deps import require_permission
        checker = require_permission('FINANCE_VIEW')
        result = checker(user=sample_user)
        assert result == sample_user

    def test_user_with_specific_permission_allowed(self):
        from packages.auth.deps import require_permission
        checker = require_permission('SALES_VIEW')
        user = {'id': 2, 'username': 'rep', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW']}
        result = checker(user=user)
        assert result == user

    def test_user_derived_role_permission_allowed(self):
        from packages.auth.deps import require_permission
        checker = require_permission('PRODUCTS_VIEW')
        user = {'id': 3, 'username': 'viewer', 'role': 'Viewer', 'permissions': None}
        result = checker(user=user)
        assert result == user

    def test_user_without_permission_raises_403(self):
        from packages.auth.deps import require_permission
        checker = require_permission('FINANCE_VIEW')
        user = {'id': 4, 'username': 'salesrep', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW', 'PRODUCTS_VIEW']}
        with pytest.raises(HTTPException) as exc:
            checker(user=user)
        assert exc.value.status_code == 403
        assert 'FINANCE_VIEW' in str(exc.value.detail)

    def test_user_derived_role_without_permission_raises_403(self):
        from packages.auth.deps import require_permission
        checker = require_permission('HR_VIEW')
        user = {'id': 5, 'username': 'salesrep', 'role': 'Sales Rep', 'permissions': None}
        with pytest.raises(HTTPException) as exc:
            checker(user=user)
        assert exc.value.status_code == 403
        assert 'HR_VIEW' in str(exc.value.detail)

    def test_user_with_string_permission_allowed(self):
        from packages.auth.deps import require_permission
        checker = require_permission('SALES_VIEW')
        user = {'id': 6, 'username': 'string_user', 'role': 'Custom', 'permissions': 'SALES_VIEW'}
        result = checker(user=user)
        assert result == user

    def test_user_with_tuple_permission_allowed(self):
        from packages.auth.deps import require_permission
        checker = require_permission('POS_VIEW')
        user = {'id': 7, 'username': 'tuple_user', 'role': 'Custom', 'permissions': ('POS_VIEW', 'DASHBOARD_VIEW')}
        result = checker(user=user)
        assert result == user

    def test_cashier_role_permissions(self):
        from packages.auth.deps import require_permission
        pos_checker = require_permission('POS_VIEW')
        purchasing_checker = require_permission('PURCHASING_VIEW')
        cashier_user = {'id': 8, 'username': 'cashier1', 'role': 'Cashier', 'permissions': None}

        # POS_VIEW is granted to Cashier
        assert pos_checker(user=cashier_user) == cashier_user

        # PURCHASING_VIEW is NOT granted to Cashier
        with pytest.raises(HTTPException) as exc:
            purchasing_checker(user=cashier_user)
        assert exc.value.status_code == 403
        assert 'PURCHASING_VIEW' in str(exc.value.detail)

    def test_admin_with_empty_permissions_granted_access(self):
        from packages.auth.deps import require_permission
        checker = require_permission('ADMIN_VIEW')
        admin_user = {'id': 9, 'username': 'admin_empty', 'role': 'Admin', 'permissions': []}
        assert checker(user=admin_user) == admin_user


class TestAuthMeEndpoint:
    def test_me_endpoint_returns_derived_permissions_for_sales_rep(self):
        from packages.auth.controller import me_endpoint
        user = {
            'id': 10,
            'username': 'rep_user',
            'full_name': 'Sales User',
            'email': 'sales@example.com',
            'role': 'Sales Rep',
            'permissions': None,
            'business_id': 1,
        }
        res = me_endpoint(user=user)
        assert res['id'] == 10
        assert res['role'] == 'Sales Rep'
        assert 'SALES_VIEW' in res['permissions']
        assert 'DASHBOARD_VIEW' in res['permissions']
        assert 'HR_VIEW' not in res['permissions']

    def test_me_endpoint_returns_wildcard_for_admin(self):
        from packages.auth.controller import me_endpoint
        user = {
            'id': 1,
            'username': 'admin_user',
            'full_name': 'Admin User',
            'email': 'admin@example.com',
            'role': 'Admin',
            'permissions': [],
            'business_id': 1,
        }
        res = me_endpoint(user=user)
        assert res['permissions'] == ['*']

    def test_me_endpoint_preserves_explicit_custom_permissions(self):
        from packages.auth.controller import me_endpoint
        user = {
            'id': 20,
            'username': 'custom_user',
            'full_name': 'Custom User',
            'email': 'custom@example.com',
            'role': 'Viewer',
            'permissions': ['CUSTOM_VIEW'],
            'business_id': 1,
        }
        res = me_endpoint(user=user)
        assert res['permissions'] == ['CUSTOM_VIEW']

    def test_api_v1_and_api_auth_me_routes_exist_on_app(self):
        from fastapi.testclient import TestClient
        from apps.api.main import app
        from packages.auth.jwt import create_access_token

        client = TestClient(app)
        user_mock = {
            'id': 50,
            'username': 'manager_user',
            'full_name': 'Manager User',
            'email': 'mgr@example.com',
            'role': 'Manager',
            'permissions': None,
            'business_id': 1,
        }
        token = create_access_token(50)
        headers = {'Authorization': f'Bearer {token}'}

        with patch('packages.auth.deps.get_user_by_id', return_value=user_mock):
            # Test /api/auth/me
            resp1 = client.get('/api/auth/me', headers=headers)
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1['role'] == 'Manager'
            assert 'FINANCE_VIEW' in data1['permissions']
            assert 'HR_VIEW' in data1['permissions']

            # Test /api/v1/auth/me
            resp2 = client.get('/api/v1/auth/me', headers=headers)
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2['role'] == 'Manager'
            assert 'FINANCE_VIEW' in data2['permissions']
            assert 'HR_VIEW' in data2['permissions']


