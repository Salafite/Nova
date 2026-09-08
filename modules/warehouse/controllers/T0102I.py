from modules.warehouse.models import PickListItemCreate, PickListItemUpdate, PickListItemResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository(
    'T0102',
    business_columns=[
        'id',
        'pick_list_id',
        'sales_order_line_id',
        'product_id',
        'product_name',
        'qty_ordered',
        'qty_picked',
        'line_number',
        'batch_id',
        'batch_number',
        'expiry_date',
        'picked_batch_id',
        'picked_batch_number',
        'catch_weight_actual',
        'catch_weight_uom',
        'nominal_weight',
        'tolerance_pct',
        'tolerance_variance_pct',
        'tolerance_status',
        'supervisor_approved',
        'supervisor_approved_by',
        'supervisor_approved_at',
        'supervisor_notes',
    ],
)
service = CrudService(repo)
router = create_crud_router(
    '/api/T0102I',
    'T0102 - Pick List Items',
    service,
    PickListItemCreate,
    PickListItemUpdate,
    PickListItemResponse,
)
