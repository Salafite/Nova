import pytest
import jwt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from packages.auth.jwt import create_access_token, create_refresh_token, decode_token, _SECRET, _ALGO
from packages.auth.service import (
    refresh, is_token_revoked, is_family_revoked,
    revoke_jti, revoke_family, revoke_refresh_token
)
from packages.redis.client import get_redis_client, reset_redis_client
from apps.api.main import app


@pytest.fixture(autouse=True)
def clean_redis():
    reset_redis_client()
    yield
    reset_redis_client()


@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "username": "testuser",
        "full_name": "Test User",
        "email": "test@example.com",
        "role": "Admin",
        "permissions": ["*"],
        "business_id": 42,
    }


class TestJwtRotation:
    def test_single_use_refresh_token_rotation_success(self, mock_user):
        initial_token = create_refresh_token(1, business_id=42)
        initial_payload = decode_token(initial_token)
        old_jti = initial_payload["jti"]
        family_id = initial_payload["family_id"]

        assert not is_token_revoked(old_jti)
        assert not is_family_revoked(family_id)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            result = refresh(initial_token)

        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result

        # Old JTI must now be revoked in Redis
        assert is_token_revoked(old_jti)

        # New refresh token must have the same family_id but a new JTI
        new_payload = decode_token(result["refresh_token"])
        assert new_payload["sub"] == "1"
        assert new_payload["business_id"] == 42
        assert new_payload["family_id"] == family_id
        assert new_payload["jti"] != old_jti
        assert not is_token_revoked(new_payload["jti"])

    def test_token_reuse_detection_and_family_invalidation(self, mock_user):
        initial_token = create_refresh_token(1, business_id=42)
        initial_payload = decode_token(initial_token)
        family_id = initial_payload["family_id"]

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            # 1. Legitimate user rotates token
            result1 = refresh(initial_token)
            assert result1 is not None
            rotated_token = result1["refresh_token"]

            # 2. Attacker attempts to reuse the already rotated initial token
            with patch("packages.auth.service.record_security_event") as mock_sec_event:
                result2 = refresh(initial_token)
                assert result2 is None
                assert mock_sec_event.called
                assert mock_sec_event.call_args[1]["action"] == "REFRESH_TOKEN_REUSE"

            # 3. Hijack detection must have invalidated the entire token family
            assert is_family_revoked(family_id)

            # 4. Subsequent refresh with the legitimate rotated token must also be rejected
            result3 = refresh(rotated_token)
            assert result3 is None

    def test_revoked_family_access_attempt(self, mock_user):
        token = create_refresh_token(1, business_id=42)
        payload = decode_token(token)
        family_id = payload["family_id"]

        # Explicitly invalidate family
        revoke_family(family_id)
        assert is_family_revoked(family_id)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            with patch("packages.auth.service.record_security_event") as mock_sec_event:
                result = refresh(token)
                assert result is None
                assert mock_sec_event.called
                assert mock_sec_event.call_args[1]["action"] == "REVOKED_FAMILY_ACCESS"

    def test_invalid_token_types_rejected(self, mock_user):
        # Access token cannot be used in refresh()
        access_tok = create_access_token(1, business_id=42)
        assert refresh(access_tok) is None

        # Expired token cannot be used
        expired = jwt.encode(
            {"sub": "1", "exp": 0, "type": "refresh", "jti": "exp-1", "family_id": "fam-1"},
            _SECRET,
            algorithm=_ALGO,
        )
        assert refresh(expired) is None

        # Malformed token cannot be used
        assert refresh("not.a.valid.jwt") is None

        # User not found in DB
        valid_tok = create_refresh_token(9999)
        with patch("packages.auth.service.get_user_by_id", return_value=None):
            assert refresh(valid_tok) is None

    def test_explicit_token_revocation_logout(self, mock_user):
        token = create_refresh_token(1, business_id=42)
        payload = decode_token(token)
        jti = payload["jti"]
        family_id = payload["family_id"]

        assert revoke_refresh_token(token) is True
        assert is_token_revoked(jti)
        assert is_family_revoked(family_id)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            assert refresh(token) is None

    def test_multiple_rotations_in_same_family(self, mock_user):
        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            token_0 = create_refresh_token(1, business_id=42)
            family_id = decode_token(token_0)["family_id"]
            jti_0 = decode_token(token_0)["jti"]

            # Rotation 1
            res_1 = refresh(token_0)
            token_1 = res_1["refresh_token"]
            jti_1 = decode_token(token_1)["jti"]
            assert decode_token(token_1)["family_id"] == family_id
            assert is_token_revoked(jti_0)
            assert not is_token_revoked(jti_1)

            # Rotation 2
            res_2 = refresh(token_1)
            token_2 = res_2["refresh_token"]
            jti_2 = decode_token(token_2)["jti"]
            assert decode_token(token_2)["family_id"] == family_id
            assert is_token_revoked(jti_1)
            assert not is_token_revoked(jti_2)

            # Rotation 3
            res_3 = refresh(token_2)
            token_3 = res_3["refresh_token"]
            jti_3 = decode_token(token_3)["jti"]
            assert decode_token(token_3)["family_id"] == family_id
            assert is_token_revoked(jti_2)
            assert not is_token_revoked(jti_3)

            # Reusing token_1 (an old token) invalidates the whole family
            assert refresh(token_1) is None
            assert is_family_revoked(family_id)

            # token_3 is now also invalid
            assert refresh(token_3) is None

    def test_controller_refresh_and_logout_endpoints(self, mock_user):
        client = TestClient(app)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            tok = create_refresh_token(1, business_id=42)

            # Valid refresh
            resp = client.post("/api/auth/refresh", json={"refresh_token": tok})
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            new_tok = data["refresh_token"]

            # Reused token returns 401
            resp2 = client.post("/api/auth/refresh", json={"refresh_token": tok})
            assert resp2.status_code == 401

            # Logout endpoint
            logout_tok = create_refresh_token(1, business_id=42)
            resp3 = client.post("/api/auth/logout", json={"refresh_token": logout_tok})
            assert resp3.status_code == 200
            assert resp3.json()["message"] == "Successfully logged out"

            # Refreshing logged out token returns 401
            resp4 = client.post("/api/auth/refresh", json={"refresh_token": logout_tok})
            assert resp4.status_code == 401

    def test_redis_error_handling_and_fallback(self, mock_user):
        """When Redis encounters an unexpected error, helper functions fail gracefully without crashing."""
        with patch("packages.auth.service.get_redis_client") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.get.side_effect = Exception("Redis connection lost")
            mock_redis.set.side_effect = Exception("Redis write failed")
            mock_get_redis.return_value = mock_redis

            # Check functions gracefully return False instead of raising unhandled exceptions
            assert is_token_revoked("any-jti") is False
            assert is_family_revoked("any-family") is False
            assert revoke_jti("any-jti") is False
            assert revoke_family("any-family") is False

            # Refresh should still process the request if DB user is valid
            with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
                token = create_refresh_token(1, business_id=42)
                result = refresh(token)
                assert result is not None
                assert "access_token" in result
                assert "refresh_token" in result

    def test_token_expiration_ttl_calculation(self):
        """Tokens nearing expiry have TTL calculated from remaining exp timestamp."""
        with patch("packages.auth.service.get_redis_client") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis

            # Create token with short remaining expiry
            import time
            from datetime import timedelta, timezone, datetime
            now = datetime.now(timezone.utc)
            payload = {
                "sub": "1",
                "iat": now,
                "exp": now + timedelta(seconds=120),
                "type": "refresh",
                "jti": "custom-jti-123",
                "family_id": "custom-fam-123",
            }
            short_token = jwt.encode(payload, _SECRET, algorithm=_ALGO)

            with patch("packages.auth.service.get_user_by_id", return_value={"id": 1, "username": "u1", "role": "Admin", "permissions": ["*"]}):
                res = refresh(short_token)
                assert res is not None

                # Verify set was called with calculated TTL
                mock_redis.set.assert_called_once()
                args, kwargs = mock_redis.set.call_args
                assert args[0] == "auth:revoked_jti:custom-jti-123"
                assert args[1] == "revoked"
                assert kwargs["ex"] <= 120 and kwargs["ex"] >= 60


