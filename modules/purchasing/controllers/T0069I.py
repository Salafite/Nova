from modules.purchasing.services.requisition_service import RequisitionService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RequisitionCreate, RequisitionUpdate, RequisitionResponse

repo = CrudRepository('T0069', business_columns=['id', 'req_number', 'title', 'description', 'department_id', 'requested_by', 'approved_by', 'status', 'priority', 'notes'])
service = RequisitionService(repo)
router = create_crud_router('/api/T0069I', 'T0069 - Purchase Requisitions', service,
                            RequisitionCreate, RequisitionUpdate, RequisitionResponse)
