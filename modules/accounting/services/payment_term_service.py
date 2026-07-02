from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

repo = CrudRepository('T0096', business_columns=['id', 'name', 'code', 'description', 'due_days', 'discount_percentage', 'discount_days', 'is_active', 'is_default'])
PaymentTermService = CrudService(repo)
