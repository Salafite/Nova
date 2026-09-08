from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin
from modules.core.repositories.base import CrudRepository


# Customer Communication Event Models (t0122_customer_communications)
class CustomerCommunicationCreate(BaseModel):
    tracking_number: Optional[str] = Field(None, max_length=50)
    customer_id: int
    rule_id: Optional[int] = None
    template_id: Optional[int] = None
    channel: str = Field('EMAIL', max_length=30)
    communication_type: str = Field('REMINDER', max_length=50)
    recipient_address: str = Field(..., max_length=255)
    recipient_name: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = Field(None, max_length=255)
    message_body: str
    status: str = Field('PENDING', max_length=30)
    delivery_timestamp: Optional[datetime] = None
    read_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    external_message_id: Optional[str] = Field(None, max_length=255)
    statement_pdf_path: Optional[str] = Field(None, max_length=500)
    statement_pdf_size: Optional[int] = None
    invoice_count: int = 0
    total_balance: float = 0.0
    overdue_amount: float = 0.0
    payment_link: Optional[str] = None
    dispatched_by: Optional[int] = None
    is_automated: bool = True
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True
    business_id: Optional[int] = None


class CustomerCommunicationUpdate(BaseModel):
    tracking_number: Optional[str] = Field(None, max_length=50)
    customer_id: Optional[int] = None
    rule_id: Optional[int] = None
    template_id: Optional[int] = None
    channel: Optional[str] = Field(None, max_length=30)
    communication_type: Optional[str] = Field(None, max_length=50)
    recipient_address: Optional[str] = Field(None, max_length=255)
    recipient_name: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = Field(None, max_length=255)
    message_body: Optional[str] = None
    status: Optional[str] = Field(None, max_length=30)
    delivery_timestamp: Optional[datetime] = None
    read_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    external_message_id: Optional[str] = Field(None, max_length=255)
    statement_pdf_path: Optional[str] = Field(None, max_length=500)
    statement_pdf_size: Optional[int] = None
    invoice_count: Optional[int] = None
    total_balance: Optional[float] = None
    overdue_amount: Optional[float] = None
    payment_link: Optional[str] = None
    dispatched_by: Optional[int] = None
    is_automated: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class CustomerCommunicationResponse(AuditMixin):
    id: int
    tracking_number: str
    customer_id: int
    rule_id: Optional[int] = None
    template_id: Optional[int] = None
    channel: str
    communication_type: str
    recipient_address: str
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    message_body: str
    status: str
    delivery_timestamp: Optional[datetime] = None
    read_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    external_message_id: Optional[str] = None
    statement_pdf_path: Optional[str] = None
    statement_pdf_size: Optional[int] = None
    invoice_count: int = 0
    total_balance: float = 0.0
    overdue_amount: float = 0.0
    payment_link: Optional[str] = None
    dispatched_by: Optional[int] = None
    is_automated: bool = True
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True
    customer_name: Optional[str] = None
    rule_name: Optional[str] = None


# Delivery Status & Webhook Callback Models
class CommunicationStatusUpdate(BaseModel):
    status: str = Field(..., max_length=30)  # SENT, DELIVERED, READ, FAILED, CANCELLED
    external_message_id: Optional[str] = Field(None, max_length=255)
    delivery_timestamp: Optional[datetime] = None
    read_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CustomerCommunicationTimelineQuery(BaseModel):
    customer_id: Optional[int] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    communication_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


# Customer Reminder Preferences Models
class CustomerReminderPreferencesUpdate(BaseModel):
    is_vip: Optional[bool] = None
    exclude_from_reminders: Optional[bool] = None
    preferred_reminder_channel: Optional[str] = Field(None, max_length=30)  # EMAIL, WHATSAPP, BOTH, NONE
    reminder_phone: Optional[str] = Field(None, max_length=50)
    reminder_email: Optional[str] = Field(None, max_length=255)


class CustomerReminderPreferencesResponse(TenantMixin):
    customer_id: int
    customer_name: str
    is_vip: bool = False
    exclude_from_reminders: bool = False
    preferred_reminder_channel: str = 'EMAIL'
    reminder_phone: Optional[str] = None
    reminder_email: Optional[str] = None
    last_reminder_sent_at: Optional[datetime] = None
    last_statement_sent_at: Optional[datetime] = None


# CrudRepository
CUSTOMER_COMMUNICATION_REPO = CrudRepository(
    't0122_customer_communications',
    business_columns=[
        'id', 'tracking_number', 'customer_id', 'rule_id', 'template_id',
        'channel', 'communication_type', 'recipient_address', 'recipient_name',
        'subject', 'message_body', 'status', 'delivery_timestamp',
        'read_timestamp', 'error_message', 'external_message_id',
        'statement_pdf_path', 'statement_pdf_size', 'invoice_count',
        'total_balance', 'overdue_amount', 'payment_link', 'dispatched_by',
        'is_automated', 'metadata', 'is_active'
    ]
)
