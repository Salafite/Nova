from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.commission_service import commission_payout_service
from modules.sales.models.commission import (
    CommissionPayoutCreate,
    CommissionPayoutUpdate,
    CommissionPayoutResponse,
)

repo = CrudRepository('T0108', business_columns=[
    'id', 'payout_number', 'sales_rep_id', 'invoice_id', 'payment_id',
    'rule_id', 'period_start', 'period_end', 'collected_amount',
    'realized_gross_margin', 'commission_rate', 'commission_amount',
    'discount_penalty', 'net_commission_amount', 'status', 'payment_date', 'notes'
])
router = create_crud_router(
    '/api/T0108I',
    'T0108 - Commission Payouts',
    commission_payout_service,
    CommissionPayoutCreate,
    CommissionPayoutUpdate,
    CommissionPayoutResponse,
)
