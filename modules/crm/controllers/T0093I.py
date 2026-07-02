from modules.crm.models.crm_lead import LeadActivityCreate, LeadActivityUpdate, LeadActivityResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0093', business_columns=['id', 'lead_id', 'activity_type', 'subject', 'description', 'activity_date', 'completed'])
service = CrudService(repo)
router = create_crud_router('/api/T0093I', 'T0093 - Lead Activities', service,
                            LeadActivityCreate, LeadActivityUpdate, LeadActivityResponse)
