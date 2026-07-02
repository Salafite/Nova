from modules.enterprise.models.enterprise import ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0063', business_columns=['id', 'rule_code', 'rule_name', 'category', 'description', 'config', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0063I', 'T0063 - Compliance Rules', service,
                            ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse)
