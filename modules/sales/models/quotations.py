from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class QuotationCreate(BaseModel):
    quote_number: str = Field(..., max_length=30)
    customer_id: int
    quote_date: date = Field(default_factory=date.today)
    valid_until: Optional[date] = None
    subtotal: float = 0
    tax: float = 0
    grand_total: float = 0
    status: str = 'Draft'
    notes: Optional[str] = None

class QuotationUpdate(BaseModel):
    quote_number: Optional[str] = Field(None, max_length=30)
    customer_id: Optional[int] = None
    quote_date: Optional[date] = None
    valid_until: Optional[date] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    grand_total: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class QuotationResponse(AuditMixin):
    id: int
    quote_number: str
    customer_id: int
    quote_date: date
    valid_until: Optional[date]
    subtotal: float
    tax: float
    grand_total: float
    status: str
    notes: Optional[str]
    converted_order_id: Optional[int]


class QuotationLineCreate(BaseModel):
    quotation_id: int
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    uom_id: Optional[int] = None
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)
    line_number: int = 0

class QuotationLineUpdate(BaseModel):
    quotation_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    uom_id: Optional[int] = None
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_total: Optional[float] = Field(None, ge=0)
    line_number: Optional[int] = None

class QuotationLineResponse(AuditMixin):
    id: int
    quotation_id: int
    product_id: Optional[int]
    product_name: str
    uom_id: Optional[int]
    qty: float
    unit_price: float
    line_total: float
    line_number: int
