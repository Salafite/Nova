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


@router.get('/standard-terms', response_model=list[PaymentTermCreate])
def get_standard_payment_terms():
    """Get standard predefined payment term templates (Net 30, COD, Net 15, Net 60, 2/10 Net 30, Due on Receipt)."""
    return service.get_standard_terms()


@router.post('/seed-standard', response_model=list[PaymentTermResponse])
def seed_standard_payment_terms():
    """Seed standard payment terms into the database for the active tenant."""
    return service.seed_standard_terms()


# Ensure static routes (e.g. /standard-terms, /default, /seed-standard) are evaluated before /{id}
router.routes = (
    [r for r in router.routes if '{id}' not in getattr(r, 'path', '')]
    + [r for r in router.routes if '{id}' in getattr(r, 'path', '')]
)


