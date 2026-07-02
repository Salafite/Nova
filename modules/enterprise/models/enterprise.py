from typing import Optional
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin


class TenantCreate(BaseModel):
    tenant_code: str = Field(..., max_length=50)
    tenant_name: str = Field(..., max_length=200)
    domain: Optional[str] = Field(None, max_length=255)
    config: Optional[str] = None
    is_active: bool = True

class TenantUpdate(BaseModel):
    tenant_code: Optional[str] = Field(None, max_length=50)
    tenant_name: Optional[str] = Field(None, max_length=200)
    domain: Optional[str] = Field(None, max_length=255)
    config: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(AuditMixin):
    id: int
    tenant_code: str
    tenant_name: str
    domain: Optional[str]
    config: Optional[str]
    is_active: bool


class WorkflowDefinitionCreate(BaseModel):
    workflow_code: str = Field(..., max_length=50)
    workflow_name: str = Field(..., max_length=200)
    entity_type: Optional[str] = Field(None, max_length=100)
    config: Optional[str] = None
    is_active: bool = True

class WorkflowDefinitionUpdate(BaseModel):
    workflow_code: Optional[str] = Field(None, max_length=50)
    workflow_name: Optional[str] = Field(None, max_length=200)
    entity_type: Optional[str] = Field(None, max_length=100)
    config: Optional[str] = None
    is_active: Optional[bool] = None

class WorkflowDefinitionResponse(AuditMixin):
    id: int
    workflow_code: str
    workflow_name: str
    entity_type: Optional[str]
    config: Optional[str]
    is_active: bool


class WorkflowInstanceCreate(BaseModel):
    workflow_id: int
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[int] = None
    status: str = 'Active'
    current_step: Optional[str] = None
    config: Optional[str] = None
    is_active: bool = True

class WorkflowInstanceUpdate(BaseModel):
    workflow_id: Optional[int] = None
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[int] = None
    status: Optional[str] = None
    current_step: Optional[str] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None

class WorkflowInstanceResponse(AuditMixin):
    id: int
    workflow_id: int
    entity_type: Optional[str]
    entity_id: Optional[int]
    status: str
    current_step: Optional[str]
    config: Optional[str]
    is_active: bool


class DocumentCreate(BaseModel):
    document_code: str = Field(..., max_length=50)
    document_name: str = Field(..., max_length=200)
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[int] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = Field(None, max_length=50)
    file_size: Optional[int] = None
    version: int = 1
    is_active: bool = True

class DocumentUpdate(BaseModel):
    document_code: Optional[str] = Field(None, max_length=50)
    document_name: Optional[str] = Field(None, max_length=200)
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[int] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = Field(None, max_length=50)
    file_size: Optional[int] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None

class DocumentResponse(AuditMixin):
    id: int
    document_code: str
    document_name: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    file_path: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    version: int
    is_active: bool


class ComplianceRuleCreate(BaseModel):
    rule_code: str = Field(..., max_length=50)
    rule_name: str = Field(..., max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    config: Optional[str] = None
    is_active: bool = True

class ComplianceRuleUpdate(BaseModel):
    rule_code: Optional[str] = Field(None, max_length=50)
    rule_name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None

class ComplianceRuleResponse(AuditMixin):
    id: int
    rule_code: str
    rule_name: str
    category: Optional[str]
    description: Optional[str]
    config: Optional[str]
    is_active: bool
