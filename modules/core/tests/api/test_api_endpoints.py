import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-32-bytes-long!!')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'nova_erp_test')
os.environ.setdefault('DB_USER', 'test')
os.environ.setdefault('DB_PASSWORD', 'test')
os.environ.setdefault('DB_SCHEMA', 'Nova')
os.environ.setdefault('ACCESS_TOKEN_EXPIRE_MINUTES', '1440')
os.environ.setdefault('REFRESH_TOKEN_EXPIRE_DAYS', '7')
os.environ.setdefault('ALLOWED_ORIGINS', '*')

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

test_app = FastAPI(title='Nova ERP API Test', version='1.0')


@test_app.get('/api')
def root():
    return {'message': 'Welcome to Nova ERP API'}


@test_app.get('/api/health')
def health_check():
    return {'status': 'ok', 'app': 'Nova App'}


@test_app.get('/api/auth/me')
def protected_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    from packages.auth.jwt import decode_token
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')
    return {'user_id': int(payload['sub']), 'type': payload['type']}


client = TestClient(test_app)


class TestHealth:
    def test_root_endpoint(self):
        resp = client.get('/api')
        assert resp.status_code == 200
        data = resp.json()
        assert data['message'] == 'Welcome to Nova ERP API'

    def test_health_check(self):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        assert data['app'] == 'Nova App'


class TestAuthProtection:
    def test_no_auth_header_returns_401(self):
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        resp = client.get('/api/auth/me', headers={'Authorization': 'Bearer invalidtoken'})
        assert resp.status_code == 401

    def test_valid_token_returns_user(self):
        from packages.auth.jwt import create_access_token
        token = create_access_token(42)
        resp = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['user_id'] == 42


from packages.auth.deps import require_permission
from unittest.mock import patch

@test_app.get('/api/test-admin-only', dependencies=[Depends(require_permission('ADMIN_VIEW'))])
def admin_only_endpoint():
    return {'status': 'admin_ok'}

@test_app.get('/api/test-sales-only', dependencies=[Depends(require_permission('SALES_VIEW'))])
def sales_only_endpoint():
    return {'status': 'sales_ok'}


class TestRBACRouteProtection:
    def test_unauthorized_role_returns_403(self):
        from packages.auth.jwt import create_access_token
        token = create_access_token(99)
        user = {'id': 99, 'username': 'rep', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW']}
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get('/api/test-admin-only', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 403
            assert 'Permission denied: ADMIN_VIEW required' in resp.json()['detail']

    def test_authorized_role_returns_200(self):
        from packages.auth.jwt import create_access_token
        token = create_access_token(99)
        user = {'id': 99, 'username': 'rep', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW']}
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get('/api/test-sales-only', headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200
            assert resp.json()['status'] == 'sales_ok'

    def test_admin_wildcard_returns_200(self):
        from packages.auth.jwt import create_access_token
        token = create_access_token(1)
        admin_user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}
        with patch('packages.auth.deps.get_user_by_id', return_value=admin_user):
            resp1 = client.get('/api/test-admin-only', headers={'Authorization': f'Bearer {token}'})
            assert resp1.status_code == 200
            assert resp1.json()['status'] == 'admin_ok'

            resp2 = client.get('/api/test-sales-only', headers={'Authorization': f'Bearer {token}'})
            assert resp2.status_code == 200
            assert resp2.json()['status'] == 'sales_ok'

