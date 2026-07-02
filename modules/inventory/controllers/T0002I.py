from models import UOMConvCreate, UOMConvUpdate, UOMConvResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0002', business_columns=['id', 'from_uom_id', 'to_uom_id', 'factor'])
service = CrudService(repo)
router = create_crud_router('/api/T0002I', 'T0002 - UOM Conversion', service,
                            UOMConvCreate, UOMConvUpdate, UOMConvResponse)
