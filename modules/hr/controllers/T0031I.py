from modules.hr.models.employee import EmployeeContractCreate, EmployeeContractUpdate, EmployeeContractResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0031', business_columns=['id', 'employee_id', 'contract_type', 'start_date', 'end_date', 'basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances', 'currency', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0031I', 'T0031 - Employee Contracts', service,
                            EmployeeContractCreate, EmployeeContractUpdate, EmployeeContractResponse)
