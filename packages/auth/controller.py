from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth.schemas import LoginRequest, RefreshRequest, TokenResponse, CurrentUserResponse
from packages.auth.service import login, refresh
from packages.auth.deps import get_current_user

router = APIRouter(tags=['auth'])


@router.post('/login', response_model=TokenResponse)
def login_endpoint(body: LoginRequest):
    result = login(body.username, body.password)
    if not result:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid username or password')
    return result


@router.post('/refresh', response_model=TokenResponse)
def refresh_endpoint(body: RefreshRequest):
    result = refresh(body.refresh_token)
    if not result:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or expired refresh token')
    return result


@router.get('/me', response_model=CurrentUserResponse)
def me_endpoint(user: dict = Depends(get_current_user)):
    return {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'permissions': user['permissions'] or [],
    }
