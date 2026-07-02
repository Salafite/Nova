from modules.accounting.services.journal_service import JournalEntryService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.accounting.models import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse

repo = CrudRepository('T0027', business_columns=['id', 'entry_date', 'reference', 'description', 'status'])
service = JournalEntryService(repo)
router = create_crud_router('/api/T0027I', 'T0027 - Journal Entries', service,
                            JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse)
