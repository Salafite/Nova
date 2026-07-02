from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class ProjectCreate(BaseModel):
    project_code: str = Field(..., max_length=50)
    project_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: float = Field(default=0, ge=0)
    status: str = 'Draft'
    is_active: bool = True

class ProjectUpdate(BaseModel):
    project_code: Optional[str] = Field(None, max_length=50)
    project_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(AuditMixin):
    id: int
    project_code: str
    project_name: str
    description: Optional[str]
    department_id: Optional[int]
    manager_id: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: float
    status: str
    is_active: bool


class ProjectTaskCreate(BaseModel):
    project_id: int
    task_code: str = Field(..., max_length=50)
    task_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    priority: str = 'Medium'
    status: str = 'Pending'
    estimated_hours: Optional[float] = None
    actual_hours: float = Field(default=0, ge=0)
    parent_task_id: Optional[int] = None
    is_active: bool = True

class ProjectTaskUpdate(BaseModel):
    project_id: Optional[int] = None
    task_code: Optional[str] = Field(None, max_length=50)
    task_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = Field(None, ge=0)
    parent_task_id: Optional[int] = None
    is_active: Optional[bool] = None

class ProjectTaskResponse(AuditMixin):
    id: int
    project_id: int
    task_code: str
    task_name: str
    description: Optional[str]
    assigned_to: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    priority: str
    status: str
    estimated_hours: Optional[float]
    actual_hours: float
    parent_task_id: Optional[int]
    is_active: bool


class ResourceAllocationCreate(BaseModel):
    project_id: int
    employee_id: int
    allocation_pct: int = 100
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    role: Optional[str] = None
    is_active: bool = True

class ResourceAllocationUpdate(BaseModel):
    project_id: Optional[int] = None
    employee_id: Optional[int] = None
    allocation_pct: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class ResourceAllocationResponse(AuditMixin):
    id: int
    project_id: int
    employee_id: int
    allocation_pct: int
    start_date: Optional[date]
    end_date: Optional[date]
    role: Optional[str]
    is_active: bool


class TimesheetCreate(BaseModel):
    employee_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    date: date
    hours: float = Field(..., gt=0)
    description: Optional[str] = None
    status: str = 'Submitted'
    approved_by: Optional[int] = None
    is_active: bool = True

class TimesheetUpdate(BaseModel):
    employee_id: Optional[int] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    date: Optional[date] = None
    hours: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[int] = None
    is_active: Optional[bool] = None

class TimesheetResponse(AuditMixin):
    id: int
    employee_id: int
    project_id: Optional[int]
    task_id: Optional[int]
    date: date
    hours: float
    description: Optional[str]
    status: str
    approved_by: Optional[int]
    is_active: bool


class ServiceRequestCreate(BaseModel):
    request_code: str = Field(..., max_length=50)
    subject: str = Field(..., max_length=200)
    description: Optional[str] = None
    customer_id: Optional[int] = None
    priority: str = 'Medium'
    status: str = 'Open'
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None
    resolved_date: Optional[date] = None
    is_active: bool = True

class ServiceRequestUpdate(BaseModel):
    request_code: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    customer_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None
    resolved_date: Optional[date] = None
    is_active: Optional[bool] = None

class ServiceRequestResponse(AuditMixin):
    id: int
    request_code: str
    subject: str
    description: Optional[str]
    customer_id: Optional[int]
    priority: str
    status: str
    assigned_to: Optional[int]
    resolution: Optional[str]
    resolved_date: Optional[date]
    is_active: bool


class ContractCreate(BaseModel):
    contract_code: str = Field(..., max_length=50)
    contract_name: str = Field(..., max_length=200)
    customer_id: Optional[int] = None
    contract_type: Optional[str] = Field(None, max_length=100)
    start_date: date
    end_date: Optional[date] = None
    value: float = Field(default=0, ge=0)
    status: str = 'Active'
    notes: Optional[str] = None
    is_active: bool = True

class ContractUpdate(BaseModel):
    contract_code: Optional[str] = Field(None, max_length=50)
    contract_name: Optional[str] = Field(None, max_length=200)
    customer_id: Optional[int] = None
    contract_type: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ContractResponse(AuditMixin):
    id: int
    contract_code: str
    contract_name: str
    customer_id: Optional[int]
    contract_type: Optional[str]
    start_date: date
    end_date: Optional[date]
    value: float
    status: str
    notes: Optional[str]
    is_active: bool


class SLADefinitionCreate(BaseModel):
    contract_id: int
    sla_code: str = Field(..., max_length=50)
    sla_name: str = Field(..., max_length=200)
    response_time: Optional[str] = None
    resolution_time: Optional[str] = None
    penalty_rate: float = Field(default=0, ge=0)
    is_active: bool = True

class SLADefinitionUpdate(BaseModel):
    contract_id: Optional[int] = None
    sla_code: Optional[str] = Field(None, max_length=50)
    sla_name: Optional[str] = Field(None, max_length=200)
    response_time: Optional[str] = None
    resolution_time: Optional[str] = None
    penalty_rate: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

class SLADefinitionResponse(AuditMixin):
    id: int
    contract_id: int
    sla_code: str
    sla_name: str
    response_time: Optional[str]
    resolution_time: Optional[str]
    penalty_rate: float
    is_active: bool
