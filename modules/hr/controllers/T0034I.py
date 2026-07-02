from modules.hr.services.attendance_service import AttendanceService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.hr.models.employee import AttendanceCreate, AttendanceUpdate, AttendanceResponse

repo = CrudRepository('T0034', business_columns=['id', 'employee_id', 'date', 'shift_id', 'clock_in', 'clock_out', 'status', 'is_active'])
service = AttendanceService(repo)
router = create_crud_router('/api/T0034I', 'T0034 - Attendance', service,
                            AttendanceCreate, AttendanceUpdate, AttendanceResponse)
