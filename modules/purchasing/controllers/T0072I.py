from modules.purchasing.services.rfq_line_service import RFQLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RFQLineCreate, RFQLineUpdate, RFQLineResponse

repo = CrudRepository('T0072', business_columns=['id', 'rfq_id', 'product_id', 'description', 'qty', 'uom_id', 'line_number'])
service = RFQLineService(repo)
router = create_crud_router('/api/T0072I', 'T0072 - RFQ Lines', service,
                            RFQLineCreate, RFQLineUpdate, RFQLineResponse)
