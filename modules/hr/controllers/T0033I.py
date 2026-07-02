from modules.hr.models.employee import ShiftCreate, ShiftUpdate, ShiftResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0033', business_columns=['id', 'shift_code', 'shift_name', 'start_time', 'end_time', 'grace_minutes', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0033I', 'T0033 - Shifts', service,
                            ShiftCreate, ShiftUpdate, ShiftResponse)
