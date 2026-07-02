from modules.purchasing.services.purchase_order_service import PurchaseOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse

repo = CrudRepository('T0014', business_columns=['id', 'order_number', 'supplier_id', 'total', 'status', 'order_date', 'expected_date', 'notes', 'converted_rfq_id'])
service = PurchaseOrderService(repo)
router = create_crud_router('/api/T0014I', 'T0014 - Purchase Orders', service,
                            PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse)