class TestMcpAuthHelper:
    def test_mcp_refresh_access_token_persists_rotated_credentials(self, tmp_path, mock_user):
        from packages.mcp.auth import refresh_access_token, load_token

        token_file = tmp_path / "test_mcp_token.json"
        initial_refresh = create_refresh_token(1, business_id=42)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            token_data = refresh_access_token(initial_refresh, save=True, token_path=token_file)

        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["refresh_token"] != initial_refresh

        # File on disk must have the rotated credentials
        persisted = load_token(token_file)
        assert persisted is not None
        assert persisted["access_token"] == token_data["access_token"]
        assert persisted["refresh_token"] == token_data["refresh_token"]
        assert persisted["expires_at"] == token_data["expires_at"]

    def test_mcp_get_valid_user_auto_refreshes_nearing_expiration(self, tmp_path, mock_user):
        from packages.mcp.auth import get_valid_user, save_token, load_token
        import time

        token_file = tmp_path / "expiring_token.json"
        initial_refresh = create_refresh_token(1, business_id=42)
        initial_access = create_access_token(1, business_id=42)

        # Save with expiration in 60 seconds (< 300 second margin)
        save_token({
            "access_token": initial_access,
            "refresh_token": initial_refresh,
            "expires_at": int(time.time()) + 60,
        }, token_path=token_file)

        with patch("packages.auth.service.get_user_by_id", return_value=mock_user):
            with patch("packages.mcp.auth.get_user_by_id", return_value=mock_user):
                user = get_valid_user(str(token_file))

        assert user["id"] == 1
        assert user["role"] == "Admin"
        assert user["permissions"] == ["*"]

        # Token file should have been updated with rotated tokens
        updated = load_token(token_file)
        assert updated["refresh_token"] != initial_refresh
        assert updated["expires_at"] > time.time() + 600

    def test_mcp_get_valid_user_direct_jwt_string(self, mock_user):
        from packages.mcp.auth import get_valid_user

        access_token = create_access_token(1, business_id=42)
        with patch("packages.mcp.auth.get_user_by_id", return_value=mock_user):
            user = get_valid_user(access_token)

        assert user["id"] == 1
        assert user["username"] == "testuser"
        assert user["business_id"] == 42


