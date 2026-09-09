from modules.integrations.models.edi import (
    EdiSsccPalletCreate,
    EdiSsccPalletUpdate,
    EdiSsccPalletResponse,
    EDI_SSCC_PALLET_REPO,
)
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(EDI_SSCC_PALLET_REPO)
router = create_crud_router(
    '/api/T0137I',
    'T0137 - EDI SSCC Pallet Logistics',
    service,
    EdiSsccPalletCreate,
    EdiSsccPalletUpdate,
    EdiSsccPalletResponse,
)
