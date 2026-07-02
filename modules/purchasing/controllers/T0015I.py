from modules.purchasing.services.purchase_line_service import PurchaseLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import PurchaseLineCreate, PurchaseLineUpdate, PurchaseLineResponse

repo = CrudRepository('T0015', business_columns=['id', 'purchase_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total', 'line_number'])
service = PurchaseLineService(repo)
router = create_crud_router('/api/T0015I', 'T0015 - Purchase Lines', service,
                            PurchaseLineCreate, PurchaseLineUpdate, PurchaseLineResponse)
