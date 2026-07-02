from modules.administration.models.system import AuditLogCreate, AuditLogResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0023', business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at'])
service = CrudService(repo)
router = create_crud_router('/api/T0023I', 'T0023 - Audit Log', service,
                            AuditLogCreate, None, AuditLogResponse)
