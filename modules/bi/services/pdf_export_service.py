import io
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, date

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from ..models.executive_analytics import (
    ExecutiveAnalyticsFilter,
    ExecutiveMarginSummary,
    CategoryMarginResponse,
    SkuMarginResponse,
    CustomerProfitabilityResponse,
    DeliveryFulfillmentSummaryResponse,
)
from .executive_analytics_service import (
    ExecutiveAnalyticsService,
    executive_analytics_service as default_executive_service,
    resolve_date_range,
)
from .customer_profitability_service import (
    CustomerProfitabilityService,
    customer_profitability_service as default_customer_service,
)
from .delivery_analytics_service import (
    DeliveryAnalyticsService,
    delivery_analytics_service as default_delivery_service,
)
from modules.sales.services.commission_service import (
    CommissionService,
    commission_service as default_commission_service,
)

logger = logging.getLogger(__name__)

# Colors
PRIMARY_COLOR = colors.HexColor("#1E3A8A")  # Deep Navy
SECONDARY_COLOR = colors.HexColor("#2563EB")  # Royal Blue
ACCENT_COLOR = colors.HexColor("#0D9488")  # Teal
DARK_TEXT = colors.HexColor("#0F172A")
MUTED_TEXT = colors.HexColor("#64748B")
LIGHT_BG = colors.HexColor("#F8FAFC")
BORDER_COLOR = colors.HexColor("#CBD5E1")
ALERT_RED = colors.HexColor("#DC2626")
ALERT_GREEN = colors.HexColor("#16A34A")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render running headers and 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 580, "NOVA ERP — EXECUTIVE MARGIN OPTIMIZATION & FINANCIAL REVIEW")
            self.drawRightString(756, 580, "CONFIDENTIAL — BOARD & BANK REVIEW")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(36, 574, 756, 574)

        # Running Footer
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(36, 32, 756, 32)

        footer_text = f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Nova ERP Business Intelligence | Page {self._pageNumber} of {page_count}"
        self.drawString(36, 20, "CONFIDENTIAL & PROPRIETARY — ALL RIGHTS RESERVED")
        self.drawRightString(756, 20, footer_text)
        self.restoreState()


