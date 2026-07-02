from modules.administration.models import NavPermissionCreate, NavPermissionUpdate, NavPermissionResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0022', business_columns=['id', 'module_key', 'label', 'label_ar', 'icon', 'section', 'permission_key', 'sort_order', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0022I', 'T0022 - Nav Permissions', service,
                            NavPermissionCreate, NavPermissionUpdate, NavPermissionResponse)
