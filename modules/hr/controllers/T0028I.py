from modules.hr.models.employee import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0028', business_columns=['id', 'department_code', 'department_name', 'parent_id', 'manager_id', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0028I', 'T0028 - Departments', service,
                            DepartmentCreate, DepartmentUpdate, DepartmentResponse)
