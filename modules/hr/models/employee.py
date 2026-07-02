from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class DepartmentCreate(BaseModel):
    department_code: str = Field(..., max_length=20)
    department_name: str = Field(..., max_length=100)
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: bool = True

class DepartmentUpdate(BaseModel):
    department_code: Optional[str] = Field(None, max_length=20)
    department_name: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

class DepartmentResponse(AuditMixin):
    id: int
    department_code: str
    department_name: str
    parent_id: Optional[int]
    manager_id: Optional[int]
    is_active: bool


class DesignationCreate(BaseModel):
    designation_code: str = Field(..., max_length=20)
    designation_name: str = Field(..., max_length=100)
    department_id: Optional[int] = None
    is_active: bool = True

class DesignationUpdate(BaseModel):
    designation_code: Optional[str] = Field(None, max_length=20)
    designation_name: Optional[str] = Field(None, max_length=100)
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class DesignationResponse(AuditMixin):
    id: int
    designation_code: str
    designation_name: str
    department_id: Optional[int]
    is_active: bool


class EmployeeCreate(BaseModel):
    employee_code: str = Field(..., max_length=30)
    full_name: str = Field(..., max_length=200)
    arabic_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = None
    national_id: Optional[str] = Field(None, max_length=30)
    passport_no: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=10)
    marital_status: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    employment_status: str = 'Active'
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: bool = True

class EmployeeUpdate(BaseModel):
    employee_code: Optional[str] = Field(None, max_length=30)
    full_name: Optional[str] = Field(None, max_length=200)
    arabic_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = None
    national_id: Optional[str] = Field(None, max_length=30)
    passport_no: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=10)
    marital_status: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    employment_status: Optional[str] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

class EmployeeResponse(AuditMixin):
    id: int
    employee_code: str
    full_name: str
    arabic_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    national_id: Optional[str]
    passport_no: Optional[str]
    gender: Optional[str]
    marital_status: Optional[str]
    birth_date: Optional[date]
    hire_date: Optional[date]
    termination_date: Optional[date]
    employment_status: str
    department_id: Optional[int]
    designation_id: Optional[int]
    manager_id: Optional[int]
    is_active: bool


class EmployeeContractCreate(BaseModel):
    employee_id: int
    contract_type: str = 'Permanent'
    start_date: date
    end_date: Optional[date] = None
    basic_salary: float = 0
    housing_allowance: float = 0
    transport_allowance: float = 0
    other_allowances: float = 0
    currency: str = 'USD'
    is_active: bool = True

class EmployeeContractUpdate(BaseModel):
    employee_id: Optional[int] = None
    contract_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    basic_salary: Optional[float] = None
    housing_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    other_allowances: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeContractResponse(AuditMixin):
    id: int
    employee_id: int
    contract_type: str
    start_date: date
    end_date: Optional[date]
    basic_salary: float
    housing_allowance: float
    transport_allowance: float
    other_allowances: float
    currency: str
    is_active: bool


class EmployeeDocumentCreate(BaseModel):
    employee_id: int
    document_type: str = Field(..., max_length=50)
    document_name: str = Field(..., max_length=200)
    file_path: Optional[str] = Field(None, max_length=500)
    expiry_date: Optional[date] = None
    is_active: bool = True

class EmployeeDocumentUpdate(BaseModel):
    employee_id: Optional[int] = None
    document_type: Optional[str] = Field(None, max_length=50)
    document_name: Optional[str] = Field(None, max_length=200)
    file_path: Optional[str] = Field(None, max_length=500)
    expiry_date: Optional[date] = None
    is_active: Optional[bool] = None

class EmployeeDocumentResponse(AuditMixin):
    id: int
    employee_id: int
    document_type: str
    document_name: str
    file_path: Optional[str]
    expiry_date: Optional[date]
    is_active: bool


class ShiftCreate(BaseModel):
    shift_code: str = Field(..., max_length=20)
    shift_name: str = Field(..., max_length=100)
    start_time: str = Field(..., max_length=10)
    end_time: str = Field(..., max_length=10)
    grace_minutes: Optional[int] = 0
    is_active: bool = True

class ShiftUpdate(BaseModel):
    shift_code: Optional[str] = Field(None, max_length=20)
    shift_name: Optional[str] = Field(None, max_length=100)
    start_time: Optional[str] = Field(None, max_length=10)
    end_time: Optional[str] = Field(None, max_length=10)
    grace_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class ShiftResponse(AuditMixin):
    id: int
    shift_code: str
    shift_name: str
    start_time: str
    end_time: str
    grace_minutes: Optional[int]
    is_active: bool


class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    shift_id: Optional[int] = None
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    status: str = 'Present'
    is_active: bool = True