class PdfExportService:
    """
    Generates board-ready, bank-level PDF financial review documents
    summarizing real-time gross margins, category performance, customer profitability matrix,
    sales representative commissions, and delivery route logistics.
    """

    def __init__(
        self,
        executive_service: Optional[ExecutiveAnalyticsService] = None,
        customer_service: Optional[CustomerProfitabilityService] = None,
        delivery_service: Optional[DeliveryAnalyticsService] = None,
        commission_service: Optional[CommissionService] = None,
    ):
        self.executive_service = executive_service or default_executive_service
        self.customer_service = customer_service or default_customer_service
        self.delivery_service = delivery_service or default_delivery_service
        self.commission_service = commission_service or default_commission_service

    def _normalize_filter(
        self, filter_input: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None]
    ) -> tuple[ExecutiveAnalyticsFilter, date, date]:
        if filter_input is None:
            flt = ExecutiveAnalyticsFilter()
        elif isinstance(filter_input, dict):
            flt = ExecutiveAnalyticsFilter(**filter_input)
        else:
            flt = filter_input

        start_date, end_date = resolve_date_range(
            period=flt.period,
            date_from=flt.date_from,
            date_to=flt.date_to,
        )
        return flt, start_date, end_date

    def generate_pdf(
        self,
        filters: Union[ExecutiveAnalyticsFilter, Dict[str, Any], None] = None,
        confidentiality_notice: str = "CONFIDENTIAL — FOR BOARD & BANK REVIEW ONLY",
        conn=None,
    ) -> io.BytesIO:
        """
        Generates and returns an in-memory PDF financial document stream.
        """
        flt, start_date, end_date = self._normalize_filter(filters)

        # Query all required data sources
        summary = self.executive_service.get_margin_summary(filters=flt, conn=conn)
        category_res = self.executive_service.get_category_margins(filters=flt, conn=conn)
        sku_res = self.executive_service.get_sku_margins(filters=flt, limit=15, offset=0, conn=conn)
        matrix_res = self.customer_service.get_customer_profitability_matrix(filters=flt, conn=conn)
        commissions = self.commission_service.get_commission_summaries(
            period_start=start_date,
            period_end=end_date,
            sales_rep_id=flt.sales_rep_id,
            conn=conn,
        )
        delivery_res = self.delivery_service.get_delivery_fulfillment_summary(filters=flt, conn=conn)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),  # 792 x 612 pts
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=44,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=PRIMARY_COLOR,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=MUTED_TEXT,
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=PRIMARY_COLOR,
            spaceAfter=4,
        )
        notice_style = ParagraphStyle(
            "NoticeStyle",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=ALERT_RED,
        )
        tbl_hdr_style = ParagraphStyle(
            "TblHdr",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,  # Centered
        )
        tbl_cell_style = ParagraphStyle(
            "TblCell",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=DARK_TEXT,
        )
        tbl_cell_right = ParagraphStyle(
            "TblCellRight",
            parent=tbl_cell_style,
            alignment=2,  # Right
        )
        tbl_cell_bold_right = ParagraphStyle(
            "TblCellBoldRight",
            parent=tbl_cell_style,
            fontName="Helvetica-Bold",
            alignment=2,
        )

        story = []

        # ===================================================================
        # PAGE 1: Executive Overview & Margin Analysis
        # ===================================================================

        # Title & Metadata Banner
        meta_table_data = [
            [
                Paragraph("NOVA ERP — EXECUTIVE FINANCIAL & MARGIN REVIEW", title_style),
                Paragraph(confidentiality_notice, notice_style),
            ],
            [
                Paragraph(
                    f"<b>Reporting Period:</b> {summary.period} ({start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}) &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"<b>Scope:</b> All Business Units",
                    subtitle_style,
                ),
                Paragraph("<b>Classification:</b> STRICTLY CONFIDENTIAL", subtitle_style),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[540, 180])
        meta_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
            ])
        )
        story.append(meta_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceBefore=4, spaceAfter=8))

        # Section 1: Executive KPI Cards Table
        story.append(Paragraph("1. Executive Financial Summary & Key Margin Drivers", section_style))

        kpi_card_data = [
            [
                Paragraph("<b>GROSS SALES</b>", tbl_hdr_style),
                Paragraph("<b>DISCOUNTS</b>", tbl_hdr_style),
                Paragraph("<b>NET REVENUE</b>", tbl_hdr_style),
                Paragraph("<b>COGS</b>", tbl_hdr_style),
                Paragraph("<b>FREIGHT COST</b>", tbl_hdr_style),
                Paragraph("<b>GROSS PROFIT</b>", tbl_hdr_style),
                Paragraph("<b>MARGIN %</b>", tbl_hdr_style),
            ],
            [
                Paragraph(f"<b>${summary.gross_sales:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(f"-${summary.discount_amount:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${summary.net_revenue:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(f"-${summary.cogs:,.2f}", tbl_cell_right),
                Paragraph(f"-${summary.freight_cost:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${summary.gross_profit:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(
                    f"<b>{summary.gross_margin_pct:.1f}%</b>",
                    ParagraphStyle(
                        "MarginKPI",
                        parent=tbl_cell_bold_right,
                        textColor=ALERT_RED if summary.gross_margin_pct < 15.0 else ALERT_GREEN,
                    ),
                ),
            ],
            [
                Paragraph(f"Orders: {summary.total_orders}", subtitle_style),
                Paragraph(f"Discounts Granted", subtitle_style),
                Paragraph(f"Net Invoiced Sales", subtitle_style),
                Paragraph(f"Product Cost", subtitle_style),
                Paragraph(f"Outbound Logistics", subtitle_style),
                Paragraph(f"Growth: {summary.gross_profit_growth_pct or 0.0:+.1f}%", subtitle_style),
                Paragraph(f"Target: {summary.target_margin_pct:.1f}%", subtitle_style),
            ],
        ]
        kpi_card_table = Table(kpi_card_data, colWidths=[102, 102, 104, 102, 102, 105, 103])
        kpi_card_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
                ("BACKGROUND", (0, 2), (-1, 2), LIGHT_BG),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(kpi_card_table)
        story.append(Spacer(1, 10))

        # Section 2: Category Margin Table
        story.append(Paragraph("2. Product Category Margin Optimization Breakdown", section_style))

        cat_table_data = [
            [
                Paragraph("<b>Product Category</b>", tbl_hdr_style),
                Paragraph("<b>Gross Sales</b>", tbl_hdr_style),
                Paragraph("<b>Discounts</b>", tbl_hdr_style),
                Paragraph("<b>Net Revenue</b>", tbl_hdr_style),
                Paragraph("<b>COGS</b>", tbl_hdr_style),
                Paragraph("<b>Freight</b>", tbl_hdr_style),
                Paragraph("<b>Gross Profit</b>", tbl_hdr_style),
                Paragraph("<b>Margin %</b>", tbl_hdr_style),
                Paragraph("<b>Share %</b>", tbl_hdr_style),
                Paragraph("<b>Units</b>", tbl_hdr_style),
                Paragraph("<b>Status</b>", tbl_hdr_style),
            ]
        ]

        for cat in category_res.items or []:
            status_color = ALERT_RED if cat.is_low_margin else ALERT_GREEN
            cat_table_data.append([
                Paragraph(cat.category_name, tbl_cell_style),
                Paragraph(f"${cat.gross_sales:,.2f}", tbl_cell_right),
                Paragraph(f"${cat.discount_amount:,.2f}", tbl_cell_right),
                Paragraph(f"${cat.net_revenue:,.2f}", tbl_cell_right),
                Paragraph(f"${cat.cogs:,.2f}", tbl_cell_right),
                Paragraph(f"${cat.freight_cost:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${cat.gross_profit:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(
                    f"<b>{cat.gross_margin_pct:.1f}%</b>",
                    ParagraphStyle("CMarg", parent=tbl_cell_bold_right, textColor=status_color),
                ),
                Paragraph(f"{cat.revenue_share_pct:.1f}%", tbl_cell_right),
                Paragraph(f"{cat.units_sold:,.0f}", tbl_cell_right),
                Paragraph(f"<font color='{status_color.hexval()}'>{cat.status}</font>", tbl_cell_style),
            ])

        cat_table = Table(cat_table_data, colWidths=[110, 65, 55, 65, 60, 50, 65, 52, 48, 45, 65])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SECONDARY_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(cat_table)
        story.append(Spacer(1, 10))

        # Section 3: SKU-Level Sample
        story.append(Paragraph("3. SKU-Level Profitability Highlights (Top / Low-Margin Lines)", section_style))

        sku_table_data = [
            [
                Paragraph("<b>SKU Code</b>", tbl_hdr_style),
                Paragraph("<b>Product Name</b>", tbl_hdr_style),
                Paragraph("<b>Category</b>", tbl_hdr_style),
                Paragraph("<b>Units Sold</b>", tbl_hdr_style),
                Paragraph("<b>Avg Price</b>", tbl_hdr_style),
                Paragraph("<b>Unit Cost</b>", tbl_hdr_style),
                Paragraph("<b>Net Revenue</b>", tbl_hdr_style),
                Paragraph("<b>Gross Profit</b>", tbl_hdr_style),
                Paragraph("<b>Margin %</b>", tbl_hdr_style),
                Paragraph("<b>Alert Status</b>", tbl_hdr_style),
            ]
        ]

        for s in (sku_res.items or [])[:8]:
            s_color = ALERT_RED if s.is_low_margin else ALERT_GREEN
            sku_table_data.append([
                Paragraph(s.sku_code or f"SKU-{s.product_id}", tbl_cell_style),
                Paragraph(s.product_name[:24], tbl_cell_style),
                Paragraph(s.category_name or "", tbl_cell_style),
                Paragraph(f"{s.units_sold:,.0f}", tbl_cell_right),
                Paragraph(f"${s.avg_selling_price:,.2f}", tbl_cell_right),
                Paragraph(f"${s.unit_cost:,.2f}", tbl_cell_right),
                Paragraph(f"${s.net_revenue:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${s.gross_profit:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(
                    f"<b>{s.gross_margin_pct:.1f}%</b>",
                    ParagraphStyle("SMarg", parent=tbl_cell_bold_right, textColor=s_color),
                ),
                Paragraph(
                    f"<font color='{s_color.hexval()}'>{'LOW MARGIN' if s.is_low_margin else 'HEALTHY'}</font>",
                    tbl_cell_style,
                ),
            ])

        sku_table = Table(sku_table_data, colWidths=[65, 140, 95, 55, 55, 55, 65, 65, 55, 70])
        sku_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(sku_table)

        # Page Break to Page 2
        story.append(PageBreak())

        # ===================================================================
        # PAGE 2: Customer Profitability, Commissions, Logistics & Sign-off
        # ===================================================================

        story.append(Paragraph("4. Customer Profitability Matrix (4-Quadrant Strategic Segmentation)", section_style))

        # Quadrant Summary Table
        quad_table_data = [
            [
                Paragraph("<b>Quadrant Name</b>", tbl_hdr_style),
                Paragraph("<b>Code</b>", tbl_hdr_style),
                Paragraph("<b>Strategic Rationale & Playbook Action</b>", tbl_hdr_style),
                Paragraph("<b>Accounts</b>", tbl_hdr_style),
                Paragraph("<b>Net Revenue</b>", tbl_hdr_style),
                Paragraph("<b>Gross Profit</b>", tbl_hdr_style),
                Paragraph("<b>Avg Margin %</b>", tbl_hdr_style),
                Paragraph("<b>Profit Share %</b>", tbl_hdr_style),
            ]
        ]

        for q in matrix_res.quadrants or []:
            quad_table_data.append([
                Paragraph(f"<b>{q.quadrant}</b>", tbl_cell_style),
                Paragraph(q.quadrant_code, tbl_cell_style),
                Paragraph(q.description, tbl_cell_style),
                Paragraph(str(q.customer_count), tbl_cell_right),
                Paragraph(f"${q.total_net_revenue:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${q.total_gross_profit:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(f"{q.avg_margin_pct:.1f}%", tbl_cell_right),
                Paragraph(f"{q.profit_share_pct:.1f}%", tbl_cell_right),
            ])

        quad_table = Table(quad_table_data, colWidths=[100, 40, 230, 50, 75, 75, 75, 75])
        quad_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(quad_table)
        story.append(Spacer(1, 10))

        # Section 5: Sales Rep Commission Table
        story.append(Paragraph("5. Sales Representative Collected Margin Commission Ledger", section_style))

        comm_table_data = [
            [
                Paragraph("<b>Sales Rep Name</b>", tbl_hdr_style),
                Paragraph("<b>Invoices</b>", tbl_hdr_style),
                Paragraph("<b>Collected Cash</b>", tbl_hdr_style),
                Paragraph("<b>Realized Margin</b>", tbl_hdr_style),
                Paragraph("<b>Margin %</b>", tbl_hdr_style),
                Paragraph("<b>Gross Comm</b>", tbl_hdr_style),
                Paragraph("<b>Disc Penalty</b>", tbl_hdr_style),
                Paragraph("<b>Net Commission</b>", tbl_hdr_style),
                Paragraph("<b>Paid Amount</b>", tbl_hdr_style),
                Paragraph("<b>Pending Balance</b>", tbl_hdr_style),
            ]
        ]

        for c in commissions[:6]:
            comm_table_data.append([
                Paragraph(c.sales_rep_name, tbl_cell_style),
                Paragraph(str(c.total_invoices), tbl_cell_right),
                Paragraph(f"${c.total_collected:,.2f}", tbl_cell_right),
                Paragraph(f"${c.total_gross_margin:,.2f}", tbl_cell_right),
                Paragraph(f"{c.avg_margin_pct:.1f}%", tbl_cell_right),
                Paragraph(f"${c.gross_commission:,.2f}", tbl_cell_right),
                Paragraph(f"-${c.discount_penalty:,.2f}", tbl_cell_right),
                Paragraph(f"<b>${c.net_commission:,.2f}</b>", tbl_cell_bold_right),
                Paragraph(f"${c.paid_commission:,.2f}", tbl_cell_right),
                Paragraph(f"${c.pending_commission:,.2f}", tbl_cell_right),
            ])

        comm_table = Table(comm_table_data, colWidths=[120, 45, 75, 75, 55, 65, 65, 75, 70, 75])
        comm_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SECONDARY_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(comm_table)
        story.append(Spacer(1, 10))

        # Section 6: Delivery Route Logistics
        story.append(Paragraph("6. Delivery Route Logistics & Freight Cost Efficiency", section_style))

        deliv_table_data = [
            [
                Paragraph("<b>Delivery Route</b>", tbl_hdr_style),
                Paragraph("<b>Warehouse</b>", tbl_hdr_style),
                Paragraph("<b>Deliveries</b>", tbl_hdr_style),
                Paragraph("<b>Completed</b>", tbl_hdr_style),
                Paragraph("<b>On-Time</b>", tbl_hdr_style),
                Paragraph("<b>OTD Rate %</b>", tbl_hdr_style),
                Paragraph("<b>Total Freight</b>", tbl_hdr_style),
                Paragraph("<b>Avg Freight/Deliv</b>", tbl_hdr_style),
                Paragraph("<b>Ordered Qty</b>", tbl_hdr_style),
                Paragraph("<b>Shipped Qty</b>", tbl_hdr_style),
            ]
        ]

        for r in (delivery_res.routes or [])[:5]:
            otd_color = ALERT_GREEN if r.on_time_delivery_rate >= 90.0 else ALERT_RED
            deliv_table_data.append([
                Paragraph(r.delivery_route, tbl_cell_style),
                Paragraph(r.warehouse_name or "Primary WH", tbl_cell_style),
                Paragraph(str(r.total_deliveries), tbl_cell_right),
                Paragraph(str(r.completed_deliveries), tbl_cell_right),
                Paragraph(str(r.on_time_deliveries), tbl_cell_right),
                Paragraph(
                    f"<b>{r.on_time_delivery_rate:.1f}%</b>",
                    ParagraphStyle("OTDCell", parent=tbl_cell_bold_right, textColor=otd_color),
                ),
                Paragraph(f"${r.total_freight_cost:,.2f}", tbl_cell_right),
                Paragraph(f"${r.avg_freight_per_delivery:,.2f}", tbl_cell_right),
                Paragraph(f"{r.total_qty_ordered:,.0f}", tbl_cell_right),
                Paragraph(f"{r.total_qty_shipped:,.0f}", tbl_cell_right),
            ])

        deliv_table = Table(deliv_table_data, colWidths=[110, 90, 50, 50, 50, 65, 75, 75, 75, 80])
        deliv_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(deliv_table)
        story.append(Spacer(1, 14))

        # Section 7: Executive & Banking Sign-off Block
        signoff_data = [
            [
                Paragraph("<b>PREPARED & CERTIFIED BY:</b>", ParagraphStyle("S1", parent=normal_style, fontName="Helvetica-Bold", fontSize=8, textColor=PRIMARY_COLOR)),
                Paragraph("<b>BOARD / CFO APPROVAL:</b>", ParagraphStyle("S2", parent=normal_style, fontName="Helvetica-Bold", fontSize=8, textColor=PRIMARY_COLOR)),
                Paragraph("<b>BANK / CREDIT REVIEW OFFICER:</b>", ParagraphStyle("S3", parent=normal_style, fontName="Helvetica-Bold", fontSize=8, textColor=PRIMARY_COLOR)),
            ],
            [
                Paragraph("Signature: ___________________________<br/>Name: Controller / VP Finance<br/>Date: _______________________________", subtitle_style),
                Paragraph("Signature: ___________________________<br/>Name: Chief Financial Officer<br/>Date: _______________________________", subtitle_style),
                Paragraph("Signature: ___________________________<br/>Name: Senior Credit Officer<br/>Date: _______________________________", subtitle_style),
            ],
        ]
        signoff_table = Table(signoff_data, colWidths=[240, 240, 240])
        signoff_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(KeepTogether(signoff_table))

        # Build PDF
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer


# Default singleton instance
pdf_export_service = PdfExportService()
