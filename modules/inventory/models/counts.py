from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class InventoryCountCreate(BaseModel):
    warehouse_id: Optional[int] = None
    count_date: date
    notes: Optional[str] = None


class InventoryCountUpdate(BaseModel):
    warehouse_id: Optional[int] = None
    count_date: Optional[date] = None
    notes: Optional[str] = None


class InventoryCountResponse(AuditMixin):
    id: int
    count_number: str
    warehouse_id: Optional[int] = None
    count_date: date
    status: str = 'Draft'
    notes: Optional[str] = None


class CountItemCreate(BaseModel):
    count_id: int
    product_id: int
    expected_qty: float = 0
    counted_qty: Optional[float] = None
    notes: Optional[str] = None


class CountItemUpdate(BaseModel):
    counted_qty: Optional[float] = None
    expected_qty: Optional[float] = None
    notes: Optional[str] = None


class CountItemResponse(AuditMixin):
    id: int
    count_id: int
    product_id: int
    expected_qty: float
    counted_qty: Optional[float] = None
    notes: Optional[str] = None
