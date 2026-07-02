from modules.projects.models.project import SLADefinitionCreate, SLADefinitionUpdate, SLADefinitionResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0050', business_columns=['id', 'contract_id', 'sla_code', 'sla_name', 'response_time', 'resolution_time', 'penalty_rate', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0050I', 'T0050 - SLA Definitions', service,
                            SLADefinitionCreate, SLADefinitionUpdate, SLADefinitionResponse)
