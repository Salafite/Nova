from modules.bi.models.analytics import KPIDefinitionCreate, KPIDefinitionUpdate, KPIDefinitionResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0052', business_columns=['id', 'kpi_code', 'kpi_name', 'category', 'metric_unit', 'target_value', 'formula', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0052I', 'T0052 - KPI Definitions', service,
                            KPIDefinitionCreate, KPIDefinitionUpdate, KPIDefinitionResponse)
