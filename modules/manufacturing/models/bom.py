from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

class BOMCreate(BaseModel):
    bom_code: str = Field(..., max_length=30)
    bom_name: str = Field(..., max_length=200)
    product_id: int
    quantity: float = 1
    version: int = 1
    is_active: bool = True

class BOMUpdate(BaseModel):
    bom_code: Optional[str] = Field(None, max_length=30)
    bom_name: Optional[str] = Field(None, max_length=200)
    product_id: Optional[int] = None
    quantity: Optional[float] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None

class BOMResponse(AuditMixin):
    id: int
    bom_code: str
    bom_name: str
    product_id: int
    quantity: float
    version: int
    is_active: bool

class BOMLineCreate(BaseModel):
    bom_id: int
    component_id: int
    component_name: str = Field(..., max_length=200)
    quantity: float = Field(..., gt=0)
    uom_id: Optional[int] = None
    scrap_pct: float = 0
    line_number: int = 0
    is_active: bool = True

class BOMLineUpdate(BaseModel):
    bom_id: Optional[int] = None
    component_id: Optional[int] = None
    component_name: Optional[str] = Field(None, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    uom_id: Optional[int] = None
    scrap_pct: Optional[float] = None
    line_number: Optional[int] = None
    is_active: Optional[bool] = None

class BOMLineResponse(AuditMixin):
    id: int
    bom_id: int
    component_id: int
    component_name: str
    quantity: float
    uom_id: Optional[int]
    scrap_pct: float
    line_number: int
    is_active: bool
