from typing import Optional
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
    business_id: Optional[int] = None


class PaymentTermUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    due_days: Optional[int] = Field(None, ge=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    discount_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    business_id: Optional[int] = None


class PaymentTermResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    due_days: int = 30
    discount_percentage: float = 0
    discount_days: int = 0
    is_active: bool = True
    is_default: bool = False


# Payment Methods
class PaymentMethodCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    business_id: Optional[int] = None


class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    business_id: Optional[int] = None


class PaymentMethodResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
