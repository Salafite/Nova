from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router
from modules.sales.models.price_list import (
    CustomerGroupPriceListCreate,
    CustomerGroupPriceListUpdate,
    CustomerGroupPriceListResponse,
)

repo = CrudRepository(
    'T0116',
    business_columns=[
        'id', 'customer_group', 'price_list_id', 'priority', 'description', 'is_active'
    ]
)
service = CrudService(repo)
router = create_crud_router(
    '/api/T0116I',
    'T0116 - Customer Group Price Mappings',
    service,
    CustomerGroupPriceListCreate,
    CustomerGroupPriceListUpdate,
    CustomerGroupPriceListResponse,
)
