from modules.hr.models.employee import EmployeeDocumentCreate, EmployeeDocumentUpdate, EmployeeDocumentResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0032', business_columns=['id', 'employee_id', 'document_type', 'document_name', 'file_path', 'expiry_date', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0032I', 'T0032 - Employee Documents', service,
                            EmployeeDocumentCreate, EmployeeDocumentUpdate, EmployeeDocumentResponse)
