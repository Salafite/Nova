from modules.hr.models.employee import JobOpeningCreate, JobOpeningUpdate, JobOpeningResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0039', business_columns=['id', 'job_code', 'job_title', 'department_id', 'designation_id', 'openings', 'description', 'requirements', 'status', 'posted_date', 'closing_date', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0039I', 'T0039 - Job Openings', service,
                            JobOpeningCreate, JobOpeningUpdate, JobOpeningResponse)
