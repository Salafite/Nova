from modules.sales.models.delivery import DeliveryLineCreate, DeliveryLineUpdate, DeliveryLineResponse
from modules.sales.services.delivery_line_service import DeliveryLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0078', business_columns=['id', 'delivery_id', 'sales_order_line_id', 'product_id', 'product_name', 'qty_shipped', 'qty_ordered', 'uom_id', 'line_number'])
service = DeliveryLineService(repo)
router = create_crud_router('/api/T0078I', 'T0078 - Delivery Lines', service,
                            DeliveryLineCreate, DeliveryLineUpdate, DeliveryLineResponse)
