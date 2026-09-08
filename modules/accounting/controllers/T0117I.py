from modules.accounting.models.check_clearing import (
    StatementTransactionCreate,
    StatementTransactionUpdate,
    StatementTransactionResponse,
    STATEMENT_TRANSACTION_REPO,
)
from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService

service = CrudService(STATEMENT_TRANSACTION_REPO)

router = create_crud_router(
    '/api/T0117I',
    'T0117 - Statement Transactions',
    service,
    StatementTransactionCreate,
    StatementTransactionUpdate,
    StatementTransactionResponse,
)
