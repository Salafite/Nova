from modules.enterprise.models.enterprise import WorkflowDefinitionCreate, WorkflowDefinitionUpdate, WorkflowDefinitionResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0060', business_columns=['id', 'workflow_code', 'workflow_name', 'entity_type', 'config', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0060I', 'T0060 - Workflow Definitions', service,
                            WorkflowDefinitionCreate, WorkflowDefinitionUpdate, WorkflowDefinitionResponse)
