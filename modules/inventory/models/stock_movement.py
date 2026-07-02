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

class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    movement_type: str
    reference_type: Optional[str]
    reference_id: Optional[int]
    qty_change: float
    balance_after: float
    description: Optional[str]
    movement_date: Optional[datetime]
    created_by: Optional[int]
    created_at: Optional[datetime]
