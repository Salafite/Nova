from modules.sales.services.sales_line_service import SalesLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models import SalesLineCreate, SalesLineUpdate, SalesLineResponse

repo = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total', 'line_number'])
service = SalesLineService(repo)
router = create_crud_router('/api/T0013I', 'T0013 - Sales Lines', service,
                            SalesLineCreate, SalesLineUpdate, SalesLineResponse)
