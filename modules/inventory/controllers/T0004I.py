from modules.inventory.models import BarcodeCreate, BarcodeUpdate, BarcodeResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0004', business_columns=['id', 'product_id', 'barcode', 'barcode_type', 'is_primary'])
service = CrudService(repo)
router = create_crud_router('/api/T0004I', 'T0004 - Barcodes', service,
                            BarcodeCreate, BarcodeUpdate, BarcodeResponse)