class AttendanceUpdate(BaseModel):
    employee_id: Optional[int] = None
    date: Optional[date] = None
    shift_id: Optional[int] = None
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

class AttendanceResponse(AuditMixin):
    id: int
    employee_id: int
    date: date
    shift_id: Optional[int]
    clock_in: Optional[datetime]
    clock_out: Optional[datetime]
    status: str
    is_active: bool


class LeaveTypeCreate(BaseModel):
    leave_code: str = Field(..., max_length=20)
    leave_name: str = Field(..., max_length=100)
    days_per_year: float = 0
    is_paid: bool = True
    is_active: bool = True

class LeaveTypeUpdate(BaseModel):
    leave_code: Optional[str] = Field(None, max_length=20)
    leave_name: Optional[str] = Field(None, max_length=100)
    days_per_year: Optional[float] = None
    is_paid: Optional[bool] = None
    is_active: Optional[bool] = None

class LeaveTypeResponse(AuditMixin):
    id: int
    leave_code: str
    leave_name: str
    days_per_year: float
    is_paid: bool
    is_active: bool


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    days: float
    reason: Optional[str] = None
    status: str = 'Pending'
    approved_by: Optional[int] = None
    is_active: bool = True

class LeaveRequestUpdate(BaseModel):
    employee_id: Optional[int] = None
    leave_type_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[float] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[int] = None
    is_active: Optional[bool] = None

class LeaveRequestResponse(AuditMixin):
    id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    days: float
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    is_active: bool


class PayrollPeriodCreate(BaseModel):
    period_code: str = Field(..., max_length=20)
    period_name: str = Field(..., max_length=100)
    start_date: date
    end_date: date
    status: str = 'Open'
    is_active: bool = True

class PayrollPeriodUpdate(BaseModel):
    period_code: Optional[str] = Field(None, max_length=20)
    period_name: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

class PayrollPeriodResponse(AuditMixin):
    id: int
    period_code: str
    period_name: str
    start_date: date
    end_date: date
    status: str
    is_active: bool


class PayrollEntryCreate(BaseModel):
    employee_id: int
    payroll_period_id: int
    basic_salary: float = 0
    housing_allowance: float = 0
    transport_allowance: float = 0
    other_allowances: float = 0
    overtime: float = 0
    deductions: float = 0
    tax: float = 0
    gross_pay: float = 0
    net_pay: float = 0
    status: str = 'Draft'
    payment_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: bool = True

class PayrollEntryUpdate(BaseModel):
    employee_id: Optional[int] = None
    payroll_period_id: Optional[int] = None
    basic_salary: Optional[float] = None
    housing_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    other_allowances: Optional[float] = None
    overtime: Optional[float] = None
    deductions: Optional[float] = None
    tax: Optional[float] = None
    gross_pay: Optional[float] = None
    net_pay: Optional[float] = None
    status: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class PayrollEntryResponse(AuditMixin):
    id: int
    employee_id: int
    payroll_period_id: int
    basic_salary: float
    housing_allowance: float
    transport_allowance: float
    other_allowances: float
    overtime: float
    deductions: float
    tax: float
    gross_pay: float
    net_pay: float
    status: str
    payment_date: Optional[date]
    notes: Optional[str]
    is_active: bool


class JobOpeningCreate(BaseModel):
    job_code: str = Field(..., max_length=20)
    job_title: str = Field(..., max_length=200)
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    openings: int = 1
    description: Optional[str] = None
    requirements: Optional[str] = None
    status: str = 'Draft'
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None
    is_active: bool = True

class JobOpeningUpdate(BaseModel):
    job_code: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=200)
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    openings: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    status: Optional[str] = None
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None
    is_active: Optional[bool] = None

class JobOpeningResponse(AuditMixin):
    id: int
    job_code: str
    job_title: str
    department_id: Optional[int]
    designation_id: Optional[int]
    openings: int
    description: Optional[str]
    requirements: Optional[str]
    status: str
    posted_date: Optional[date]
    closing_date: Optional[date]
    is_active: bool


class CandidateCreate(BaseModel):
    candidate_code: str = Field(..., max_length=30)
    full_name: str = Field(..., max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    job_opening_id: Optional[int] = None
    status: str = 'Applied'
    resume_path: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    applied_date: date = Field(default_factory=date.today)
    is_active: bool = True

class CandidateUpdate(BaseModel):
    candidate_code: Optional[str] = Field(None, max_length=30)
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    job_opening_id: Optional[int] = None
    status: Optional[str] = None
    resume_path: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    applied_date: Optional[date] = None
    is_active: Optional[bool] = None

class CandidateResponse(AuditMixin):
    id: int
    candidate_code: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    job_opening_id: Optional[int]
    status: str
    resume_path: Optional[str]
    notes: Optional[str]
    applied_date: date
    is_active: bool
