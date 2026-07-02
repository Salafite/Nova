from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class SerialNumberCreate(BaseModel):
    product_id: int
    serial_number: str = Field(..., max_length=100)
    status: str = 'In Stock'
    warehouse_id: Optional[int] = None
    purchase_order_line_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    notes: Optional[str] = None

class SerialNumberUpdate(BaseModel):
    product_id: Optional[int] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    warehouse_id: Optional[int] = None
    purchase_order_line_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    notes: Optional[str] = None

class SerialNumberResponse(AuditMixin):
    id: int
    product_id: int
    serial_number: str
    status: str
    warehouse_id: Optional[int]
    purchase_order_line_id: Optional[int]
    sales_order_line_id: Optional[int]
    notes: Optional[str]


class BatchNumberCreate(BaseModel):
    product_id: int
    batch_number: str = Field(..., max_length=100)
    expiry_date: Optional[date] = None
    manufacturing_date: Optional[date] = None
    quantity: float = 0
    warehouse_id: Optional[int] = None
    status: str = 'Available'
    notes: Optional[str] = None

class BatchNumberUpdate(BaseModel):
    product_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    manufacturing_date: Optional[date] = None
    quantity: Optional[float] = Field(None, ge=0)
    warehouse_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class BatchNumberResponse(AuditMixin):
    id: int
    product_id: int
    batch_number: str
    expiry_date: Optional[date]
    manufacturing_date: Optional[date]
    quantity: float
    warehouse_id: Optional[int]
    status: str
    notes: Optional[str]
