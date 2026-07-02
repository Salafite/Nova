from modules.core.services.base import CrudService

VALID_MFG_STATUS_TRANSITIONS = {
    'Pending': ['In Progress', 'Cancelled'],
    'In Progress': ['Completed', 'On Hold'],
    'On Hold': ['In Progress', 'Cancelled'],
    'Completed': [],
    'Cancelled': [],
}

class MfgOrderService(CrudService):
    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_MFG_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid MFG status transition: {old_status} -> {new_status}. Allowed: {allowed}')
        return super().update(id_val, payload)
