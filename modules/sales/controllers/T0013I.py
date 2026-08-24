from modules.sales.services.sales_line_service import SalesLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models import SalesLineCreate, SalesLineUpdate, SalesLineResponse

repo = CrudRepository(
    'T0013',
    business_columns=[
        'id',
        'sales_order_id',
        'product_id',
        'product_name',
        'uom_id',
        'qty',
        'unit_price',
        'cost_price',
        'discount',
        'line_total',
        'line_number',
        'is_catch_weight',
        'pricing_uom_id',
        'unit_price_pricing_uom',
        'nominal_weight',
        'catch_weight_actual',
        'recalculated_total',
    ],
)
service = SalesLineService(repo)
router = create_crud_router('/api/T0013I', 'T0013 - Sales Lines', service,
                            SalesLineCreate, SalesLineUpdate, SalesLineResponse)
