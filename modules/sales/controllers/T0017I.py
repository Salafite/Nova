from modules.sales.models.sales import InstallPaymentCreate, InstallPaymentUpdate, InstallPaymentResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0017', business_columns=['id', 'installment_plan_id', 'installment_number', 'due_date', 'amount_due', 'amount_paid', 'paid_date', 'payment_method', 'status', 'notes'])
service = CrudService(repo)
router = create_crud_router('/api/T0017I', 'T0017 - Install Payments', service,
                            InstallPaymentCreate, InstallPaymentUpdate, InstallPaymentResponse)
