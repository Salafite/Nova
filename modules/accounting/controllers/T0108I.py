from modules.accounting.models.check_clearing import (
    BankStatementCreate,
    BankStatementUpdate,
    BankStatementResponse,
    BANK_STATEMENT_REPO,
)
from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService

service = CrudService(BANK_STATEMENT_REPO)

router = create_crud_router(
    '/api/T0108I',
    'T0108 - Bank Statements',
    service,
    BankStatementCreate,
    BankStatementUpdate,
    BankStatementResponse,
)
