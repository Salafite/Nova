import bcrypt
import jwt
from packages.auth.jwt import create_access_token, create_refresh_token, decode_token
from packages.auth.repository import get_user_by_username, get_user_by_id, update_last_login


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


def login(username: str, password: str) -> dict | None:
    user = authenticate_user(username, password)
    if not user:
        return None
    update_last_login(user['id'])
    return {
        'access_token': create_access_token(user['id']),
        'refresh_token': create_refresh_token(user['id']),
        'token_type': 'bearer',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'role': user['role'],
            'permissions': user['permissions'] or [],
        }
    }


def refresh(token: str) -> dict | None:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get('type') != 'refresh':
        return None
    user_id = int(payload['sub'])
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        'access_token': create_access_token(user['id']),
        'refresh_token': create_refresh_token(user['id']),
        'token_type': 'bearer',
    }
