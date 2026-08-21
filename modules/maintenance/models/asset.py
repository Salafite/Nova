from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class AssetCreate(BaseModel):
    asset_code: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=200)
    asset_type: Optional[str] = Field(None, max_length=100)
    asset_model: Optional[str] = Field(None, max_length=100)
    serial_no: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    purchase_cost: float = Field(default=0, ge=0)
    useful_life: Optional[int] = None
    warranty_expiry: Optional[date] = None
    status: str = 'Operational'
    is_active: bool = True
    business_id: Optional[int] = None

class AssetUpdate(BaseModel):
    asset_code: Optional[str] = Field(None, max_length=50)
    asset_name: Optional[str] = Field(None, max_length=200)
    asset_type: Optional[str] = Field(None, max_length=100)
    asset_model: Optional[str] = Field(None, max_length=100)
    serial_no: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    useful_life: Optional[int] = None
    warranty_expiry: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None

class AssetResponse(AuditMixin):
    id: int
    asset_code: str
    asset_name: str
    asset_type: Optional[str] = None
    asset_model: Optional[str] = None
    serial_no: Optional[str] = None
    location: Optional[str] = None
    department_id: Optional[int] = None
    purchase_date: Optional[date] = None
    purchase_cost: float = 0
    useful_life: Optional[int] = None
    warranty_expiry: Optional[date] = None
    status: str = 'Operational'
    is_active: bool = True


class MaintenanceScheduleCreate(BaseModel):
    asset_id: int
    schedule_code: str = Field(..., max_length=50)
    schedule_name: Optional[str] = Field(None, max_length=200)
    frequency_type: str = 'Monthly'
    frequency_value: int = 1
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None

class MaintenanceScheduleUpdate(BaseModel):
    asset_id: Optional[int] = None
    schedule_code: Optional[str] = Field(None, max_length=50)
    schedule_name: Optional[str] = Field(None, max_length=200)
    frequency_type: Optional[str] = None
    frequency_value: Optional[int] = None
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None

class MaintenanceScheduleResponse(AuditMixin):
    id: int
    asset_id: int
    schedule_code: str
    schedule_name: Optional[str] = None
    frequency_type: str = 'Monthly'
    frequency_value: int = 1
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True


class MaintenanceWorkOrderCreate(BaseModel):
    asset_id: int
    schedule_id: Optional[int] = None
    work_order_code: str = Field(..., max_length=50)
    description: Optional[str] = None
    priority: str = 'Medium'
    status: str = 'Open'
    assigned_to: Optional[int] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    cost: float = Field(default=0, ge=0)
    notes: Optional[str] = None
    is_active: bool = True
    business_id: Optional[int] = None

class MaintenanceWorkOrderUpdate(BaseModel):
    asset_id: Optional[int] = None
    schedule_id: Optional[int] = None
    work_order_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None

class MaintenanceWorkOrderResponse(AuditMixin):
    id: int
    asset_id: int
    schedule_id: Optional[int] = None
    work_order_code: str
    description: Optional[str] = None
    priority: str = 'Medium'
    status: str = 'Open'
    assigned_to: Optional[int] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    cost: float = 0
    notes: Optional[str] = None
    is_active: bool = True
