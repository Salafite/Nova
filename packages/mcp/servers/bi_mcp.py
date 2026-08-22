import base64
from typing import Optional, Dict, Any, Union
from datetime import date, datetime

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource

from modules.bi.services.executive_analytics_service import (
    ExecutiveAnalyticsService,
    executive_analytics_service as default_executive_analytics_svc,
)
from modules.bi.services.customer_profitability_service import (
    CustomerProfitabilityService,
    customer_profitability_service as default_customer_profitability_svc,
)
from modules.bi.services.delivery_analytics_service import (
    DeliveryAnalyticsService,
    delivery_analytics_service as default_delivery_analytics_svc,
)
from modules.sales.services.commission_service import (
    CommissionService,
    commission_service as default_commission_svc,
)
from modules.bi.services.excel_export_service import (
    ExcelExportService,
    excel_export_service as default_excel_export_svc,
)
from modules.bi.services.pdf_export_service import (
    PdfExportService,
    pdf_export_service as default_pdf_export_svc,
)


_kpi_def_repo = CrudRepository('T0052', business_columns=['id', 'kpi_code', 'kpi_name', 'category', 'metric_unit', 'target_value', 'formula', 'is_active'])
_kpi_def_svc = CrudService(_kpi_def_repo)

_kpi_val_repo = CrudRepository('T0053', business_columns=['id', 'kpi_id', 'period', 'period_type', 'actual_value', 'target_value', 'is_active'])
_kpi_val_svc = CrudService(_kpi_val_repo)

_dash_repo = CrudRepository('T0054', business_columns=['id', 'dashboard_code', 'dashboard_name', 'owner_id', 'config', 'is_active'])
_dash_svc = CrudService(_dash_repo)

_widget_repo = CrudRepository('T0055', business_columns=['id', 'dashboard_id', 'widget_type', 'title', 'config', 'position', 'is_active'])
_widget_svc = CrudService(_widget_repo)

_executive_analytics_svc = default_executive_analytics_svc
_customer_profitability_svc = default_customer_profitability_svc
_delivery_analytics_svc = default_delivery_analytics_svc
_commission_svc = default_commission_svc
_excel_export_svc = default_excel_export_svc
_pdf_export_svc = default_pdf_export_svc


