import bcrypt
import jwt
from packages.auth.jwt import create_access_token, create_refresh_token, decode_token
from packages.auth.repository import (
    get_user_by_username, get_user_by_email, get_user_by_id,
    update_last_login, create_business, create_user, create_invited_user
)


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
    return {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'permissions': user['permissions'] or [],
        'business_id': user.get('business_id'),
    }


def login(username: str, password: str) -> dict | None:
    user = authenticate_user(username, password)
    if not user:
        return None
    update_last_login(user['id'])
    return {
        'access_token': create_access_token(user['id']),
        'refresh_token': create_refresh_token(user['id']),
        'token_type': 'bearer',
        'user': _build_user_dict(user),
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
        'access_token': create_access_token(user['id']),
        'refresh_token': create_refresh_token(user['id']),
        'token_type': 'bearer',
        'user': _build_user_dict(user),
    }


def invite_user(email: str, role: str, full_name: str | None,
                business_id: int, invited_by: int) -> dict | None:
    existing = get_user_by_email(email)
    if existing:
        return None
    user = create_invited_user(email, role, full_name, business_id, invited_by)
    invite_link = f'/accept-invite?token={user["invite_token"]}'
    return {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'invite_link': invite_link,
    }
