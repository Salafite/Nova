from models import ShopJobCreate, ShopJobUpdate, ShopJobResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0020', business_columns=['id', 'job_number', 'product_id', 'product_name', 'quantity', 'workstation', 'status'])
service = CrudService(repo)
router = create_crud_router('/api/T0020I', 'T0020 - Shop Floor Jobs', service,
                            ShopJobCreate, ShopJobUpdate, ShopJobResponse)
