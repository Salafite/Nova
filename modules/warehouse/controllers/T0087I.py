from modules.warehouse.models.serial_batch import SerialNumberCreate, SerialNumberUpdate, SerialNumberResponse
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.warehouse.services.serial_number_service import SerialNumberService

repo = CrudRepository('T0087', business_columns=[
    'id', 'product_id', 'serial_number', 'status', 'warehouse_id',
    'purchase_order_line_id', 'sales_order_line_id', 'notes'
])
service = SerialNumberService(repo)
router = create_crud_router('/api/T0087I', 'T0087 - Serial Numbers', service,
                            SerialNumberCreate, SerialNumberUpdate, SerialNumberResponse)
