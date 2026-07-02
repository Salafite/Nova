from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

class ProductSupplierCreate(BaseModel):
    product_id: int
    supplier_id: int
    supplier_sku: Optional[str] = None
    unit_cost: float = 0
    lead_time_days: int = 0
    is_preferred: bool = False

class ProductSupplierUpdate(BaseModel):
    supplier_sku: Optional[str] = None
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None
    is_preferred: Optional[bool] = None

class ProductSupplierResponse(AuditMixin):
    id: int
    product_id: int
    supplier_id: int
    supplier_sku: Optional[str] = None
    unit_cost: float
    lead_time_days: int
    is_preferred: bool
