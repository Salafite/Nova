from modules.projects.models.project import ResourceAllocationCreate, ResourceAllocationUpdate, ResourceAllocationResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0046', business_columns=['id', 'project_id', 'employee_id', 'allocation_pct', 'start_date', 'end_date', 'role', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0046I', 'T0046 - Resource Allocations', service,
                            ResourceAllocationCreate, ResourceAllocationUpdate, ResourceAllocationResponse)
