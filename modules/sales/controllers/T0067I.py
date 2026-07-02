from fastapi import APIRouter, HTTPException, status
from modules.sales.services.quotation_service import QuotationService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.models.quotations import QuotationCreate, QuotationUpdate, QuotationResponse

repo = CrudRepository('T0067', business_columns=['id', 'quote_number', 'customer_id', 'quote_date', 'valid_until', 'subtotal', 'tax', 'grand_total', 'status', 'notes', 'converted_order_id'])
service = QuotationService(repo)
router = create_crud_router('/api/T0067I', 'T0067 - Sales Quotations', service,
                            QuotationCreate, QuotationUpdate, QuotationResponse)

@router.post('/{id}/convert')
def convert_quote(id: int):
    order = service.convert_to_order(id)
    if not order:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Failed to convert quotation')
    return order
