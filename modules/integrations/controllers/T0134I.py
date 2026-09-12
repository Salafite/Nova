from modules.integrations.models.edi import (
    EdiPartnerCreate,
    EdiPartnerUpdate,
    EdiPartnerResponse,
    EDI_PARTNER_REPO,
)
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(EDI_PARTNER_REPO)
router = create_crud_router(
    '/api/T0134I',
    'T0134 - EDI Trading Partners',
    service,
    EdiPartnerCreate,
    EdiPartnerUpdate,
    EdiPartnerResponse,
)
