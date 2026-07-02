from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AuditMixin(BaseModel):
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    update_number: int = 1
