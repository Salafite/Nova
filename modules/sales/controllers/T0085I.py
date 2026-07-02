from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.sales.services.tax_rate_service import TaxRateService
from modules.sales.models.tax import TaxRateCreate, TaxRateUpdate, TaxRateResponse

repo = CrudRepository('T0085', business_columns=['id', 'name', 'code', 'rate', 'type', 'is_active', 'is_default', 'description'])
service = TaxRateService(repo)
router = create_crud_router('/api/T0085I', 'T0085 - Tax Rates', service,
                            TaxRateCreate, TaxRateUpdate, TaxRateResponse)
