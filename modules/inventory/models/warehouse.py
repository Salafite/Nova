from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

class WarehouseCreate(BaseModel):
    name: str = Field(..., max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class WarehouseResponse(AuditMixin):
    id: int
    name: str
    location: Optional[str]
    is_active: bool
