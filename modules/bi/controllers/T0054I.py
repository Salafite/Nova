from modules.bi.models.analytics import BIDashboardCreate, BIDashboardUpdate, BIDashboardResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0054', business_columns=['id', 'dashboard_code', 'dashboard_name', 'owner_id', 'config', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0054I', 'T0054 - BI Dashboards', service,
                            BIDashboardCreate, BIDashboardUpdate, BIDashboardResponse)
