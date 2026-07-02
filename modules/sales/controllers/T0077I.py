from modules.sales.models.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from modules.sales.services.delivery_service import DeliveryService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0077', business_columns=['id', 'delivery_number', 'sales_order_id', 'delivery_date', 'warehouse_id', 'status', 'notes'])
service = DeliveryService(repo)
router = create_crud_router('/api/T0077I', 'T0077 - Deliveries', service,
                            DeliveryCreate, DeliveryUpdate, DeliveryResponse)
