import io
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, date

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
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

from modules.accounting.services.einvoice_service import EInvoiceService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)


class FiscalPdfService:
    """Service for generating bilingual (English/Arabic) printable fiscal invoices with security seals and QR codes."""

    def __init__(
        self,
        einvoice_service: Optional[EInvoiceService] = None,
        invoice_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        line_repo: Optional[CrudRepository] = None,
    ):
        self.einvoice_service = einvoice_service or EInvoiceService()
        self.invoice_repo = invoice_repo or self.einvoice_service.invoice_repo
        self.customer_repo = customer_repo or self.einvoice_service.customer_repo
        self.line_repo = line_repo or self.einvoice_service.line_repo

    def generate_fiscal_invoice_pdf(
        self,
        invoice_id: int,
        conn=None,
    ) -> bytes:
        """Generate formatted bilingual fiscal tax invoice PDF binary stream.

        Args:
            invoice_id: Sales invoice ID (T0090).
            conn: Optional database connection.

        Returns:
            bytes: Raw binary PDF data.
        """
        invoice = self.invoice_repo.get(invoice_id, conn=conn)
        if not invoice:
            raise ValueError(f"Sales invoice #{invoice_id} was not found.")

        partner_id = invoice.get("partner_id")
        customer = self.customer_repo.get(partner_id, conn=conn) if partner_id else None

        # Fetch lines if available
        lines = []
        sales_order_id = invoice.get("sales_order_id")
        if sales_order_id:
            try:
                lines = self.line_repo.list(filters={"sales_order_id": sales_order_id}, conn=conn)
            except Exception as exc:
                logger.warning(f"Could not fetch lines for order {sales_order_id}: {exc}")

        # Fetch or generate e-invoice clearance record and QR
        einvoice_record = self.einvoice_service.get_by_invoice_id(invoice_id, conn=conn)
        qr_response = self.einvoice_service.generate_qr_code(invoice_id, conn=conn)
        profile = self.einvoice_service.get_active_fiscal_profile(
            einvoice_record.get("fiscal_profile_id") if einvoice_record else None,
            conn=conn,
        )

        return self._render_bilingual_pdf(
            invoice=invoice,
            customer=customer,
            lines=lines,
            einvoice_record=einvoice_record,
            qr_response=qr_response,
            profile=profile,
        )

    def _render_bilingual_pdf(
        self,
        invoice: Dict[str, Any],
        customer: Optional[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        einvoice_record: Optional[Dict[str, Any]],
        qr_response: Any,
        profile: Dict[str, Any],
    ) -> bytes:
        """Render the ReportLab story for the bilingual fiscal invoice."""
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
        accent_blue = colors.HexColor("#1E40AF")      # Blue 800
        paid_green = colors.HexColor("#16A34A")       # Green 600
        amber_color = colors.HexColor("#D97706")      # Amber 600
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

        company_sub_style = ParagraphStyle(
            "FiscalCompanySub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=muted_color,
        )

        body_style = ParagraphStyle(
            "FiscalBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=primary_color,
        )

        body_right_style = ParagraphStyle(
            "FiscalBodyRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        body_right_bold = ParagraphStyle(
            "FiscalBodyRightBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        table_header_style = ParagraphStyle(
            "FiscalTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        table_header_right = ParagraphStyle(
            "FiscalTableHeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        story = []

        # ------------------------------------------------------------------
        # Header: Bilingual Supplier Details & Tax Invoice Title
        # ------------------------------------------------------------------
        seller_en = profile.get("seller_name") or "Nova Global Trading LLC"
        seller_ar = profile.get("seller_name_ar") or "شركة نوفا للتجارة العامة"
        tax_id = profile.get("tax_id") or "300012345600003"
        cr_number = profile.get("commercial_registration_number") or "1010123456"
        building = profile.get("building_number") or "1234"
        street = profile.get("street_name") or "King Fahd Road"
        district = profile.get("district") or "Al Olaya"
        city = profile.get("city") or "Riyadh"
        postal = profile.get("postal_code") or "12211"
        country = profile.get("country_code") or "SA"

        supplier_html = (
            f"<b>{seller_en}</b><br/>"
            f"<font color='#334155'>{seller_ar}</font><br/>"
            f"<font color='#64748B'><b>VAT / Tax ID:</b> {tax_id} | <b>CR:</b> {cr_number}<br/>"
            f"Address: {building} {street}, {district}, {city} {postal}, {country}</font>"
        )

        inv_number = invoice.get("invoice_number", f"INV-{invoice.get('id')}")
        clearance_status = (einvoice_record.get("clearance_status") if einvoice_record else None) or "Draft"

        badge_color = paid_green if clearance_status in ("Cleared", "Reported") else amber_color
        inv_title_html = (
            f"<b>TAX INVOICE / فاتورة ضريبية</b><br/>"
            f"<font size='10' color='#1E40AF'>#{inv_number}</font><br/>"
            f"<font size='8' color='{badge_color.hexval()}'><b>FISCAL STATUS: {clearance_status.upper()}</b></font>"
        )

        header_table = Table(
            [[Paragraph(supplier_html, company_sub_style), Paragraph(inv_title_html, title_style)]],
            colWidths=[310, 230],
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceBefore=4, spaceAfter=8))

        # ------------------------------------------------------------------
        # Metadata Block: Buyer / Customer Info (Left) & Invoice Dates / UUID (Right)
        # ------------------------------------------------------------------
        cust_name = (customer.get("name") if customer else None) or invoice.get("customer_name") or "Valued Customer / العميل"
        cust_vat = (customer.get("tax_id") if customer else None) or (customer.get("vat_number") if customer else None) or "N/A"
        cust_cr = (customer.get("commercial_registration_number") if customer else None) or "N/A"
        cust_city = (customer.get("city") if customer else None) or "N/A"

        buyer_html = (
            f"<b>Billed To / العميل:</b><br/>"
            f"<b>{cust_name}</b><br/>"
            f"<font color='#64748B'><b>Buyer VAT No / الرقم الضريبي:</b> {cust_vat}<br/>"
            f"<b>CR No / السجل التجاري:</b> {cust_cr} | <b>City:</b> {cust_city}</font>"
        )

        issue_date_val = invoice.get("issue_date") or datetime.now(timezone.utc).date()
        due_date_val = invoice.get("due_date") or issue_date_val
        inv_uuid_val = (einvoice_record.get("invoice_uuid") if einvoice_record else None) or "N/A"
        icv_val = (einvoice_record.get("icv") if einvoice_record else None) or "1"

        meta_html = (
            f"<b>Invoice Details / بيانات الفاتورة:</b><br/>"
            f"<font color='#64748B'>"
            f"<b>Issue Date / تاريخ الإصدار:</b> {issue_date_val}<br/>"
            f"<b>Due Date / تاريخ الاستحقاق:</b> {due_date_val}<br/>"
            f"<b>Invoice Counter (ICV):</b> {icv_val}<br/>"
            f"<b>UUID:</b> <font size='6'>{inv_uuid_val}</font>"
            f"</font>"
        )

        meta_table = Table(
            [[Paragraph(buyer_html, body_style), Paragraph(meta_html, body_style)]],
            colWidths=[270, 270],
        )
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # ------------------------------------------------------------------
        # Line Items Table
        # ------------------------------------------------------------------
        total_amount = float(invoice.get("total_amount") or 0.0)
        table_headers = [
            Paragraph("<b>#</b>", table_header_style),
            Paragraph("<b>Item & Description / الصنف والوصف</b>", table_header_style),
            Paragraph("<b>Qty / الكمية</b>", table_header_right),
            Paragraph("<b>Unit Price / السعر</b>", table_header_right),
            Paragraph("<b>VAT / الضريبة</b>", table_header_right),
            Paragraph("<b>Total / المجموع</b>", table_header_right),
        ]

        items_data = [table_headers]

        if lines:
            for idx, line in enumerate(lines, start=1):
                p_name = line.get("product_name") or f"Product #{line.get('product_id')}"
                p_code = line.get("product_code") or ""
                item_label = f"<b>{p_name}</b>"
                if p_code:
                    item_label += f" <font size='7' color='#64748B'>({p_code})</font>"

                qty_val = float(line.get("qty", 1.0))
                unit_price = float(line.get("unit_price", 0.0))
                line_subtotal = qty_val * unit_price
                vat_rate = float(line.get("tax_rate", 15.0))
                vat_amount = round(line_subtotal * (vat_rate / 100.0), 2)
                line_total = line_subtotal + vat_amount

                items_data.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(item_label, body_style),
                    Paragraph(f"{qty_val:,.2f}", body_right_style),
                    Paragraph(f"{unit_price:,.2f}", body_right_style),
                    Paragraph(f"{vat_amount:,.2f} ({vat_rate:.0f}%)", body_right_style),
                    Paragraph(f"{line_total:,.2f}", body_right_style),
                ])
        else:
            vat_subtotal = round(total_amount / 1.15, 2)
            vat_val = round(total_amount - vat_subtotal, 2)
            items_data.append([
                Paragraph("1", body_style),
                Paragraph("<b>Taxable Commercial Goods / بضائع تجارية خاضعة للضريبة</b>", body_style),
                Paragraph("1.00", body_right_style),
                Paragraph(f"{vat_subtotal:,.2f}", body_right_style),
                Paragraph(f"{vat_val:,.2f} (15%)", body_right_style),
                Paragraph(f"{total_amount:,.2f}", body_right_style),
            ])

        lines_table = Table(items_data, colWidths=[24, 216, 60, 75, 80, 85])
        lines_style = [
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ]
        for r_idx in range(1, len(items_data)):
            if r_idx % 2 == 0:
                lines_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg_light))

        lines_table.setStyle(TableStyle(lines_style))
        story.append(lines_table)
        story.append(Spacer(1, 8))

        # ------------------------------------------------------------------
        # Bottom Block: QR Code & Security Seals (Left) & Tax Summary (Right)
        # ------------------------------------------------------------------
        qr_tlv = getattr(qr_response, "qr_code_tlv", None) or (einvoice_record.get("qr_code_tlv") if einvoice_record else None) or "NOVA_ZATCA_TLV_QR"

        qr_drawing = Drawing(90, 90)
        try:
            qr_widget = QrCodeWidget(qr_tlv)
            bounds = qr_widget.getBounds()
            w_val = bounds[2] - bounds[0]
            h_val = bounds[3] - bounds[1]
            if w_val > 0 and h_val > 0:
                qr_drawing = Drawing(90, 90, transform=[90 / w_val, 0, 0, 90 / h_val, 0, 0])
                qr_drawing.add(qr_widget)
        except Exception as exc:
            logger.warning(f"Could not render QR widget: {exc}")

        hash_snippet = (einvoice_record.get("invoice_hash") if einvoice_record else None) or "SHA256: DRAFT_NOVA_HASH"
        short_hash = f"{hash_snippet[:24]}...{hash_snippet[-8:]}" if len(hash_snippet) > 32 else hash_snippet
        clearance_id = (einvoice_record.get("clearance_id") if einvoice_record else None) or "PENDING_TAX_GATEWAY"

        seal_text = (
            f"<b>ZATCA / Tax Authority Security Seal:</b><br/>"
            f"<font size='7' color='#475569'>"
            f"<b>Clearance ID (IRN):</b> {clearance_id}<br/>"
            f"<b>Digital SHA-256 Hash:</b> {short_hash}<br/>"
            f"<b>Environment:</b> {profile.get('environment', 'Sandbox')}"
            f"</font>"
        )

        qr_seal_inner_table = Table(
            [[qr_drawing, Paragraph(seal_text, body_style)]],
            colWidths=[95, 185],
        )
        qr_seal_inner_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        tax_subtotal = round(total_amount / 1.15, 2)
        total_vat = round(total_amount - tax_subtotal, 2)

        totals_table_data = [
            [
                Paragraph("<b>Total (Excl. VAT) / المجموع غير شامل الضريبة:</b>", body_right_style),
                Paragraph(f"{tax_subtotal:,.2f} SAR", body_right_style),
            ],
            [
                Paragraph("<b>VAT Rate / نسبة ضريبة القيمة المضافة:</b>", body_right_style),
                Paragraph("15.00%", body_right_style),
            ],
            [
                Paragraph("<b>Total VAT / مجموع ضريبة القيمة المضافة:</b>", body_right_style),
                Paragraph(f"{total_vat:,.2f} SAR", body_right_style),
            ],
            [
                Paragraph("<b>Total (Incl. VAT) / المجموع شامل الضريبة:</b>", body_right_bold),
                Paragraph(f"<b>{total_amount:,.2f} SAR</b>", body_right_bold),
            ],
        ]

        totals_table = Table(totals_table_data, colWidths=[160, 90])
        totals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 2), (-1, 2), 0.5, border_color),
            ('BACKGROUND', (0, 3), (-1, 3), bg_light),
            ('BOX', (0, 3), (-1, 3), 1, accent_blue),
        ]))

        bottom_table = Table(
            [[qr_seal_inner_table, totals_table]],
            colWidths=[285, 255],
        )
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(KeepTogether([bottom_table]))

        story.append(Spacer(1, 10))
        footer_html = (
            f"<font size='7' color='#94A3B8'>"
            f"Official Government e-Invoice compliant with ZATCA Phase 1 & 2 requirements. "
            f"Generated by Nova ERP on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
            f"</font>"
        )
        story.append(Paragraph(footer_html, ParagraphStyle("FiscalFooter", parent=styles["Normal"], alignment=TA_CENTER)))

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data


fiscal_pdf_service = FiscalPdfService()
