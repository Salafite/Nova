import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.auth.jwt import create_access_token
from modules.core.services.permission_service import T_CODE_PERMISSIONS, get_required_permission, derive_permissions

client = TestClient(app)


def _make_user_header(user_id: int, role: str, permissions=None):
    """Helper to generate JWT header and user dictionary for testing."""
    token = create_access_token(user_id)
    user_dict = {
        'id': user_id,
        'username': f'user_{role.lower().replace(" ", "_")}_{user_id}',
        'full_name': f'Test {role}',
        'email': f'{role.lower().replace(" ", "_")}@example.com',
        'role': role,
        'permissions': permissions,
        'status': 'Active',
        'business_id': 1,
    }
    return {'Authorization': f'Bearer {token}'}, user_dict


class TestTCodeRBACEnforcement:
    """Test HTTP 403 Forbidden vs HTTP 200 OK across T-code controllers for different roles."""

    @pytest.mark.parametrize("endpoint,expected_perm", [
        ("/api/T0012I/", "SALES_VIEW"),
        ("/api/T0001I/", "PRODUCTS_VIEW"),
        ("/api/T0010I/", "CRM_VIEW"),
        ("/api/T0009I/", "INVENTORY_VIEW"),
    ])
    def test_sales_rep_authorized_endpoints(self, endpoint, expected_perm):
        headers, user = _make_user_header(101, 'Sales Rep')
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == 200, f"Expected 200 for Sales Rep on {endpoint}, got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("endpoint,expected_perm", [
        ("/api/T0038I/", "HR_VIEW"),        # Payroll Entries
        ("/api/T0030I/", "HR_VIEW"),        # Employees
        ("/api/T0026I/", "FINANCE_VIEW"),   # Chart of Accounts
        ("/api/T0027I/", "FINANCE_VIEW"),   # Journal Entries
        ("/api/T0021I/", "ADMIN_VIEW"),     # System Users
        ("/api/T0018I/", "MFG_VIEW"),       # Manufacturing Orders
        ("/api/T0044I/", "PROJECTS_VIEW"),  # Projects
        ("/api/T0041I/", "MAINTENANCE_VIEW"), # Assets
        ("/api/T0052I/", "BI_VIEW"),        # KPI Definitions
    ])
    def test_sales_rep_forbidden_endpoints(self, endpoint, expected_perm):
        headers, user = _make_user_header(102, 'Sales Rep')
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == 403
            assert f"Permission denied: {expected_perm} required" in resp.json().get('detail', '')

    @pytest.mark.parametrize("endpoint,expected_status", [
        ("/api/T0012I/", 200),  # Sales Orders (SALES_VIEW) - allowed
        ("/api/T0003I/", 200),  # Products (PRODUCTS_VIEW) - allowed
        ("/api/T0010I/", 200),  # Customers (CRM_VIEW) - allowed
        ("/api/T0038I/", 403),  # Payroll (HR_VIEW) - forbidden
        ("/api/T0014I/", 403),  # Purchase Orders (PURCHASING_VIEW) - forbidden
        ("/api/T0026I/", 403),  # Finance (FINANCE_VIEW) - forbidden
        ("/api/T0021I/", 403),  # Admin (ADMIN_VIEW) - forbidden
    ])
    def test_cashier_access_matrix(self, endpoint, expected_status):
        headers, user = _make_user_header(201, 'Cashier')
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == expected_status

    @pytest.mark.parametrize("endpoint,expected_status", [
        ("/api/T0012I/", 200),  # Sales Orders (SALES_VIEW) - allowed
        ("/api/T0014I/", 200),  # Purchase Orders (PURCHASING_VIEW) - allowed
        ("/api/T0026I/", 200),  # Finance (FINANCE_VIEW) - allowed
        ("/api/T0038I/", 200),  # HR (HR_VIEW) - allowed
        ("/api/T0018I/", 200),  # Manufacturing (MFG_VIEW) - allowed
        ("/api/T0044I/", 200),  # Projects (PROJECTS_VIEW) - allowed
        ("/api/T0052I/", 200),  # BI (BI_VIEW) - allowed
        ("/api/T0021I/", 403),  # Admin Users (ADMIN_VIEW) - forbidden
        ("/api/T0022I/", 403),  # Nav Permissions (ADMIN_VIEW) - forbidden
        ("/api/T0023I/", 403),  # Audit Log (ADMIN_VIEW) - forbidden
        ("/api/T0025I/", 403),  # Global Settings (ADMIN_VIEW) - forbidden
    ])
    def test_manager_access_matrix(self, endpoint, expected_status):
        headers, user = _make_user_header(301, 'Manager')
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == expected_status

    @pytest.mark.parametrize("endpoint,expected_status", [
        ("/api/T0001I/", 200),  # Products (PRODUCTS_VIEW) - allowed
        ("/api/T0003I/", 200),  # Products (PRODUCTS_VIEW) - allowed
        ("/api/T0010I/", 200),  # Customers (CRM_VIEW) - allowed
        ("/api/T0012I/", 403),  # Sales Orders (SALES_VIEW) - forbidden
        ("/api/T0014I/", 403),  # Purchase Orders (PURCHASING_VIEW) - forbidden
        ("/api/T0026I/", 403),  # Finance (FINANCE_VIEW) - forbidden
        ("/api/T0038I/", 403),  # HR (HR_VIEW) - forbidden
        ("/api/T0021I/", 403),  # Admin (ADMIN_VIEW) - forbidden
    ])
    def test_viewer_access_matrix(self, endpoint, expected_status):
        headers, user = _make_user_header(401, 'Viewer')
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == expected_status

    @pytest.mark.parametrize("endpoint", [
        "/api/T0001I/",
        "/api/T0012I/",
        "/api/T0014I/",
        "/api/T0018I/",
        "/api/T0021I/",
        "/api/T0026I/",
        "/api/T0038I/",
        "/api/T0041I/",
        "/api/T0044I/",
        "/api/T0052I/",
    ])
    def test_admin_wildcard_access_all_endpoints(self, endpoint):
        headers, user = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user):
            resp = client.get(endpoint, headers=headers)
            assert resp.status_code == 200


