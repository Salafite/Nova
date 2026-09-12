from modules.integrations.models.edi import (
    EdiCatalogItemCreate,
    EdiCatalogItemUpdate,
    EdiCatalogItemResponse,
    EDI_CATALOG_ITEM_REPO,
)
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(EDI_CATALOG_ITEM_REPO)
router = create_crud_router(
    '/api/T0138I',
    'T0138 - Supplier Catalog Sync',
    service,
    EdiCatalogItemCreate,
    EdiCatalogItemUpdate,
    EdiCatalogItemResponse,
)
