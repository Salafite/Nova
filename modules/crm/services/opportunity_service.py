from modules.core.services.base import CrudService


STAGE_ORDER = [
    'Prospecting',
    'Qualification',
    'Needs Analysis',
    'Proposal',
    'Negotiation',
    'Closed Won',
    'Closed Lost',
]


class OpportunityService(CrudService):
    def create(self, payload: dict):
        payload['amount'] = float(payload.get('amount', 0))
        payload['probability'] = int(payload.get('probability', 10))
        return super().create(payload)

    def update(self, id_val, payload: dict):
        if 'probability' in payload:
            payload['probability'] = int(payload['probability'])
        return super().update(id_val, payload)
