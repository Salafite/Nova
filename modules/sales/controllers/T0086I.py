from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.tax_rule_service import TaxRuleService
from modules.sales.models.tax import TaxRuleCreate, TaxRuleUpdate, TaxRuleResponse

repo = CrudRepository('T0086', business_columns=['id', 'tax_rate_id', 'applies_to', 'target_id', 'is_active'])
service = TaxRuleService(repo)
router = create_crud_router('/api/T0086I', 'T0086 - Tax Rules', service,
                            TaxRuleCreate, TaxRuleUpdate, TaxRuleResponse)
