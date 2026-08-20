from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_invoice_number

INVOICE_REPO = CrudRepository(
    'T0090',
    business_columns=[
        'id',
        'invoice_number',
        'invoice_type',
        'partner_id',
        'sales_order_id',
        'issue_date',
        'due_date',
        'total_amount',
        'status',
        'notes',
    ],
)


class InvoiceService(CrudService):
    def __init__(self, repo: CrudRepository = None):
        super().__init__(repo or INVOICE_REPO)

    def create(self, payload: dict, conn=None):
        if not payload.get('invoice_number') or not str(payload.get('invoice_number')).strip():
            payload['invoice_number'] = generate_invoice_number(conn=conn)
        return super().create(payload, conn=conn)
