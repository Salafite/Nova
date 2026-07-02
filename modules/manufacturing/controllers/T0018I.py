from modules.manufacturing.services.mfg_service import MfgOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.manufacturing.models import MfgOrderCreate, MfgOrderUpdate, MfgOrderResponse

repo = CrudRepository('T0018', business_columns=['id', 'order_number', 'product_id', 'product_name', 'quantity', 'status', 'due_date', 'priority'])
service = MfgOrderService(repo)
router = create_crud_router('/api/T0018I', 'T0018 - Manufacturing Orders', service,
                            MfgOrderCreate, MfgOrderUpdate, MfgOrderResponse)
