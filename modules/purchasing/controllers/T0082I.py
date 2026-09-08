from modules.purchasing.services.purchase_return_line_service import PurchaseReturnLineService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import PurchaseReturnLineCreate, PurchaseReturnLineUpdate, PurchaseReturnLineResponse

repo = CrudRepository(
    'T0082',
    business_columns=[
        'id',
        'return_id',
        'product_id',
        'product_name',
        'qty',
        'unit_price',
        'line_total',
        'uom_id',
        'batch_id',
        'batch_number',
        'expiry_date',
        'reason_code',
        'photos',
        'quarantine_status',
        'disposition',
        'line_number',
        'business_id',
        'is_active',
    ],
)
service = PurchaseReturnLineService(repo)
router = create_crud_router(
    '/api/T0082I',
    'T0082 - Purchase Return Lines',
    service,
    PurchaseReturnLineCreate,
    PurchaseReturnLineUpdate,
    PurchaseReturnLineResponse,
)
