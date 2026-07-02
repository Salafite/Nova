from modules.inventory.models.product import AttrDefCreate, AttrDefUpdate, AttrDefResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0005', business_columns=['id', 'attribute_name', 'attribute_type', 'is_required', 'sort_order', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0005I', 'T0005 - Attr Definitions', service,
                            AttrDefCreate, AttrDefUpdate, AttrDefResponse)
