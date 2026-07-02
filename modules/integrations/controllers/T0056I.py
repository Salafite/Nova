from modules.integrations.models.integration import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0056', business_columns=['id', 'key_name', 'api_key', 'client_id', 'permissions', 'expires_at', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0056I', 'T0056 - API Keys', service,
                            ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse)
