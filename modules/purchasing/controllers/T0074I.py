from modules.purchasing.services.rfq_quote_service import RFQQuoteService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RFQQuoteCreate, RFQQuoteUpdate, RFQQuoteResponse

repo = CrudRepository('T0074', business_columns=['id', 'rfq_id', 'vendor_id', 'rfq_vendor_id', 'line_id', 'unit_price', 'total_price', 'delivery_days', 'currency', 'valid_until', 'notes'])
service = RFQQuoteService(repo)
router = create_crud_router('/api/T0074I', 'T0074 - RFQ Quotes', service,
                            RFQQuoteCreate, RFQQuoteUpdate, RFQQuoteResponse)
