from modules.integrations.models.integration import SyncLogCreate, SyncLogResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0058', business_columns=['id', 'integration_id', 'entity_type', 'action', 'status', 'message', 'synced_at'])
service = CrudService(repo)
router = create_crud_router('/api/T0058I', 'T0058 - Sync Logs', service,
                            SyncLogCreate, None, SyncLogResponse)
