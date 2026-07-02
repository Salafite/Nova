from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository

repo = CrudRepository('T0097', business_columns=['id', 'name', 'code', 'description', 'is_active', 'is_default'])
PaymentMethodService = CrudService(repo)
