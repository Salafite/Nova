from modules.manufacturing.models.bom import BOMLineCreate, BOMLineUpdate, BOMLineResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0066', business_columns=['id', 'bom_id', 'component_id', 'component_name', 'quantity', 'uom_id', 'scrap_pct', 'line_number', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0066I', 'T0066 - BOM Lines', service,
                            BOMLineCreate, BOMLineUpdate, BOMLineResponse)
