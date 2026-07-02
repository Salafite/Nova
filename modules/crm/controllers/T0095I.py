from modules.crm.models.crm_lead import OpportunityLineCreate, OpportunityLineUpdate, OpportunityLineResponse
from modules.crm.services.opportunity_line_service import OpportunityLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0095', business_columns=['id', 'opportunity_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
service = OpportunityLineService(repo)
router = create_crud_router('/api/T0095I', 'T0095 - Opportunity Lines', service,
                            OpportunityLineCreate, OpportunityLineUpdate, OpportunityLineResponse)
