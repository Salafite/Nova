import logging
from datetime import datetime, timezone
import bcrypt
import jwt
from packages.auth.jwt import create_access_token, create_refresh_token, decode_token
from packages.auth.repository import (
    get_user_by_username, get_user_by_email, get_user_by_id,
    update_last_login, create_business, create_user, create_invited_user
)
from modules.core.services.permission_service import derive_permissions
from packages.redis.client import get_redis_client
from packages.security.audit import record_security_event

logger = logging.getLogger("auth.service")

REVOKED_JTI_PREFIX = "auth:revoked_jti:"
REVOKED_FAMILY_PREFIX = "auth:revoked_family:"
DEFAULT_REFRESH_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def is_token_revoked(jti: str | None) -> bool:
    """Check whether a specific JWT ID (jti) has been marked as revoked in Redis."""
    if not jti:
        return False
    try:
        r = get_redis_client()
        return bool(r.get(f"{REVOKED_JTI_PREFIX}{jti}"))
    except Exception as e:
        logger.warning("Redis error checking token revocation for jti %s: %s", jti, str(e))
        return False


def is_family_revoked(family_id: str | None) -> bool:
    """Check whether an entire token family has been invalidated in Redis."""
    if not family_id:
        return False
    try:
        r = get_redis_client()
        return bool(r.get(f"{REVOKED_FAMILY_PREFIX}{family_id}"))
    except Exception as e:
        logger.warning("Redis error checking token family revocation for family %s: %s", family_id, str(e))
        return False


def revoke_jti(jti: str | None, ttl_seconds: int = DEFAULT_REFRESH_TTL_SECONDS) -> bool:
    """Mark a specific JWT ID (jti) as revoked in Redis for the remaining token lifetime."""
    if not jti:
        return False
    try:
        r = get_redis_client()
        r.set(f"{REVOKED_JTI_PREFIX}{jti}", "revoked", ex=max(1, int(ttl_seconds)))
        return True
    except Exception as e:
        logger.warning("Redis error revoking jti %s: %s", jti, str(e))
        return False


def revoke_family(family_id: str | None, ttl_seconds: int = DEFAULT_REFRESH_TTL_SECONDS) -> bool:
    """Invalidate an entire token family in Redis (e.g. upon detecting token reuse/theft)."""
    if not family_id:
        return False
    try:
        r = get_redis_client()
        r.set(f"{REVOKED_FAMILY_PREFIX}{family_id}", "revoked", ex=max(1, int(ttl_seconds)))
        return True
    except Exception as e:
        logger.warning("Redis error revoking token family %s: %s", family_id, str(e))
        return False


