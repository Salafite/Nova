from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.price_list_service import PriceListService
from modules.sales.models.price_list import PriceListCreate, PriceListUpdate, PriceListResponse

repo = CrudRepository('T0083', business_columns=['id', 'name', 'code', 'description', 'currency', 'is_active', 'is_default'])
service = PriceListService(repo)
router = create_crud_router('/api/T0083I', 'T0083 - Price Lists', service,
                            PriceListCreate, PriceListUpdate, PriceListResponse)
