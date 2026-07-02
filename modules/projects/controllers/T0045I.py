from modules.projects.models.project import ProjectTaskCreate, ProjectTaskUpdate, ProjectTaskResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0045', business_columns=['id', 'project_id', 'task_code', 'task_name', 'description', 'assigned_to', 'start_date', 'end_date', 'priority', 'status', 'estimated_hours', 'actual_hours', 'parent_task_id', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0045I', 'T0045 - Project Tasks', service,
                            ProjectTaskCreate, ProjectTaskUpdate, ProjectTaskResponse)
