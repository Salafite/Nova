from unittest.mock import patch, MagicMock
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
