from modules.hr.services.payroll_service import PayrollEntryService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.hr.models.employee import PayrollEntryCreate, PayrollEntryUpdate, PayrollEntryResponse

repo = CrudRepository('T0038', business_columns=['id', 'employee_id', 'payroll_period_id', 'basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances', 'overtime', 'deductions', 'tax', 'gross_pay', 'net_pay', 'status', 'payment_date', 'notes', 'is_active'])
service = PayrollEntryService(repo)
router = create_crud_router('/api/T0038I', 'T0038 - Payroll Entries', service,
                            PayrollEntryCreate, PayrollEntryUpdate, PayrollEntryResponse)
