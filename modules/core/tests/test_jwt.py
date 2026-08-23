from packages.auth.jwt import create_access_token, create_refresh_token, decode_token
import jwt


def test_create_access_token_returns_string():
    token = create_access_token(1)
    assert isinstance(token, str)
    assert len(token.split('.')) == 3


def test_create_access_token_contains_user_id():
    token = create_access_token(42)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['type'] == 'access'
    assert 'customer_id' not in payload


def test_create_access_token_with_customer_id():
    token = create_access_token(42, customer_id=105)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['type'] == 'access'
    assert payload['customer_id'] == 105


def test_create_refresh_token_contains_user_id():
    token = create_refresh_token(42)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['type'] == 'refresh'
    assert 'customer_id' not in payload


def test_create_refresh_token_with_customer_id():
    token = create_refresh_token(42, customer_id=105)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['type'] == 'refresh'
    assert payload['customer_id'] == 105


def test_access_token_expires_in_default_window():
    from datetime import timedelta, timezone, datetime
    token = create_access_token(1)
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    iat = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
    assert timedelta(minutes=1439) <= (exp - iat) <= timedelta(minutes=1441)


def test_refresh_token_expires_in_default_window():
    from datetime import timedelta, timezone, datetime
    token = create_refresh_token(1)
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    iat = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
    assert timedelta(days=6) <= (exp - iat) <= timedelta(days=7)


def test_decode_invalid_token_raises():
    import pytest
    with pytest.raises(jwt.PyJWTError):
        decode_token('invalid.token.here')


def test_decode_expired_token_raises():
    import pytest
    from packages.auth.jwt import _SECRET, _ALGO
    expired = jwt.encode({'sub': '1', 'exp': 0, 'type': 'access'}, _SECRET, algorithm=_ALGO)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)


def test_decode_wrong_secret_raises():
    import pytest
    token = jwt.encode({'sub': '1', 'exp': 9999999999, 'type': 'access'}, 'wrong-secret-thats-long-enough-32chars', algorithm='HS256')
    with pytest.raises(jwt.PyJWTError):
        decode_token(token)


def test_tokens_have_distinct_values():
    import time
    t1 = create_access_token(1)
    time.sleep(1.1)
    t2 = create_access_token(1)
    assert t1 != t2


def test_is_production_env(monkeypatch):
    from packages.auth.jwt import is_production_env

    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    assert is_production_env() is False

    monkeypatch.setenv('NOVA_ENV', 'production')
    assert is_production_env() is True

    monkeypatch.setenv('NOVA_ENV', 'PRODUCTION')
    assert is_production_env() is True

    monkeypatch.setenv('NOVA_ENV', 'development')
    assert is_production_env() is False

    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.setenv('ENVIRONMENT', 'production')
    assert is_production_env() is True


def test_validate_secret_key_valid_in_production():
    from packages.auth.jwt import validate_secret_key
    valid_key = 'a-very-strong-production-secret-key-32-chars-minimum!!'
    assert validate_secret_key(valid_key, is_production=True) == valid_key


def test_validate_secret_key_missing_in_production():
    import pytest
    from packages.auth.jwt import validate_secret_key

    with pytest.raises(RuntimeError, match='SECRET_KEY environment variable is required'):
        validate_secret_key(None, is_production=True)

    with pytest.raises(RuntimeError, match='SECRET_KEY environment variable is required'):
        validate_secret_key('', is_production=True)

    with pytest.raises(RuntimeError, match='SECRET_KEY environment variable is required'):
        validate_secret_key('   ', is_production=True)


def test_validate_secret_key_short_in_production():
    import pytest
    from packages.auth.jwt import validate_secret_key

    with pytest.raises(RuntimeError, match='at least 32 characters long'):
        validate_secret_key('short-key-less-than-32-chars', is_production=True)


def test_validate_secret_key_insecure_placeholder_in_production():
    import pytest
    from packages.auth.jwt import validate_secret_key

    insecure_keys = [
        'change-me-in-production',
        'change-me-in-production-extra-padding-here',
        'nova_secret_key_for_testing_purposes_123',
        'default_secret_for_system_testing_32chars',
        'your-secret-key-here-must-be-changed-32chars',
        'replace-me-with-a-real-secret-key-32chars',
    ]
    for key in insecure_keys:
        with pytest.raises(RuntimeError, match='insecure default or placeholder'):
            validate_secret_key(key, is_production=True)


def test_validate_secret_key_non_production_defaults(monkeypatch):
    from packages.auth.jwt import validate_secret_key, DEFAULT_DEV_SECRET

    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.delenv('SECRET_KEY', raising=False)

    # Missing in non-prod returns DEFAULT_DEV_SECRET
    assert validate_secret_key(None, is_production=False) == DEFAULT_DEV_SECRET
    assert validate_secret_key('', is_production=False) == DEFAULT_DEV_SECRET

    # Insecure/placeholder allowed in non-prod
    assert validate_secret_key('change-me-in-production', is_production=False) == 'change-me-in-production'
    assert validate_secret_key('short', is_production=False) == 'short'
def test_create_access_token_contains_business_id():
    token = create_access_token(42, business_id=99)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['business_id'] == 99


def test_create_refresh_token_contains_business_id():
    token = create_refresh_token(42, business_id=99)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['business_id'] == 99

