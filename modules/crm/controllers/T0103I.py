from modules.crm.models.product_supplier import ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.core.services.base import CrudService

repo = CrudRepository('T0103', business_columns=['id', 'product_id', 'supplier_id', 'supplier_sku', 'unit_cost', 'lead_time_days', 'is_preferred'])
service = CrudService(repo)

router = create_crud_router('/api/T0103I', 'T0103 - Product Suppliers', service,
                            ProductSupplierCreate, ProductSupplierUpdate, ProductSupplierResponse)

@router.get('/by-product/{product_id}')
def get_by_product(product_id: int):
    return repo.list(filters={'product_id': product_id})

@router.get('/by-supplier/{supplier_id}')
def get_by_supplier(supplier_id: int):
    return repo.list(filters={'supplier_id': supplier_id})
