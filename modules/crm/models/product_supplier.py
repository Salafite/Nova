from typing import Optional
from pydantic import BaseModel
from modules.core.models.base import AuditMixin

class ProductSupplierCreate(BaseModel):
    product_id: int
    supplier_id: int
    supplier_sku: Optional[str] = None
    unit_cost: float = 0
    lead_time_days: int = 0
    min_order_qty: float = 1
    is_preferred: bool = False
    business_id: Optional[int] = None

class ProductSupplierUpdate(BaseModel):
    supplier_sku: Optional[str] = None
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None
    min_order_qty: Optional[float] = None
    is_preferred: Optional[bool] = None
    business_id: Optional[int] = None

class ProductSupplierResponse(AuditMixin):
    id: int
    product_id: int
    supplier_id: int
    supplier_sku: Optional[str] = None
    unit_cost: float
    lead_time_days: int
    min_order_qty: float = 1
    is_preferred: bool


