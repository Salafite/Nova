from modules.hr.models.employee import PayrollPeriodCreate, PayrollPeriodUpdate, PayrollPeriodResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0037', business_columns=['id', 'period_code', 'period_name', 'start_date', 'end_date', 'status', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0037I', 'T0037 - Payroll Periods', service,
                            PayrollPeriodCreate, PayrollPeriodUpdate, PayrollPeriodResponse)
