from modules.accounting.models import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from modules.accounting.services.invoice_service import InvoiceService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0090', business_columns=['id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes', 'stripe_payment_intent_id', 'stripe_checkout_session_id', 'payment_link'])

service = InvoiceService(repo)
router = create_crud_router('/api/T0090I', 'T0090 - Invoices', service,
                            InvoiceCreate, InvoiceUpdate, InvoiceResponse)
