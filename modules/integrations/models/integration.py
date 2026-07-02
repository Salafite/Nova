from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class ApiKeyCreate(BaseModel):
    key_name: str = Field(..., max_length=100)
    api_key: str = Field(..., max_length=255)
    client_id: Optional[str] = Field(None, max_length=100)
    permissions: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

class ApiKeyUpdate(BaseModel):
    key_name: Optional[str] = Field(None, max_length=100)
    api_key: Optional[str] = Field(None, max_length=255)
    client_id: Optional[str] = Field(None, max_length=100)
    permissions: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None

class ApiKeyResponse(AuditMixin):
    id: int
    key_name: str
    api_key: str
    client_id: Optional[str]
    permissions: Optional[str]
    expires_at: Optional[datetime]
    is_active: bool


class IntegrationConfigCreate(BaseModel):
    integration_code: str = Field(..., max_length=50)
    integration_name: str = Field(..., max_length=200)
    provider: Optional[str] = Field(None, max_length=100)
    config: Optional[str] = None
    credentials: Optional[str] = None
    is_active: bool = True

class IntegrationConfigUpdate(BaseModel):
    integration_code: Optional[str] = Field(None, max_length=50)
    integration_name: Optional[str] = Field(None, max_length=200)
    provider: Optional[str] = Field(None, max_length=100)
    config: Optional[str] = None
    credentials: Optional[str] = None
    is_active: Optional[bool] = None

class IntegrationConfigResponse(AuditMixin):
    id: int
    integration_code: str
    integration_name: str
    provider: Optional[str]
    config: Optional[str]
    credentials: Optional[str]
    is_active: bool


class SyncLogCreate(BaseModel):
    integration_id: Optional[int] = None
    entity_type: Optional[str] = Field(None, max_length=50)
    action: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    message: Optional[str] = None
    synced_at: Optional[datetime] = None
    is_active: bool = True

class SyncLogResponse(AuditMixin):
    id: int
    integration_id: Optional[int]
    entity_type: Optional[str]
    action: Optional[str]
    status: Optional[str]
    message: Optional[str]
    synced_at: Optional[datetime]
    is_active: bool
