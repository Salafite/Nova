from modules.crm.models.crm_lead import OpportunityCreate, OpportunityUpdate, OpportunityResponse
from modules.crm.services.opportunity_service import OpportunityService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0094', business_columns=['id', 'opportunity_name', 'lead_id', 'customer_id', 'stage', 'amount', 'probability', 'expected_close_date', 'assigned_to', 'notes'])
service = OpportunityService(repo)
router = create_crud_router('/api/T0094I', 'T0094 - Opportunities', service,
                            OpportunityCreate, OpportunityUpdate, OpportunityResponse)
