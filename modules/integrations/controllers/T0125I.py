from modules.integrations.models.edi import (
    EdiSkuMappingCreate,
    EdiSkuMappingUpdate,
    EdiSkuMappingResponse,
    EDI_SKU_MAPPING_REPO,
)
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(EDI_SKU_MAPPING_REPO)
router = create_crud_router(
    '/api/T0125I',
    'T0125 - EDI SKU Cross-Reference Matrix',
    service,
    EdiSkuMappingCreate,
    EdiSkuMappingUpdate,
    EdiSkuMappingResponse,
)
