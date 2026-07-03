from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth.schemas import (
    LoginRequest, RefreshRequest, TokenResponse, CurrentUserResponse,
    SignupRequest, SignupResponse, InviteRequest, InviteResponse,
)
from packages.auth.service import login, refresh, signup, invite_user
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
    perms = user['permissions'] or []
    if user['role'] == 'Admin' and '*' not in perms:
        perms = ['*']
    return {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'permissions': perms,
        'business_id': user.get('business_id'),
    }


@router.post('/signup', response_model=SignupResponse)
def signup_endpoint(body: SignupRequest):
    result = signup(body.business_name, body.username, body.password, body.full_name, body.email)
    if not result:
        existing_user = body.username
        raise HTTPException(status.HTTP_409_CONFLICT, f'User or email already exists: {existing_user}')
    return result


@router.post('/invite', response_model=InviteResponse)
def invite_endpoint(body: InviteRequest, user: dict = Depends(get_current_user)):
    if user['role'] != 'Admin':
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Only admins can invite users')
    business_id = user.get('business_id')
    if not business_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'User is not associated with a business')
    result = invite_user(body.email, body.role, body.full_name, business_id, user['id'])
    if not result:
        raise HTTPException(status.HTTP_409_CONFLICT, 'User with this email already exists in this business')
    return result
