from modules.inventory.models.product import AttrValueCreate, AttrValueUpdate, AttrValueResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0006', business_columns=['id', 'product_id', 'attribute_id', 'value_text', 'value_number', 'value_date', 'value_boolean'])
service = CrudService(repo)
router = create_crud_router('/api/T0006I', 'T0006 - Attr Values', service,
                            AttrValueCreate, AttrValueUpdate, AttrValueResponse)
