"""
Account Statement PDF Generation Service for Nova ERP.

Generates branded customer account statements containing:
- Header information (Company metadata, statement date, period / as-of date)
- Customer details (Account ID, name, group, contact info)
- 5-bucket aging breakdown summary (Current, 1-30, 31-60, 61-90, 90+)
- Open invoice transaction table with due dates, balances, and overdue days
- Payment instructions, online portal links, and custom collection notices
"""

import io
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import date, datetime, timezone

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

from modules.core.repositories.base import CrudRepository
from modules.crm.services.aging_service import AgingService, parse_date, classify_overdue_days

logger = logging.getLogger(__name__)


class StatementPdfService:
    """Service for generating downloadable, printable PDF Account Statements for AR collections."""

    def __init__(
        self,
        customer_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        aging_service: Optional[AgingService] = None,
    ):
        self.customer_repo = customer_repo or CrudRepository(
            'T0010',
            business_columns=[
                'id',
                'name',
                'group_name',
                'phone',
                'email',
                'credit_limit',
                'balance',
                'is_vip',
                'exclude_from_reminders',
                'preferred_reminder_channel',
                'reminder_phone',
                'reminder_email',
                'is_active',
            ],
        )
        self.invoice_repo = invoice_repo or CrudRepository(
            'T0090',
            business_columns=[
                'id',
                'invoice_number',
                'invoice_type',
                'partner_id',
                'sales_order_id',
                'issue_date',
                'due_date',
                'discount_due_date',
                'discount_percentage',
                'discount_days',
                'early_discount_amount',
                'total_amount',
                'paid_amount',
                'status',
                'notes',
            ],
        )
        self.aging_service = aging_service or AgingService(
            customer_repo=self.customer_repo,
            invoice_repo=self.invoice_repo,
        )

    def generate_statement_pdf_for_customer(
        self,
        customer_id: int,
        as_of_date: Optional[Union[date, str]] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        payment_link: Optional[str] = None,
        custom_message: Optional[str] = None,
        company_info: Optional[Dict[str, Any]] = None,
        currency: str = 'USD',
    ) -> bytes:
        """Convenience method to generate PDF statement for a customer by ID."""
        return self.generate_statement_pdf(
            customer_id=customer_id,
            as_of_date=as_of_date,
            start_date=start_date,
            end_date=end_date,
            payment_link=payment_link,
            custom_message=custom_message,
            company_info=company_info,
            currency=currency,
        )

    def generate_statement_pdf(
        self,
        customer_id: Optional[int] = None,
        customer: Optional[Dict[str, Any]] = None,
        invoices: Optional[List[Dict[str, Any]]] = None,
        aging: Optional[Dict[str, Any]] = None,
        as_of_date: Optional[Union[date, str]] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        payment_link: Optional[str] = None,
        custom_message: Optional[str] = None,
        company_info: Optional[Dict[str, Any]] = None,
        currency: str = 'USD',
    ) -> bytes:
        """Generate formatted PDF binary stream for a customer account statement.

        Args:
            customer_id: ID of the customer (T0010).
            customer: Optional customer dictionary. Fetched if omitted.
            invoices: Optional list of customer invoice dictionaries.
            aging: Optional 5-bucket aging breakdown dictionary.
            as_of_date: Evaluation date for overdue days calculation (defaults to today).
            start_date: Optional start date filter for statement period.
            end_date: Optional end date filter for statement period.
            payment_link: Optional online payment URL.
            custom_message: Optional custom collection or notice text.
            company_info: Optional custom company header details.
            currency: Currency code symbol (defaults to USD).

        Returns:
            bytes: Raw binary PDF data.

        Raises:
            ValueError: If customer not found.
        """
        eval_date = parse_date(as_of_date) or date.today()
        period_start = parse_date(start_date)
        period_end = parse_date(end_date) or eval_date

        # 1. Resolve Customer Data
        if customer is None and customer_id is not None:
            customer = self.customer_repo.get(customer_id)
            if not customer:
                raise ValueError(f'Customer #{customer_id} was not found.')
        elif customer is not None and customer_id is None:
            customer_id = customer.get('id')

        if not customer:
            customer = {
                'id': customer_id or 0,
                'name': 'Valued Customer',
                'email': 'N/A',
                'phone': 'N/A',
                'group_name': 'General',
                'balance': 0.0,
            }

        # 2. Resolve Invoices
        if invoices is None:
            if customer_id:
                invoices = self.invoice_repo.list(filters={'partner_id': customer_id}, limit=500)
            else:
                invoices = []

        # Filter by date range if provided
        filtered_invoices = []
        for inv in invoices:
            inv_date = parse_date(inv.get('issue_date'))
            if period_start and inv_date and inv_date < period_start:
                continue
            if period_end and inv_date and inv_date > period_end:
                continue
            filtered_invoices.append(inv)

        # 3. Resolve Aging Breakdown
        if aging is None:
            aging = self.aging_service.calculate_aging(filtered_invoices, as_of_date=eval_date)

        # 4. Resolve Default Company Info
        default_company = {
            'name': 'NOVA ERP',
            'subtitle': 'B2B Wholesale Supplies & Replenishment',
            'address': '100 Enterprise Way, Suite 400, Food District',
            'contact': 'billing@novaerp.com | +1 (800) 555-NOVA',
            'bank_name': 'Nova Commercial Bank, N.A.',
            'bank_routing': '123456789',
            'bank_account': '987654321098',
        }
        if company_info:
            default_company.update(company_info)

        # 5. Render PDF
        return self._render_pdf(
            customer=customer,
            invoices=filtered_invoices,
            aging=aging,
            as_of_date=eval_date,
            start_date=period_start,
            end_date=period_end,
            payment_link=payment_link,
            custom_message=custom_message,
            company_info=default_company,
            currency=currency,
        )

    def _render_pdf(
        self,
        customer: Dict[str, Any],
        invoices: List[Dict[str, Any]],
        aging: Dict[str, Any],
        as_of_date: date,
        start_date: Optional[date],
        end_date: date,
        payment_link: Optional[str],
        custom_message: Optional[str],
        company_info: Dict[str, Any],
        currency: str,
    ) -> bytes:
        """Internal helper to construct ReportLab story flowables and render statement PDF bytes."""
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

        # Color palette
        primary_color = colors.HexColor('#0F172A')    # Slate 900
        secondary_color = colors.HexColor('#334155')  # Slate 700
        muted_color = colors.HexColor('#64748B')      # Slate 500
        accent_blue = colors.HexColor('#2563EB')      # Blue 600
        accent_indigo = colors.HexColor('#4F46E5')    # Indigo 600
        paid_green = colors.HexColor('#16A34A')       # Green 600
        warning_amber = colors.HexColor('#D97706')    # Amber 600
        danger_red = colors.HexColor('#DC2626')       # Red 600
        bg_light = colors.HexColor('#F8FAFC')         # Slate 50
        bg_subtle = colors.HexColor('#F1F5F9')        # Slate 100
        border_color = colors.HexColor('#E2E8F0')     # Slate 200

        # Custom Typography Styles
        title_style = ParagraphStyle(
            'StatementTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        company_title_style = ParagraphStyle(
            'CompanyTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=accent_blue,
        )

        company_sub_style = ParagraphStyle(
            'CompanySub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=muted_color,
        )

        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=secondary_color,
        )

        body_style = ParagraphStyle(
            'StmtBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
        )

        body_right_style = ParagraphStyle(
            'StmtBodyRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        body_right_bold = ParagraphStyle(
            'StmtBodyRightBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=12,
            textColor=primary_color,
            alignment=TA_RIGHT,
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )

        table_header_right = ParagraphStyle(
            'TableHeaderRight',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        aging_header_style = ParagraphStyle(
            'AgingHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        )

        aging_value_style = ParagraphStyle(
            'AgingValue',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=primary_color,
            alignment=TA_CENTER,
        )

        story = []

        # ------------------------------------------------------------------
        # 1. Header: Company Info (Left) & Statement Title / Ref (Right)
        # ------------------------------------------------------------------
        customer_id = customer.get('id') or 'N/A'
        stmt_ref = f'STMT-{customer_id}-{as_of_date.strftime("%Y%m%d")}'

        company_html = (
            f"<b>{company_info.get('name', 'NOVA ERP')}</b><br/>"
            f"<font size='8' color='#64748B'>{company_info.get('subtitle', 'B2B Wholesale Supplies & Replenishment')}</font><br/>"
            f"<font size='8' color='#64748B'>{company_info.get('address', '')}<br/>"
            f"{company_info.get('contact', '')}</font>"
        )

        period_str = f"As of {as_of_date.isoformat()}"
        if start_date:
            period_str = f"{start_date.isoformat()} to {end_date.isoformat()}"

        stmt_header_html = (
            f"<b>ACCOUNT STATEMENT</b><br/>"
            f"<font size='9' color='#64748B'>Reference: <b>#{stmt_ref}</b></font><br/>"
            f"<font size='8.5' color='#334155'>Statement Period: {period_str}</font><br/>"
            f"<font size='8' color='#64748B'>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</font>"
        )

        header_table = Table(
            [
                [
                    Paragraph(company_html, company_sub_style),
                    Paragraph(stmt_header_html, title_style),
                ]
            ],
            colWidths=[270, 270],
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width='100%', thickness=2, color=accent_blue, spaceBefore=4, spaceAfter=10))

        # ------------------------------------------------------------------
        # 2. Metadata Cards: Customer Details (Left) & Statement Overview (Right)
        # ------------------------------------------------------------------
        cust_name = customer.get('name') or 'Valued Customer'
        cust_email = customer.get('reminder_email') or customer.get('email') or 'N/A'
        cust_phone = customer.get('reminder_phone') or customer.get('phone') or 'N/A'
        cust_group = customer.get('group_name') or 'Wholesale'
        is_vip = customer.get('is_vip', False)
        vip_badge = " <font color='#D97706'><b>[VIP Account]</b></font>" if is_vip else ""

        billed_to_html = (
            f"<b>{cust_name}</b>{vip_badge}<br/>"
            f"<font color='#64748B'>Customer Account ID:</font> #{customer_id}<br/>"
            f"<font color='#64748B'>Customer Group:</font> {cust_group}<br/>"
            f"<font color='#64748B'>Billing Email:</font> {cust_email}<br/>"
            f"<font color='#64748B'>Phone:</font> {cust_phone}"
        )

        total_outstanding = float(aging.get('total_outstanding', 0.0))
        total_overdue = sum(
            float(aging.get(b, 0.0))
            for b in ('1_30', '31_60', '61_90', '90_plus')
        )
        total_current = float(aging.get('current', 0.0))

        status_text = 'CURRENT / IN GOOD STANDING'
        status_color_hex = '#16A34A'
        if total_overdue > 0:
            status_text = 'ACTION REQUIRED: OVERDUE BALANCE'
            status_color_hex = '#DC2626'
        elif total_outstanding == 0:
            status_text = 'ZERO BALANCE / FULLY SETTLED'
            status_color_hex = '#16A34A'

        overview_html = (
            f"<font color='#64748B'>Total Outstanding Balance:</font> <b>${total_outstanding:,.2f} {currency}</b><br/>"
            f"<font color='#64748B'>Current (Not Overdue):</font> ${total_current:,.2f}<br/>"
            f"<font color='#64748B'>Total Overdue:</font> <font color='{status_color_hex}'><b>${total_overdue:,.2f}</b></font><br/>"
            f"<font color='#64748B'>Account Status:</font> <font color='{status_color_hex}'><b>{status_text}</b></font>"
        )

        meta_table = Table(
            [
                [
                    Paragraph('<b>BILLED TO / ACCOUNT DETAILS</b>', section_heading_style),
                    Paragraph('<b>STATEMENT SUMMARY</b>', section_heading_style),
                ],
                [
                    Paragraph(billed_to_html, body_style),
                    Paragraph(overview_html, body_style),
                ]
            ],
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
        # 3. 5-Bucket Aging Breakdown Matrix
        # ------------------------------------------------------------------
        story.append(Paragraph('<b>ACCOUNTS RECEIVABLE AGING BREAKDOWN</b>', section_heading_style))
        story.append(Spacer(1, 4))

        aging_val_current = float(aging.get('current', 0.0))
        aging_val_1_30 = float(aging.get('1_30', aging.get('30', 0.0)))
        aging_val_31_60 = float(aging.get('31_60', aging.get('60', 0.0)))
        aging_val_61_90 = float(aging.get('61_90', aging.get('90', 0.0)))
        aging_val_90_plus = float(aging.get('90_plus', 0.0))
        aging_val_total = float(aging.get('total_outstanding', sum([
            aging_val_current, aging_val_1_30, aging_val_31_60, aging_val_61_90, aging_val_90_plus
        ])))

        aging_headers = [
            Paragraph('Current', aging_header_style),
            Paragraph('1–30 Days', aging_header_style),
            Paragraph('31–60 Days', aging_header_style),
            Paragraph('61–90 Days', aging_header_style),
            Paragraph('90+ Days', aging_header_style),
            Paragraph('Total Balance', aging_header_style),
        ]

        def format_aging_cell(val: float, is_overdue: bool = False, is_total: bool = False) -> Paragraph:
            if val > 0:
                if is_total:
                    txt = f'<b>${val:,.2f}</b>'
                elif is_overdue:
                    txt = f"<font color='#DC2626'><b>${val:,.2f}</b></font>"
                else:
                    txt = f'<b>${val:,.2f}</b>'
            else:
                txt = '$0.00'
            return Paragraph(txt, aging_value_style)

        aging_values = [
            format_aging_cell(aging_val_current, is_overdue=False),
            format_aging_cell(aging_val_1_30, is_overdue=True),
            format_aging_cell(aging_val_31_60, is_overdue=True),
            format_aging_cell(aging_val_61_90, is_overdue=True),
            format_aging_cell(aging_val_90_plus, is_overdue=True),
            format_aging_cell(aging_val_total, is_total=True),
        ]

        aging_col_w = 540 / 6  # 90pt each
        aging_table = Table([aging_headers, aging_values], colWidths=[aging_col_w] * 6)
        aging_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-2, 0), secondary_color),
            ('BACKGROUND', (-1, 0), (-1, 0), primary_color),
            ('BACKGROUND', (0, 1), (-1, 1), bg_light),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ]))
        story.append(aging_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # 4. Open Invoices & Statement Transactions Table
        # ------------------------------------------------------------------
        story.append(Paragraph('<b>OPEN INVOICES & RECENT TRANSACTIONS</b>', section_heading_style))
        story.append(Spacer(1, 4))

        table_headers = [
            Paragraph('#', table_header_style),
            Paragraph('Invoice #', table_header_style),
            Paragraph('Issue Date', table_header_style),
            Paragraph('Due Date', table_header_style),
            Paragraph('Total', table_header_right),
            Paragraph('Paid', table_header_right),
            Paragraph('Balance Due', table_header_right),
            Paragraph('Overdue', table_header_right),
            Paragraph('Status', table_header_style),
        ]

        # Column widths: 20 + 80 + 55 + 55 + 65 + 55 + 70 + 60 + 80 = 540
        col_widths = [20, 80, 55, 55, 65, 55, 70, 60, 80]

        table_rows = [table_headers]

        # Classify open invoices
        open_invoices = [
            inv for inv in invoices
            if str(inv.get('status', '')).lower() not in ('cancelled', 'void')
        ]

        if open_invoices:
            for idx, inv in enumerate(open_invoices, start=1):
                inv_num = inv.get('invoice_number') or f"INV-{inv.get('id')}"
                iss_date = parse_date(inv.get('issue_date'))
                iss_str = iss_date.isoformat() if iss_date else '—'
                d_date = parse_date(inv.get('due_date')) or iss_date or as_of_date
                due_str = d_date.isoformat() if d_date else '—'

                tot_val = float(inv.get('total_amount', 0.0) or 0.0)
                paid_val = float(inv.get('paid_amount', 0.0) or 0.0)
                inv_status = str(inv.get('status', 'Unpaid')).strip()

                if inv_status.lower() == 'paid':
                    bal_val = 0.0
                    days_over = 0
                else:
                    bal_val = float(inv.get('balance_due', max(0.0, tot_val - paid_val)))
                    days_over = (as_of_date - d_date).days if d_date and d_date < as_of_date else 0

                # Determine badge styling
                if inv_status.lower() == 'paid':
                    status_display = "<font color='#16A34A'><b>Paid</b></font>"
                    overdue_display = '—'
                elif days_over > 0:
                    status_display = f"<font color='#DC2626'><b>Overdue</b></font>"
                    overdue_display = f"<font color='#DC2626'><b>+{days_over}d</b></font>"
                elif inv_status.lower() == 'partially paid':
                    status_display = "<font color='#D97706'><b>Partially Paid</b></font>"
                    overdue_display = 'Current'
                else:
                    status_display = "<font color='#2563EB'><b>Open</b></font>"
                    overdue_display = 'Current'

                table_rows.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(f'<b>{inv_num}</b>', body_style),
                    Paragraph(iss_str, body_style),
                    Paragraph(due_str, body_style),
                    Paragraph(f'${tot_val:,.2f}', body_right_style),
                    Paragraph(f'${paid_val:,.2f}', body_right_style),
                    Paragraph(f'<b>${bal_val:,.2f}</b>', body_right_bold),
                    Paragraph(overdue_display, body_right_style),
                    Paragraph(status_display, body_style),
                ])
        else:
            # Fallback zero-balance row
            table_rows.append([
                Paragraph('—', body_style),
                Paragraph('<b>No Outstanding Invoices</b>', body_style),
                Paragraph('—', body_style),
                Paragraph('—', body_style),
                Paragraph('$0.00', body_right_style),
                Paragraph('$0.00', body_right_style),
                Paragraph('$0.00', body_right_bold),
                Paragraph('—', body_right_style),
                Paragraph("<font color='#16A34A'><b>Settled</b></font>", body_style),
            ])

        tx_table = Table(table_rows, colWidths=col_widths)
        tx_style = [
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ]

        # Alternating row highlights
        for r_idx in range(1, len(table_rows)):
            if r_idx % 2 == 0:
                tx_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg_light))

        tx_table.setStyle(TableStyle(tx_style))
        story.append(tx_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # 5. Payment Instructions & Action Notice (KeepTogether)
        # ------------------------------------------------------------------
        payment_info_html = (
            f"<b>REMITTANCE & PAYMENT INSTRUCTIONS:</b><br/>"
            f"• <b>Direct Bank ACH / Wire Transfer:</b> Bank: <b>{company_info.get('bank_name')}</b> | "
            f"Routing: <b>{company_info.get('bank_routing')}</b> | Account: <b>{company_info.get('bank_account')}</b><br/>"
            f"• <b>B2B Customer Portal:</b> Log in to settle invoices via Corporate Credit Card or instant ACH.<br/>"
            f"• Please quote Statement Reference <b>#{stmt_ref}</b> with all remittance advices."
        )
        if payment_link:
            payment_info_html += (
                f"<br/>• <b>Direct One-Click Payment Link:</b> "
                f"<font color='#2563EB'><u>{payment_link}</u></font>"
            )

        if custom_message:
            payment_info_html += f"<br/><br/><b>Special Notice:</b> {custom_message}"

        notice_box = Table(
            [[Paragraph(payment_info_html, body_style)]],
            colWidths=[540],
        )
        notice_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        footer_html = (
            f"<font size='7.5' color='#94A3B8'>"
            f"Generated automatically by Nova ERP AR Collection & Statement Dispatch Engine on "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"For questions, billing disputes, or payment assistance, contact {company_info.get('contact', 'billing@novaerp.com')}."
            f"</font>"
        )
        footer_p = Paragraph(footer_html, ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER))

        closing_block = KeepTogether([
            notice_box,
            Spacer(1, 8),
            footer_p,
        ])
        story.append(closing_block)

        # Build Document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
