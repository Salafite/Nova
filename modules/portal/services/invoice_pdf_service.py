import io
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from modules.portal.repositories.portal_repo import PortalRepository

logger = logging.getLogger(__name__)


class InvoicePdfService:
    """Service for generating downloadable, printable PDF invoices for B2B Customer Portal."""

    def __init__(self, portal_repo: Optional[PortalRepository] = None):
        self.portal_repo = portal_repo or PortalRepository()

    def generate_invoice_pdf(
        self,
        invoice_id: int,
        customer_id: Optional[int] = None,
    ) -> bytes:
        """Generate formatted PDF binary stream for a specific customer invoice.
        
        Args:
            invoice_id: ID of the invoice (T0090).
            customer_id: Optional customer ID to enforce ownership security isolation.
            
        Returns:
            bytes: Raw binary PDF data.
            
        Raises:
            ValueError: If invoice not found or does not belong to customer.
        """
        # 1. Fetch invoice with ownership validation
        invoice = self.portal_repo.get_invoice_by_id(invoice_id, customer_id=customer_id)
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} was not found or does not belong to your account.")

        partner_id = invoice.get("partner_id")
        customer = self.portal_repo.get_customer_by_id(partner_id) if partner_id else None

        # 2. Fetch linked sales order details and line items if available
        sales_order = None
        order_lines = []
        sales_order_id = invoice.get("sales_order_id")
        if sales_order_id:
            sales_order = self.portal_repo.get_order_by_id(sales_order_id, customer_id=customer_id)
            order_lines = self.portal_repo.get_order_lines(sales_order_id)

        # 3. Build PDF
        return self._render_pdf(invoice=invoice, customer=customer, sales_order=sales_order, order_lines=order_lines)

    def _render_pdf(
        self,
        invoice: Dict[str, Any],
        customer: Optional[Dict[str, Any]],
        sales_order: Optional[Dict[str, Any]],
        order_lines: List[Dict[str, Any]],
    ) -> bytes:
        """Internal helper to construct ReportLab story flowables and render PDF bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        primary_color = colors.HexColor("#0F172A")    # Slate 900
        secondary_color = colors.HexColor("#334155")  # Slate 700
        muted_color = colors.HexColor("#64748B")      # Slate 500
        accent_blue = colors.HexColor("#2563EB")      # Blue 600
        paid_green = colors.HexColor("#16A34A")       # Green 600
        unpaid_amber = colors.HexColor("#D97706")     # Amber 600
        bg_light = colors.HexColor("#F8FAFC")         # Slate 50
        border_color = colors.HexColor("#E2E8F0")     # Slate 200

        title_style = ParagraphStyle(
            "InvoiceTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        company_title_style = ParagraphStyle(
            "CompanyTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=accent_blue,
        )

        company_sub_style = ParagraphStyle(
            "CompanySub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=muted_color,
        )

        section_heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=secondary_color,
        )

        body_style = ParagraphStyle(
            "InvoiceBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=primary_color,
        )

        body_bold_style = ParagraphStyle(
            "InvoiceBodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=primary_color,
        )

        body_right_style = ParagraphStyle(
            "InvoiceBodyRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        body_right_bold = ParagraphStyle(
            "InvoiceBodyRightBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.white,
        )

        table_header_right = ParagraphStyle(
            "TableHeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        story = []

        # ------------------------------------------------------------------
        # Header: Company Info (Left) & Invoice Title / Status (Right)
        # ------------------------------------------------------------------
        inv_status = (invoice.get("status") or "Unpaid").strip()
        status_color = paid_green if inv_status == "Paid" else (unpaid_amber if inv_status in ("Unpaid", "Partially Paid") else secondary_color)

        company_html = (
            "<b>NOVA ERP</b><br/>"
            "<font size='8' color='#64748B'>B2B Wholesale Supplies & Replenishment</font><br/>"
            "<font size='8' color='#64748B'>100 Enterprise Way, Suite 400<br/>"
            "billing@novaerp.com | +1 (800) 555-NOVA</font>"
        )

        inv_number = invoice.get("invoice_number", f"INV-{invoice.get('id')}")
        issue_date_str = str(invoice.get("issue_date") or "")
        due_date_str = str(invoice.get("due_date") or "")

        inv_header_html = (
            f"<b>INVOICE</b><br/>"
            f"<font size='10' color='#334155'>#{inv_number}</font><br/>"
            f"<font size='9' color='{status_color.hexval()}'><b>STATUS: {inv_status.upper()}</b></font>"
        )

        header_table_data = [
            [
                Paragraph(company_html, company_sub_style),
                Paragraph(inv_header_html, title_style),
            ]
        ]
        header_table = Table(header_table_data, colWidths=[270, 270])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)

        story.append(HRFlowable(width="100%", thickness=2, color=accent_blue, spaceBefore=4, spaceAfter=14))

        # ------------------------------------------------------------------
        # Metadata: Billed To (Left) & Invoice Info (Right)
        # ------------------------------------------------------------------
        cust_name = (customer.get("name") if customer else None) or invoice.get("customer_name") or "Valued Customer"
        cust_email = (customer.get("email") if customer else None) or "N/A"
        cust_phone = (customer.get("phone") if customer else None) or "N/A"
        cust_group = (customer.get("group_name") if customer else None) or "Wholesale"

        billed_to_html = (
            f"<b>{cust_name}</b><br/>"
            f"<font color='#64748B'>Customer Group: {cust_group}</font><br/>"
            f"<font color='#64748B'>Email: {cust_email}</font><br/>"
            f"<font color='#64748B'>Phone: {cust_phone}</font>"
        )

        so_number = invoice.get("sales_order_number") or (sales_order.get("order_number") if sales_order else None) or "N/A"

        invoice_details_html = (
            f"<b>Invoice Date:</b> {issue_date_str}<br/>"
            f"<b>Payment Due Date:</b> {due_date_str}<br/>"
            f"<b>Sales Order Reference:</b> {so_number}<br/>"
            f"<b>Currency:</b> USD ($)"
        )

        meta_table_data = [
            [
                Paragraph("<b>BILLED TO</b>", section_heading_style),
                Paragraph("<b>INVOICE DETAILS</b>", section_heading_style),
            ],
            [
                Paragraph(billed_to_html, body_style),
                Paragraph(invoice_details_html, body_style),
            ]
        ]
        meta_table = Table(meta_table_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # ------------------------------------------------------------------
        # Line Items Table
        # ------------------------------------------------------------------
        line_items_data = [
            [
                Paragraph("#", table_header_style),
                Paragraph("Item Description", table_header_style),
                Paragraph("Qty", table_header_right),
                Paragraph("Unit Price", table_header_right),
                Paragraph("Line Total", table_header_right),
            ]
        ]

        total_amount = float(invoice.get("total_amount", 0.0))
        paid_amount = float(invoice.get("paid_amount", 0.0))
        balance_due = float(invoice.get("balance_due", max(0.0, total_amount - paid_amount)))

        if order_lines:
            for idx, line in enumerate(order_lines, start=1):
                p_code = line.get("product_code")
                p_name = line.get("product_name") or f"Product #{line.get('product_id')}"
                item_label = f"<b>{p_name}</b>"
                if p_code:
                    item_label += f"<br/><font size='8' color='#64748B'>SKU: {p_code}</font>"

                qty_val = float(line.get("qty", 0.0))
                uom_str = line.get("uom_name") or ""
                qty_display = f"{qty_val:,.2f} {uom_str}".strip()
                unit_price_val = float(line.get("unit_price", 0.0))
                line_total_val = float(line.get("line_total", qty_val * unit_price_val))

                line_items_data.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(item_label, body_style),
                    Paragraph(qty_display, body_right_style),
                    Paragraph(f"${unit_price_val:,.2f}", body_right_style),
                    Paragraph(f"${line_total_val:,.2f}", body_right_style),
                ])
        else:
            # Fallback line item representing invoice summary
            line_items_data.append([
                Paragraph("1", body_style),
                Paragraph(f"<b>Wholesale Supplies & Services</b><br/><font size='8' color='#64748B'>Invoice #{inv_number}</font>", body_style),
                Paragraph("1.00", body_right_style),
                Paragraph(f"${total_amount:,.2f}", body_right_style),
                Paragraph(f"${total_amount:,.2f}", body_right_style),
            ])

        lines_table = Table(line_items_data, colWidths=[30, 240, 80, 95, 95])
        lines_style = [
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ]

        # Alternating row background
        for r_idx in range(1, len(line_items_data)):
            if r_idx % 2 == 0:
                lines_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg_light))

        lines_table.setStyle(TableStyle(lines_style))
        story.append(lines_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # Summary & Totals Block (Right aligned)
        # ------------------------------------------------------------------
        subtotal_val = sales_order.get("subtotal") if sales_order else total_amount
        subtotal_val = float(subtotal_val) if subtotal_val is not None else total_amount
        tax_val = float(sales_order.get("tax", 0.0)) if sales_order else 0.0

        totals_table_data = [
            [
                Paragraph("<b>Subtotal:</b>", body_right_style),
                Paragraph(f"${subtotal_val:,.2f}", body_right_style),
            ],
            [
                Paragraph("<b>Tax:</b>", body_right_style),
                Paragraph(f"${tax_val:,.2f}", body_right_style),
            ],
            [
                Paragraph("<b>Total Amount:</b>", body_right_bold),
                Paragraph(f"<b>${total_amount:,.2f}</b>", body_right_bold),
            ],
            [
                Paragraph("<b>Amount Paid:</b>", body_right_style),
                Paragraph(f"${paid_amount:,.2f}", body_right_style),
            ],
            [
                Paragraph("<b>Balance Due:</b>", body_right_bold),
                Paragraph(f"<font color='{status_color.hexval()}'><b>${balance_due:,.2f}</b></font>", body_right_bold),
            ]
        ]

        totals_table = Table(totals_table_data, colWidths=[150, 100])
        totals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 2), (-1, 2), 1, border_color),
            ('BACKGROUND', (0, 4), (-1, 4), bg_light),
            ('BOX', (0, 4), (-1, 4), 1, status_color),
        ]))

        # Place totals in right column of summary layout
        summary_table_data = [
            [
                "",  # Left empty space
                totals_table
            ]
        ]
        summary_table = Table(summary_table_data, colWidths=[290, 250])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(KeepTogether([summary_table]))

        story.append(Spacer(1, 14))

        # ------------------------------------------------------------------
        # Notes & Online Payment Settlement Notice
        # ------------------------------------------------------------------
        notes_text = invoice.get("notes") or ""
        payment_link = invoice.get("payment_link") or ""

        payment_notice_html = "<b>PAYMENT INSTRUCTIONS:</b><br/>"
        if inv_status == "Paid":
            payment_notice_html += "<font color='#16A34A'><b>✓ PAID IN FULL:</b> Thank you for your payment! Your account receivables balance has been credited.</font>"
        else:
            payment_notice_html += (
                "Please settle your balance online via the <b>Nova Customer Portal</b>.<br/>"
                "• Accepted payment methods: <b>Credit Card</b> and <b>ACH Bank Transfer</b>.<br/>"
                "• All transactions are secured and reconciled automatically."
            )
            if payment_link:
                payment_notice_html += f"<br/>• Direct payment link: <font color='#2563EB'><u>{payment_link}</u></font>"

        if notes_text:
            payment_notice_html += f"<br/><br/><b>Invoice Notes:</b> {notes_text}"

        notice_table = Table([[Paragraph(payment_notice_html, body_style)]], colWidths=[540])
        notice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(KeepTogether([notice_table]))

        # ------------------------------------------------------------------
        # Footer
        # ------------------------------------------------------------------
        story.append(Spacer(1, 14))
        footer_html = (
            f"<font size='8' color='#94A3B8'>"
            f"Generated by Nova ERP Self-Service B2B Customer Portal on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"For questions regarding this invoice, please contact support@novaerp.com."
            f"</font>"
        )
        story.append(Paragraph(footer_html, ParagraphStyle("Footer", parent=styles["Normal"], alignment=TA_CENTER)))

        # Build document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
