from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class SearchIndexCreate(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: int
    keywords: Optional[str] = None
    search_content: Optional[str] = None
    is_active: bool = True

class SearchIndexUpdate(BaseModel):
    entity_type: Optional[str] = Field(None, max_length=50)
    entity_id: Optional[int] = None
    keywords: Optional[str] = None
    search_content: Optional[str] = None
    is_active: Optional[bool] = None

class SearchIndexResponse(AuditMixin):
    id: int
    entity_type: str
    entity_id: int
    keywords: Optional[str]
    search_content: Optional[str]
    is_active: bool
