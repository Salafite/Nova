from typing import Optional, List, Any, Dict, Union
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


class RMAReasonCode(str, Enum):
    DAMAGED = "damaged"
    EXPIRED = "expired"
    REJECTED = "rejected"
    WRONG_ITEM = "wrong_item"
    QC_FAILED = "qc_failed"
    DEFECTIVE = "defective"
    OVER_DELIVERY = "over_delivery"
    OTHER = "other"


class RMAStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    RETURNED = "Returned"
    CANCELLED = "Cancelled"


class QuarantineStatus(str, Enum):
    QUARANTINE = "Quarantine"
    RELEASED = "Released"
    SCRAPPED = "Scrapped"


class RMADisposition(str, Enum):
    RETURN_TO_VENDOR = "Return to Vendor"
    SCRAP = "Scrap"
    SUPPLIER_CREDIT = "Supplier Credit"
    REPLACEMENT = "Replacement"


class InspectionAttachment(BaseModel):
    id: Optional[str] = None
    filename: Optional[str] = None
    url: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by: Optional[int] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    data_base64: Optional[str] = None


class PurchaseReturnCreate(TenantMixin):
    return_number: Optional[str] = Field(None, max_length=30, description="RMA number. Auto-generated if omitted.")
    purchase_order_id: Optional[int] = None
    goods_receipt_id: Optional[int] = None
    supplier_id: int
    debit_memo_id: Optional[int] = None
    return_date: date = Field(default_factory=date.today)
    status: str = Field(default='Draft', max_length=30)
    total_amount: float = Field(default=0.0, ge=0)
    reason: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[Any]] = Field(default_factory=list)
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None


class PurchaseReturnUpdate(TenantMixin):
    return_number: Optional[str] = Field(None, max_length=30)
    purchase_order_id: Optional[int] = None
    goods_receipt_id: Optional[int] = None
    supplier_id: Optional[int] = None
    debit_memo_id: Optional[int] = None
    return_date: Optional[date] = None
    status: Optional[str] = None
    total_amount: Optional[float] = Field(None, ge=0)
    reason: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[Any]] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None


class PurchaseReturnResponse(AuditMixin):
    id: int
    return_number: str
    purchase_order_id: Optional[int] = None
    goods_receipt_id: Optional[int] = None
    supplier_id: int
    debit_memo_id: Optional[int] = None
    return_date: date
    status: str
    total_amount: float = 0.0
    reason: Optional[str] = None
    notes: Optional[str] = None
    attachments: Optional[List[Any]] = Field(default_factory=list)
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None


class PurchaseReturnLineCreate(TenantMixin):
    return_id: int
    product_id: Optional[int] = None
    product_name: str = Field(..., max_length=200)
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(default=0.0, ge=0)
    uom_id: Optional[int] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    reason_code: Optional[str] = Field(None, max_length=50)
    photos: Optional[List[Any]] = Field(default_factory=list)
    quarantine_status: Optional[str] = Field(default='Quarantine', max_length=30)
    disposition: Optional[str] = Field(default='Return to Vendor', max_length=50)
    line_number: int = 0


class PurchaseReturnLineUpdate(TenantMixin):
    return_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = Field(None, max_length=200)
    qty: Optional[float] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_total: Optional[float] = Field(None, ge=0)
    uom_id: Optional[int] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    reason_code: Optional[str] = Field(None, max_length=50)
    photos: Optional[List[Any]] = None
    quarantine_status: Optional[str] = Field(None, max_length=30)
    disposition: Optional[str] = Field(None, max_length=50)
    line_number: Optional[int] = None


class PurchaseReturnLineResponse(AuditMixin):
    id: int
    return_id: int
    product_id: Optional[int] = None
    product_name: str
    qty: float
    unit_price: float
    line_total: float
    uom_id: Optional[int] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    reason_code: Optional[str] = None
    photos: Optional[List[Any]] = Field(default_factory=list)
    quarantine_status: Optional[str] = 'Quarantine'
    disposition: Optional[str] = 'Return to Vendor'
    line_number: int


class DockRejectionLineItem(BaseModel):
    goods_receipt_line_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str
    qty_rejected: float = Field(..., gt=0)
    unit_price: float = Field(default=0.0, ge=0)
    uom_id: Optional[int] = None
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    reason_code: str = Field(default=RMAReasonCode.REJECTED.value)
    reason_details: Optional[str] = None
    photos: Optional[List[Any]] = Field(default_factory=list)
    disposition: Optional[str] = "Return to Vendor"


class ReceivingRejectionCreate(TenantMixin):
    goods_receipt_id: int
    purchase_order_id: Optional[int] = None
    supplier_id: int
    rejection_date: date = Field(default_factory=date.today)
    reason: Optional[str] = None
    notes: Optional[str] = None
    lines: List[DockRejectionLineItem] = Field(..., min_length=1)
    attachments: Optional[List[Any]] = Field(default_factory=list)


class RMAApprovalRequest(BaseModel):
    approved_by: Optional[int] = None
    notes: Optional[str] = None
    create_debit_memo: bool = True
    quarantine_inventory: bool = True

