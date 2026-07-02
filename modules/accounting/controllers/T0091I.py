from modules.accounting.models import PaymentCreate, PaymentUpdate, PaymentResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0091', business_columns=['id', 'payment_date', 'invoice_id', 'partner_id', 'amount', 'payment_method', 'reference', 'status', 'notes'])
service = CrudService(repo)
router = create_crud_router('/api/T0091I', 'T0091 - Payments', service,
                            PaymentCreate, PaymentUpdate, PaymentResponse)
