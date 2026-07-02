from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class KPIDefinitionCreate(BaseModel):
    kpi_code: str = Field(..., max_length=50)
    kpi_name: str = Field(..., max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    metric_unit: Optional[str] = Field(None, max_length=50)
    target_value: Optional[float] = None
    formula: Optional[str] = None
    is_active: bool = True

class KPIDefinitionUpdate(BaseModel):
    kpi_code: Optional[str] = Field(None, max_length=50)
    kpi_name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    metric_unit: Optional[str] = Field(None, max_length=50)
    target_value: Optional[float] = None
    formula: Optional[str] = None
    is_active: Optional[bool] = None

class KPIDefinitionResponse(AuditMixin):
    id: int
    kpi_code: str
    kpi_name: str
    category: Optional[str]
    metric_unit: Optional[str]
    target_value: Optional[float]
    formula: Optional[str]
    is_active: bool


class KPIValueCreate(BaseModel):
    kpi_id: int
    period: date
    period_type: str = 'Daily'
    actual_value: Optional[float] = None
    target_value: Optional[float] = None
    is_active: bool = True

class KPIValueUpdate(BaseModel):
    kpi_id: Optional[int] = None
    period: Optional[date] = None
    period_type: Optional[str] = None
    actual_value: Optional[float] = None
    target_value: Optional[float] = None
    is_active: Optional[bool] = None

class KPIValueResponse(AuditMixin):
    id: int
    kpi_id: int
    period: date
    period_type: str
    actual_value: Optional[float]
    target_value: Optional[float]
    is_active: bool


class BIDashboardCreate(BaseModel):
    dashboard_code: str = Field(..., max_length=50)
    dashboard_name: str = Field(..., max_length=200)
    owner_id: Optional[int] = None
    config: Optional[str] = None
    is_active: bool = True

class BIDashboardUpdate(BaseModel):
    dashboard_code: Optional[str] = Field(None, max_length=50)
    dashboard_name: Optional[str] = Field(None, max_length=200)
    owner_id: Optional[int] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None

class BIDashboardResponse(AuditMixin):
    id: int
    dashboard_code: str
    dashboard_name: str
    owner_id: Optional[int]
    config: Optional[str]
    is_active: bool


class DashboardWidgetCreate(BaseModel):
    dashboard_id: int
    widget_type: str = Field(..., max_length=50)
    title: Optional[str] = Field(None, max_length=200)
    config: Optional[str] = None
    position: Optional[str] = None
    is_active: bool = True

class DashboardWidgetUpdate(BaseModel):
    dashboard_id: Optional[int] = None
    widget_type: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=200)
    config: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None

class DashboardWidgetResponse(AuditMixin):
    id: int
    dashboard_id: int
    widget_type: str
    title: Optional[str]
    config: Optional[str]
    position: Optional[str]
    is_active: bool
