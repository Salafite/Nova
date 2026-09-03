from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router
from modules.sales.models.promotions import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)

repo = CrudRepository(
    'T0117',
    business_columns=[
        'id', 'code', 'name', 'description', 'promo_type', 'buy_product_id',
        'buy_quantity', 'get_product_id', 'get_quantity', 'get_discount_percentage',
        'customer_group', 'customer_id', 'start_date', 'end_date', 'usage_limit',
        'times_used', 'is_active'
    ]
)
service = CrudService(repo)
router = create_crud_router(
    '/api/T0117I',
    'T0117 - Promotional Campaign Rules',
    service,
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)
