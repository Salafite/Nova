from unittest.mock import patch
from packages.auth.service import login, refresh, authenticate_user


class TestAuthenticateUser:
    def test_returns_user_on_valid_credentials(self, mock_bcrypt, sample_user):
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            with patch('packages.auth.service.update_last_login'):
                result = authenticate_user('testuser', 'password')
                assert result is not None
                assert result['id'] == 1

    def test_returns_none_on_wrong_password(self, mock_db, sample_user):
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            with patch('bcrypt.checkpw', return_value=False):
                result = authenticate_user('testuser', 'wrongpass')
                assert result is None

    def test_returns_none_on_unknown_user(self, mock_db):
        with patch('packages.auth.service.get_user_by_username', return_value=None):
            result = authenticate_user('nobody', 'password')
            assert result is None

    def test_returns_none_on_empty_hash(self, mock_db, sample_user):
        sample_user['password_hash'] = ''
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            result = authenticate_user('testuser', 'password')
            assert result is None

    def test_returns_none_on_invalid_hash_format(self, mock_db, sample_user):
        sample_user['password_hash'] = 'not-a-bcrypt-hash'
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            result = authenticate_user('testuser', 'password')
            assert result is None


class TestLogin:
    def test_returns_token_dict_on_success(self, mock_bcrypt, sample_user):
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            with patch('packages.auth.service.update_last_login'):
                result = login('testuser', 'password')
                assert result is not None
                assert 'access_token' in result
                assert 'refresh_token' in result
                assert result['token_type'] == 'bearer'

    def test_returns_user_info_with_login(self, mock_bcrypt, sample_user):
        with patch('packages.auth.service.get_user_by_username', return_value=sample_user):
            with patch('packages.auth.service.update_last_login'):
                result = login('testuser', 'password')
                user = result['user']
                assert user['id'] == 1
                assert user['username'] == 'testuser'
                assert user['role'] == 'Admin'
                assert user['permissions'] == ['*']

    def test_returns_none_on_failure(self, mock_db):
        with patch('packages.auth.service.get_user_by_username', return_value=None):
            result = login('baduser', 'badpass')
            assert result is None


class TestRefresh:
    def test_returns_new_tokens_on_valid_refresh(self, valid_refresh_token):
        with patch('packages.auth.service.get_user_by_id') as mock_get:
            mock_get.return_value = {'id': 1, 'username': 'testuser'}
            result = refresh(valid_refresh_token)
            assert result is not None
            assert 'access_token' in result
            assert 'refresh_token' in result
            assert result['token_type'] == 'bearer'

    def test_returns_none_on_invalid_token(self):
        result = refresh('invalid.token.here')
        assert result is None

    def test_returns_none_on_access_token_used_as_refresh(self, valid_token):
        result = refresh(valid_token)
        assert result is None

    def test_returns_none_when_user_not_found(self, valid_refresh_token):
        with patch('packages.auth.service.get_user_by_id', return_value=None):
            result = refresh(valid_refresh_token)
            assert result is None


