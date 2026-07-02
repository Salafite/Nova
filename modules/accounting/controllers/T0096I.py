from modules.accounting.models.payment_term import PaymentTermCreate, PaymentTermUpdate, PaymentTermResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0096', business_columns=['id', 'name', 'code', 'description', 'due_days', 'discount_percentage', 'discount_days', 'is_active', 'is_default'])
service = CrudService(repo)
router = create_crud_router('/api/T0096I', 'T0096 - Payment Terms', service,
                            PaymentTermCreate, PaymentTermUpdate, PaymentTermResponse)
