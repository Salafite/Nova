from modules.sales.services.quotation_line_service import QuotationLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models.quotations import QuotationLineCreate, QuotationLineUpdate, QuotationLineResponse

repo = CrudRepository('T0068', business_columns=['id', 'quotation_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total', 'line_number'])
service = QuotationLineService(repo)
router = create_crud_router('/api/T0068I', 'T0068 - Sales Quotation Lines', service,
                            QuotationLineCreate, QuotationLineUpdate, QuotationLineResponse)
