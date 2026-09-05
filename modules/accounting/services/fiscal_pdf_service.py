import io
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
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
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget

from modules.accounting.services.einvoice_service import EInvoiceService
from modules.accounting.services.invoice_service import INVOICE_REPO, CUSTOMER_REPO, LINE_REPO
from modules.accounting.models.einvoice import EINVOICE_RECORD_REPO, FISCAL_PROFILE_REPO

logger = logging.getLogger(__name__)


class FiscalPdfService:
    """Service for generating printable, bilingual (English/Arabic) fiscal tax invoices with embedded QR code & security seals."""

    def __init__(
        self,
        einvoice_service: Optional[EInvoiceService] = None,
        invoice_repo=None,
        customer_repo=None,
        line_repo=None,
        fiscal_profile_repo=None,
    ):
        self.einvoice_service = einvoice_service or EInvoiceService(
            repo=EINVOICE_RECORD_REPO,
            fiscal_profile_repo=fiscal_profile_repo or FISCAL_PROFILE_REPO,
            invoice_repo=invoice_repo or INVOICE_REPO,
            customer_repo=customer_repo or CUSTOMER_REPO,
            line_repo=line_repo or LINE_REPO,
        )
        self.invoice_repo = invoice_repo or INVOICE_REPO
        self.customer_repo = customer_repo or CUSTOMER_REPO
        self.line_repo = line_repo or LINE_REPO
        self.fiscal_profile_repo = fiscal_profile_repo or FISCAL_PROFILE_REPO

    def generate_fiscal_pdf(
        self,
        invoice_id: int,
        profile_id: Optional[int] = None,
        conn=None,
    ) -> bytes:
        """Generate formatted PDF binary stream for a fiscal tax invoice.

        Args:
            invoice_id: ID of the sales invoice (T0090).
            profile_id: Optional fiscal profile ID.
            conn: Optional database connection.

        Returns:
            bytes: Raw binary PDF data.
        """
        invoice = self.invoice_repo.get(invoice_id, conn=conn)
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} not found")

        einvoice_record = self.einvoice_service.get_by_invoice_id(invoice_id, conn=conn)
        profile = self.einvoice_service.get_active_fiscal_profile(profile_id or (einvoice_record.get("fiscal_profile_id") if einvoice_record else None), conn=conn)

        customer = None
        partner_id = invoice.get("partner_id")
        if partner_id:
            try:
                customer = self.customer_repo.get(partner_id, conn=conn)
            except Exception as e:
                logger.warning(f"Could not fetch customer {partner_id}: {e}")

        lines = []
        sales_order_id = invoice.get("sales_order_id")
        if sales_order_id:
            try:
                lines = self.line_repo.list(filters={"sales_order_id": sales_order_id}, conn=conn)
            except Exception as e:
                logger.warning(f"Could not fetch lines for order {sales_order_id}: {e}")

        # Get QR code
        qr_resp = self.einvoice_service.generate_qr_code(invoice_id, conn=conn)
        qr_code_tlv = qr_resp.qr_code_tlv

        return self._render_pdf(
            invoice=invoice,
            einvoice_record=einvoice_record,
            profile=profile,
            customer=customer,
            lines=lines,
            qr_code_tlv=qr_code_tlv,
        )

    def _create_qr_drawing(self, text: str, size: float = 110.0) -> Drawing:
        """Construct ReportLab Drawing containing scaled QR code."""
        d = Drawing(size, size)
        qr = QrCodeWidget(text)
        bounds = qr.getBounds()
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        if w > 0 and h > 0:
            qr.transform = [size / w, 0, 0, size / h, 0, 0]
        d.add(qr)
        return d

    def _render_pdf(
        self,
        invoice: Dict[str, Any],
        einvoice_record: Optional[Dict[str, Any]],
        profile: Dict[str, Any],
        customer: Optional[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        qr_code_tlv: str,
    ) -> bytes:
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

        primary_color = colors.HexColor("#0F172A")    # Slate 900
        secondary_color = colors.HexColor("#334155")  # Slate 700
        muted_color = colors.HexColor("#64748B")      # Slate 500
        accent_blue = colors.HexColor("#2563EB")      # Blue 600
        green_seal = colors.HexColor("#16A34A")       # Green 600
        amber_seal = colors.HexColor("#D97706")       # Amber 600
        bg_light = colors.HexColor("#F8FAFC")         # Slate 50
        border_color = colors.HexColor("#CBD5E1")     # Slate 300

        title_style = ParagraphStyle(
            "FiscalTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        seller_title_style = ParagraphStyle(
            "SellerTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=accent_blue,
        )

        body_style = ParagraphStyle(
            "FiscalBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
        )

        body_bold = ParagraphStyle(
            "FiscalBodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
        )

        body_right = ParagraphStyle(
            "FiscalBodyRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        body_right_bold = ParagraphStyle(
            "FiscalBodyRightBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        table_hdr = ParagraphStyle(
            "TableHdr",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )

        table_hdr_right = ParagraphStyle(
            "TableHdrRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        story = []

        # ------------------------------------------------------------------
        # Header: Seller Details (Left) vs Tax Invoice Title & Status (Right)
        # ------------------------------------------------------------------
        seller_en = profile.get("seller_name") or "Nova Global Trading LLC"
        seller_ar = profile.get("seller_name_ar") or "شركة نوفا للتجارة العامة"
        tax_id = profile.get("tax_id") or "300012345600003"
        cr_no = profile.get("commercial_registration_number") or "1010123456"
        building = profile.get("building_number") or "1234"
        street = profile.get("street_name") or "King Fahd Road"
        district = profile.get("district") or "Al Olaya"
        city = profile.get("city") or "Riyadh"
        postal = profile.get("postal_code") or "12211"
        country = profile.get("country_code") or "SA"

        seller_html = (
            f"<b>{seller_en}</b><br/>"
            f"<b>{seller_ar}</b><br/>"
            f"<font color='#64748B'>VAT / Tax ID: <b>{tax_id}</b> | CR: {cr_no}<br/>"
            f"Addr: Bldg {building}, {street}, {district}, {city} {postal}, {country}</font>"
        )

        inv_number = invoice.get("invoice_number", f"INV-{invoice.get('id')}")
        inv_type = "TAX INVOICE / فاتورة ضريبية"
        clearance_status = (einvoice_record.get("clearance_status") if einvoice_record else "Draft") or "Draft"
        status_color = green_seal if clearance_status in ("Cleared", "Reported") else (amber_seal if clearance_status in ("Pending", "Draft") else secondary_color)

        invoice_header_html = (
            f"<b>{inv_type}</b><br/>"
            f"<font size='11' color='#334155'>#{inv_number}</font><br/>"
            f"<font size='9' color='{status_color.hexval()}'><b>STATUS / الحالة: {clearance_status.upper()}</b></font>"
        )

        header_table = Table(
            [[Paragraph(seller_html, body_style), Paragraph(invoice_header_html, title_style)]],
            colWidths=[310, 230],
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceBefore=4, spaceAfter=10))

        # ------------------------------------------------------------------
        # Metadata Block: Buyer Details & Fiscal Metadata
        # ------------------------------------------------------------------
        cust_name = (customer.get("name") if customer else None) or invoice.get("customer_name") or "Retail Customer / عميل نقدي"
        cust_vat = (customer.get("tax_id") if customer else None) or (customer.get("vat_number") if customer else None) or "N/A"
        cust_addr = (customer.get("address") if customer else None) or "N/A"

        buyer_html = (
            f"<b>BUYER / العميل:</b><br/>"
            f"<b>Name:</b> {cust_name}<br/>"
            f"<b>VAT / Tax ID:</b> {cust_vat}<br/>"
            f"<b>Address:</b> {cust_addr}"
        )

        issue_date_str = str(invoice.get("issue_date") or "")
        due_date_str = str(invoice.get("due_date") or "")
        icv = einvoice_record.get("icv") if einvoice_record else 1
        clearance_id = (einvoice_record.get("clearance_id") if einvoice_record else None) or "N/A"
        inv_uuid = (einvoice_record.get("invoice_uuid") if einvoice_record else None) or "N/A"

        meta_html = (
            f"<b>INVOICE DETAILS / تفاصيل الفاتورة:</b><br/>"
            f"<b>Issue Date:</b> {issue_date_str} | <b>Due:</b> {due_date_str}<br/>"
            f"<b>Invoice UUID:</b> <font size='7.5'>{inv_uuid}</font><br/>"
            f"<b>ICV:</b> {icv} | <b>Clearance ID:</b> {clearance_id}"
        )

        meta_table = Table(
            [[Paragraph(buyer_html, body_style), Paragraph(meta_html, body_style)]],
            colWidths=[270, 270],
        )
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # Line Items Table
        # ------------------------------------------------------------------
        line_data = [
            [
                Paragraph("#", table_hdr),
                Paragraph("Item / الصنف", table_hdr),
                Paragraph("Qty / الكمية", table_hdr_right),
                Paragraph("Unit Price / السعر", table_hdr_right),
                Paragraph("VAT (15%) / الضريبة", table_hdr_right),
                Paragraph("Total / المجموع", table_hdr_right),
            ]
        ]

        total_amount = float(invoice.get("total_amount", 0.0) or 0.0)
        total_vat = round(total_amount - (total_amount / 1.15), 2)
        subtotal = round(total_amount - total_vat, 2)

        if lines:
            for idx, line in enumerate(lines, start=1):
                p_name = line.get("product_name") or f"Product #{line.get('product_id')}"
                qty = float(line.get("qty", 1.0) or 1.0)
                u_price = float(line.get("unit_price", 0.0) or 0.0)
                l_total = float(line.get("line_total", qty * u_price) or (qty * u_price))
                l_vat = round(l_total * 0.15, 2)
                l_gross = round(l_total + l_vat, 2)

                line_data.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(f"<b>{p_name}</b>", body_style),
                    Paragraph(f"{qty:,.2f}", body_right),
                    Paragraph(f"{u_price:,.2f}", body_right),
                    Paragraph(f"{l_vat:,.2f}", body_right),
                    Paragraph(f"{l_gross:,.2f}", body_right),
                ])
        else:
            line_data.append([
                Paragraph("1", body_style),
                Paragraph("<b>Taxable Goods & Services / توريد سلع وخدمات</b>", body_style),
                Paragraph("1.00", body_right),
                Paragraph(f"{subtotal:,.2f}", body_right),
                Paragraph(f"{total_vat:,.2f}", body_right),
                Paragraph(f"{total_amount:,.2f}", body_right),
            ])

        lines_table = Table(line_data, colWidths=[25, 205, 60, 80, 85, 85])
        lines_style = [
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ]
        for r in range(1, len(line_data)):
            if r % 2 == 0:
                lines_style.append(('BACKGROUND', (0, r), (-1, r), bg_light))
        lines_table.setStyle(TableStyle(lines_style))
        story.append(lines_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # Bottom Block: QR Code (Left) and Tax Totals Breakdown (Right)
        # ------------------------------------------------------------------
        qr_drawing = self._create_qr_drawing(qr_code_tlv, size=100.0)

        inv_hash = (einvoice_record.get("invoice_hash") if einvoice_record else None) or ""
        hash_snippet = f"Hash: {inv_hash[:32]}..." if inv_hash else ""

        qr_cell = [
            qr_drawing,
            Spacer(1, 4),
            Paragraph(f"<font size='7' color='#64748B'><b>ZATCA / Fiscal QR Code</b><br/>{hash_snippet}</font>", body_style)
        ]

        totals_table_data = [
            [
                Paragraph("<b>Taxable Amount / المبلغ الخاضع للضريبة:</b>", body_right),
                Paragraph(f"SAR {subtotal:,.2f}", body_right),
            ],
            [
                Paragraph("<b>VAT Total (15%) / مجموع ضريبة القيمة المضافة:</b>", body_right),
                Paragraph(f"SAR {total_vat:,.2f}", body_right),
            ],
            [
                Paragraph("<b>Total Amount / إجمالي الفاتورة:</b>", body_right_bold),
                Paragraph(f"<b>SAR {total_amount:,.2f}</b>", body_right_bold),
            ],
        ]

        totals_table = Table(totals_table_data, colWidths=[200, 100])
        totals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 1), (-1, 1), 1, border_color),
            ('BACKGROUND', (0, 2), (-1, 2), bg_light),
            ('BOX', (0, 2), (-1, 2), 1, accent_blue),
        ]))

        bottom_table = Table(
            [[qr_cell, totals_table]],
            colWidths=[230, 310],
        )
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(KeepTogether([bottom_table]))

        # ------------------------------------------------------------------
        # Footer
        # ------------------------------------------------------------------
        story.append(Spacer(1, 12))
        footer_text = (
            f"<font size='7.5' color='#94A3B8'>"
            f"Official Government e-Invoice compliant with ZATCA Phase 1 & 2 regulations. Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
            f"</font>"
        )
        story.append(Paragraph(footer_text, ParagraphStyle("FiscalFooter", parent=styles["Normal"], alignment=TA_CENTER)))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
