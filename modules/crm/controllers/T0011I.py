from modules.crm.models import SupplierCreate, SupplierUpdate, SupplierResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0011', business_columns=['id', 'name', 'category', 'phone', 'email', 'payment_terms', 'rating', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0011I', 'T0011 - Suppliers', service,
                            SupplierCreate, SupplierUpdate, SupplierResponse)
