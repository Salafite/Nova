from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from modules.core.models.base import AuditMixin


class UserCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    username: str = Field(..., max_length=50)
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    status: str = 'Active'
    customer_id: Optional[int] = None
    business_id: Optional[int] = None

class UserUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    username: Optional[str] = Field(None, max_length=50)
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None
    customer_id: Optional[int] = None
    business_id: Optional[int] = None

class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    role: str = Field(..., max_length=30)
    permissions: Optional[list[str]] = None

class UserResponse(AuditMixin):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    permissions: list[str]
    status: str
    last_login: Optional[datetime]
    customer_id: Optional[int] = None


class NavPermissionCreate(BaseModel):
    module_key: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    label_ar: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=100)
    permission_key: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0
    is_active: bool = True

class NavPermissionUpdate(BaseModel):
    module_key: Optional[str] = Field(None, max_length=50)
    label: Optional[str] = Field(None, max_length=100)
    label_ar: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=100)
    permission_key: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class NavPermissionResponse(AuditMixin):
    id: int
    module_key: str
    label: str
    label_ar: Optional[str]
    icon: Optional[str]
    section: Optional[str]
    permission_key: Optional[str]
    sort_order: int
    is_active: bool


class AuditLogCreate(BaseModel):
    table_name: str = Field(..., max_length=10)
    record_id: int
    action: str
    changed_data: Optional[dict] = None
    changed_by: Optional[int] = None

class AuditLogResponse(BaseModel):
    id: int
    table_name: str
    record_id: int
    action: str
    changed_data: Optional[dict] = None
    changed_by: Optional[int] = None
    changed_at: Optional[datetime] = None
    business_id: Optional[int] = None

class SettingCreate(BaseModel):
    setting_key: str = Field(..., max_length=100)
    setting_value: Optional[str] = None
    description: Optional[str] = None
    setting_group: Optional[str] = Field(None, max_length=50)
    is_active: bool = True

class SettingUpdate(BaseModel):
    setting_key: Optional[str] = Field(None, max_length=100)
    setting_value: Optional[str] = None
    description: Optional[str] = None
    setting_group: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class SettingResponse(AuditMixin):
    id: int
    setting_key: str
    setting_value: Optional[str]
    description: Optional[str]
    setting_group: Optional[str]
    is_active: bool
