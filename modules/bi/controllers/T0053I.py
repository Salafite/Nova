from modules.bi.models.analytics import KPIValueCreate, KPIValueUpdate, KPIValueResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0053', business_columns=['id', 'kpi_id', 'period', 'period_type', 'actual_value', 'target_value', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0053I', 'T0053 - KPI Values', service,
                            KPIValueCreate, KPIValueUpdate, KPIValueResponse)
