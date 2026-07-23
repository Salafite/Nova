from modules.inventory.models import ProductTypeCreate, ProductTypeUpdate, ProductTypeResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0107', business_columns=['id', 'name', 'code', 'description', 'color', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0107I', 'T0107 - Product Types', service,
                            ProductTypeCreate, ProductTypeUpdate, ProductTypeResponse)
