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


def test_create_refresh_token_contains_user_id():
    token = create_refresh_token(42)
    payload = decode_token(token)
    assert payload['sub'] == '42'
    assert payload['type'] == 'refresh'


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
