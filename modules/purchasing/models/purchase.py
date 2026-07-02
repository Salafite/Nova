from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class PurchaseOrderCreate(BaseModel):
    order_number: str = Field(..., max_length=30)
    supplier_id: int
    total: float = 0
    status: str = 'Pending'
    order_date: date = Field(default_factory=date.today)
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    converted_rfq_id: Optional[int] = None

class PurchaseOrderUpdate(BaseModel):
    order_number: Optional[str] = Field(None, max_length=30)
    supplier_id: Optional[int] = None
    total: Optional[float] = None
    status: Optional[str] = None
    order_date: Optional[date] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    converted_rfq_id: Optional[int] = None

class PurchaseOrderResponse(AuditMixin):
    id: int
    order_number: str
    supplier_id: int
    total: float
    status: str
    order_date: date
    expected_date: Optional[date]
    notes: Optional[str]
    converted_rfq_id: Optional[int]


class PurchaseLineCreate(BaseModel):
    purchase_order_id: int
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    uom_id: Optional[int] = None
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)
    line_number: int = 0

class PurchaseLineUpdate(BaseModel):
    purchase_order_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    uom_id: Optional[int] = None
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_total: Optional[float] = Field(None, ge=0)
    line_number: Optional[int] = None

class PurchaseLineResponse(AuditMixin):
    id: int
    purchase_order_id: int
    product_id: Optional[int]
    product_name: str
    uom_id: Optional[int]
    qty: float
    unit_price: float
    line_total: float
    line_number: int


class RequisitionCreate(BaseModel):
    req_number: str = Field(..., max_length=30)
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    department_id: Optional[int] = None
    requested_by: int
    status: str = 'Draft'
    priority: str = 'Medium'
    notes: Optional[str] = None

class RequisitionUpdate(BaseModel):
    req_number: Optional[str] = Field(None, max_length=30)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    department_id: Optional[int] = None
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None

class RequisitionResponse(AuditMixin):
    id: int
    req_number: str
    title: str
    description: Optional[str]
    department_id: Optional[int]
    requested_by: int
    approved_by: Optional[int]
    status: str
    priority: str
    notes: Optional[str]


class RequisitionLineCreate(BaseModel):
    requisition_id: int
    product_id: Optional[int] = None
    description: str = Field(..., max_length=500)
    qty: float = Field(..., gt=0)
    unit_price: float = Field(0, ge=0)
    total_price: float = Field(0, ge=0)
    uom_id: Optional[int] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    line_number: int = 0

class RequisitionLineUpdate(BaseModel):
    requisition_id: Optional[int] = None
    product_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=500)
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    total_price: Optional[float] = Field(None, ge=0)
    uom_id: Optional[int] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    line_number: Optional[int] = None

class RequisitionLineResponse(AuditMixin):
    id: int
    requisition_id: int
    product_id: Optional[int]
    description: str
    qty: float
    unit_price: float
    total_price: float
    uom_id: Optional[int]
    expected_date: Optional[date]
    notes: Optional[str]
    line_number: int


class RFQCreate(BaseModel):
    rfq_number: str = Field(..., max_length=30)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: str = 'Draft'
    due_date: Optional[date] = None
    notes: Optional[str] = None

class RFQUpdate(BaseModel):
    rfq_number: Optional[str] = Field(None, max_length=30)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None

class RFQResponse(AuditMixin):
    id: int
    rfq_number: str
    title: Optional[str]
    description: Optional[str]
    status: str
    due_date: Optional[date]
    notes: Optional[str]


class RFQLineCreate(BaseModel):
    rfq_id: int
    product_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=500)
    qty: float = Field(..., gt=0)
    uom_id: Optional[int] = None
    line_number: int = 0

class RFQLineUpdate(BaseModel):
    rfq_id: Optional[int] = None
    product_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=500)
    qty: Optional[float] = Field(None, gt=0)
    uom_id: Optional[int] = None
    line_number: Optional[int] = None

class RFQLineResponse(AuditMixin):
    id: int
    rfq_id: int
    product_id: Optional[int]
    description: Optional[str]
    qty: float
    uom_id: Optional[int]
    line_number: int


class RFQVendorCreate(BaseModel):
    rfq_id: int
    vendor_id: int
    status: str = 'Pending'

class RFQVendorUpdate(BaseModel):
    rfq_id: Optional[int] = None
    vendor_id: Optional[int] = None
    status: Optional[str] = None

class RFQVendorResponse(AuditMixin):
    id: int
    rfq_id: int
    vendor_id: int
    status: str


class RFQQuoteCreate(BaseModel):
    rfq_id: int
    vendor_id: Optional[int] = None
    rfq_vendor_id: Optional[int] = None
    line_id: int
    unit_price: float = 0
    total_price: float = 0
    delivery_days: Optional[int] = None
    currency: str = 'USD'
    valid_until: Optional[date] = None
    notes: Optional[str] = None

class RFQQuoteUpdate(BaseModel):
    rfq_id: Optional[int] = None
    vendor_id: Optional[int] = None
    rfq_vendor_id: Optional[int] = None
    line_id: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    delivery_days: Optional[int] = None
    currency: Optional[str] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None

class RFQQuoteResponse(AuditMixin):
    id: int
    rfq_id: int
    vendor_id: Optional[int]
    rfq_vendor_id: Optional[int]
    line_id: int
    unit_price: float
    total_price: float
    delivery_days: Optional[int]
    currency: str
    valid_until: Optional[date]
    notes: Optional[str]
