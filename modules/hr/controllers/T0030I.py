from modules.hr.models.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0030', business_columns=['id', 'employee_code', 'full_name', 'arabic_name', 'email', 'phone', 'address', 'national_id', 'passport_no', 'gender', 'marital_status', 'birth_date', 'hire_date', 'termination_date', 'employment_status', 'department_id', 'designation_id', 'manager_id', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0030I', 'T0030 - Employees', service,
                            EmployeeCreate, EmployeeUpdate, EmployeeResponse)
