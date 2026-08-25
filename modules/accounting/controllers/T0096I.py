from fastapi import HTTPException
from modules.accounting.models.payment_term import PaymentTermCreate, PaymentTermUpdate, PaymentTermResponse
from modules.accounting.services.payment_term_service import PaymentTermService, PAYMENT_TERM_REPO
from modules.core.controllers.base import create_crud_router

repo = PAYMENT_TERM_REPO
service = PaymentTermService(repo)
router = create_crud_router(
    '/api/T0096I',
    'T0096 - Payment Terms',
    service,
    PaymentTermCreate,
    PaymentTermUpdate,
    PaymentTermResponse,
)


@router.get('/default', response_model=PaymentTermResponse)
def get_default_payment_term():
    """Get the currently configured default payment term."""
    term = service.get_default_term()
    if not term:
        raise HTTPException(404, "No default payment term found")
    return term
