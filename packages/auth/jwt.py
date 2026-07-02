from datetime import datetime, timedelta, timezone
import os
import jwt

_SECRET = os.environ.get('SECRET_KEY')
if not _SECRET:
    raise RuntimeError('SECRET_KEY environment variable is required')
_ALGO = 'HS256'
_ACCESS_EXPIRE = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 1440))
_REFRESH_EXPIRE = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=_ACCESS_EXPIRE), 'type': 'access'}
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def create_refresh_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'iat': now, 'exp': now + timedelta(days=_REFRESH_EXPIRE), 'type': 'refresh'}
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _SECRET, algorithms=[_ALGO])
