from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class WarehouseCreate(BaseModel):
    name: str = Field(..., max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class WarehouseResponse(AuditMixin):
    id: int
    name: str
    location: Optional[str]
    is_active: bool


class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    qty: float = Field(default=0, ge=0)
    reorder_level: float = 10

class InventoryUpdate(BaseModel):
    product_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    qty: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[float] = None

class InventoryResponse(AuditMixin):
    id: int
    product_id: int
    warehouse_id: int
    qty: float
    reorder_level: float


class GoodsReceiptCreate(BaseModel):
    receipt_number: str = Field(..., max_length=30)
    purchase_order_id: Optional[int] = None
    receipt_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: str = 'Draft'
    notes: Optional[str] = None

class GoodsReceiptUpdate(BaseModel):
    receipt_number: Optional[str] = Field(None, max_length=30)
    purchase_order_id: Optional[int] = None
    receipt_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class GoodsReceiptResponse(AuditMixin):
    id: int
    receipt_number: str
    purchase_order_id: Optional[int]
    receipt_date: date
    warehouse_id: Optional[int]
    status: str
    notes: Optional[str]


class GoodsReceiptLineCreate(BaseModel):
    receipt_id: int
    purchase_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    qty_received: float = Field(..., gt=0)
    qty_ordered: float = 0
    uom_id: Optional[int] = None
    line_number: int = 0

class GoodsReceiptLineUpdate(BaseModel):
    receipt_id: Optional[int] = None
    purchase_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    qty_received: Optional[float] = Field(None, gt=0)
    qty_ordered: Optional[float] = None
    uom_id: Optional[int] = None
    line_number: Optional[int] = None

class GoodsReceiptLineResponse(AuditMixin):
    id: int
    receipt_id: int
    purchase_order_line_id: Optional[int]
    product_id: Optional[int]
    product_name: str
    qty_received: float
    qty_ordered: float
    uom_id: Optional[int]
    line_number: int
