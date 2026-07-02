from modules.enterprise.models.enterprise import TenantCreate, TenantUpdate, TenantResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0059', business_columns=['id', 'tenant_code', 'tenant_name', 'domain', 'config', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0059I', 'T0059 - Tenants', service,
                            TenantCreate, TenantUpdate, TenantResponse)
