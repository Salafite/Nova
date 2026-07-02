from modules.core.services.base import CrudService

VALID_REQ_STATUS_TRANSITIONS = {
    'Draft': ['Pending Approval', 'Cancelled'],
    'Pending Approval': ['Approved', 'Rejected', 'Draft'],
    'Approved': ['Partially Ordered', 'Ordered', 'Cancelled'],
    'Rejected': ['Draft'],
    'Partially Ordered': ['Ordered'],
    'Ordered': [],
    'Cancelled': [],
}

class RequisitionService(CrudService):
    def update(self, id_val, payload: dict):
        old = self.repo.get(id_val)
        if old and 'status' in payload:
            old_status = old.get('status')
            new_status = payload['status']
            if old_status != new_status:
                allowed = VALID_REQ_STATUS_TRANSITIONS.get(old_status, [])
                if new_status not in allowed:
                    from fastapi import HTTPException
                    raise HTTPException(400, f'Invalid requisition status transition: {old_status} -> {new_status}. Allowed: {allowed}')
        return super().update(id_val, payload)
