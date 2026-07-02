from modules.inventory.models.warehouse import WarehouseCreate, WarehouseUpdate, WarehouseResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0008', business_columns=['id', 'name', 'location', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0008I', 'T0008 - Warehouses', service,
                            WarehouseCreate, WarehouseUpdate, WarehouseResponse)
