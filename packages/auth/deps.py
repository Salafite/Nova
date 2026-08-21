import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from packages.auth.jwt import decode_token
from packages.auth.repository import get_user_by_id
from modules.core.services.permission_service import has_permission, derive_permissions
from modules.core.context import set_current_tenant

_bearer = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        payload = decode_token(creds.credentials)
        if payload.get('type') != 'access':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid token type')
        user = get_user_by_id(int(payload['sub']))
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'User not found')

        business_id = payload.get('business_id')
        if business_id is None and isinstance(user, dict):
            business_id = user.get('business_id')
        if business_id is not None:
            set_current_tenant(business_id)

        return user
    except HTTPException:
        raise
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or expired token')


def require_permission(key: str):
    """FastAPI dependency factory that verifies the authenticated user has the required permission key."""
    def _permission_checker(user: dict = Depends(get_current_user)) -> dict:
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
            perms.append('*')

        if not has_permission(perms, key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Permission denied: {key} required'
            )
        return user

    return _permission_checker