class TestCustomRoutersRBAC:
    """Test RBAC on custom non-CRUD routers."""

    def test_bi_dashboard_summary_allowed_for_manager_and_admin(self):
        # Manager
        headers_mgr, user_mgr = _make_user_header(302, 'Manager')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_mgr):
            with patch('modules.bi.controllers.dashboard.get_dashboard_summary', return_value={'kpi': 100}):
                resp = client.get('/api/bi/dashboard/summary', headers=headers_mgr)
                assert resp.status_code == 200

        # Admin
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            with patch('modules.bi.controllers.dashboard.get_dashboard_summary', return_value={'kpi': 100}):
                resp = client.get('/api/bi/dashboard/summary', headers=headers_adm)
                assert resp.status_code == 200

    def test_bi_dashboard_summary_forbidden_for_sales_rep_and_viewer(self):
        # Sales Rep
        headers_rep, user_rep = _make_user_header(103, 'Sales Rep')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_rep):
            resp = client.get('/api/bi/dashboard/summary', headers=headers_rep)
            assert resp.status_code == 403
            assert 'BI_VIEW' in resp.json().get('detail', '')

        # Viewer
        headers_vwr, user_vwr = _make_user_header(402, 'Viewer')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_vwr):
            resp = client.get('/api/bi/dashboard/summary', headers=headers_vwr)
            assert resp.status_code == 403
            assert 'BI_VIEW' in resp.json().get('detail', '')

    def test_admin_user_preferences_allowed_for_admin(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            with patch('modules.administration.controllers.admin_preferences.service.get_all', return_value={'theme': 'dark'}):
                resp = client.get('/api/admin/users/10/preferences', headers=headers_adm)
                assert resp.status_code == 200

    def test_admin_user_preferences_forbidden_for_non_admin(self):
        # Manager
        headers_mgr, user_mgr = _make_user_header(303, 'Manager')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_mgr):
            resp = client.get('/api/admin/users/10/preferences', headers=headers_mgr)
            assert resp.status_code == 403

        # Sales Rep
        headers_rep, user_rep = _make_user_header(104, 'Sales Rep')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_rep):
            resp = client.get('/api/admin/users/10/preferences', headers=headers_rep)
            assert resp.status_code == 403


class TestUnauthenticatedAccess:
    """Test unauthenticated or malformed token requests."""

    def test_missing_auth_header_returns_401_or_403(self):
        resp = client.get('/api/T0012I/')
        assert resp.status_code in (401, 403)

    def test_invalid_token_returns_401(self):
        resp = client.get('/api/T0012I/', headers={'Authorization': 'Bearer invalid.token.value'})
        assert resp.status_code == 401


class TestUserPrivilegeEscalationPrevention:
    """Test that UserCreate and UserUpdate schemas forbid client-supplied role/password_hash/permissions."""

    def test_create_user_with_injected_role_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.post('/api/T0021I/', json={
                'username': 'newadmin',
                'role': 'Admin'
            }, headers=headers_adm)
            assert resp.status_code == 422

    def test_create_user_with_injected_password_hash_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.post('/api/T0021I/', json={
                'username': 'newuser',
                'password_hash': 'injected_hash'
            }, headers=headers_adm)
            assert resp.status_code == 422

    def test_create_user_with_injected_permissions_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.post('/api/T0021I/', json={
                'username': 'newuser',
                'permissions': ['*']
            }, headers=headers_adm)
            assert resp.status_code == 422

    def test_update_user_with_injected_role_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.put('/api/T0021I/5', json={
                'role': 'Admin'
            }, headers=headers_adm)
            assert resp.status_code == 422

    def test_update_user_with_injected_password_hash_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.put('/api/T0021I/5', json={
                'password_hash': 'hacked'
            }, headers=headers_adm)
            assert resp.status_code == 422

    def test_update_user_with_injected_permissions_rejected(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm):
            resp = client.put('/api/T0021I/5', json={
                'permissions': ['*']
            }, headers=headers_adm)
            assert resp.status_code == 422


