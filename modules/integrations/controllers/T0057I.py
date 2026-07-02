from modules.integrations.models.integration import IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0057', business_columns=['id', 'integration_code', 'integration_name', 'provider', 'config', 'credentials', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0057I', 'T0057 - Integration Configs', service,
                            IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigResponse)
