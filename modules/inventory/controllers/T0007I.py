from models import ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0007', business_columns=['id', 'product_id', 'base_uom_id', 'purchase_uom_id', 'sales_uom_id', 'purchase_factor', 'sales_factor'])
service = CrudService(repo)
router = create_crud_router('/api/T0007I', 'T0007 - Product UOM', service,
                            ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse)
