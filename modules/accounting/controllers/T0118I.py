from modules.accounting.models.check_clearing import (
    CheckClearingRecordCreate,
    CheckClearingRecordUpdate,
    CheckClearingRecordResponse,
    CHECK_CLEARING_RECORD_REPO,
)
from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService

service = CrudService(CHECK_CLEARING_RECORD_REPO)

router = create_crud_router(
    '/api/T0118I',
    'T0118 - Check Clearing Records',
    service,
    CheckClearingRecordCreate,
    CheckClearingRecordUpdate,
    CheckClearingRecordResponse,
)
