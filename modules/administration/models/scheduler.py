from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class ScheduledTaskCreate(BaseModel):
    task_name: str = Field(..., max_length=200)
    task_type: str = Field(..., max_length=50)
    cron_expression: str = Field(..., max_length=50)
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: bool = True
    business_id: Optional[int] = None

class ScheduledTaskUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=200)
    task_type: Optional[str] = Field(None, max_length=50)
    cron_expression: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None

class ScheduledTaskResponse(AuditMixin):
    id: int
    task_name: str
    task_type: str
    cron_expression: str
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    status: str = 'Active'
