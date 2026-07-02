from modules.hr.services.leave_service import LeaveRequestService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.hr.models.employee import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse

repo = CrudRepository('T0036', business_columns=['id', 'employee_id', 'leave_type_id', 'start_date', 'end_date', 'days', 'reason', 'status', 'approved_by', 'is_active'])
service = LeaveRequestService(repo)
router = create_crud_router('/api/T0036I', 'T0036 - Leave Requests', service,
                            LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse)