def _parse_date(d: Union[str, date, None]) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def register_tools():
    # Standard BI Tools
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

    # Executive Analytics & Margin Optimization Tools
    register_tool(
        Tool(
            name="get_executive_margin_summary",
            description="Calculate real-time executive gross profit margin summary factoring gross sales, customer discounts, COGS, freight costs, margin %, and prior period comparisons.",
            input_schema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Reporting interval (Daily, Weekly, Monthly, Quarterly, YTD, Custom)"},
                    "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "product_id": {"type": "integer", "description": "Optional filter by product SKU ID"},
                    "brand": {"type": "string", "description": "Optional filter by brand"},
                    "sales_rep_id": {"type": "integer", "description": "Optional filter by sales representative ID"},
                    "customer_id": {"type": "integer", "description": "Optional filter by customer account ID"},
                    "warehouse_id": {"type": "integer", "description": "Optional filter by fulfillment warehouse ID"},
                    "delivery_route": {"type": "string", "description": "Optional filter by logistics delivery route"},
                },
            },
        ),
        _get_executive_margin_summary,
    )

    register_tool(
        Tool(
            name="get_product_category_margins",
            description="Get gross profit margin breakdown and revenue share by product category and SKU line, identifying low-margin lines (<15%).",
            input_schema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Reporting interval (Daily, Weekly, Monthly, Quarterly, YTD, Custom)"},
                    "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "sales_rep_id": {"type": "integer", "description": "Optional filter by sales rep ID"},
                    "customer_id": {"type": "integer", "description": "Optional filter by customer ID"},
                    "warehouse_id": {"type": "integer", "description": "Optional filter by warehouse ID"},
                    "delivery_route": {"type": "string", "description": "Optional filter by delivery route"},
                    "min_margin_pct": {"type": "number", "description": "Filter categories/SKUs above minimum margin percentage"},
                    "max_margin_pct": {"type": "number", "description": "Filter categories/SKUs below maximum margin percentage"},
                    "include_skus": {"type": "boolean", "description": "Whether to include SKU-level line items in the response"},
                    "limit": {"type": "integer", "description": "Max SKU items returned if include_skus is true (default 100)"},
                },
            },
        ),
        _get_product_category_margins,
    )

    register_tool(
        Tool(
            name="get_customer_profitability_matrix",
            description="Segment and rank customer accounts into a 4-quadrant strategic profitability matrix (Core Stars Q1, Volume Risks Q2, High Potential Q3, Drain Accounts Q4).",
            input_schema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Reporting interval (Daily, Weekly, Monthly, Quarterly, YTD, Custom)"},
                    "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "quadrant": {"type": "string", "description": "Filter by quadrant code (Q1, Q2, Q3, Q4) or name (e.g. Core Stars)"},
                    "sales_rep_id": {"type": "integer", "description": "Optional filter by sales rep ID"},
                    "customer_id": {"type": "integer", "description": "Optional filter by customer ID"},
                    "warehouse_id": {"type": "integer", "description": "Optional filter by warehouse ID"},
                    "delivery_route": {"type": "string", "description": "Optional filter by delivery route"},
                    "margin_threshold_pct": {"type": "number", "description": "Threshold percentage to distinguish high vs low margin accounts (default 15.0)"},
                    "revenue_threshold": {"type": "number", "description": "Threshold dollar volume to distinguish high vs low volume accounts (defaults to cohort median)"},
                    "min_margin_pct": {"type": "number", "description": "Minimum margin % filter"},
                    "max_margin_pct": {"type": "number", "description": "Maximum margin % filter"},
                },
            },
        ),
        _get_customer_profitability_matrix,
    )

    register_tool(
        Tool(
            name="calculate_sales_rep_commissions",
            description="Calculate sales representative commissions tied strictly to paid invoices, collected cash, and realized gross profit rather than top-line bookings.",
            input_schema={
                "type": "object",
                "properties": {
                    "sales_rep_id": {"type": "integer", "description": "Sales representative ID (if omitted, summarizes all sales reps)"},
                    "period_start": {"type": "string", "description": "Period start date in YYYY-MM-DD format"},
                    "period_end": {"type": "string", "description": "Period end date in YYYY-MM-DD format"},
                    "rule_id": {"type": "integer", "description": "Optional commission rule ID to apply"},
                    "include_pending": {"type": "boolean", "description": "Whether to include unpaid/pending invoices (default true)"},
                },
            },
        ),
        _calculate_sales_rep_commissions,
    )

    register_tool(
        Tool(
            name="get_delivery_fulfillment_metrics",
            description="Get delivery route fulfillment metrics, on-time delivery (OTD) rates, completion rates, and freight cost efficiency.",
            input_schema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Reporting interval (Daily, Weekly, Monthly, Quarterly, YTD, Custom)"},
                    "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "delivery_route": {"type": "string", "description": "Filter by route code or name"},
                    "warehouse_id": {"type": "integer", "description": "Filter by dispatch warehouse ID"},
                    "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                    "sales_rep_id": {"type": "integer", "description": "Filter by sales rep ID"},
                    "include_warehouses": {"type": "boolean", "description": "Whether to include warehouse dispatch metrics (default true)"},
                },
            },
        ),
        _get_delivery_fulfillment_metrics,
    )

    register_tool(
        Tool(
            name="export_executive_analytics_report",
            description="Export complete executive analytics financial reports as PDF, Excel (.xlsx), or structured JSON for board and bank review.",
            input_schema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "description": "Export document format: 'pdf', 'excel', or 'json' (default 'json')"},
                    "period": {"type": "string", "description": "Reporting interval (Daily, Weekly, Monthly, Quarterly, YTD, Custom)"},
                    "date_from": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "date_to": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "sales_rep_id": {"type": "integer", "description": "Optional sales rep ID filter"},
                    "customer_id": {"type": "integer", "description": "Optional customer ID filter"},
                    "warehouse_id": {"type": "integer", "description": "Optional warehouse ID filter"},
                    "delivery_route": {"type": "string", "description": "Optional delivery route filter"},
                    "confidentiality_notice": {"type": "string", "description": "Confidentiality header statement"},
                },
            },
        ),
        _export_executive_analytics_report,
    )

    register_resource(
        Resource(uri="nova://bi/executive-margin", name="Executive Margin Analytics", description="Executive gross profit margin performance and KPI summary"),
        lambda: _get_executive_margin_summary(),
    )


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