class TestDedicatedRoleUpdateEndpoints:
    """Test dedicated admin role update endpoints with T0023 audit logging."""

    def test_t0021i_role_update_by_admin_succeeds_and_creates_audit_log(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        target_user_before = {
            'id': 15,
            'username': 'target_user',
            'full_name': 'Target User',
            'email': 'target@example.com',
            'role': 'Viewer',
            'permissions': ['DASHBOARD_VIEW'],
            'status': 'Active',
            'last_login': None
        }
        target_user_after = {
            'id': 15,
            'username': 'target_user',
            'full_name': 'Target User',
            'email': 'target@example.com',
            'role': 'Sales Rep',
            'permissions': ['DASHBOARD_VIEW', 'SALES_VIEW', 'POS_VIEW', 'CRM_VIEW', 'CUSTOMERS_VIEW', 'PRODUCTS_VIEW', 'INVENTORY_VIEW'],
            'status': 'Active',
            'last_login': None
        }

        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm), \
             patch('modules.administration.controllers.T0021I.service.get', return_value=target_user_before), \
             patch('modules.administration.controllers.T0021I.service.update_role', return_value=target_user_after), \
             patch('modules.administration.controllers.T0021I.audit_repo.create') as mock_audit:

            resp = client.put('/api/T0021I/15/role', json={'role': 'Sales Rep'}, headers=headers_adm)
            assert resp.status_code == 200
            data = resp.json()
            assert data['role'] == 'Sales Rep'
            assert 'SALES_VIEW' in data['permissions']

            mock_audit.assert_called_once()
            audit_entry = mock_audit.call_args[0][0]
            assert audit_entry['table_name'] == 'T0021'
            assert audit_entry['record_id'] == 15
            assert audit_entry['action'] == 'UPDATE'
            assert audit_entry['changed_by'] == 1
            assert 'before' in audit_entry['changed_data']
            assert 'after' in audit_entry['changed_data']

    def test_t0021i_role_update_forbidden_for_non_admin(self):
        headers_mgr, user_mgr = _make_user_header(305, 'Manager')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_mgr):
            resp = client.put('/api/T0021I/15/role', json={'role': 'Sales Rep'}, headers=headers_mgr)
            assert resp.status_code == 403

    def test_admin_preferences_role_update_by_admin_succeeds_and_creates_audit_log(self):
        headers_adm, user_adm = _make_user_header(1, 'Admin', permissions=['*'])
        target_user_before = {'id': 25, 'username': 'user25', 'full_name': 'U25', 'email': 'u25@test.com', 'role': 'Cashier', 'permissions': ['POS_VIEW'], 'status': 'Active', 'last_login': None}
        target_user_after = {'id': 25, 'username': 'user25', 'full_name': 'U25', 'email': 'u25@test.com', 'role': 'Manager', 'permissions': ['FINANCE_VIEW', 'HR_VIEW'], 'status': 'Active', 'last_login': None}

        with patch('packages.auth.deps.get_user_by_id', return_value=user_adm), \
             patch('modules.administration.controllers.admin_preferences.user_service.get', return_value=target_user_before), \
             patch('modules.administration.controllers.admin_preferences.user_service.update_role', return_value=target_user_after), \
             patch('modules.administration.controllers.admin_preferences.user_audit_repo.create') as mock_audit:

            resp = client.put('/api/admin/users/25/role', json={'role': 'Manager'}, headers=headers_adm)
            assert resp.status_code == 200
            data = resp.json()
            assert data['role'] == 'Manager'
            mock_audit.assert_called_once()
            assert mock_audit.call_args[0][0]['record_id'] == 25

    def test_admin_preferences_role_update_forbidden_for_non_admin(self):
        headers_rep, user_rep = _make_user_header(105, 'Sales Rep')
        with patch('packages.auth.deps.get_user_by_id', return_value=user_rep):
            resp = client.put('/api/admin/users/25/role', json={'role': 'Manager'}, headers=headers_rep)
            assert resp.status_code == 403


class TestCompleteTCodeMapCoverage:
    """Ensure all mapped T-codes in T_CODE_PERMISSIONS have valid permission strings."""

    def test_all_tcode_permissions_have_non_empty_strings(self):
        for tcode, perm in T_CODE_PERMISSIONS.items():
            assert isinstance(tcode, str) and tcode.startswith('T'), f"Invalid tcode key: {tcode}"
            assert isinstance(perm, str) and len(perm) > 0, f"Invalid perm for {tcode}: {perm}"
            assert perm.endswith('_VIEW') or perm == 'ADMIN_VIEW', f"Unexpected permission format for {tcode}: {perm}"

    def test_get_required_permission_resolves_all_mapped_tcodes(self):
        for tcode, expected_perm in T_CODE_PERMISSIONS.items():
            resolved = get_required_permission(prefix=f'/api/{tcode}I', tag=f'{tcode} - Test Tag')
            assert resolved == expected_perm, f"Failed for {tcode}: expected {expected_perm}, got {resolved}"
