from modules.enterprise.models.enterprise import WorkflowInstanceCreate, WorkflowInstanceUpdate, WorkflowInstanceResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0061', business_columns=['id', 'workflow_id', 'entity_type', 'entity_id', 'status', 'current_step', 'config', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0061I', 'T0061 - Workflow Instances', service,
                            WorkflowInstanceCreate, WorkflowInstanceUpdate, WorkflowInstanceResponse)
