from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class MfgOrderCreate(BaseModel):
    order_number: str = Field(..., max_length=30)
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    quantity: float = Field(..., gt=0)
    status: str = 'Pending'
    due_date: Optional[date] = None
    priority: str = 'Medium'

class MfgOrderUpdate(BaseModel):
    order_number: Optional[str] = Field(None, max_length=30)
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None

class MfgOrderResponse(AuditMixin):
    id: int
    order_number: str
    product_id: Optional[int]
    product_name: str
    quantity: float
    status: str
    due_date: Optional[date]
    priority: str


class QCInspectionCreate(BaseModel):
    inspection_no: str = Field(..., max_length=30)
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    batch_no: Optional[str] = Field(None, max_length=50)
    result: str = 'Pending'
    inspector: Optional[str] = Field(None, max_length=100)
    inspection_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None

class QCInspectionUpdate(BaseModel):
    inspection_no: Optional[str] = Field(None, max_length=30)
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    batch_no: Optional[str] = Field(None, max_length=50)
    result: Optional[str] = None
    inspector: Optional[str] = Field(None, max_length=100)
    inspection_date: Optional[date] = None
    notes: Optional[str] = None

class QCInspectionResponse(AuditMixin):
    id: int
    inspection_no: str
    product_id: Optional[int]
    product_name: str
    batch_no: Optional[str]
    result: str
    inspector: Optional[str]
    inspection_date: date
    notes: Optional[str]


class ShopJobCreate(BaseModel):
    job_number: str = Field(..., max_length=30)
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    quantity: float = Field(..., gt=0)
    workstation: Optional[str] = Field(None, max_length=100)
    status: str = 'Pending'

class ShopJobUpdate(BaseModel):
    job_number: Optional[str] = Field(None, max_length=30)
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    workstation: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None

class ShopJobResponse(AuditMixin):
    id: int
    job_number: str
    product_id: Optional[int]
    product_name: str
    quantity: float
    workstation: Optional[str]
    status: str
