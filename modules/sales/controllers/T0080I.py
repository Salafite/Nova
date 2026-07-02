from modules.sales.services.sales_return_line_service import SalesReturnLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models.sales_return import SalesReturnLineCreate, SalesReturnLineUpdate, SalesReturnLineResponse

repo = CrudRepository('T0080', business_columns=['id', 'return_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'uom_id', 'line_number'])
service = SalesReturnLineService(repo)
router = create_crud_router('/api/T0080I', 'T0080 - Sales Return Lines', service,
                            SalesReturnLineCreate, SalesReturnLineUpdate, SalesReturnLineResponse)
