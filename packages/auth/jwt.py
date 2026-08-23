from datetime import datetime, timedelta, timezone
import os
import jwt

DEFAULT_DEV_SECRET = 'dev-insecure-secret-key-for-development-only-32chars'

INSECURE_SECRETS = {
    'change-me-in-production',
    'change-me',
    'changeme',
    'secret',
    'secret_key',
    'secretkey',
    'default',
    'default_secret',
    'nova_secret',
    'password',
    'admin',
    'your-secret-key-here',
    'replace-me',
    'replace_this_with_a_secure_secret',
    'dev-secret',
    'dev-secret-key',
    'test-secret',
    'test-secret-key',
    'test-secret-key-for-pytest-32-bytes-long!!',
}

INSECURE_PATTERNS = (
    'change-me',
    'change_me',
    'changeme',
    'replace-me',
    'replace_me',
    'your-secret',
    'your_secret',
    'secret-key-here',
    'secret_key_here',
    'placeholder',
    'example-secret',
    'example_secret',
    'default-secret',
    'default_secret',
    'nova-secret',
    'nova_secret',
    'todo-set-in-prod',
    'test-secret',
    'test_secret',
)



_UNSET = object()


def is_production_env() -> bool:
    """Check whether the application is running in production mode."""
    nova_env = os.getenv('NOVA_ENV', '').strip().lower()
    env = os.getenv('ENVIRONMENT', '').strip().lower()
    return nova_env == 'production' or env == 'production'


def validate_secret_key(secret_key: str | None = _UNSET, is_production: bool | None = None) -> str:
    """Validate SECRET_KEY configuration.

    In production mode (NOVA_ENV=production or ENVIRONMENT=production):
      - Must be present and non-empty
      - Must not be a known default, placeholder, or insecure pattern
      - Must be at least 32 characters long
    Raises RuntimeError if validation fails.
    In non-production mode, returns configured secret or fallback dev secret.
    """
    if secret_key is _UNSET:
        secret_key = os.environ.get('SECRET_KEY')

    if is_production is None:
        is_production = is_production_env()

    if is_production:
        if not secret_key or not secret_key.strip():
            raise RuntimeError('SECRET_KEY environment variable is required in production mode')
        cleaned = secret_key.strip()
        s_lower = cleaned.lower()
        if s_lower in INSECURE_SECRETS or any(pattern in s_lower for pattern in INSECURE_PATTERNS):
            raise RuntimeError(
                'SECRET_KEY cannot be set to an insecure default or placeholder value in production mode'
            )
        if len(cleaned) < 32:
            raise RuntimeError(
                f'SECRET_KEY must be at least 32 characters long in production (current length: {len(cleaned)})'
            )
        return cleaned

    if not secret_key or not secret_key.strip():
        return DEFAULT_DEV_SECRET
    return secret_key.strip()



def get_secret_key() -> str:
    """Retrieve and validate the current secret key."""
    return validate_secret_key()


_SECRET = get_secret_key()
_ALGO = 'HS256'
_ACCESS_EXPIRE = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 1440))
_REFRESH_EXPIRE = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))


def create_access_token(user_id: int, business_id: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=_ACCESS_EXPIRE), 'type': 'access'}
    if business_id is not None:
        payload['business_id'] = business_id
    return jwt.encode(payload, get_secret_key(), algorithm=_ALGO)


def create_refresh_token(user_id: int, business_id: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'iat': now, 'exp': now + timedelta(days=_REFRESH_EXPIRE), 'type': 'refresh'}
    if business_id is not None:
        payload['business_id'] = business_id
    return jwt.encode(payload, get_secret_key(), algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_secret_key(), algorithms=[_ALGO])

