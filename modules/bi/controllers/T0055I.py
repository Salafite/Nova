from modules.bi.models.analytics import DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router

repo = CrudRepository('T0055', business_columns=['id', 'dashboard_id', 'widget_type', 'title', 'config', 'position', 'is_active'])
service = CrudService(repo)
router = create_crud_router('/api/T0055I', 'T0055 - Dashboard Widgets', service,
                            DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse)
