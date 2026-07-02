from modules.inventory.models.stock_level import StockLevelCreate, StockLevelUpdate, StockLevelResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reorder_level'])
service = CrudService(repo)
router = create_crud_router('/api/T0009I', 'T0009 - Stock Levels', service,
                            StockLevelCreate, StockLevelUpdate, StockLevelResponse)
