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
