from modules.integrations.models.edi import (
    EdiTransactionCreate,
    EdiTransactionUpdate,
    EdiTransactionResponse,
    EDI_TRANSACTION_REPO,
)
from modules.core.services.base import CrudService
from modules.core.controllers.base import create_crud_router

service = CrudService(EDI_TRANSACTION_REPO)
router = create_crud_router(
    '/api/T0136I',
    'T0136 - EDI Transactions',
    service,
    EdiTransactionCreate,
    EdiTransactionUpdate,
    EdiTransactionResponse,
)
