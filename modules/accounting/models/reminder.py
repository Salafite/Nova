from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin
from modules.core.repositories.base import CrudRepository


# AR Reminder Template Models (t0121_ar_reminder_templates)
class ARReminderTemplateCreate(BaseModel):
    template_code: Optional[str] = Field(None, max_length=50)
    template_name: str = Field(..., max_length=100)
    channel: str = Field('EMAIL', max_length=30)
    subject_template: Optional[str] = Field(None, max_length=255)
    body_template: str
    whatsapp_template_name: Optional[str] = Field(None, max_length=100)
    whatsapp_namespace: Optional[str] = Field(None, max_length=100)
    language: str = Field('en', max_length=10)
    is_default: bool = False
    is_active: bool = True
    description: Optional[str] = None
    business_id: Optional[int] = None


class ARReminderTemplateUpdate(BaseModel):
    template_code: Optional[str] = Field(None, max_length=50)
    template_name: Optional[str] = Field(None, max_length=100)
    channel: Optional[str] = Field(None, max_length=30)
    subject_template: Optional[str] = Field(None, max_length=255)
    body_template: Optional[str] = None
    whatsapp_template_name: Optional[str] = Field(None, max_length=100)
    whatsapp_namespace: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    business_id: Optional[int] = None


class ARReminderTemplateResponse(AuditMixin):
    id: int
    template_code: str
    template_name: str
    channel: str
    subject_template: Optional[str] = None
    body_template: str
    whatsapp_template_name: Optional[str] = None
    whatsapp_namespace: Optional[str] = None
    language: str = 'en'
    is_default: bool = False
    is_active: bool = True
    description: Optional[str] = None


# AR Reminder Rule Models (t0120_ar_reminder_rules)
class ARReminderRuleCreate(BaseModel):
    rule_name: str = Field(..., max_length=100)
    rule_code: Optional[str] = Field(None, max_length=50)
    trigger_type: str = Field('AGING_THRESHOLD', max_length=50)
    threshold_days: int = Field(30)
    frequency: str = Field('ONCE', max_length=30)
    schedule_day: Optional[str] = Field(None, max_length=20)
    schedule_time: Optional[str] = Field('09:00:00', max_length=20)
    channel: str = Field('ALL', max_length=30)
    template_id: Optional[int] = None
    attach_statement_pdf: bool = True
    include_payment_link: bool = True
    min_overdue_balance: float = Field(0.0, ge=0)
    exclude_vip: bool = True
    exclude_credit_hold: bool = False
    customer_group: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    description: Optional[str] = None
    business_id: Optional[int] = None


class ARReminderRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(None, max_length=100)
    rule_code: Optional[str] = Field(None, max_length=50)
    trigger_type: Optional[str] = Field(None, max_length=50)
    threshold_days: Optional[int] = None
    frequency: Optional[str] = Field(None, max_length=30)
    schedule_day: Optional[str] = Field(None, max_length=20)
    schedule_time: Optional[str] = Field(None, max_length=20)
    channel: Optional[str] = Field(None, max_length=30)
    template_id: Optional[int] = None
    attach_statement_pdf: Optional[bool] = None
    include_payment_link: Optional[bool] = None
    min_overdue_balance: Optional[float] = None
    exclude_vip: Optional[bool] = None
    exclude_credit_hold: Optional[bool] = None
    customer_group: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    description: Optional[str] = None
    business_id: Optional[int] = None


class ARReminderRuleResponse(AuditMixin):
    id: int
    rule_name: str
    rule_code: str
    trigger_type: str
    threshold_days: int
    frequency: str
    schedule_day: Optional[str] = None
    schedule_time: Optional[str] = None
    channel: str
    template_id: Optional[int] = None
    attach_statement_pdf: bool = True
    include_payment_link: bool = True
    min_overdue_balance: float = 0.0
    exclude_vip: bool = True
    exclude_credit_hold: bool = False
    customer_group: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None
    template_name: Optional[str] = None


# Dispatch Payloads and Batch Requests
class ReminderDispatchPayload(BaseModel):
    customer_id: int
    rule_id: Optional[int] = None
    template_id: Optional[int] = None
    channel: Optional[str] = None  # EMAIL, WHATSAPP, ALL, or None (use customer preference)
    custom_message: Optional[str] = None
    attach_statement_pdf: bool = True
    include_payment_link: bool = True
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    business_id: Optional[int] = None


class StatementDispatchPayload(BaseModel):
    customer_id: int
    channel: Optional[str] = 'EMAIL'  # EMAIL, WHATSAPP, BOTH
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    as_of_date: Optional[date] = None
    custom_message: Optional[str] = None
    business_id: Optional[int] = None


class BatchReminderRunRequest(BaseModel):
    rule_id: Optional[int] = None
    customer_ids: Optional[List[int]] = None
    as_of_date: Optional[date] = None
    dry_run: bool = False
    force: bool = False
    business_id: Optional[int] = None


class BatchReminderResult(BaseModel):
    total_evaluated: int = 0
    total_eligible: int = 0
    total_dispatched: int = 0
    total_skipped_vip: int = 0
    total_skipped_excluded: int = 0
    total_skipped_balance: int = 0
    total_skipped_channel: int = 0
    total_failed: int = 0
    dispatched_communications: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []


# CrudRepositories
AR_REMINDER_RULE_REPO = CrudRepository(
    't0120_ar_reminder_rules',
    business_columns=[
        'id', 'rule_name', 'rule_code', 'trigger_type', 'threshold_days',
        'frequency', 'schedule_day', 'schedule_time', 'channel', 'template_id',
        'attach_statement_pdf', 'include_payment_link', 'min_overdue_balance',
        'exclude_vip', 'exclude_credit_hold', 'customer_group', 'description',
        'is_active'
    ]
)

AR_REMINDER_TEMPLATE_REPO = CrudRepository(
    't0121_ar_reminder_templates',
    business_columns=[
        'id', 'template_code', 'template_name', 'channel', 'subject_template',
        'body_template', 'whatsapp_template_name', 'whatsapp_namespace',
        'language', 'is_default', 'description', 'is_active'
    ]
)
