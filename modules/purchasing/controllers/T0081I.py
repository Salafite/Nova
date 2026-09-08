from modules.purchasing.services.purchase_return_service import PurchaseReturnService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import PurchaseReturnCreate, PurchaseReturnUpdate, PurchaseReturnResponse

repo = CrudRepository(
    'T0081',
    business_columns=[
        'id',
        'return_number',
        'purchase_order_id',
        'goods_receipt_id',
        'supplier_id',
        'debit_memo_id',
        'return_date',
        'status',
        'total_amount',
        'reason',
        'notes',
        'attachments',
        'approved_at',
        'approved_by',
        'business_id',
        'is_active',
    ],
)
service = PurchaseReturnService(repo)
router = create_crud_router(
    '/api/T0081I',
    'T0081 - Purchase Returns',
    service,
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
    PurchaseReturnResponse,
)