# ---------------------------------------------------------------------------
# Executive Analytics & Margin Optimization Handlers
# ---------------------------------------------------------------------------

def _get_executive_margin_summary(
    period: str = "Monthly",
    date_from: str = None,
    date_to: str = None,
    product_id: int = None,
    brand: str = None,
    sales_rep_id: int = None,
    customer_id: int = None,
    warehouse_id: int = None,
    delivery_route: str = None,
):
    flt = {
        "period": period,
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "product_id": product_id,
        "brand": brand,
        "sales_rep_id": sales_rep_id,
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "delivery_route": delivery_route,
    }
    flt = {k: v for k, v in flt.items() if v is not None}
    res = _executive_analytics_svc.get_margin_summary(filters=flt)
    return res.model_dump() if hasattr(res, "model_dump") else res


def _get_product_category_margins(
    period: str = "Monthly",
    date_from: str = None,
    date_to: str = None,
    sales_rep_id: int = None,
    customer_id: int = None,
    warehouse_id: int = None,
    delivery_route: str = None,
    min_margin_pct: float = None,
    max_margin_pct: float = None,
    include_skus: bool = False,
    limit: int = 100,
):
    flt = {
        "period": period,
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "sales_rep_id": sales_rep_id,
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "delivery_route": delivery_route,
        "min_margin_pct": min_margin_pct,
        "max_margin_pct": max_margin_pct,
    }
    flt = {k: v for k, v in flt.items() if v is not None}
    cat_res = _executive_analytics_svc.get_category_margins(filters=flt)
    result = cat_res.model_dump() if hasattr(cat_res, "model_dump") else cat_res
    if include_skus:
        sku_res = _executive_analytics_svc.get_sku_margins(filters=flt, limit=limit)
        sku_dump = sku_res.model_dump() if hasattr(sku_res, "model_dump") else sku_res
        result["skus"] = sku_dump.get("items", [])
    return result


def _get_customer_profitability_matrix(
    period: str = "Monthly",
    date_from: str = None,
    date_to: str = None,
    quadrant: str = None,
    sales_rep_id: int = None,
    customer_id: int = None,
    warehouse_id: int = None,
    delivery_route: str = None,
    margin_threshold_pct: float = 15.0,
    revenue_threshold: float = None,
    min_margin_pct: float = None,
    max_margin_pct: float = None,
):
    flt = {
        "period": period,
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "quadrant": quadrant,
        "sales_rep_id": sales_rep_id,
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "delivery_route": delivery_route,
        "min_margin_pct": min_margin_pct,
        "max_margin_pct": max_margin_pct,
    }
    flt = {k: v for k, v in flt.items() if v is not None}
    res = _customer_profitability_svc.get_customer_profitability_matrix(
        filters=flt,
        margin_threshold_pct=margin_threshold_pct,
        revenue_threshold=revenue_threshold,
    )
    return res.model_dump() if hasattr(res, "model_dump") else res


def _calculate_sales_rep_commissions(
    sales_rep_id: int = None,
    period_start: str = None,
    period_end: str = None,
    rule_id: int = None,
    include_pending: bool = True,
):
    p_start = _parse_date(period_start)
    p_end = _parse_date(period_end)

    if sales_rep_id is not None:
        stmt = _commission_svc.calculate_statement(
            sales_rep_id=sales_rep_id,
            period_start=p_start,
            period_end=p_end,
            rule_id=rule_id,
            include_pending=include_pending,
        )
        return stmt.model_dump() if hasattr(stmt, "model_dump") else stmt
    else:
        summaries = _commission_svc.get_commission_summaries(
            period_start=p_start,
            period_end=p_end,
            sales_rep_id=None,
        )
        return [s.model_dump() if hasattr(s, "model_dump") else s for s in summaries]


