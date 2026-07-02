from models import QCInspectionCreate, QCInspectionUpdate, QCInspectionResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0019', business_columns=['id', 'inspection_no', 'product_id', 'product_name', 'batch_no', 'result', 'inspector', 'inspection_date', 'notes'])
service = CrudService(repo)
router = create_crud_router('/api/T0019I', 'T0019 - QC Inspections', service,
                            QCInspectionCreate, QCInspectionUpdate, QCInspectionResponse)
