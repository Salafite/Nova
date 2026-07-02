from modules.hr.models.employee import CandidateCreate, CandidateUpdate, CandidateResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0040', business_columns=['id', 'candidate_code', 'full_name', 'email', 'phone', 'job_opening_id', 'status', 'resume_path', 'notes', 'applied_date', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0040I', 'T0040 - Candidates', service,
                            CandidateCreate, CandidateUpdate, CandidateResponse)
