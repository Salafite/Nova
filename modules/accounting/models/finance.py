from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin

# Chart of Accounts
class COACreate(BaseModel):
    account_code: str = Field(..., max_length=20)
    account_name: str = Field(..., max_length=100)
    account_type: str = Field(..., max_length=50) # Asset, Liability, Equity, Revenue, Expense
    currency: str = 'USD'
    is_active: bool = True
    business_id: Optional[int] = None

class COAUpdate(BaseModel):
    account_code: Optional[str] = Field(None, max_length=20)
    account_name: Optional[str] = Field(None, max_length=100)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None

class COAResponse(AuditMixin):
    id: int
    account_code: str
    account_name: str
    account_type: str
    currency: str = 'USD'
    is_active: bool = True


# Journal Entry
class JournalEntryCreate(BaseModel):
    entry_date: date
    reference: Optional[str] = Field(None, max_length=100)
    description: str = Field(..., max_length=255)
    status: str = 'Draft' # Draft, Posted, Cancelled
    business_id: Optional[int] = None

class JournalEntryUpdate(BaseModel):
    entry_date: Optional[date] = None
    reference: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    business_id: Optional[int] = None

class JournalEntryResponse(AuditMixin):
    id: int
    entry_date: date
    reference: Optional[str] = None
    description: str
    status: str = 'Draft'


# Journal Line
class JournalLineCreate(BaseModel):
    journal_entry_id: int
    account_id: int
    description: Optional[str] = Field(None, max_length=255)
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    business_id: Optional[int] = None

class JournalLineUpdate(BaseModel):
    journal_entry_id: Optional[int] = None
    account_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=255)
    debit: Optional[float] = Field(None, ge=0)
    credit: Optional[float] = Field(None, ge=0)
    business_id: Optional[int] = None

class JournalLineResponse(AuditMixin):
    id: int
    journal_entry_id: int
    account_id: int
    description: Optional[str] = None
    debit: float = 0
    credit: float = 0


# Invoice (Accounts Receivable / Payable)
class InvoiceCreate(BaseModel):
    invoice_number: Optional[str] = Field(None, max_length=50)
    invoice_type: str = 'Sales'
    partner_id: int
    sales_order_id: Optional[int] = None
    sales_rep_id: Optional[int] = None
    issue_date: date
    due_date: date
    freight_amount: float = 0
    discount_amount: float = 0
    total_amount: float = Field(..., ge=0)
    status: str = 'Unpaid'
    notes: Optional[str] = None
    business_id: Optional[int] = None

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = Field(None, max_length=50)
    invoice_type: Optional[str] = None
    partner_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    sales_rep_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    freight_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    notes: Optional[str] = None
    business_id: Optional[int] = None

class InvoiceResponse(AuditMixin):
    id: int
    invoice_number: str
    invoice_type: str
    partner_id: int
    sales_order_id: Optional[int] = None
    sales_rep_id: Optional[int] = None
    issue_date: date
    due_date: date
    freight_amount: float = 0
    discount_amount: float = 0
    total_amount: float
    status: str = 'Unpaid'
    notes: Optional[str] = None


# Payment
class PaymentCreate(BaseModel):
    payment_date: date
    invoice_id: Optional[int] = None
    partner_id: int
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50) # Cash, Bank Transfer, Card
    reference: Optional[str] = Field(None, max_length=100)
    status: str = 'Completed'
    business_id: Optional[int] = None

class PaymentUpdate(BaseModel):
    payment_date: Optional[date] = None
    invoice_id: Optional[int] = None
    partner_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    payment_method: Optional[str] = Field(None, max_length=50)
    reference: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    business_id: Optional[int] = None

class PaymentResponse(AuditMixin):
    id: int
    payment_date: date
    invoice_id: Optional[int] = None
    partner_id: int
    amount: float
    payment_method: str
    reference: Optional[str] = None
    status: str = 'Completed'
