from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.accounting.models.finance import JournalLineCreate, JournalLineUpdate, JournalLineResponse

repo = CrudRepository('T0089', business_columns=['id', 'journal_entry_id', 'account_id', 'description', 'debit', 'credit', 'is_active'])
service = type('JournalLineService', (object,), {'repo': repo, 'list': lambda self: repo.list(), 'get': lambda self, id: repo.get(id), 'create': lambda self, data: repo.create(data), 'update': lambda self, id, data: repo.update(id, data), 'delete': lambda self, id: repo.delete(id)})()

router = create_crud_router('/api/T0089I', 'T0089 - Journal Entry Lines', service,
                            JournalLineCreate, JournalLineUpdate, JournalLineResponse)
