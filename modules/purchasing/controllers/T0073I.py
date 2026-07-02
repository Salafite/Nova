from modules.purchasing.services.rfq_vendor_service import RFQVendorService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from modules.purchasing.models import RFQVendorCreate, RFQVendorUpdate, RFQVendorResponse

repo = CrudRepository('T0073', business_columns=['id', 'rfq_id', 'vendor_id', 'status'])
service = RFQVendorService(repo)
router = create_crud_router('/api/T0073I', 'T0073 - RFQ Vendors', service,
                            RFQVendorCreate, RFQVendorUpdate, RFQVendorResponse)
