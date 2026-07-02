from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class TaxRateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    rate: float = Field(..., ge=0, le=100)
    type: str = 'Sales'
    is_active: bool = True
    is_default: bool = False
    description: Optional[str] = None

class TaxRateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    rate: Optional[float] = Field(None, ge=0, le=100)
    type: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None

class TaxRateResponse(AuditMixin):
    id: int
    name: str
    code: str
    rate: float
    type: str
    is_active: bool
    is_default: bool
    description: Optional[str]


class TaxRuleCreate(BaseModel):
    tax_rate_id: int
    applies_to: str = 'All'
    target_id: Optional[int] = 0
    is_active: bool = True

class TaxRuleUpdate(BaseModel):
    tax_rate_id: Optional[int] = None
    applies_to: Optional[str] = None
    target_id: Optional[int] = None
    is_active: Optional[bool] = None

class TaxRuleResponse(AuditMixin):
    id: int
    tax_rate_id: int
    applies_to: str
    target_id: Optional[int]
    is_active: bool
