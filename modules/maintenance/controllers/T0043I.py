from modules.maintenance.models.asset import MaintenanceWorkOrderCreate, MaintenanceWorkOrderUpdate, MaintenanceWorkOrderResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0043', business_columns=['id', 'asset_id', 'schedule_id', 'work_order_code', 'description', 'priority', 'status', 'assigned_to', 'scheduled_date', 'completed_date', 'cost', 'notes', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0043I', 'T0043 - Maintenance Work Orders', service,
                            MaintenanceWorkOrderCreate, MaintenanceWorkOrderUpdate, MaintenanceWorkOrderResponse)
