from modules.hr.models.employee import LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0035', business_columns=['id', 'leave_code', 'leave_name', 'days_per_year', 'is_paid', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0035I', 'T0035 - Leave Types', service,
                            LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse)
