from modules.sales.services.installment_service import InstallmentPlanService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models import InstallmentPlanCreate, InstallmentPlanUpdate, InstallmentPlanResponse

repo = CrudRepository('T0016', business_columns=['id', 'sales_order_id', 'plan_name', 'total_amount', 'num_installments', 'frequency_days', 'first_due_date', 'status', 'notes'])
service = InstallmentPlanService(repo)
router = create_crud_router('/api/T0016I', 'T0016 - Installment Plans', service,
                            InstallmentPlanCreate, InstallmentPlanUpdate, InstallmentPlanResponse)
