from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

VALID_JE_STATUS_TRANSITIONS = {
    'Draft': ['Posted', 'Cancelled'],
    'Posted': [],
    'Cancelled': [],
}

class JournalEntryService(CrudService):
    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            allowed = VALID_JE_STATUS_TRANSITIONS.get(old_status, [])
            if new_status not in allowed:
                from fastapi import HTTPException
                raise HTTPException(400, f'Invalid JE status transition: {old_status} -> {new_status}')
        if payload.get('status') == 'Posted':
            line_repo = CrudRepository('T0089', business_columns=['id', 'journal_entry_id', 'account_id', 'description', 'debit', 'credit', 'line_number'])
        return super().update(id_val, payload)

    def delete(self, id_val):
        old = self.repo.get(id_val)
        if old and old.get('status') == 'Posted':
            from fastapi import HTTPException
            raise HTTPException(400, 'Cannot delete a posted journal entry')
        return super().delete(id_val)
