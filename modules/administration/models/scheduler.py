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

class ScheduledTaskUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=200)
    task_type: Optional[str] = Field(None, max_length=50)
    cron_expression: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None

class ScheduledTaskResponse(AuditMixin):
    id: int
    task_name: str
    task_type: str
    cron_expression: str
    description: Optional[str]
    config: Optional[dict]
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    status: str
