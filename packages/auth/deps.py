import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from packages.auth.jwt import decode_token
from packages.auth.repository import get_user_by_id

_bearer = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        payload = decode_token(creds.credentials)
        if payload.get('type') != 'access':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid token type')
        user = get_user_by_id(int(payload['sub']))
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'User not found')
        return user
    except HTTPException:
        raise
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or expired token')
