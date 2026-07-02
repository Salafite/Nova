from modules.inventory.models import UOMCreate, UOMUpdate, UOMResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0001', business_columns=['id', 'uom_code', 'uom_name', 'category', 'is_base_unit', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0001I', 'T0001 - UOM', service,
                            UOMCreate, UOMUpdate, UOMResponse)
