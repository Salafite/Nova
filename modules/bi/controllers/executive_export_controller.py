import io
import csv
import logging
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from packages.auth.deps import require_permission
from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    ExecutiveExportRequest,
)
from ..services.excel_export_service import (
    ExcelExportService,
    excel_export_service as default_excel_service,
)
from ..services.pdf_export_service import (
    PdfExportService,
    pdf_export_service as default_pdf_service,
)
from ..services.executive_analytics_service import (
    ExecutiveAnalyticsService,
    executive_analytics_service as default_executive_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/api/bi/executive/export',
    tags=['Executive Financial Exports'],
    dependencies=[Depends(require_permission('BI_VIEW'))],
)


def _build_filter(
    period: str = 'Monthly',
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category_id: Optional[int] = None,
    sales_rep_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    delivery_route: Optional[str] = None,
) -> ExecutiveAnalyticsFilter:
    return ExecutiveAnalyticsFilter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )


@router.get('/pdf')
def export_executive_pdf(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='End date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Category ID filter'),
    sales_rep_id: Optional[int] = Query(None, description='Sales rep ID filter'),
    customer_id: Optional[int] = Query(None, description='Customer ID filter'),
    warehouse_id: Optional[int] = Query(None, description='Warehouse ID filter'),
    delivery_route: Optional[str] = Query(None, description='Delivery route filter'),
    confidentiality_notice: str = Query('CONFIDENTIAL — BOARD & BANK REVIEW ONLY', description='Header confidentiality label'),
):
    """
    Streams board-ready, bank-level PDF financial review document.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )
    pdf_buffer = default_pdf_service.generate_pdf(
        filters=flt,
        confidentiality_notice=confidentiality_notice,
    )
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Nova_Executive_Margin_Report_{timestamp}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/excel')
def export_executive_excel(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='End date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Category ID filter'),
    sales_rep_id: Optional[int] = Query(None, description='Sales rep ID filter'),
    customer_id: Optional[int] = Query(None, description='Customer ID filter'),
    warehouse_id: Optional[int] = Query(None, description='Warehouse ID filter'),
    delivery_route: Optional[str] = Query(None, description='Delivery route filter'),
    confidentiality_notice: str = Query('CONFIDENTIAL - BOARD & EXECUTIVE REVIEW ONLY', description='Confidentiality header'),
):
    """
    Streams multi-tab Excel financial workbook (.xlsx) containing executive KPI summaries,
    category & SKU margins, customer matrix, commissions ledger, and delivery fulfillment metrics.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        delivery_route=delivery_route,
    )
    excel_buffer = default_excel_service.generate_workbook(
        filters=flt,
        confidentiality_notice=confidentiality_notice,
    )
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Nova_Executive_Financial_Model_{timestamp}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/csv')
def export_executive_csv(
    period: str = Query('Monthly', description='Daily, Weekly, Monthly, Quarterly, YTD, Custom'),
    date_from: Optional[date] = Query(None, description='Start date (YYYY-MM-DD)'),
    date_to: Optional[date] = Query(None, description='End date (YYYY-MM-DD)'),
    category_id: Optional[int] = Query(None, description='Category ID filter'),
    sales_rep_id: Optional[int] = Query(None, description='Sales rep ID filter'),
    customer_id: Optional[int] = Query(None, description='Customer ID filter'),
):
    """
    Streams tabular category margin summary in CSV format.
    """
    flt = _build_filter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        sales_rep_id=sales_rep_id,
        customer_id=customer_id,
    )
    category_margins = default_executive_service.get_category_margins(filters=flt)
    summary_kpi = default_executive_service.get_margin_summary(filters=flt)

    output = io.StringIO()
    writer = csv.writer(output)

    # Executive KPI summary block
    writer.writerow(['NOVA ERP — EXECUTIVE MARGIN SUMMARY'])
    writer.writerow(['Period', summary_kpi.period])
    writer.writerow(['Gross Sales', f"{summary_kpi.gross_sales:.2f}"])
    writer.writerow(['Customer Discounts', f"{summary_kpi.discount_amount:.2f}"])
    writer.writerow(['Net Revenue', f"{summary_kpi.net_revenue:.2f}"])
    writer.writerow(['COGS', f"{summary_kpi.cogs:.2f}"])
    writer.writerow(['Freight Cost', f"{summary_kpi.freight_cost:.2f}"])
    writer.writerow(['Gross Profit', f"{summary_kpi.gross_profit:.2f}"])
    writer.writerow(['Gross Margin %', f"{summary_kpi.gross_margin_pct:.2f}%"])
    writer.writerow(['Total Orders', summary_kpi.total_orders])
    writer.writerow([])

    # Category breakdown table
    writer.writerow([
        'Category Name',
        'Gross Sales',
        'Discounts',
        'Net Revenue',
        'COGS',
        'Freight Cost',
        'Gross Profit',
        'Gross Margin %',
        'Revenue Share %',
        'Units Sold',
        'Order Count',
        'Margin Status',
    ])

    for item in category_margins.items:
        writer.writerow([
            item.category_name,
            f"{item.gross_sales:.2f}",
            f"{item.discount_amount:.2f}",
            f"{item.net_revenue:.2f}",
            f"{item.cogs:.2f}",
            f"{item.freight_cost:.2f}",
            f"{item.gross_profit:.2f}",
            f"{item.gross_margin_pct:.2f}%",
            f"{item.revenue_share_pct:.2f}%",
            f"{item.units_sold:.2f}",
            item.order_count,
            item.status,
        ])

    csv_data = output.getvalue().encode('utf-8')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Nova_Executive_Category_Margins_{timestamp}.csv"

    return StreamingResponse(
        io.BytesIO(csv_data),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('')
def request_executive_export(
    body: ExecutiveExportRequest,
):
    """
    POST endpoint to request export generation for PDF, Excel, or CSV formats.
    """
    flt = _build_filter(
        period=body.period,
        date_from=body.date_from,
        date_to=body.date_to,
        category_id=body.category_id,
        sales_rep_id=body.sales_rep_id,
        customer_id=body.customer_id,
        warehouse_id=body.warehouse_id,
        delivery_route=body.delivery_route,
    )

    fmt = (body.export_format or 'pdf').lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if fmt == 'excel' or fmt == 'xlsx':
        excel_buf = default_excel_service.generate_workbook(
            filters=flt,
            confidentiality_notice=body.confidentiality_notice or 'CONFIDENTIAL',
        )
        return StreamingResponse(
            excel_buf,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="Nova_Executive_Financial_Model_{timestamp}.xlsx"'},
        )
    elif fmt == 'csv':
        return export_executive_csv(
            period=body.period,
            date_from=body.date_from,
            date_to=body.date_to,
            category_id=body.category_id,
            sales_rep_id=body.sales_rep_id,
            customer_id=body.customer_id,
        )
    else:  # default PDF
        pdf_buf = default_pdf_service.generate_pdf(
            filters=flt,
            confidentiality_notice=body.confidentiality_notice or 'CONFIDENTIAL — FOR BOARD & BANK REVIEW ONLY',
        )
        return StreamingResponse(
            pdf_buf,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="Nova_Executive_Margin_Report_{timestamp}.pdf"'},
        )
