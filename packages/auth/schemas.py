from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str

class CurrentUserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    permissions: list[str] = []
    business_id: Optional[int] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    user: Optional[CurrentUserResponse] = None

class SignupRequest(BaseModel):
    business_name: str
    username: str
    password: str
    full_name: str
    email: str

class SignupResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    user: CurrentUserResponse

class InviteRequest(BaseModel):
    email: str
    role: str
    full_name: Optional[str] = None

class InviteResponse(BaseModel):
    user_id: int
    email: str
    role: str
    invite_link: str
