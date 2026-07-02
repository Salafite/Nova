from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class SalesOrderCreate(BaseModel):
    order_number: str = Field(..., max_length=30)
    customer_id: int
    warehouse_id: Optional[int] = None
    subtotal: float = 0
    tax: float = 0
    grand_total: float = 0
    status: str = 'Pending'
    order_date: date = Field(default_factory=date.today)
    price_list_id: Optional[int] = None
    tax_rate_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    notes: Optional[str] = None

class SalesOrderUpdate(BaseModel):
    order_number: Optional[str] = Field(None, max_length=30)
    customer_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    grand_total: Optional[float] = None
    status: Optional[str] = None
    order_date: Optional[date] = None
    price_list_id: Optional[int] = None
    tax_rate_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    notes: Optional[str] = None

class SalesOrderResponse(AuditMixin):
    id: int
    order_number: str
    customer_id: int
    warehouse_id: Optional[int] = None
    subtotal: float
    tax: float
    grand_total: float
    status: str
    order_date: date
    price_list_id: Optional[int] = None
    tax_rate_id: Optional[int] = None
    payment_term_id: Optional[int] = None
    notes: Optional[str]


class SalesLineCreate(BaseModel):
    sales_order_id: int
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    uom_id: Optional[int] = None
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)
    line_number: int = 0

class SalesLineUpdate(BaseModel):
    sales_order_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    uom_id: Optional[int] = None
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_total: Optional[float] = Field(None, ge=0)
    line_number: Optional[int] = None

class SalesLineResponse(AuditMixin):
    id: int
    sales_order_id: int
    product_id: Optional[int]
    product_name: str
    uom_id: Optional[int]
    qty: float
    unit_price: float
    line_total: float
    line_number: int


class InstallmentPlanCreate(BaseModel):
    sales_order_id: int
    plan_name: str = 'Standard Plan'
    total_amount: float = Field(..., gt=0)
    num_installments: int = Field(..., gt=0)
    frequency_days: int = 30
    first_due_date: date
    status: str = 'Pending'
    notes: Optional[str] = None

class InstallmentPlanUpdate(BaseModel):
    sales_order_id: Optional[int] = None
    plan_name: Optional[str] = None
    total_amount: Optional[float] = Field(None, gt=0)
    num_installments: Optional[int] = Field(None, gt=0)
    frequency_days: Optional[int] = None
    first_due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class InstallmentPlanResponse(AuditMixin):
    id: int
    sales_order_id: int
    plan_name: str
    total_amount: float
    num_installments: int
    frequency_days: int
    first_due_date: date
    status: str
    notes: Optional[str]


class InstallPaymentCreate(BaseModel):
    installment_plan_id: int
    installment_number: int = Field(..., gt=0)
    due_date: date
    amount_due: float = Field(..., gt=0)
    amount_paid: float = 0
    paid_date: Optional[date] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    status: str = 'Pending'
    notes: Optional[str] = None

class InstallPaymentUpdate(BaseModel):
    installment_plan_id: Optional[int] = None
    installment_number: Optional[int] = Field(None, gt=0)
    due_date: Optional[date] = None
    amount_due: Optional[float] = Field(None, gt=0)
    amount_paid: Optional[float] = None
    paid_date: Optional[date] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None
    notes: Optional[str] = None

class InstallPaymentResponse(AuditMixin):
    id: int
    installment_plan_id: int
    installment_number: int
    due_date: date
    amount_due: float
    amount_paid: float
    paid_date: Optional[date]
    payment_method: Optional[str]
    status: str
    notes: Optional[str]
