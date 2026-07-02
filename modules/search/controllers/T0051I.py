from modules.search.models.search import SearchIndexCreate, SearchIndexUpdate, SearchIndexResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0051', business_columns=['id', 'entity_type', 'entity_id', 'keywords', 'search_content', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0051I', 'T0051 - Search Index', service,
                            SearchIndexCreate, SearchIndexUpdate, SearchIndexResponse)
