from modules.planning.models.planning import PlanCreate, PlanUpdate, PlanResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0024', business_columns=['id', 'plan_number', 'product_id', 'product_name', 'quantity', 'start_date', 'end_date', 'status', 'notes'])
service = CrudService(repo)
router = create_crud_router('/api/T0024I', 'T0024 - Production Plans', service,
                            PlanCreate, PlanUpdate, PlanResponse)
