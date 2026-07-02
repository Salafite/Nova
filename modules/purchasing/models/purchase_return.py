from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class PurchaseReturnCreate(BaseModel):
    return_number: str = Field(..., max_length=30)
    purchase_order_id: Optional[int] = None
    supplier_id: int
    return_date: date = Field(default_factory=date.today)
    status: str = 'Draft'
    reason: Optional[str] = None
    notes: Optional[str] = None

class PurchaseReturnUpdate(BaseModel):
    return_number: Optional[str] = Field(None, max_length=30)
    purchase_order_id: Optional[int] = None
    supplier_id: Optional[int] = None
    return_date: Optional[date] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

class PurchaseReturnResponse(AuditMixin):
    id: int
    return_number: str
    purchase_order_id: Optional[int]
    supplier_id: int
    return_date: date
    status: str
    reason: Optional[str]
    notes: Optional[str]


class PurchaseReturnLineCreate(BaseModel):
    return_id: int
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = 0
    uom_id: Optional[int] = None
    line_number: int = 0

class PurchaseReturnLineUpdate(BaseModel):
    return_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_total: Optional[float] = None
    uom_id: Optional[int] = None
    line_number: Optional[int] = None

class PurchaseReturnLineResponse(AuditMixin):
    id: int
    return_id: int
    product_id: Optional[int]
    product_name: str
    qty: float
    unit_price: float
    line_total: float
    uom_id: Optional[int]
    line_number: int
