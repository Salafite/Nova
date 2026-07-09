from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_kpi_def_repo = CrudRepository('T0052', business_columns=['id', 'kpi_code', 'kpi_name', 'category', 'metric_unit', 'target_value', 'formula', 'is_active'])
_kpi_def_svc = CrudService(_kpi_def_repo)

_kpi_val_repo = CrudRepository('T0053', business_columns=['id', 'kpi_id', 'period', 'period_type', 'actual_value', 'target_value', 'is_active'])
_kpi_val_svc = CrudService(_kpi_val_repo)

_dash_repo = CrudRepository('T0054', business_columns=['id', 'dashboard_code', 'dashboard_name', 'owner_id', 'config', 'is_active'])
_dash_svc = CrudService(_dash_repo)

_widget_repo = CrudRepository('T0055', business_columns=['id', 'dashboard_id', 'widget_type', 'title', 'config', 'position', 'is_active'])
_widget_svc = CrudService(_widget_repo)


def register_tools():
    register_tool(Tool(name="list_kpis", description="List KPI definitions", input_schema={
        "type": "object", "properties": {"category": {"type": "string"}, "limit": {"type": "integer"}},
    }), _list_kpis)
    register_tool(Tool(name="get_kpi_values", description="Get values for a KPI", input_schema={
        "type": "object", "properties": {
            "kpi_id": {"type": "integer"}, "period_type": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["kpi_id"],
    }), _get_kpi_values)
    register_tool(Tool(name="list_dashboards", description="List BI dashboards", input_schema={
        "type": "object", "properties": {},
    }), _list_dashboards)
    register_tool(Tool(name="get_dashboard_widgets", description="Get widgets for a dashboard", input_schema={
        "type": "object", "properties": {"dashboard_id": {"type": "integer"}},
        "required": ["dashboard_id"],
    }), _get_widgets)


def _list_kpis(category: str = None, limit: int = 100):
    filters = {}
    if category: filters["category"] = category
    return _kpi_def_svc.list(filters=filters or None, limit=limit)

def _get_kpi_values(kpi_id: int, period_type: str = None, limit: int = 50):
    filters = {"kpi_id": kpi_id}
    if period_type: filters["period_type"] = period_type
    return _kpi_val_svc.list(filters=filters, limit=limit)

def _list_dashboards():
    return _dash_svc.list()

def _get_widgets(dashboard_id: int):
    return _widget_svc.list(filters={"dashboard_id": dashboard_id})


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="bi-mcp", version="1.0"))

if __name__ == "__main__":
    main()
