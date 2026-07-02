from modules.accounting.models.payment_term import PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0097', business_columns=['id', 'name', 'code', 'description', 'is_active', 'is_default'])
service = CrudService(repo)
router = create_crud_router('/api/T0097I', 'T0097 - Payment Methods', service,
                            PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse)
