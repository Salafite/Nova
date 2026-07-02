from modules.projects.models.project import ProjectCreate, ProjectUpdate, ProjectResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0044', business_columns=['id', 'project_code', 'project_name', 'description', 'department_id', 'manager_id', 'start_date', 'end_date', 'budget', 'status', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0044I', 'T0044 - Projects', service,
                            ProjectCreate, ProjectUpdate, ProjectResponse)
