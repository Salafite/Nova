from modules.maintenance.models.asset import MaintenanceScheduleCreate, MaintenanceScheduleUpdate, MaintenanceScheduleResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0042', business_columns=['id', 'asset_id', 'schedule_code', 'schedule_name', 'frequency_type', 'frequency_value', 'last_maintenance', 'next_maintenance', 'assigned_to', 'notes', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0042I', 'T0042 - Maintenance Schedules', service,
                            MaintenanceScheduleCreate, MaintenanceScheduleUpdate, MaintenanceScheduleResponse)
