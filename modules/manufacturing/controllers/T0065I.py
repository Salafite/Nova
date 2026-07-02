from modules.manufacturing.models.bom import BOMCreate, BOMUpdate, BOMResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0065', business_columns=['id', 'bom_code', 'bom_name', 'product_id', 'quantity', 'version', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0065I', 'T0065 - Bill of Materials', service,
                            BOMCreate, BOMUpdate, BOMResponse)
