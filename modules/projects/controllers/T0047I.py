from modules.projects.models.project import TimesheetCreate, TimesheetUpdate, TimesheetResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0047', business_columns=['id', 'employee_id', 'project_id', 'task_id', 'date', 'hours', 'description', 'status', 'approved_by', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0047I', 'T0047 - Timesheets', service,
                            TimesheetCreate, TimesheetUpdate, TimesheetResponse)
