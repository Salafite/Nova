from modules.warehouse.models.serial_batch import BatchNumberCreate, BatchNumberUpdate, BatchNumberResponse
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.warehouse.services.batch_number_service import BatchNumberService

repo = CrudRepository('T0088', business_columns=[
    'id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date',
    'quantity', 'warehouse_id', 'status', 'notes'
])
service = BatchNumberService(repo)
router = create_crud_router('/api/T0088I', 'T0088 - Batch Numbers', service,
                            BatchNumberCreate, BatchNumberUpdate, BatchNumberResponse)