def _get_delivery_fulfillment_metrics(
    period: str = "Monthly",
    date_from: str = None,
    date_to: str = None,
    delivery_route: str = None,
    warehouse_id: int = None,
    customer_id: int = None,
    sales_rep_id: int = None,
    include_warehouses: bool = True,
):
    flt = {
        "period": period,
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "delivery_route": delivery_route,
        "warehouse_id": warehouse_id,
        "customer_id": customer_id,
        "sales_rep_id": sales_rep_id,
    }
    flt = {k: v for k, v in flt.items() if v is not None}
    summary = _delivery_analytics_svc.get_delivery_fulfillment_summary(filters=flt)
    res = summary.model_dump() if hasattr(summary, "model_dump") else summary
    if include_warehouses:
        wh_items = _delivery_analytics_svc.get_warehouse_efficiency(filters=flt)
        res["warehouses"] = [w.model_dump() if hasattr(w, "model_dump") else w for w in wh_items]
    return res


def _export_executive_analytics_report(
    format: str = "json",
    period: str = "Monthly",
    date_from: str = None,
    date_to: str = None,
    sales_rep_id: int = None,
    customer_id: int = None,
    warehouse_id: int = None,
    delivery_route: str = None,
    confidentiality_notice: str = "CONFIDENTIAL - BOARD & EXECUTIVE REVIEW ONLY",
):
    flt = {
        "period": period,
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "sales_rep_id": sales_rep_id,
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "delivery_route": delivery_route,
    }
    flt = {k: v for k, v in flt.items() if v is not None}
    fmt = (format or "json").lower()

    if fmt == "pdf":
        buf = _pdf_export_svc.generate_pdf(filters=flt, confidentiality_notice=confidentiality_notice)
        pdf_bytes = buf.getvalue()
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return {
            "format": "pdf",
            "filename": f"Executive_Analytics_Report_{period}_{date.today().isoformat()}.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(pdf_bytes),
            "data_base64": b64,
            "status": "generated",
        }
    elif fmt in ("excel", "xlsx"):
        buf = _excel_export_svc.generate_workbook(filters=flt, confidentiality_notice=confidentiality_notice)
        xlsx_bytes = buf.getvalue()
        b64 = base64.b64encode(xlsx_bytes).decode("utf-8")
        return {
            "format": "excel",
            "filename": f"Executive_Analytics_{period}_{date.today().isoformat()}.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size_bytes": len(xlsx_bytes),
            "data_base64": b64,
            "status": "generated",
        }
    else:
        # Structured JSON executive report
        summary = _executive_analytics_svc.get_margin_summary(filters=flt)
        categories = _executive_analytics_svc.get_category_margins(filters=flt)
        matrix = _customer_profitability_svc.get_customer_profitability_matrix(filters=flt)
        p_start, p_end = (summary.date_from, summary.date_to)
        commissions = _commission_svc.get_commission_summaries(
            period_start=p_start, period_end=p_end, sales_rep_id=sales_rep_id
        )
        delivery = _delivery_analytics_svc.get_delivery_fulfillment_summary(filters=flt)

        return {
            "format": "json",
            "period": period,
            "date_from": summary.date_from.isoformat() if summary.date_from else None,
            "date_to": summary.date_to.isoformat() if summary.date_to else None,
            "confidentiality_notice": confidentiality_notice,
            "executive_summary": summary.model_dump() if hasattr(summary, "model_dump") else summary,
            "category_margins": categories.model_dump() if hasattr(categories, "model_dump") else categories,
            "customer_profitability": matrix.model_dump() if hasattr(matrix, "model_dump") else matrix,
            "commissions": [c.model_dump() if hasattr(c, "model_dump") else c for c in commissions],
            "delivery_fulfillment": delivery.model_dump() if hasattr(delivery, "model_dump") else delivery,
        }


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="bi-mcp", version="1.0"))


if __name__ == "__main__":
    main()

