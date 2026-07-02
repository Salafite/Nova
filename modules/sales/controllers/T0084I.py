from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.price_list_item_service import PriceListItemService
from modules.sales.models.price_list import PriceListItemCreate, PriceListItemUpdate, PriceListItemResponse

repo = CrudRepository('T0084', business_columns=['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty', 'uom_id', 'effective_from', 'effective_to', 'line_number'])
service = PriceListItemService(repo)
router = create_crud_router('/api/T0084I', 'T0084 - Price List Items', service,
                            PriceListItemCreate, PriceListItemUpdate, PriceListItemResponse)
