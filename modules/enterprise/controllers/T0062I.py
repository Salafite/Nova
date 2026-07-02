from modules.enterprise.models.enterprise import DocumentCreate, DocumentUpdate, DocumentResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0062', business_columns=['id', 'document_code', 'document_name', 'entity_type', 'entity_id', 'file_path', 'file_type', 'file_size', 'version', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0062I', 'T0062 - Documents', service,
                            DocumentCreate, DocumentUpdate, DocumentResponse)
