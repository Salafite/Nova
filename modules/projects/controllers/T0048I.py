from modules.projects.models.project import ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0048', business_columns=['id', 'request_code', 'customer_id', 'subject', 'description', 'priority', 'status', 'assigned_to', 'resolution', 'resolved_date', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0048I', 'T0048 - Service Requests', service,
                            ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestResponse)