class TestPermissionService:
    def test_derive_permissions_admin(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('Admin')
        assert perms == ['*']

    def test_derive_permissions_sales_rep(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('Sales Rep')
        assert 'SALES_VIEW' in perms
        assert 'FINANCE_VIEW' not in perms
        assert 'HR_VIEW' not in perms

    def test_derive_permissions_manager(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('Manager')
        assert 'SALES_VIEW' in perms
        assert 'FINANCE_VIEW' in perms
        assert 'HR_VIEW' in perms

    def test_derive_permissions_cashier(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('Cashier')
        assert 'POS_VIEW' in perms
        assert 'SALES_VIEW' in perms
        assert 'PURCHASING_VIEW' not in perms
        assert 'FINANCE_VIEW' not in perms

    def test_derive_permissions_viewer(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('Viewer')
        assert 'DASHBOARD_VIEW' in perms
        assert 'PRODUCTS_VIEW' in perms
        assert 'SALES_VIEW' not in perms
        assert 'FINANCE_VIEW' not in perms

    def test_derive_permissions_unknown_role(self):
        from modules.core.services.permission_service import derive_permissions
        perms = derive_permissions('UnknownRole')
        assert perms == ['DASHBOARD_VIEW']

    def test_get_required_permission_tcodes(self):
        from modules.core.services.permission_service import get_required_permission
        assert get_required_permission('/api/T0001I', 'T0001 - UOM') == 'PRODUCTS_VIEW'
        assert get_required_permission('/api/T0012I', 'T0012 - Sales Orders') == 'SALES_VIEW'
        assert get_required_permission('/api/T0026I', 'T0026 - Chart of Accounts') == 'FINANCE_VIEW'
        assert get_required_permission('/api/T0038I', 'T0038 - Payroll Entries') == 'HR_VIEW'
        assert get_required_permission('/api/T0021I', 'T0021 - System Users') == 'ADMIN_VIEW'

    def test_get_required_permission_custom_routes(self):
        from modules.core.services.permission_service import get_required_permission
        assert get_required_permission('/api/categories', 'Categories') == 'PRODUCTS_VIEW'
        assert get_required_permission('/api/v1/migration', 'Migration') == 'ADMIN_VIEW'
        assert get_required_permission('/api/bi/dashboard', 'BI Dashboard') == 'BI_VIEW'
        assert get_required_permission('/api/admin/users', 'Admin User Preferences') == 'ADMIN_VIEW'
        assert get_required_permission('/api/adjustments', 'Stock Adjustments') == 'INVENTORY_VIEW'
        assert get_required_permission('/api/pos', 'POS') == 'POS_VIEW'

    def test_get_required_permission_fallback_to_admin_view(self):
        from modules.core.services.permission_service import get_required_permission
        assert get_required_permission('/api/unknown', 'Unknown Feature') == 'ADMIN_VIEW'
        assert get_required_permission('', '') == 'ADMIN_VIEW'

    def test_has_permission(self):
        from modules.core.services.permission_service import has_permission
        assert has_permission(['*'], 'HR_VIEW') is True
        assert has_permission(['SALES_VIEW', 'DASHBOARD_VIEW'], 'SALES_VIEW') is True
        assert has_permission(['SALES_VIEW', 'DASHBOARD_VIEW'], 'HR_VIEW') is False
        assert has_permission(None, 'HR_VIEW') is False
        assert has_permission(['SALES_VIEW'], None) is True


class TestCreateCrudRouter:
    def test_crud_router_attaches_permission_dependency(self):
        from unittest.mock import MagicMock
        from modules.core.controllers.base import create_crud_router
        mock_svc = MagicMock()
        router = create_crud_router('/api/T0026I', 'T0026 - Chart of Accounts', mock_svc)
        assert len(router.dependencies) == 1
        dep = router.dependencies[0].dependency
        assert callable(dep)


class TestCustomRouterPermissions:
    def test_bi_dashboard_router_has_permission_dependency(self):
        from modules.bi.controllers.dashboard import router as bi_router
        assert len(bi_router.dependencies) == 1
        dep = bi_router.dependencies[0].dependency
        assert callable(dep)

    def test_admin_preferences_router_has_permission_dependency(self):
        from modules.administration.controllers.admin_preferences import router as admin_pref_router
        assert len(admin_pref_router.dependencies) == 1
        dep = admin_pref_router.dependencies[0].dependency
        assert callable(dep)


class TestUserSchemas:
    def test_user_create_valid(self):
        from modules.administration.models.system import UserCreate
        user = UserCreate(username='johndoe', full_name='John Doe', email='john@example.com')
        assert user.username == 'johndoe'
        assert user.full_name == 'John Doe'
        assert user.email == 'john@example.com'
        assert user.status == 'Active'

    def test_user_create_rejects_role(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(username='johndoe', role='Admin')

    def test_user_create_rejects_password_hash(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(username='johndoe', password_hash='hash123')

    def test_user_create_rejects_permissions(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(username='johndoe', permissions=['*'])

    def test_user_update_valid(self):
        from modules.administration.models.system import UserUpdate
        update = UserUpdate(full_name='Jane Doe', status='Inactive')
        dump = update.model_dump(exclude_unset=True)
        assert dump == {'full_name': 'Jane Doe', 'status': 'Inactive'}

    def test_user_update_rejects_role(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserUpdate
        with pytest.raises(ValidationError):
            UserUpdate(role='Admin')

    def test_user_update_rejects_password_hash(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserUpdate
        with pytest.raises(ValidationError):
            UserUpdate(password_hash='newhash')

    def test_user_update_rejects_permissions(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserUpdate
        with pytest.raises(ValidationError):
            UserUpdate(permissions=['*'])

    def test_user_role_update_valid(self):
        from modules.administration.models.system import UserRoleUpdate
        role_update = UserRoleUpdate(role='Manager', permissions=['FINANCE_VIEW'])
        assert role_update.role == 'Manager'
        assert role_update.permissions == ['FINANCE_VIEW']

    def test_user_role_update_rejects_extra_fields(self):
        import pytest
        from pydantic import ValidationError
        from modules.administration.models.system import UserRoleUpdate
        with pytest.raises(ValidationError):
            UserRoleUpdate(role='Manager', username='hacker')


class TestUserService:
    def test_user_service_create_default_role_and_permissions(self):
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        mock_repo.create.side_effect = lambda data: {'id': 1, **data}
        svc = UserService(mock_repo)

        result = svc.create({'username': 'alice', 'email': 'alice@example.com'})
        assert result['role'] == 'Viewer'
        assert 'DASHBOARD_VIEW' in result['permissions']
        assert result['password_hash'] == ''
        assert mock_repo.create.called

    def test_user_service_create_rejects_role(self):
        import pytest
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        svc = UserService(mock_repo)

        with pytest.raises(ValueError, match="Protected fields cannot be supplied"):
            svc.create({'username': 'hacker', 'role': 'Admin'})

    def test_user_service_create_rejects_password_hash(self):
        import pytest
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        svc = UserService(mock_repo)

        with pytest.raises(ValueError, match="Protected fields cannot be supplied"):
            svc.create({'username': 'hacker', 'password_hash': 'injected_hash'})

    def test_user_service_create_rejects_permissions(self):
        import pytest
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        svc = UserService(mock_repo)

        with pytest.raises(ValueError, match="Protected fields cannot be supplied"):
            svc.create({'username': 'hacker', 'permissions': ['*']})

    def test_user_service_update_rejects_protected_fields(self):
        import pytest
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        svc = UserService(mock_repo)

        with pytest.raises(ValueError, match="Protected fields cannot be modified"):
            svc.update(1, {'role': 'Admin'})

        with pytest.raises(ValueError, match="Protected fields cannot be modified"):
            svc.update(1, {'password_hash': 'hacked'})

        with pytest.raises(ValueError, match="Protected fields cannot be modified"):
            svc.update(1, {'permissions': ['*']})

    def test_user_service_update_allowed_fields(self):
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        mock_repo.update.return_value = {'id': 1, 'full_name': 'New Name'}
        svc = UserService(mock_repo)

        result = svc.update(1, {'full_name': 'New Name'})
        assert result['full_name'] == 'New Name'
        mock_repo.update.assert_called_once_with(1, {'full_name': 'New Name'})

    def test_user_service_update_role(self):
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        mock_repo.update.side_effect = lambda uid, data: {'id': uid, **data}
        svc = UserService(mock_repo)

        result = svc.update_role(1, 'Manager')
        assert result['role'] == 'Manager'
        assert 'FINANCE_VIEW' in result['permissions']
        assert 'HR_VIEW' in result['permissions']

    def test_user_service_update_role_custom_permissions(self):
        from unittest.mock import MagicMock
        from modules.core.services.user_service import UserService
        mock_repo = MagicMock()
        mock_repo.update.side_effect = lambda uid, data: {'id': uid, **data}
        svc = UserService(mock_repo)

        result = svc.update_role(1, 'CustomRole', ['SALES_VIEW', 'CRM_VIEW'])
        assert result['role'] == 'CustomRole'
        assert result['permissions'] == ['SALES_VIEW', 'CRM_VIEW']


class TestUserRoleEndpoints:
    def test_t0021i_update_role_with_audit_log(self):
        from unittest.mock import patch
        import pytest
        from modules.administration.controllers.T0021I import update_user_role
        from modules.administration.models import UserRoleUpdate

        existing_user = {
            'id': 5,
            'username': 'bob',
            'full_name': 'Bob Smith',
            'email': 'bob@example.com',
            'role': 'Viewer',
            'permissions': ['DASHBOARD_VIEW'],
            'status': 'Active',
            'last_login': None
        }
        updated_user = {
            'id': 5,
            'username': 'bob',
            'full_name': 'Bob Smith',
            'email': 'bob@example.com',
            'role': 'Manager',
            'permissions': ['DASHBOARD_VIEW', 'SALES_VIEW', 'FINANCE_VIEW'],
            'status': 'Active',
            'last_login': None
        }

        with patch('modules.administration.controllers.T0021I.service.get', return_value=existing_user), \
             patch('modules.administration.controllers.T0021I.service.update_role', return_value=updated_user), \
             patch('modules.administration.controllers.T0021I.audit_repo.create') as mock_audit:
            admin_user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}
            res = update_user_role(id=5, body=UserRoleUpdate(role='Manager'), user=admin_user)
            assert res['role'] == 'Manager'
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args[0][0]
            assert call_args['table_name'] == 'T0021'
            assert call_args['record_id'] == 5
            assert call_args['action'] == 'UPDATE'
            assert call_args['changed_by'] == 1
            assert 'before' in call_args['changed_data']
            assert 'after' in call_args['changed_data']

    def test_t0021i_update_role_not_found(self):
        from unittest.mock import patch
        import pytest
        from fastapi import HTTPException
        from modules.administration.controllers.T0021I import update_user_role
        from modules.administration.models import UserRoleUpdate

        with patch('modules.administration.controllers.T0021I.service.get', return_value=None):
            admin_user = {'id': 1, 'username': 'admin', 'role': 'Admin', 'permissions': ['*']}
            with pytest.raises(HTTPException) as exc:
                update_user_role(id=999, body=UserRoleUpdate(role='Manager'), user=admin_user)
            assert exc.value.status_code == 404

    def test_admin_preferences_update_role_with_audit_log(self):
        from unittest.mock import patch
        from modules.administration.controllers.admin_preferences import update_user_role
        from modules.administration.models import UserRoleUpdate

        existing_user = {'id': 10, 'username': 'charlie', 'role': 'Viewer', 'permissions': ['DASHBOARD_VIEW']}
        updated_user = {'id': 10, 'username': 'charlie', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW']}

        with patch('modules.administration.controllers.admin_preferences.user_service.get', return_value=existing_user), \
             patch('modules.administration.controllers.admin_preferences.user_service.update_role', return_value=updated_user), \
             patch('modules.administration.controllers.admin_preferences.user_audit_repo.create') as mock_audit:
            admin_user = {'id': 1, 'username': 'admin'}
            res = update_user_role(user_id=10, body=UserRoleUpdate(role='Sales Rep'), user=admin_user)
            assert res['role'] == 'Sales Rep'
            mock_audit.assert_called_once()



