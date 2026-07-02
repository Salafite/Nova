from typing import Optional
from pydantic import BaseModel, Field, computed_field
from modules.core.models.base import AuditMixin

class StockLevelCreate(BaseModel):
    product_id: int
    warehouse_id: int
    qty: float = Field(default=0, ge=0)
    reserved_qty: float = Field(default=0, ge=0)
    reorder_level: float = Field(default=0, ge=0)

class StockLevelUpdate(BaseModel):
    product_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    qty: Optional[float] = Field(None, ge=0)
    reserved_qty: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[float] = Field(None, ge=0)

class StockLevelResponse(AuditMixin):
    id: int
    product_id: int
    warehouse_id: int
    qty: float
    reserved_qty: float = 0
    reorder_level: float

    @computed_field
    @property
    def available_qty(self) -> float:
        return max(0, self.qty - self.reserved_qty)
