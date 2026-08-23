from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class StockMovementCreate(BaseModel):
    product_id: int
    warehouse_id: int
    movement_type: str = Field(..., max_length=30)
    reference_type: Optional[str] = Field(None, max_length=30)
    reference_id: Optional[int] = None
    qty_change: float  # positive = stock in, negative = stock out
    balance_after: float = 0
    description: Optional[str] = None
    business_id: Optional[int] = None

class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    movement_type: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    qty_change: float
    balance_after: float
    description: Optional[str] = None
    movement_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    business_id: Optional[int] = None

