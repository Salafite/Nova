from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class DeliveryCreate(BaseModel):
    delivery_number: str = Field(..., max_length=30)
    sales_order_id: int
    delivery_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: str = 'Draft'
    notes: Optional[str] = None

class DeliveryUpdate(BaseModel):
    delivery_number: Optional[str] = Field(None, max_length=30)
    sales_order_id: Optional[int] = None
    delivery_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class DeliveryResponse(AuditMixin):
    id: int
    delivery_number: str
    sales_order_id: int
    delivery_date: date
    warehouse_id: Optional[int]
    status: str
    notes: Optional[str]


class DeliveryLineCreate(BaseModel):
    delivery_id: int
    sales_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    qty_shipped: float = Field(..., gt=0)
    qty_ordered: float = 0
    uom_id: Optional[int] = None
    line_number: int = 0

class DeliveryLineUpdate(BaseModel):
    delivery_id: Optional[int] = None
    sales_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    qty_shipped: Optional[float] = Field(None, gt=0)
    qty_ordered: Optional[float] = None
    uom_id: Optional[int] = None
    line_number: Optional[int] = None

class DeliveryLineResponse(AuditMixin):
    id: int
    delivery_id: int
    sales_order_line_id: Optional[int]
    product_id: Optional[int]
    product_name: str
    qty_shipped: float
    qty_ordered: float
    uom_id: Optional[int]
    line_number: int
