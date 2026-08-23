from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

class PickListCreate(BaseModel):
    pick_list_number: Optional[str] = Field(None, max_length=50)
    sales_order_id: int
    warehouse_id: Optional[int] = None
    status: str = 'Pending'
    notes: Optional[str] = None
    business_id: Optional[int] = None

class PickListUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    business_id: Optional[int] = None

class PickListResponse(AuditMixin):
    id: int
    pick_list_number: str
    sales_order_id: int
    warehouse_id: Optional[int] = None
    status: str
    notes: Optional[str] = None

class PickListItemCreate(BaseModel):
    pick_list_id: int
    sales_order_line_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    qty_ordered: float = Field(default=0, ge=0)
    qty_picked: float = Field(default=0, ge=0)
    line_number: int = 1
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=255)
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = Field(None, max_length=255)
    business_id: Optional[int] = None

class PickListItemUpdate(BaseModel):
    qty_picked: Optional[float] = Field(None, ge=0)
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=255)
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = Field(None, max_length=255)
    business_id: Optional[int] = None

class PickListItemResponse(AuditMixin):
    id: int
    pick_list_id: int
    sales_order_line_id: Optional[int] = None
    product_id: int
    product_name: Optional[str] = None
    qty_ordered: float
    qty_picked: float
    line_number: int
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    picked_batch_id: Optional[int] = None
    picked_batch_number: Optional[str] = None
