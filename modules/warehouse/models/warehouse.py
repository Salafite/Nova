from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


class WarehouseCreate(TenantMixin):
    name: str = Field(..., max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    warehouse_type: Optional[str] = Field(default="Standard", max_length=50, description="Warehouse classification: Central Hub | Regional DC | Retail Branch | In-Transit Virtual | Standard")
    is_virtual: bool = Field(default=False, description="Flag indicating if warehouse is a virtual location")
    is_active: bool = True

class WarehouseUpdate(TenantMixin):
    name: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    warehouse_type: Optional[str] = Field(None, max_length=50)
    is_virtual: Optional[bool] = None
    is_active: Optional[bool] = None

class WarehouseResponse(AuditMixin):
    id: int
    name: str
    location: Optional[str] = None
    warehouse_type: Optional[str] = "Standard"
    is_virtual: bool = False
    is_active: bool


class InventoryCreate(TenantMixin):
    product_id: int
    warehouse_id: int
    qty: float = Field(default=0, ge=0)
    in_transit_qty: float = Field(default=0, ge=0)
    reorder_level: float = 10

class InventoryUpdate(TenantMixin):
    product_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    qty: Optional[float] = Field(None, ge=0)
    in_transit_qty: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[float] = None

class InventoryResponse(AuditMixin):
    id: int
    product_id: int
    warehouse_id: int
    qty: float
    in_transit_qty: float = 0
    reorder_level: float


class GoodsReceiptCreate(TenantMixin):
    receipt_number: str = Field(..., max_length=30)
    purchase_order_id: Optional[int] = None
    receipt_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: str = 'Draft'
    notes: Optional[str] = None

class GoodsReceiptUpdate(TenantMixin):
    receipt_number: Optional[str] = Field(None, max_length=30)
    purchase_order_id: Optional[int] = None
    receipt_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class GoodsReceiptResponse(AuditMixin):
    id: int
    receipt_number: str
    purchase_order_id: Optional[int] = None
    receipt_date: date
    warehouse_id: Optional[int] = None
    status: str
    notes: Optional[str] = None


class GoodsReceiptLineCreate(TenantMixin):
    receipt_id: int
    purchase_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    qty_received: float = Field(..., gt=0)
    qty_ordered: float = 0
    uom_id: Optional[int] = None
    line_number: int = 0
    batch_number: Optional[str] = Field(None, max_length=255)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None

class GoodsReceiptLineUpdate(TenantMixin):
    receipt_id: Optional[int] = None
    purchase_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    qty_received: Optional[float] = Field(None, gt=0)
    qty_ordered: Optional[float] = None
    uom_id: Optional[int] = None
    line_number: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=255)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None

class GoodsReceiptLineResponse(AuditMixin):
    id: int
    receipt_id: int
    purchase_order_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str
    qty_received: float
    qty_ordered: float
    uom_id: Optional[int] = None
    line_number: int
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