def revoke_refresh_token(token: str) -> bool:
    """Explicitly revoke a refresh token and its family (e.g. during logout)."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return False
    if payload.get("type") != "refresh":
        return False

    jti = payload.get("jti")
    family_id = payload.get("family_id") or payload.get("family")
    exp = payload.get("exp")
    ttl = DEFAULT_REFRESH_TTL_SECONDS
    if exp:
        now_ts = datetime.now(timezone.utc).timestamp()
        remaining = int(exp - now_ts)
        if remaining > 0:
            ttl = remaining

    if jti:
        revoke_jti(jti, ttl_seconds=ttl)
    if family_id:
        revoke_family(family_id, ttl_seconds=ttl)
    return True


def authenticate_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if not user:
        return None
    stored = user['password_hash']
    if not stored or not stored.startswith('$2b$'):
        return None
    if not bcrypt.checkpw(password.encode(), stored.encode()):
        return None
    return user


def _build_user_dict(user: dict) -> dict:
    raw_perms = user.get('permissions')
    if raw_perms is None or (isinstance(raw_perms, (list, tuple)) and len(raw_perms) == 0):
        role = user.get('role', '')
        perms = derive_permissions(role)
    elif isinstance(raw_perms, list):
        perms = list(raw_perms)
    elif isinstance(raw_perms, str):
        perms = [raw_perms]
    else:
        perms = list(raw_perms)

    if user.get('role') == 'Admin' and '*' not in perms:
        perms = ['*']

    return {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'permissions': perms,
        'business_id': user.get('business_id'),
        'customer_id': user.get('customer_id'),
    }


def login(username: str, password: str) -> dict | None:
    user = authenticate_user(username, password)
    if not user:
        return None
    update_last_login(user['id'])
    return {
        'access_token': create_access_token(user['id'], business_id=user.get('business_id'), customer_id=user.get('customer_id')),
        'refresh_token': create_refresh_token(user['id'], business_id=user.get('business_id'), customer_id=user.get('customer_id')),
        'token_type': 'bearer',
        'user': _build_user_dict(user),
    }


def refresh(token: str) -> dict | None:
    """
    Refresh access and refresh token pair using single-use refresh token rotation.

    Security mechanisms:
    1. Rejects invalid, expired, or non-refresh tokens.
    2. Checks if token family is revoked -> rejects.
    3. Checks if specific jti was previously revoked -> DETECTS TOKEN REUSE / THEFT.
       Immediately invalidates entire token family and logs security audit alert.
    4. Marks current jti as revoked with TTL.
    5. Issues new access token and new refresh token in the same token family.
    """
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None

    if payload.get('type') != 'refresh':
        return None

    user_id_val = payload.get('sub')
    if not user_id_val:
        return None
    try:
        user_id = int(user_id_val)
    except (ValueError, TypeError):
        return None

    jti = payload.get('jti')
    family_id = payload.get('family_id') or payload.get('family')
    business_id = payload.get('business_id')

    # Compute TTL based on token expiration
    exp = payload.get('exp')
    if exp:
        now_ts = datetime.now(timezone.utc).timestamp()
        remaining_ttl = int(exp - now_ts)
        if remaining_ttl <= 0:
            return None
        ttl = max(60, remaining_ttl)
    else:
        ttl = DEFAULT_REFRESH_TTL_SECONDS

    # 1. Check if token family was already invalidated
    if family_id and is_family_revoked(family_id):
        record_security_event(
            table_name="AUTH",
            record_id=user_id,
            action="REVOKED_FAMILY_ACCESS",
            user_id=user_id,
            business_id=business_id,
            details={
                "family_id": family_id,
                "jti": jti,
                "reason": "Attempted to use refresh token from revoked/compromised family",
            }
        )
        return None

    # 2. Check if this JTI was already revoked (Token Reuse / Hijacking Attempt!)
    if jti and is_token_revoked(jti):
        # Invalidate the entire token family to protect user account
        if family_id:
            revoke_family(family_id, ttl_seconds=ttl)

        record_security_event(
            table_name="AUTH",
            record_id=user_id,
            action="REFRESH_TOKEN_REUSE",
            user_id=user_id,
            business_id=business_id,
            details={
                "family_id": family_id,
                "jti": jti,
                "reason": "Refresh token reuse detected: token has already been rotated. Entire token family invalidated.",
            }
        )
        return None

    # 3. Retrieve user from repository
    user = get_user_by_id(user_id)
    if not user:
        return None

    # 4. Mark old jti as revoked (single-use rotation)
    if jti:
        revoke_jti(jti, ttl_seconds=ttl)

    # 5. Issue fresh access token and fresh refresh token (preserving family_id)
    new_access = create_access_token(
        user['id'],
        business_id=user.get('business_id'),
        customer_id=user.get('customer_id')
    )
    new_refresh = create_refresh_token(
        user['id'],
        business_id=user.get('business_id'),
        customer_id=user.get('customer_id'),
        family_id=family_id  # Preserves family for subsequent rotation tracking
    )

    return {
        'access_token': new_access,
        'refresh_token': new_refresh,
        'token_type': 'bearer',
    }


def signup(business_name: str, username: str, password: str,
           full_name: str, email: str) -> dict | None:
    if get_user_by_username(username):
        return None
    if get_user_by_email(email):
        return None
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    business = create_business(business_name, 0)
    user = create_user(username, password_hash, full_name, email, 'Admin', business['id'])
    return {
        'access_token': create_access_token(user['id'], business_id=user.get('business_id'), customer_id=user.get('customer_id')),
        'refresh_token': create_refresh_token(user['id'], business_id=user.get('business_id'), customer_id=user.get('customer_id')),
        'token_type': 'bearer',
        'user': _build_user_dict(user),
    }


def invite_user(email: str, role: str, full_name: str | None,
                business_id: int, invited_by: int, customer_id: int | None = None) -> dict | None:
    existing = get_user_by_email(email)
    if existing:
        return None
    user = create_invited_user(email, role, full_name, business_id, invited_by, customer_id=customer_id)
    invite_link = f'/accept-invite?token={user["invite_token"]}'
    return {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'invite_link': invite_link,
    }
