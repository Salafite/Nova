from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel
from modules.core.models.base import AuditMixin


class PriceListCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    currency: str = 'USD'
    is_active: bool = True
    is_default: bool = False
    business_id: Optional[int] = None


class PriceListUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    business_id: Optional[int] = None


class PriceListResponse(AuditMixin):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    currency: str
    is_active: bool
    is_default: bool


class PriceListItemCreate(BaseModel):
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = 1
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int = 0
    business_id: Optional[int] = None


class PriceListItemUpdate(BaseModel):
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    unit_price: Optional[float] = None
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: Optional[int] = None
    business_id: Optional[int] = None


class PriceListItemResponse(AuditMixin):
    id: int
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int

