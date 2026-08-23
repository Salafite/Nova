from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class TenantMixin(BaseModel):
    """Multi-tenant mixin providing business_id field."""
    business_id: Optional[int] = None


class AuditMixin(TenantMixin):
    """Audit mixin providing created/updated audit tracking and tenant business_id."""
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    update_number: int = 1

