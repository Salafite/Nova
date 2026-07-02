from modules.core.services.base import CrudService
from fastapi import HTTPException, status


VALID_TRANSITIONS = {
    'New': ['Contacted', 'Disqualified'],
    'Contacted': ['Qualified', 'Disqualified'],
    'Qualified': ['Converted', 'Disqualified'],
    'Disqualified': [],
    'Converted': [],
}


class LeadService(CrudService):
    def qualify(self, id_val):
        lead = self.get(id_val)
        if not lead:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lead not found')
        if lead['status'] not in ('New', 'Contacted'):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f'Cannot qualify lead in status "{lead["status"]}"')
        return self.update(id_val, {'status': 'Qualified'})

    def disqualify(self, id_val):
        lead = self.get(id_val)
        if not lead:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lead not found')
        if lead['status'] == 'Converted':
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Cannot disqualify a converted lead')
        return self.update(id_val, {'status': 'Disqualified'})

    def convert(self, id_val):
        lead = self.get(id_val)
        if not lead:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lead not found')
        if lead['status'] != 'Qualified':
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f'Cannot convert lead in status "{lead["status"]}"')
        return self.update(id_val, {'status': 'Converted'})
