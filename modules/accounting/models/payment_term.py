from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


# Payment Terms
class PaymentTermCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    due_days: int = Field(default=30, ge=0)
    discount_percentage: float = Field(default=0, ge=0, le=100)
    discount_days: int = Field(default=0, ge=0)
    is_active: bool = True
    is_default: bool = False


class PaymentTermUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    due_days: Optional[int] = Field(None, ge=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    discount_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class PaymentTermResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str]
    due_days: int
    discount_percentage: float
    discount_days: int
    is_active: bool
    is_default: bool


# Payment Methods
class PaymentMethodCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class PaymentMethodResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    is_default: bool
