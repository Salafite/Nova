from modules.accounting.models import COACreate, COAUpdate, COAResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0026', business_columns=['id', 'account_code', 'account_name', 'account_type', 'parent_id', 'currency', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0026I', 'T0026 - Chart of Accounts', service,
                            COACreate, COAUpdate, COAResponse)
