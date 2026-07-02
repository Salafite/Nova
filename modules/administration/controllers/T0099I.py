from modules.administration.models.scheduler import ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskResponse
from modules.administration.services.scheduler_service import SchedulerService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0099', business_columns=['id', 'task_name', 'task_type', 'cron_expression', 'description', 'config', 'is_active', 'last_run_at', 'next_run_at', 'status'])
service = SchedulerService(repo)
router = create_crud_router('/api/T0099I', 'T0099 - Scheduled Tasks', service,
                            ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskResponse)

@router.put('/{id}/run-now')
def run_now(id: int):
    return {'ok': service.run_now(id)}
