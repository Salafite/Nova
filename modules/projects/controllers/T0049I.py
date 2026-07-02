from modules.projects.models.project import ContractCreate, ContractUpdate, ContractResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0049', business_columns=['id', 'contract_code', 'contract_name', 'customer_id', 'contract_type', 'start_date', 'end_date', 'value', 'status', 'notes', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0049I', 'T0049 - Contracts', service,
                            ContractCreate, ContractUpdate, ContractResponse)
