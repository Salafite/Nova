from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class PriceListCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    currency: str = 'USD'
    is_active: bool = True
    is_default: bool = False


class PriceListUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class PriceListResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    currency: str
    is_active: bool
    is_default: bool
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    update_number: Optional[int] = None


class PriceListItemCreate(BaseModel):
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = 1
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int = 0


class PriceListItemUpdate(BaseModel):
    price_list_id: Optional[int] = None
    product_id: Optional[int] = None
    unit_price: Optional[float] = None
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: Optional[int] = None


class PriceListItemResponse(BaseModel):
    id: int
    price_list_id: int
    product_id: int
    unit_price: float
    min_qty: Optional[float] = None
    uom_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    line_number: int
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    update_number: Optional[int] = None
