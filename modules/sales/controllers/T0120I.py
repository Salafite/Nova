from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router
from modules.sales.models.price_list import (
    VolumeTierBreakCreate,
    VolumeTierBreakUpdate,
    VolumeTierBreakResponse,
)

repo = CrudRepository(
    'T0120',
    business_columns=[
        'id', 'price_list_id', 'product_id', 'min_quantity', 'max_quantity',
        'unit_price', 'discount_percentage', 'discount_type', 'is_active'
    ]
)
service = CrudService(repo)
router = create_crud_router(
    '/api/T0120I',
    'T0120 - Volume Tier Breaks',
    service,
    VolumeTierBreakCreate,
    VolumeTierBreakUpdate,
    VolumeTierBreakResponse,
)
