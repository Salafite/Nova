from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    title: str = Field(..., max_length=200)
    message: Optional[str] = None
    notification_type: str = 'Info'
    reference_type: Optional[str] = Field(None, max_length=30)
    reference_id: Optional[int] = None
    business_id: Optional[int] = None

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    business_id: Optional[int] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: Optional[str] = None
    notification_type: str = 'Info'
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
    business_id: Optional[int] = None

