from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class ModuleRegistryCreate(BaseModel):
    module_key: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    description_ar: Optional[str] = None
    version: str = '1.0.0'
    author: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    is_core: bool = False
    is_active: bool = True
    installed_at: Optional[datetime] = None
    dependencies: list[str] = []

class ModuleRegistryUpdate(BaseModel):
    module_key: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    description_ar: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    is_core: Optional[bool] = None
    is_active: Optional[bool] = None
    dependencies: Optional[list[str]] = None

class ModuleRegistryResponse(AuditMixin):
    id: int
    module_key: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    description_ar: Optional[str]
    version: str
    author: Optional[str]
    icon: Optional[str]
    category: Optional[str]
    is_core: bool
    is_active: bool
    installed_at: Optional[datetime]
    dependencies: Optional[list[str]] = None
