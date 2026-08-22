from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.commission_service import commission_rule_service
from modules.sales.models.commission import (
    CommissionRuleCreate,
    CommissionRuleUpdate,
    CommissionRuleResponse,
)

repo = CrudRepository('T0109', business_columns=[
    'id', 'rule_name', 'sales_rep_id', 'base_commission_rate',
    'min_margin_threshold', 'tier_rules', 'discount_penalty_rate',
    'is_active', 'notes'
])
router = create_crud_router(
    '/api/T0109I',
    'T0109 - Commission Rules',
    commission_rule_service,
    CommissionRuleCreate,
    CommissionRuleUpdate,
    CommissionRuleResponse,
)
