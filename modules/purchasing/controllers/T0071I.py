from fastapi import HTTPException, Query, status
from modules.purchasing.services.rfq_service import RFQService
from modules.purchasing.services.purchase_order_service import PurchaseOrderService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RFQCreate, RFQUpdate, RFQResponse

repo = CrudRepository('T0071', business_columns=['id', 'rfq_number', 'title', 'description', 'status', 'due_date', 'notes'])
service = RFQService(repo)
router = create_crud_router('/api/T0071I', 'T0071 - RFQs', service,
                            RFQCreate, RFQUpdate, RFQResponse)

po_repo = CrudRepository('T0014', business_columns=['id', 'order_number', 'supplier_id', 'total', 'status', 'notes', 'converted_rfq_id'])
po_service = PurchaseOrderService(po_repo)

@router.post('/{id}/convert')
def convert_rfq_to_po(id: int, vendor_id: int = Query(..., description='Vendor ID whose quote to accept')):
    po = po_service.convert_from_rfq(id, vendor_id)
    if not po:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Failed to convert RFQ to purchase order')
    return po
