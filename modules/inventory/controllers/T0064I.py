from modules.inventory.models.stock_movement import StockMovementCreate, StockMovementResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0064', business_columns=['id', 'product_id', 'warehouse_id', 'movement_type', 'reference_type', 'reference_id', 'qty_change', 'balance_after', 'description', 'movement_date'])
service = CrudService(repo)
router = create_crud_router('/api/T0064I', 'T0064 - Stock Movements', service,
                            StockMovementCreate, None, StockMovementResponse)
