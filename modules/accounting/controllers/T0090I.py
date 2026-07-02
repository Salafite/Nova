from modules.accounting.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes'])
service = CrudService(repo)
router = create_crud_router('/api/T0090I', 'T0090 - Invoices', service,
                            InvoiceCreate, InvoiceUpdate, InvoiceResponse)
