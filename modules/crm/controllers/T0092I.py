from modules.crm.models.crm_lead import LeadCreate, LeadUpdate, LeadResponse
from modules.crm.services.lead_service import LeadService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0092', business_columns=['id', 'first_name', 'last_name', 'email', 'phone', 'company', 'title', 'source', 'status', 'assigned_to', 'notes'])
service = LeadService(repo)
router = create_crud_router('/api/T0092I', 'T0092 - Leads', service,
                            LeadCreate, LeadUpdate, LeadResponse)


@router.post('/{id}/qualify')
def qualify_lead(id: int):
    return service.qualify(id)


@router.post('/{id}/disqualify')
def disqualify_lead(id: int):
    return service.disqualify(id)


@router.post('/{id}/convert')
def convert_lead(id: int):
    return service.convert(id)
