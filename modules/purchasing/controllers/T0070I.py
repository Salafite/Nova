from modules.purchasing.services.requisition_line_service import RequisitionLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RequisitionLineCreate, RequisitionLineUpdate, RequisitionLineResponse

repo = CrudRepository('T0070', business_columns=['id', 'requisition_id', 'product_id', 'description', 'qty', 'unit_price', 'total_price', 'uom_id', 'expected_date', 'notes', 'line_number'])
service = RequisitionLineService(repo)
router = create_crud_router('/api/T0070I', 'T0070 - Purchase Requisition Lines', service,
                            RequisitionLineCreate, RequisitionLineUpdate, RequisitionLineResponse)
