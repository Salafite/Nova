"""
Nova ERP — Outbound EDI 810 (Sales Invoice) & UN/EDIFACT INVOIC Generator
Constructs electronic tax invoices matching delivered lines, allowances/discounts,
tax breakdowns, and buyer PO numbers from completed deliveries and invoices (T0090/T0026).
Supports both ANSI X12 810 and UN/EDIFACT INVOIC document formats.
"""

import re
import uuid
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from packages.database.connection import get_connection, release_connection, db_transaction

from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiDirection,
    EdiInvoiceTransmitRequest,
    EdiInvoiceTransmitResponse,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_TRANSACTION_REPO,
)
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiSegment,
    EdiTransactionSet,
    EdiFunctionalGroup,
    EdiInterchange,
    detect_edi_standard,
    parse_x12,
    parse_edifact,
    parse_edi,
    serialize_x12,
    serialize_edifact,
    serialize_edi,
    X12Builder,
    EdifactBuilder,
    EdiSyntaxError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Repositories for Invoices, Orders, Deliveries, Customers, Products, Taxes
# ---------------------------------------------------------------------------

INVOICE_T0090_REPO = CrudRepository(
    'T0090',
    business_columns=[
        'id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id',
        'sales_rep_id', 'payment_term_id', 'issue_date', 'due_date',
        'discount_due_date', 'discount_percentage', 'discount_days',
        'early_discount_amount', 'total_amount', 'freight_amount',
        'discount_amount', 'status', 'notes', 'is_catch_weight',
        'nominal_total_weight', 'actual_total_weight', 'weight_adjustment_amount',
    ],
)

SALES_ORDER_T0012_REPO = CrudRepository(
    'T0012',
    business_columns=[
        'id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal',
        'tax', 'grand_total', 'freight_amount', 'discount_amount',
        'sales_rep_id', 'status', 'order_date', 'notes', 'price_list_id',
        'tax_rate_id', 'payment_term_id', 'client_order_uuid',
    ],
)

SALES_LINE_T0013_REPO = CrudRepository(
    'T0013',
    business_columns=[
        'id', 'sales_order_id', 'product_id', 'product_name', 'uom_id',
        'qty', 'unit_price', 'cost_price', 'discount', 'line_total',
        'line_number', 'is_catch_weight', 'pricing_uom_id',
        'unit_price_pricing_uom', 'nominal_weight', 'catch_weight_actual',
        'recalculated_total',
    ],
)

DELIVERY_T0077_REPO = CrudRepository(
    'T0077',
    business_columns=[
        'id', 'delivery_number', 'sales_order_id', 'delivery_date', 'warehouse_id',
        'freight_cost', 'delivery_route', 'actual_delivery_date', 'status', 'notes',
        'recipient_signature', 'delivery_photo_url', 'pod_timestamp', 'delivery_location',
        'payment_status', 'cod_cash_amount', 'cod_check_amount', 'cod_check_number',
        'cod_check_bank', 'driver_id',
    ],
)

DELIVERY_LINE_T0078_REPO = CrudRepository(
    'T0078',
    business_columns=[
        'id', 'delivery_id', 'sales_order_line_id', 'product_id',
        'product_name', 'qty_shipped', 'qty_ordered', 'uom_id', 'line_number',
    ],
)

CUSTOMER_T0010_REPO = CrudRepository(
    'T0010',
    business_columns=[
        'id', 'name', 'group_name', 'phone', 'email', 'credit_limit',
        'balance', 'is_active', 'default_price_list_id', 'default_tax_rate_id',
        'payment_term_id',
    ],
)

PRODUCT_T0001_REPO = CrudRepository(
    'T0001',
    business_columns=[
        'id', 'sku', 'name', 'description', 'category_id', 'brand_id',
        'uom_id', 'price', 'cost', 'barcode', 'is_active',
    ],
)

PAYMENT_TERM_T0089_REPO = CrudRepository(
    'T0089',
    business_columns=[
        'id', 'code', 'name', 'net_days', 'discount_days', 'discount_percent',
        'description', 'is_active',
    ],
)

TAX_RATE_T0085_REPO = CrudRepository(
    'T0085',
    business_columns=[
        'id', 'name', 'rate', 'tax_type', 'is_active',
    ],
)

PICK_LIST_ITEM_T0102_REPO = CrudRepository(
    'T0102',
    business_columns=[
        'id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name',
        'qty_ordered', 'qty_picked', 'line_number', 'batch_id', 'batch_number',
        'expiry_date', 'picked_batch_id', 'picked_batch_number',
    ],
)



# ---------------------------------------------------------------------------
# Sequence Helper
# ---------------------------------------------------------------------------

def _fetch_nextval(conn, sequence_name: str = "seq_edi_control_num") -> Optional[int]:
    """Fetch next integer value from PostgreSQL sequence."""
    try:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT nextval('\"Nova\".{sequence_name}')")
            row = cur.fetchone()
            if row:
                return int(row[0])
        except Exception:
            try:
                cur.execute(f"SELECT nextval('{sequence_name}')")
                row = cur.fetchone()
                if row:
                    return int(row[0])
            except Exception:
                pass
        finally:
            cur.close()
    except Exception as e:
        logger.debug(f"Could not read sequence {sequence_name}: {e}")
    return None


def _generate_control_number(conn=None) -> str:
    """Generate next EDI control number."""
    val = None
    if conn is not None:
        val = _fetch_nextval(conn, "seq_edi_control_num")
    else:
        try:
            c = get_connection()
            try:
                val = _fetch_nextval(c, "seq_edi_control_num")
            finally:
                release_connection(c)
        except Exception:
            pass

    if val is None:
        import time
        val = int(time.time() * 1000) % 1000000000
    return str(val)


# ---------------------------------------------------------------------------
# Domain Models for EDI 810 Invoice & INVOIC Generation and Parsing
# ---------------------------------------------------------------------------

class EdiInvoiceParty(BaseModel):
    """Party entity in an EDI invoice (Seller, Buyer, Ship To, Remit To)."""
    party_type: str = "BY"  # SE, BY, BT, ST, RE, SU, DP, IV
    party_name: Optional[str] = None
    party_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class EdiInvoiceAllowanceCharge(BaseModel):
    """Allowance (Discount) or Charge (Freight/Surcharge) detail."""
    indicator: str = "A"  # 'A' = Allowance / Discount, 'C' = Charge / Surcharge
    code: str = "F800"  # 'F800' = Promotion/Discount, 'D240' = Freight, 'E340' = Catch-Weight Adjustment
    description: Optional[str] = "Discount"
    amount: float = 0.0
    rate_percent: Optional[float] = None


class EdiInvoiceTaxSummary(BaseModel):
    """Tax rate breakdown summary."""
    tax_type: str = "VAT"  # 'VAT', 'Sales Tax', 'Standard'
    tax_rate_percent: float = 15.0
    taxable_amount: float = 0.0
    tax_amount: float = 0.0


class EdiInvoiceLine(BaseModel):
    """Line item detail within an electronic invoice."""
    line_number: int = 1
    product_id: Optional[int] = None
    sku: str
    buyer_sku: Optional[str] = None
    vendor_sku: Optional[str] = None
    gtin: Optional[str] = None
    product_name: str
    qty_invoiced: float = 1.0
    qty_delivered: Optional[float] = None
    qty_ordered: Optional[float] = None
    uom: str = "EA"
    unit_price: float = 0.0
    gross_amount: Optional[float] = None
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    tax_amount: float = 0.0
    tax_rate_percent: float = 0.0
    net_amount: float = 0.0
    is_catch_weight: bool = False
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None


# Alias for backward compatibility
EdiInvoiceItemDetail = EdiInvoiceLine



class EdiInvoiceHeader(BaseModel):
    """Header data for an EDI 810 Invoice or UN/EDIFACT INVOIC message."""
    invoice_id: Optional[int] = None
    invoice_number: str
    invoice_type: str = "Standard"  # 'Standard', 'Credit Note', 'Debit Memo'
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = None
    buyer_po_number: Optional[str] = None
    delivery_id: Optional[int] = None
    delivery_number: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    discount_due_date: Optional[date] = None
    currency: str = "USD"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    tax_rate_percent: float = 0.0
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    early_discount_amount: float = 0.0
    discount_days: int = 0
    freight_amount: float = 0.0
    grand_total: float = 0.0
    weight_adjustment_amount: float = 0.0
    nominal_total_weight: Optional[float] = None
    actual_total_weight: Optional[float] = None
    is_catch_weight: bool = False
    payment_term_id: Optional[int] = None
    payment_term_name: Optional[str] = None
    payment_term_code: Optional[str] = None
    net_days: int = 30
    seller_name: Optional[str] = "Nova Distribution Hub"
    seller_id: Optional[str] = "NOVAERP"
    seller_vat_id: Optional[str] = None
    seller_address: Optional[str] = None
    seller_city: Optional[str] = None
    seller_country: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_id: Optional[str] = None
    buyer_vat_id: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_city: Optional[str] = None
    buyer_country: Optional[str] = None
    ship_to_name: Optional[str] = None
    ship_to_id: Optional[str] = None
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_country: Optional[str] = None
    ship_to_store_number: Optional[str] = None
    remit_to_name: Optional[str] = None
    remit_to_id: Optional[str] = None
    notes: Optional[str] = None


class EdiInvoiceDocument(BaseModel):
    """Complete structured Invoice document object."""
    standard: str = "ANSI_X12"
    document_type: str = "810"
    control_number: str = "1"
    sender_id: str = ""
    sender_qualifier: str = "ZZ"
    receiver_id: str = ""
    receiver_qualifier: str = "ZZ"
    is_test: bool = False
    header: EdiInvoiceHeader
    lines: List[EdiInvoiceLine] = Field(default_factory=list)
    allowances_charges: List[EdiInvoiceAllowanceCharge] = Field(default_factory=list)
    taxes: List[EdiInvoiceTaxSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ANSI X12 810 Invoice Builder
# ---------------------------------------------------------------------------

def generate_x12_810(
    invoice_doc: EdiInvoiceDocument,
    delimiters: Optional[EdiDelimiters] = None,
    partner: Optional[Any] = None,
) -> str:
    """
    Constructs an ANSI X12 810 (Invoice) interchange document.
    Segments:
      BIG - Beginning Segment for Invoice (date, invoice_num, po_date, po_num, type)
      CUR - Currency
      REF - Reference Identifiers (VN=Sales Order, SI=Delivery Note, DP=Store, IV=Seller VAT)
      N1 / N3 / N4 - Party Identification (SE=Seller, BY/BT=Buyer, ST=Ship To, RE=Remit To)
      ITD - Terms of Sale / Deferred Terms (discount percent, net days, due dates)
      DTM - Date/Time Reference (003=Invoice, 011=Shipped, 002=Delivery)
      FOB - F.O.B. Related Instructions
      IT1 / PID / SAC / TXI - Line Item loops
      TDS - Total Monetary Value Summary
      TXI - Tax Summary Information
      SAC - Summary Allowances (Discounts) and Charges (Freight)
      ISS - Invoice Shipment Summary (Total Units, Weight)
      CTT - Transaction Totals (Line Count, Hash Quantity)
    """
    delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else EdiDelimiters.x12_default())
    header = invoice_doc.header

    builder = X12Builder(
        sender_id=invoice_doc.sender_id or "NOVAERP",
        receiver_id=invoice_doc.receiver_id or "RETAILHUB",
        sender_qualifier=invoice_doc.sender_qualifier or "ZZ",
        receiver_qualifier=invoice_doc.receiver_qualifier or "ZZ",
        control_number=invoice_doc.control_number or "1",
        is_test=invoice_doc.is_test,
        delimiters=delims,
    )

    builder.start_group(
        functional_code="IN",
        group_control_number=invoice_doc.control_number or "1",
        version="004010",
    )

    builder.start_transaction(
        doc_type="810",
        control_number=str(invoice_doc.control_number or "0001").zfill(4)[-4:],
    )

    now = datetime.now(timezone.utc)
    inv_date_str = header.issue_date.strftime("%Y%m%d") if header.issue_date else now.strftime("%Y%m%d")
    po_num = header.buyer_po_number or "PO-UNSPECIFIED"
    po_date_str = ""  # Optional PO date

    # BIG07: 'DI' = Debit Invoice / Standard Invoice, 'CR' / 'CN' = Credit Note
    is_credit = header.invoice_type in ("Credit Note", "Credit", "CN")
    tx_type_code = "CR" if is_credit else "DI"

    builder.add_segment("BIG", inv_date_str, header.invoice_number, po_date_str, po_num, "", "", tx_type_code)

    # CUR: Currency
    if header.currency:
        builder.add_segment("CUR", "SE", header.currency)

    # REF: Reference Numbers
    if header.sales_order_number:
        builder.add_segment("REF", "VN", header.sales_order_number)
    elif header.sales_order_id:
        builder.add_segment("REF", "VN", f"SO-{header.sales_order_id}")

    if header.delivery_number:
        builder.add_segment("REF", "SI", header.delivery_number)
    elif header.delivery_id:
        builder.add_segment("REF", "SI", f"DEL-{header.delivery_id}")

    if header.ship_to_store_number:
        builder.add_segment("REF", "DP", header.ship_to_store_number)

    if header.seller_vat_id:
        builder.add_segment("REF", "IV", header.seller_vat_id)

    # N1 Party Loops
    # 1. Seller (SE)
    seller_id = header.seller_id or invoice_doc.sender_id or "NOVA-HQ"
    seller_name = header.seller_name or "Nova Distribution Hub"
    builder.add_segment("N1", "SE", seller_name, "92", seller_id)
    if header.seller_address:
        builder.add_segment("N3", header.seller_address)
    if header.seller_city or header.seller_country:
        builder.add_segment("N4", header.seller_city or "", "", "", header.seller_country or "")

    # 2. Buyer (BT / BY)
    buyer_id = header.buyer_id or invoice_doc.receiver_id or "RETAIL-HQ"
    buyer_name = header.buyer_name or "Retail Supermarket Chain"
    builder.add_segment("N1", "BT", buyer_name, "92", buyer_id)
    if header.buyer_address:
        builder.add_segment("N3", header.buyer_address)
    if header.buyer_city or header.buyer_country:
        builder.add_segment("N4", header.buyer_city or "", "", "", header.buyer_country or "")

    # 3. Ship To (ST)
    st_id = header.ship_to_id or header.ship_to_store_number or buyer_id
    st_name = header.ship_to_name or buyer_name
    builder.add_segment("N1", "ST", st_name, "92", st_id)
    if header.ship_to_address:
        builder.add_segment("N3", header.ship_to_address)
    if header.ship_to_city or header.ship_to_country:
        builder.add_segment("N4", header.ship_to_city or "", "", "", header.ship_to_country or "")

    # 4. Remit To (RE) if specified
    if header.remit_to_name:
        builder.add_segment("N1", "RE", header.remit_to_name, "92", header.remit_to_id or seller_id)

    # ITD: Terms of Sale
    # ITD01: '01'=Basic, '05'=Discount Not Applicable
    # ITD02: '3'=Invoice Date
    # ITD03: Discount Percent, ITD04: Discount Due Date, ITD05: Discount Days
    # ITD06: Net Due Date, ITD07: Net Days, ITD08: Discount Amount
    disc_pct_str = f"{header.discount_percentage:.2f}" if header.discount_percentage > 0 else ""
    disc_due_str = header.discount_due_date.strftime("%Y%m%d") if header.discount_due_date else ""
    disc_days_str = str(header.discount_days) if header.discount_days > 0 else ""
    net_due_str = header.due_date.strftime("%Y%m%d") if header.due_date else ""
    net_days_str = str(header.net_days or 30)
    disc_amt_str = f"{header.early_discount_amount:.2f}" if header.early_discount_amount > 0 else ""
    term_code = "01" if (header.discount_percentage > 0 or header.early_discount_amount > 0) else "05"
    term_desc = header.payment_term_name or f"Net {net_days_str} Days"

    builder.add_segment(
        "ITD",
        term_code,
        "3",
        disc_pct_str,
        disc_due_str,
        disc_days_str,
        net_due_str,
        net_days_str,
        disc_amt_str,
        "",
        "",
        "",
        term_desc,
    )

    # DTM: Date references
    builder.add_segment("DTM", "003", inv_date_str)  # 003 = Invoice Date
    if header.due_date:
        builder.add_segment("DTM", "140", header.due_date.strftime("%Y%m%d"))  # 140 = Due Date

    # FOB: Shipping Terms (PP = Prepaid)
    builder.add_segment("FOB", "PP")

    # IT1 Line Item Loops
    total_qty = 0.0
    for line in invoice_doc.lines:
        total_qty += line.qty_invoiced

        # Construct Product Qualifiers
        # e.g. IT1*1*100*EA*15.50*PE*CB*BUYER-SKU*VN*VENDOR-SKU*UP*GTIN*IN*INTERNAL-SKU
        it1_elements = [
            str(line.line_number),
            str(int(line.qty_invoiced) if line.qty_invoiced.is_integer() else line.qty_invoiced),
            line.uom or "EA",
            f"{line.unit_price:.4f}" if line.unit_price else "0.00",
            "PE",  # Price per Each / Base Unit
        ]

        if line.buyer_sku:
            it1_elements.extend(["CB", line.buyer_sku])
        if line.vendor_sku:
            it1_elements.extend(["VN", line.vendor_sku])
        elif line.sku and line.sku != line.buyer_sku:
            it1_elements.extend(["IN", line.sku])
        if line.gtin:
            it1_elements.extend(["UP", line.gtin])

        builder.add_segment("IT1", *it1_elements)

        if line.product_name:
            builder.add_segment("PID", "F", "", "", "", line.product_name)

        # Line-level Allowance / Discount
        if line.discount_amount > 0:
            builder.add_segment(
                "SAC",
                "A",
                "F800",
                "",
                "",
                f"{line.discount_amount:.2f}",
                "",
                "",
                "",
                "",
                "",
                "02",
                "Line Discount",
            )

        # Line-level Tax
        if line.tax_amount > 0:
            builder.add_segment(
                "TXI",
                "TX",
                f"{line.tax_amount:.2f}",
                f"{line.tax_rate_percent:.2f}" if line.tax_rate_percent else "",
            )

    # TDS: Total Monetary Value Summary
    # Standard format: monetary amount
    builder.add_segment("TDS", f"{header.grand_total:.2f}")

    # TXI: Summary Tax Information
    if header.tax_amount > 0:
        builder.add_segment(
            "TXI",
            "TX",
            f"{header.tax_amount:.2f}",
            f"{header.tax_rate_percent:.2f}" if header.tax_rate_percent else "",
        )

    # SAC Summary Allowances & Charges
    # 1. Total Invoice Discount
    if header.discount_amount > 0:
        builder.add_segment(
            "SAC",
            "A",
            "F800",
            "",
            "",
            f"{header.discount_amount:.2f}",
            "",
            "",
            "",
            "",
            "",
            "02",
            "Total Invoice Discount",
        )

    # 2. Freight Charges
    if header.freight_amount > 0:
        builder.add_segment(
            "SAC",
            "C",
            "D240",
            "",
            "",
            f"{header.freight_amount:.2f}",
            "",
            "",
            "",
            "",
            "",
            "02",
            "Freight & Shipping",
        )

    # 3. Catch-Weight Adjustment
    if header.weight_adjustment_amount != 0.0:
        indicator = "C" if header.weight_adjustment_amount > 0 else "A"
        builder.add_segment(
            "SAC",
            indicator,
            "E340",
            "",
            "",
            f"{abs(header.weight_adjustment_amount):.2f}",
            "",
            "",
            "",
            "",
            "",
            "02",
            "Catch Weight Adjustment",
        )

    # Custom allowances/charges list
    for ac in invoice_doc.allowances_charges:
        builder.add_segment(
            "SAC",
            ac.indicator,
            ac.code,
            "",
            "",
            f"{ac.amount:.2f}",
            "",
            "",
            "",
            "",
            "",
            "02",
            ac.description or "Allowance/Charge",
        )

    # ISS: Summary Quantity / Weight
    total_weight = header.actual_total_weight or header.nominal_total_weight or 0.0
    builder.add_segment(
        "ISS",
        str(int(total_qty) if total_qty.is_integer() else total_qty),
        "EA",
        f"{total_weight:.2f}" if total_weight > 0 else "",
        "KG" if total_weight > 0 else "",
    )

    # CTT: Transaction Totals
    builder.add_segment("CTT", str(len(invoice_doc.lines)), str(int(total_qty)))

    return builder.build()


# ---------------------------------------------------------------------------
# UN/EDIFACT INVOIC Builder
# ---------------------------------------------------------------------------

def generate_edifact_invoic(
    invoice_doc: EdiInvoiceDocument,
    delimiters: Optional[EdiDelimiters] = None,
    partner: Optional[Any] = None,
) -> str:
    """
    Constructs a UN/EDIFACT INVOIC (D.96A / EAN008) interchange document.
    Segments:
      BGM - Beginning of Message (380=Commercial Invoice, 381=Credit Note)
      DTM - Date/Time Reference (137=Document Date, 35=Delivery Date, 140=Due Date, 12=Discount Due Date)
      RFF - References (ON=Buyer PO, DQ=Delivery Note, VN=Sales Order, VA=Seller VAT)
      NAD - Parties (SU=Supplier, BY=Buyer, DP=Delivery Party / Ship To, IV=Invoicee)
      CUX - Currencies
      PAT / PCD / MOA / DTM - Payment Terms & Discounts
      LIN / PIA / IMD / QTY / MOA / PRI / TAX / ALC - Item loops
      UNS - Section Control ('S')
      CNT - Control Totals (2=Line Count, 1=Total Quantity)
      MOA - Monetary Amounts (77=Total Invoice, 79=Subtotal, 125=Taxable, 176=Tax, 131=Freight, 52=Discount)
      TAX - Tax Breakdown Summaries
    """
    delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else EdiDelimiters.edifact_default())
    header = invoice_doc.header

    builder = EdifactBuilder(
        sender_id=invoice_doc.sender_id or "NOVAERP",
        receiver_id=invoice_doc.receiver_id or "RETAILHUB",
        sender_qualifier=invoice_doc.sender_qualifier or "14",
        receiver_qualifier=invoice_doc.receiver_qualifier or "14",
        control_number=invoice_doc.control_number or "1",
        is_test=invoice_doc.is_test,
        delimiters=delims,
    )

    builder.start_message(
        msg_type="INVOIC",
        version="D",
        release="96A",
        agency="UN",
        assoc_code="EAN008",
        control_number=invoice_doc.control_number or "1",
    )

    # BGM: 380 = Commercial Invoice, 381 = Credit Note
    is_credit = header.invoice_type in ("Credit Note", "Credit", "CN")
    msg_code = "381" if is_credit else "380"
    builder.add_segment("BGM", msg_code, header.invoice_number, "9")

    # DTM: Dates
    now = datetime.now(timezone.utc)
    inv_date_str = header.issue_date.strftime("%Y%m%d") if header.issue_date else now.strftime("%Y%m%d")
    builder.add_segment("DTM", f"137:{inv_date_str}:102")  # 137 = Document / Invoice date

    if header.due_date:
        builder.add_segment("DTM", f"140:{header.due_date.strftime('%Y%m%d')}:102")  # 140 = Due date

    # RFF: References
    if header.buyer_po_number:
        builder.add_segment("RFF", f"ON:{header.buyer_po_number}")
    if header.delivery_number:
        builder.add_segment("RFF", f"DQ:{header.delivery_number}")
    if header.sales_order_number:
        builder.add_segment("RFF", f"VN:{header.sales_order_number}")
    if header.seller_vat_id:
        builder.add_segment("RFF", f"VA:{header.seller_vat_id}")

    # NAD: Parties
    # 1. Supplier / Seller (SU)
    seller_id = header.seller_id or invoice_doc.sender_id or "NOVA-HQ"
    seller_name = header.seller_name or "Nova Distribution Hub"
    builder.add_segment(
        "NAD",
        "SU",
        f"{seller_id}::9",
        "",
        seller_name,
        header.seller_address or "",
        header.seller_city or "",
        "",
        "",
        header.seller_country or "",
    )

    # 2. Buyer (BY)
    buyer_id = header.buyer_id or invoice_doc.receiver_id or "RETAIL-HQ"
    buyer_name = header.buyer_name or "Retail Supermarket Chain"
    builder.add_segment(
        "NAD",
        "BY",
        f"{buyer_id}::9",
        "",
        buyer_name,
        header.buyer_address or "",
        header.buyer_city or "",
        "",
        "",
        header.buyer_country or "",
    )

    # 3. Delivery Party / Ship To (DP)
    st_id = header.ship_to_id or header.ship_to_store_number or buyer_id
    st_name = header.ship_to_name or buyer_name
    builder.add_segment(
        "NAD",
        "DP",
        f"{st_id}::9",
        "",
        st_name,
        header.ship_to_address or "",
        header.ship_to_city or "",
        "",
        "",
        header.ship_to_country or "",
    )

    # 4. Invoicee (IV)
    builder.add_segment(
        "NAD",
        "IV",
        f"{buyer_id}::9",
        "",
        buyer_name,
        header.buyer_address or "",
        header.buyer_city or "",
        "",
        "",
        header.buyer_country or "",
    )

    # CUX: Currency
    if header.currency:
        builder.add_segment("CUX", f"2:{header.currency}:4")

    # PAT / PCD / MOA / DTM: Payment Terms
    builder.add_segment("PAT", "1")  # 1 = Basic payment terms
    if header.discount_percentage > 0:
        builder.add_segment("PCD", f"12:{header.discount_percentage:.2f}")  # 12 = Discount percentage
    if header.early_discount_amount > 0:
        builder.add_segment("MOA", f"52:{header.early_discount_amount:.2f}")  # 52 = Discount amount
    if header.discount_due_date:
        builder.add_segment("DTM", f"12:{header.discount_due_date.strftime('%Y%m%d')}:102")

    # LIN Line Item Loops
    total_qty = 0.0
    for line in invoice_doc.lines:
        total_qty += line.qty_invoiced

        # LIN: Line Identification
        gtin_val = line.gtin or ""
        item_id_str = f"{gtin_val}:SRV" if gtin_val else f"{line.sku}:EN"
        builder.add_segment("LIN", str(line.line_number), "", item_id_str)

        # PIA: Additional Identification (Buyer / Vendor SKU)
        pia_parts = []
        if line.buyer_sku:
            pia_parts.append(f"{line.buyer_sku}:IN")
        if line.vendor_sku:
            pia_parts.append(f"{line.vendor_sku}:VN")
        elif line.sku and line.sku != line.buyer_sku:
            pia_parts.append(f"{line.sku}:VN")

        if pia_parts:
            builder.add_segment("PIA", "1", *pia_parts)

        # IMD: Item Description
        if line.product_name:
            builder.add_segment("IMD", "F", "", f":::{line.product_name}")

        # QTY: Quantity Invoiced (47) & Delivered (46)
        uom_code = line.uom or "PCE"
        if uom_code == "EA":
            uom_code = "PCE"
        elif uom_code == "CA":
            uom_code = "CS"

        builder.add_segment("QTY", f"47:{line.qty_invoiced}:{uom_code}")
        if line.qty_delivered is not None:
            builder.add_segment("QTY", f"46:{line.qty_delivered}:{uom_code}")

        # MOA: Line Total Amount (203 = Line Item Amount)
        builder.add_segment("MOA", f"203:{line.net_amount:.2f}")

        # PRI: Net Calculation Price (AAA = Net Price)
        builder.add_segment("PRI", f"AAA:{line.unit_price:.4f}:{uom_code}:NTP")

        # TAX: Line VAT
        if line.tax_rate_percent > 0 or line.tax_amount > 0:
            builder.add_segment("TAX", "7", "VAT", "", f":::{line.tax_rate_percent:.2f}", "S")

        # ALC: Line Discount (if any)
        if line.discount_amount > 0:
            builder.add_segment("ALC", "A", "", "", "1")
            builder.add_segment("MOA", f"204:{line.discount_amount:.2f}")

    # UNS: Section Control
    builder.add_segment("UNS", "S")

    # CNT: Control Totals
    builder.add_segment("CNT", f"2:{len(invoice_doc.lines)}")  # 2 = Line item count
    builder.add_segment("CNT", f"1:{total_qty}")  # 1 = Total quantity

    # MOA Summary Monetary Totals
    # 77: Invoice Total Amount (Grand Total)
    builder.add_segment("MOA", f"77:{header.grand_total:.2f}")
    # 79: Total Line Items Amount (Subtotal)
    builder.add_segment("MOA", f"79:{header.subtotal:.2f}")
    # 125: Taxable Amount
    builder.add_segment("MOA", f"125:{header.subtotal:.2f}")
    # 176: Total Tax Amount
    if header.tax_amount > 0:
        builder.add_segment("MOA", f"176:{header.tax_amount:.2f}")
    # 131: Total Freight / Charge Amount
    if header.freight_amount > 0:
        builder.add_segment("MOA", f"131:{header.freight_amount:.2f}")
    # 52: Total Discount Amount
    if header.discount_amount > 0:
        builder.add_segment("MOA", f"52:{header.discount_amount:.2f}")

    # TAX Summary Breakdown
    if header.tax_amount > 0 or header.tax_rate_percent > 0:
        builder.add_segment("TAX", "7", "VAT", "", f":::{header.tax_rate_percent:.2f}", "S")
        builder.add_segment("MOA", f"124:{header.tax_amount:.2f}")  # 124 = Tax amount
        builder.add_segment("MOA", f"125:{header.subtotal:.2f}")  # 125 = Taxable amount

    return builder.build()


# ---------------------------------------------------------------------------
# Bidirectional Parsers for EDI 810 / INVOIC
# ---------------------------------------------------------------------------

def parse_x12_810(
    raw_edi: str,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiInvoiceDocument:
    """
    Parses an ANSI X12 810 Invoice interchange into a structured EdiInvoiceDocument.
    """
    interchange = parse_x12(raw_edi, delimiters=delimiters)
    if not interchange.groups:
        raise EdiSyntaxError("No functional groups found in X12 810 message")

    tx_set = None
    for group in interchange.groups:
        for tx in group.transactions:
            if tx.doc_type == "810":
                tx_set = tx
                break
        if tx_set:
            break

    if not tx_set:
        tx_set = interchange.groups[0].transactions[0] if interchange.groups[0].transactions else None

    if not tx_set:
        raise EdiSyntaxError("No 810 transaction set found in X12 message")

    header = EdiInvoiceHeader(
        invoice_number="",
    )

    lines: List[EdiInvoiceLine] = []
    allowances_charges: List[EdiInvoiceAllowanceCharge] = []
    taxes: List[EdiInvoiceTaxSummary] = []

    current_line: Optional[EdiInvoiceLine] = None

    for seg in tx_set.segments:
        tag = seg.tag

        if tag == "BIG":
            # BIG*InvoiceDate*InvoiceNumber*PODate*PONumber***TxType
            if len(seg.elements) > 0 and seg.elements[0]:
                try:
                    d_str = seg.elements[0]
                    header.issue_date = date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                except Exception:
                    pass
            if len(seg.elements) > 1:
                header.invoice_number = seg.elements[1]
            if len(seg.elements) > 3 and seg.elements[3]:
                header.buyer_po_number = seg.elements[3]
            if len(seg.elements) > 6 and seg.elements[6] in ("CR", "CN"):
                header.invoice_type = "Credit Note"

        elif tag == "CUR":
            if len(seg.elements) > 1:
                header.currency = seg.elements[1]

        elif tag == "REF":
            ref_qual = seg.get(0, "")
            ref_val = seg.get(1, "")
            if ref_qual == "VN":
                header.sales_order_number = ref_val
            elif ref_qual == "SI":
                header.delivery_number = ref_val
            elif ref_qual == "DP":
                header.ship_to_store_number = ref_val
            elif ref_qual == "IV":
                header.seller_vat_id = ref_val

        elif tag == "N1":
            party_type = seg.get(0, "")
            party_name = seg.get(1, "")
            party_id = seg.get(3, "")
            if party_type == "SE":
                header.seller_name = party_name
                header.seller_id = party_id
            elif party_type in ("BY", "BT"):
                header.buyer_name = party_name
                header.buyer_id = party_id
            elif party_type == "ST":
                header.ship_to_name = party_name
                header.ship_to_id = party_id
            elif party_type == "RE":
                header.remit_to_name = party_name
                header.remit_to_id = party_id

        elif tag == "ITD":
            # ITD*TermsCode*BasisDate*DiscPct*DiscDueDate*DiscDays*NetDueDate*NetDays*DiscAmt****TermsDesc
            try:
                if seg.get(2):
                    header.discount_percentage = float(seg.get(2))
                if seg.get(3):
                    d_str = seg.get(3)
                    header.discount_due_date = date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                if seg.get(4):
                    header.discount_days = int(seg.get(4))
                if seg.get(5):
                    d_str = seg.get(5)
                    header.due_date = date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                if seg.get(6):
                    header.net_days = int(seg.get(6))
                if seg.get(7):
                    header.early_discount_amount = float(seg.get(7))
                if seg.get(11):
                    header.payment_term_name = seg.get(11)
            except Exception as e:
                logger.debug(f"Error parsing ITD terms: {e}")

        elif tag == "IT1":
            # Flush previous line if any
            if current_line:
                lines.append(current_line)

            line_no = int(seg.get(0, "1")) if seg.get(0, "1").isdigit() else len(lines) + 1
            qty_inv = float(seg.get(1, "1.0"))
            uom = seg.get(2, "EA")
            price = float(seg.get(3, "0.0"))

            buyer_sku = None
            vendor_sku = None
            gtin = None
            internal_sku = None

            # Parse paired qualifiers (elements starting at index 5)
            idx = 5
            while idx < len(seg.elements) - 1:
                q = seg.elements[idx]
                v = seg.elements[idx + 1]
                if q in ("CB", "BP", "IN"):
                    buyer_sku = v
                elif q in ("VN", "VP"):
                    vendor_sku = v
                elif q in ("UP", "EN", "SRV"):
                    gtin = v
                elif q == "IN":
                    internal_sku = v
                idx += 2

            primary_sku = vendor_sku or buyer_sku or internal_sku or f"SKU-{line_no}"
            current_line = EdiInvoiceLine(
                line_number=line_no,
                sku=primary_sku,
                buyer_sku=buyer_sku,
                vendor_sku=vendor_sku,
                gtin=gtin,
                product_name=primary_sku,
                qty_invoiced=qty_inv,
                uom=uom,
                unit_price=price,
                gross_amount=round(qty_inv * price, 2),
                net_amount=round(qty_inv * price, 2),
            )

        elif tag == "PID" and current_line:
            desc = seg.get(4, "")
            if desc:
                current_line.product_name = desc

        elif tag == "SAC":
            ind = seg.get(0, "A")
            sac_code = seg.get(1, "F800")
            amt = float(seg.get(4, "0.0")) if seg.get(4) else 0.0
            desc = seg.get(11, "")

            if current_line and not header.grand_total:
                # Line level allowance
                if ind == "A":
                    current_line.discount_amount = amt
                    current_line.net_amount = round(current_line.net_amount - amt, 2)
            else:
                # Summary level allowance/charge
                allowances_charges.append(
                    EdiInvoiceAllowanceCharge(
                        indicator=ind,
                        code=sac_code,
                        description=desc,
                        amount=amt,
                    )
                )
                if ind == "A" and sac_code == "F800":
                    header.discount_amount = amt
                elif ind == "C" and sac_code == "D240":
                    header.freight_amount = amt
                elif sac_code == "E340":
                    header.weight_adjustment_amount = amt if ind == "C" else -amt

        elif tag == "TXI":
            tax_amt = float(seg.get(1, "0.0")) if seg.get(1) else 0.0
            tax_rate = float(seg.get(2, "0.0")) if seg.get(2) else 0.0
            if current_line and not header.grand_total:
                current_line.tax_amount = tax_amt
                current_line.tax_rate_percent = tax_rate
            else:
                header.tax_amount = tax_amt
                header.tax_rate_percent = tax_rate
                taxes.append(
                    EdiInvoiceTaxSummary(
                        tax_type="VAT",
                        tax_rate_percent=tax_rate,
                        taxable_amount=header.subtotal,
                        tax_amount=tax_amt,
                    )
                )

        elif tag == "TDS":
            if seg.get(0):
                try:
                    header.grand_total = float(seg.get(0))
                except Exception:
                    pass

    if current_line:
        lines.append(current_line)

    if not header.subtotal and lines:
        header.subtotal = sum(l.net_amount for l in lines)
    if not header.grand_total:
        header.grand_total = header.subtotal + header.tax_amount + header.freight_amount - header.discount_amount

    return EdiInvoiceDocument(
        standard="ANSI_X12",
        document_type="810",
        control_number=interchange.control_number or "1",
        sender_id=interchange.sender_id,
        sender_qualifier=interchange.sender_qualifier,
        receiver_id=interchange.receiver_id,
        receiver_qualifier=interchange.receiver_qualifier,
        is_test=interchange.is_test,
        header=header,
        lines=lines,
        allowances_charges=allowances_charges,
        taxes=taxes,
    )


def parse_edifact_invoic(
    raw_edi: str,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiInvoiceDocument:
    """
    Parses a UN/EDIFACT INVOIC message into a structured EdiInvoiceDocument.
    """
    interchange = parse_edifact(raw_edi, delimiters=delimiters)
    if not interchange.groups:
        raise EdiSyntaxError("No functional groups found in EDIFACT message")

    tx_set = None
    for group in interchange.groups:
        for tx in group.transactions:
            if tx.doc_type == "INVOIC":
                tx_set = tx
                break
        if tx_set:
            break

    if not tx_set:
        tx_set = interchange.groups[0].transactions[0] if interchange.groups[0].transactions else None

    if not tx_set:
        raise EdiSyntaxError("No INVOIC message found in EDIFACT interchange")

    header = EdiInvoiceHeader(
        invoice_number="",
    )

    lines: List[EdiInvoiceLine] = []
    allowances_charges: List[EdiInvoiceAllowanceCharge] = []
    taxes: List[EdiInvoiceTaxSummary] = []

    current_line: Optional[EdiInvoiceLine] = None

    for seg in tx_set.segments:
        tag = seg.tag

        if tag == "BGM":
            code = seg.get(0, "380")
            header.invoice_number = seg.get(1, "")
            if code == "381":
                header.invoice_type = "Credit Note"

        elif tag == "DTM":
            dtm_val = seg.get(0, "")
            parts = dtm_val.split(":")
            if len(parts) >= 2:
                q, d_str = parts[0], parts[1]
                try:
                    d_obj = date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                    if q == "137":
                        header.issue_date = d_obj
                    elif q == "140":
                        header.due_date = d_obj
                    elif q == "12":
                        header.discount_due_date = d_obj
                except Exception:
                    pass

        elif tag == "RFF":
            rff_val = seg.get(0, "")
            parts = rff_val.split(":", 1)
            if len(parts) == 2:
                q, val = parts[0], parts[1]
                if q == "ON":
                    header.buyer_po_number = val
                elif q == "DQ":
                    header.delivery_number = val
                elif q == "VN":
                    header.sales_order_number = val
                elif q == "VA":
                    header.seller_vat_id = val

        elif tag == "NAD":
            party_type = seg.get(0, "")
            party_id_comp = seg.get(1, "")
            p_id = party_id_comp.split(":")[0] if party_id_comp else ""
            p_name = seg.get(3, "")
            p_addr = seg.get(4, "")
            p_city = seg.get(5, "")
            p_country = seg.get(8, "")

            if party_type == "SU":
                header.seller_name = p_name
                header.seller_id = p_id
                header.seller_address = p_addr
                header.seller_city = p_city
                header.seller_country = p_country
            elif party_type == "BY":
                header.buyer_name = p_name
                header.buyer_id = p_id
                header.buyer_address = p_addr
                header.buyer_city = p_city
                header.buyer_country = p_country
            elif party_type == "DP":
                header.ship_to_name = p_name
                header.ship_to_id = p_id
                header.ship_to_address = p_addr
                header.ship_to_city = p_city
                header.ship_to_country = p_country

        elif tag == "CUX":
            cux_val = seg.get(0, "")
            parts = cux_val.split(":")
            if len(parts) >= 2:
                header.currency = parts[1]

        elif tag == "PCD":
            pcd_val = seg.get(0, "")
            parts = pcd_val.split(":")
            if len(parts) >= 2 and parts[0] == "12":
                header.discount_percentage = float(parts[1])

        elif tag == "LIN":
            if current_line:
                lines.append(current_line)

            line_no = int(seg.get(0, "1")) if seg.get(0, "1").isdigit() else len(lines) + 1
            item_comp = seg.get(2, "")
            gtin = item_comp.split(":")[0] if item_comp else None

            current_line = EdiInvoiceLine(
                line_number=line_no,
                sku=gtin or f"ITEM-{line_no}",
                gtin=gtin,
                product_name=gtin or f"Item {line_no}",
                qty_invoiced=1.0,
                net_amount=0.0,
            )

        elif tag == "PIA" and current_line:
            for el in seg.elements[1:]:
                parts = el.split(":")
                if len(parts) >= 2:
                    sku_val, q = parts[0], parts[1]
                    if q == "IN":
                        current_line.buyer_sku = sku_val
                    elif q == "VN":
                        current_line.vendor_sku = sku_val
                        current_line.sku = sku_val

        elif tag == "IMD" and current_line:
            desc_comp = seg.get(2, "")
            if desc_comp:
                desc = desc_comp.split(":")[-1]
                if desc:
                    current_line.product_name = desc

        elif tag == "QTY" and current_line:
            qty_val = seg.get(0, "")
            parts = qty_val.split(":")
            if len(parts) >= 2:
                q_type, amt = parts[0], float(parts[1])
                uom_val = parts[2] if len(parts) > 2 else "EA"
                if q_type == "47":
                    current_line.qty_invoiced = amt
                    current_line.uom = uom_val
                elif q_type == "46":
                    current_line.qty_delivered = amt

        elif tag == "PRI" and current_line:
            pri_val = seg.get(0, "")
            parts = pri_val.split(":")
            if len(parts) >= 2:
                current_line.unit_price = float(parts[1])
                current_line.net_amount = round(current_line.qty_invoiced * current_line.unit_price, 2)

        elif tag == "TAX":
            tax_rate_comp = seg.get(3, "")
            rate = float(tax_rate_comp.split(":")[-1]) if tax_rate_comp else 0.0
            if current_line:
                current_line.tax_rate_percent = rate
            else:
                header.tax_rate_percent = rate

        elif tag == "MOA":
            moa_val = seg.get(0, "")
            parts = moa_val.split(":")
            if len(parts) >= 2:
                q, amt = parts[0], float(parts[1])
                if current_line and not header.grand_total:
                    if q == "203":
                        current_line.net_amount = amt
                    elif q == "204":
                        current_line.discount_amount = amt
                else:
                    if q == "77":
                        header.grand_total = amt
                    elif q == "79":
                        header.subtotal = amt
                    elif q == "176" or q == "124":
                        header.tax_amount = amt
                    elif q == "131":
                        header.freight_amount = amt
                    elif q == "52":
                        header.discount_amount = amt

    if current_line:
        lines.append(current_line)

    if not header.subtotal and lines:
        header.subtotal = sum(l.net_amount for l in lines)
    if not header.grand_total:
        header.grand_total = header.subtotal + header.tax_amount + header.freight_amount - header.discount_amount

    return EdiInvoiceDocument(
        standard="EDIFACT",
        document_type="INVOIC",
        control_number=interchange.control_number or "1",
        sender_id=interchange.sender_id,
        sender_qualifier=interchange.sender_qualifier,
        receiver_id=interchange.receiver_id,
        receiver_qualifier=interchange.receiver_qualifier,
        is_test=interchange.is_test,
        header=header,
        lines=lines,
        allowances_charges=allowances_charges,
        taxes=taxes,
    )


def parse_inbound_invoice_edi(
    raw_edi: str,
    standard: Optional[str] = None,
) -> EdiInvoiceDocument:
    """
    Universally parses an EDI Invoice message (auto-detecting ANSI X12 810 or EDIFACT INVOIC).
    """
    std = standard or detect_edi_standard(raw_edi)
    if std == EdiStandard.EDIFACT or std == "EDIFACT":
        return parse_edifact_invoic(raw_edi)
    return parse_x12_810(raw_edi)


# Alias for unified parser naming
parse_inbound_invoice = parse_inbound_invoice_edi


# ---------------------------------------------------------------------------
# Outbound EDI 810 / INVOIC Service
# ---------------------------------------------------------------------------

class Edi810Service(CrudService):
    """
    High-level Outbound EDI 810 (Sales Invoice) & EDIFACT INVOIC Service.
    Retrieves completed sales invoices (T0090), linked deliveries (T0077),
    sales orders (T0012/T0013), and trading partner configurations (T0124/T0125),
    constructs standard compliant electronic invoices, and persists transmission logs in T0126.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        partner_repo: Optional[CrudRepository] = None,
        invoice_repo: Optional[CrudRepository] = None,
        delivery_repo: Optional[CrudRepository] = None,
        delivery_line_repo: Optional[CrudRepository] = None,
        sales_order_repo: Optional[CrudRepository] = None,
        sales_line_repo: Optional[CrudRepository] = None,
        pick_list_item_repo: Optional[CrudRepository] = None,
        sku_mapping_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        payment_term_repo: Optional[CrudRepository] = None,
        tax_rate_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(repo or EDI_TRANSACTION_REPO)
        self.partner_repo = partner_repo or EDI_PARTNER_REPO
        self.invoice_repo = invoice_repo or INVOICE_T0090_REPO
        self.sales_order_repo = sales_order_repo or SALES_ORDER_T0012_REPO
        self.sales_line_repo = sales_line_repo or SALES_LINE_T0013_REPO
        self.delivery_repo = delivery_repo or DELIVERY_T0077_REPO
        self.delivery_line_repo = delivery_line_repo or DELIVERY_LINE_T0078_REPO
        self.pick_list_item_repo = pick_list_item_repo or PICK_LIST_ITEM_T0102_REPO
        self.sku_mapping_repo = sku_mapping_repo or EDI_SKU_MAPPING_REPO
        self.customer_repo = customer_repo or CUSTOMER_T0010_REPO
        self.product_repo = product_repo or PRODUCT_T0001_REPO
        self.payment_term_repo = payment_term_repo or PAYMENT_TERM_T0089_REPO
        self.tax_rate_repo = tax_rate_repo or TAX_RATE_T0085_REPO

    def build_invoice_document(
        self,
        invoice_id: int,
        delivery_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Tuple[EdiInvoiceDocument, Dict[str, Any]]:
        """
        Builds a structured EdiInvoiceDocument from Nova ERP entities (T0090, T0012, T0013, T0077, T0124, T0125).
        Returns tuple of (EdiInvoiceDocument, partner_dict).
        """
        tenant_id = tenant_id or get_current_tenant()

        # 1. Fetch Invoice (T0090)
        invoice = self.invoice_repo.get(invoice_id, conn=conn)
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} not found in T0090")

        sales_order_id = invoice.get("sales_order_id")

        # 2. Fetch Sales Order (T0012)
        so = self.sales_order_repo.get(sales_order_id, conn=conn) if sales_order_id else None

        # 3. Fetch Customer (T0010)
        customer_id = invoice.get("partner_id") or (so.get("customer_id") if so else None)
        customer = self.customer_repo.get(customer_id, conn=conn) if customer_id else None

        # 4. Resolve Trading Partner (T0124)
        partner = None
        if partner_id:
            partner = self.partner_repo.get(partner_id, conn=conn)

        if not partner and customer_id:
            partners = self.partner_repo.list(
                filters={"customer_id": customer_id, "is_active": True},
                conn=conn,
            )
            if partners:
                partner = partners[0]

        if not partner:
            raise ValueError(
                f"No EDI Trading Partner found for Customer #{customer_id} or Partner #{partner_id}"
            )

        # 5. Fetch Delivery (T0077) if available
        delivery = None
        if delivery_id:
            delivery = self.delivery_repo.get(delivery_id, conn=conn)
        elif sales_order_id:
            deliveries = self.delivery_repo.list(
                filters={"sales_order_id": sales_order_id},
                conn=conn,
            )
            if deliveries:
                delivery = deliveries[0]

        # 6. Fetch Sales Lines (T0013) & Delivery Lines (T0078)
        so_lines = []
        if sales_order_id:
            so_lines = self.sales_line_repo.list(
                filters={"sales_order_id": sales_order_id},
                conn=conn,
            )

        del_lines = []
        if delivery:
            del_lines = self.delivery_line_repo.list(
                filters={"delivery_id": delivery["id"]},
                conn=conn,
            )
        del_by_sol = {dl.get("sales_order_line_id"): dl for dl in del_lines if dl.get("sales_order_line_id")}

        # 7. Fetch SKU Cross-Reference Matrix (T0125)
        sku_mappings = []
        if partner.get("id"):
            sku_mappings = self.sku_mapping_repo.list(
                filters={"partner_id": partner["id"], "is_active": True},
                conn=conn,
            )
        map_by_product = {m["product_id"]: m for m in sku_mappings if m.get("product_id")}

        # 8. Fetch Payment Term (T0089)
        payment_term_id = invoice.get("payment_term_id") or (so.get("payment_term_id") if so else None)
        payment_term = self.payment_term_repo.get(payment_term_id, conn=conn) if payment_term_id else None

        # 9. Build Header
        issue_d = invoice.get("issue_date") or date.today()
        if isinstance(issue_d, str):
            try:
                issue_d = date.fromisoformat(issue_d[:10])
            except Exception:
                issue_d = date.today()

        due_d = invoice.get("due_date")
        if isinstance(due_d, str):
            try:
                due_d = date.fromisoformat(due_d[:10])
            except Exception:
                due_d = None

        disc_due_d = invoice.get("discount_due_date")
        if isinstance(disc_due_d, str):
            try:
                disc_due_d = date.fromisoformat(disc_due_d[:10])
            except Exception:
                disc_due_d = None

        buyer_po = None
        if so and so.get("notes") and "PO" in str(so.get("notes")):
            buyer_po = str(so.get("notes"))
        elif so and so.get("client_order_uuid"):
            buyer_po = str(so.get("client_order_uuid"))
        else:
            buyer_po = f"PO-{sales_order_id}" if sales_order_id else "PO-001"

        sf_id_val = str(partner.get("interchange_sender_id") or "NOVAERP")
        st_id_val = str(partner.get("interchange_receiver_id") or "RETAILHUB")
        st_name_val = str(customer.get("name") if customer else (partner.get("partner_name") or "Retail DC"))

        subtotal_val = float(so.get("subtotal") or 0.0) if so else 0.0
        tax_val = float(so.get("tax") or 0.0) if so else 0.0
        freight_val = float(invoice.get("freight_amount") or (so.get("freight_amount") if so else 0.0) or 0.0)
        discount_val = float(invoice.get("discount_amount") or (so.get("discount_amount") if so else 0.0) or 0.0)
        grand_total_val = float(invoice.get("total_amount") or (so.get("grand_total") if so else 0.0) or 0.0)
        is_cw = bool(invoice.get("is_catch_weight"))
        wt_adj = float(invoice.get("weight_adjustment_amount") or 0.0)

        header = EdiInvoiceHeader(
            invoice_id=invoice_id,
            invoice_number=str(invoice.get("invoice_number") or f"INV-{invoice_id}"),
            invoice_type=str(invoice.get("invoice_type") or "Standard"),
            sales_order_id=sales_order_id,
            sales_order_number=str(so.get("order_number")) if so and so.get("order_number") else None,
            buyer_po_number=buyer_po,
            delivery_id=delivery.get("id") if delivery else None,
            delivery_number=str(delivery.get("delivery_number")) if delivery and delivery.get("delivery_number") else None,
            issue_date=issue_d,
            due_date=due_d,
            discount_due_date=disc_due_d,
            currency="USD",
            subtotal=subtotal_val,
            tax_amount=tax_val,
            tax_rate_percent=15.0 if tax_val > 0 else 0.0,
            discount_amount=discount_val,
            discount_percentage=float(invoice.get("discount_percentage") or 0.0),
            early_discount_amount=float(invoice.get("early_discount_amount") or 0.0),
            discount_days=int(invoice.get("discount_days") or 0),
            freight_amount=freight_val,
            grand_total=grand_total_val or (subtotal_val + tax_val + freight_val - discount_val + wt_adj),
            weight_adjustment_amount=wt_adj,
            nominal_total_weight=float(invoice.get("nominal_total_weight") or 0.0) if invoice.get("nominal_total_weight") else None,
            actual_total_weight=float(invoice.get("actual_total_weight") or 0.0) if invoice.get("actual_total_weight") else None,
            is_catch_weight=is_cw,
            payment_term_id=payment_term_id,
            payment_term_name=payment_term.get("name") if payment_term else None,
            payment_term_code=payment_term.get("code") if payment_term else None,
            net_days=int(payment_term.get("net_days") or 30) if payment_term else 30,
            seller_name="Nova Distribution Hub",
            seller_id=sf_id_val,
            buyer_name=st_name_val,
            buyer_id=st_id_val,
            ship_to_name=st_name_val,
            ship_to_id=st_id_val,
            notes=invoice.get("notes"),
        )

        # 10. Build Lines
        lines: List[EdiInvoiceLine] = []
        calc_subtotal = 0.0

        for idx, sol in enumerate(so_lines, 1):
            pid = sol.get("product_id")
            prod = self.product_repo.get(pid, conn=conn) if pid else None
            sku_code = str(prod.get("sku") if prod else f"SKU-{pid}")
            mapping = map_by_product.get(pid, {})
            del_line = del_by_sol.get(sol.get("id"))

            qty_ord = float(sol.get("qty") or 1.0)
            qty_del = float(del_line.get("qty_shipped")) if del_line and del_line.get("qty_shipped") is not None else qty_ord
            qty_inv = qty_del  # Invoiced quantity matches delivered quantity in standard ERP cycle
            u_price = float(sol.get("unit_price") or (prod.get("price") if prod else 0.0))
            l_disc = float(sol.get("discount") or 0.0)
            l_net = float(sol.get("line_total") or ((qty_inv * u_price) - l_disc))
            calc_subtotal += l_net

            lines.append(
                EdiInvoiceLine(
                    line_number=idx,
                    product_id=pid,
                    sku=sku_code,
                    buyer_sku=str(mapping.get("partner_sku") or sku_code),
                    vendor_sku=sku_code,
                    gtin=str(mapping.get("gtin") or (prod.get("barcode") if prod else "")) or None,
                    product_name=str(sol.get("product_name") or (prod.get("name") if prod else f"Product {pid}")),
                    qty_invoiced=qty_inv,
                    qty_delivered=qty_del,
                    qty_ordered=qty_ord,
                    uom=str(mapping.get("partner_uom") or "EA"),
                    unit_price=u_price,
                    gross_amount=round(qty_inv * u_price, 2),
                    discount_amount=l_disc,
                    discount_percentage=round((l_disc / (qty_inv * u_price) * 100), 2) if (qty_inv * u_price) > 0 and l_disc > 0 else 0.0,
                    net_amount=l_net,
                    is_catch_weight=bool(sol.get("is_catch_weight")),
                )
            )

        if not header.subtotal and calc_subtotal > 0:
            header.subtotal = calc_subtotal
            if not header.grand_total:
                header.grand_total = header.subtotal + header.tax_amount + header.freight_amount - header.discount_amount + header.weight_adjustment_amount

        ctrl_num = _generate_control_number(conn)
        partner_std = str(partner.get("edi_standard") or "ANSI_X12")
        is_edifact = (partner_std == "EDIFACT" or partner_std == EdiStandard.EDIFACT)
        doc_type = "INVOIC" if is_edifact else "810"

        doc = EdiInvoiceDocument(
            standard=partner_std,
            document_type=doc_type,
            control_number=ctrl_num,
            sender_id=sf_id_val,
            sender_qualifier=str(partner.get("sender_qualifier") or "ZZ"),
            receiver_id=st_id_val,
            receiver_qualifier=str(partner.get("receiver_qualifier") or "ZZ"),
            header=header,
            lines=lines,
        )

        return doc, partner

    def generate_invoice(
        self,
        request: EdiInvoiceTransmitRequest,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> EdiInvoiceTransmitResponse:
        """
        Generates and logs an outbound EDI 810 / INVOIC document for an invoice in T0090.
        """
        tenant_id = request.business_id or tenant_id or get_current_tenant()

        with db_transaction(conn) as tx_conn:
            doc, partner = self.build_invoice_document(
                invoice_id=request.invoice_id,
                delivery_id=request.delivery_id,
                partner_id=request.partner_id,
                conn=tx_conn,
                tenant_id=tenant_id,
            )

            partner_std = doc.standard
            is_edifact = (partner_std == "EDIFACT" or partner_std == EdiStandard.EDIFACT)

            if is_edifact:
                edi_payload = generate_edifact_invoic(doc, partner=partner)
            else:
                edi_payload = generate_x12_810(doc, partner=partner)

            tx_num = f"TX-INV-{doc.control_number}"
            tx_record = {
                "transaction_number": tx_num,
                "partner_id": partner.get("id"),
                "standard": partner_std,
                "document_type": doc.document_type,
                "direction": EdiDirection.OUTBOUND.value,
                "control_number": doc.control_number,
                "status": EdiTransactionStatus.PROCESSED.value,
                "sales_order_id": doc.header.sales_order_id,
                "delivery_id": doc.header.delivery_id,
                "invoice_id": request.invoice_id,
                "raw_payload": edi_payload,
                "parsed_data": doc.model_dump(mode="json"),
                "ack_status": "PENDING",
                "processed_at": datetime.now(timezone.utc),
            }
            saved_tx = self.repo.create(tx_record, conn=tx_conn)

            return EdiInvoiceTransmitResponse(
                transaction_id=saved_tx["id"],
                transaction_number=tx_num,
                invoice_id=request.invoice_id,
                invoice_number=doc.header.invoice_number,
                control_number=doc.control_number,
                standard=partner_std,
                document_type=doc.document_type,
                edi_payload=edi_payload,
            )

    def resolve_partner_for_delivery(
        self,
        delivery: Dict[str, Any],
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves the trading partner configuration (T0124) associated with a delivery's customer.
        """
        kwargs = {"conn": conn} if conn is not None else {}
        if partner_id:
            return self.partner_repo.get(partner_id, **kwargs)

        sales_order_id = delivery.get("sales_order_id")
        if not sales_order_id:
            return None

        so = self.sales_order_repo.get(sales_order_id, **kwargs)
        if not so or not so.get("customer_id"):
            return None

        customer_id = so["customer_id"]
        partners = self.partner_repo.list(
            filters={"customer_id": customer_id, "is_active": True},
            limit=1,
            **kwargs,
        )
        return partners[0] if partners else None

    def transmit_invoice_for_delivery(
        self,
        delivery_id: int,
        partner_id: Optional[int] = None,
        auto_create_invoice: bool = True,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Optional[EdiInvoiceTransmitResponse]:
        """
        Resolves the invoice associated with a completed delivery (T0077) or sales order (T0012)
        and transmits the outbound EDI 810 (Sales Invoice) or UN/EDIFACT INVOIC message to the trading partner.
        If no invoice exists and auto_create_invoice is True, generates an invoice in T0090 first.
        Returns EdiInvoiceTransmitResponse, or None if the customer is not configured as an EDI partner.
        """
        tenant_id = tenant_id or get_current_tenant()
        with db_transaction(conn) as tx_conn:
            delivery = self.delivery_repo.get(delivery_id, conn=tx_conn)
            if not delivery:
                raise ValueError(f"Delivery record {delivery_id} not found in T0077")

            partner = self.resolve_partner_for_delivery(delivery, partner_id, conn=tx_conn, tenant_id=tenant_id)
            if not partner:
                logger.info(f"No active EDI Trading Partner (T0124) found for Delivery #{delivery_id}; skipping EDI invoice transmission.")
                return None

            sales_order_id = delivery.get("sales_order_id")
            invoice = None
            if sales_order_id:
                invoices = self.invoice_repo.list(
                    filters={"sales_order_id": sales_order_id},
                    conn=tx_conn,
                )
                if invoices:
                    invoice = invoices[0]

            if not invoice and auto_create_invoice and sales_order_id:
                from modules.accounting.services.invoice_service import InvoiceService
                so = self.sales_order_repo.get(sales_order_id, conn=tx_conn)
                if so:
                    inv_svc = InvoiceService(
                        repo=self.invoice_repo,
                        customer_repo=self.customer_repo,
                        order_repo=self.sales_order_repo,
                        line_repo=self.sales_line_repo,
                        payment_term_repo=self.payment_term_repo,
                    )
                    invoice = inv_svc.create_from_order(so, conn=tx_conn)

            if not invoice:
                raise ValueError(f"No sales invoice (T0090) found or created for delivery #{delivery_id} (Sales Order #{sales_order_id})")

            return self.transmit_invoice(
                invoice_id=invoice["id"],
                delivery_id=delivery_id,
                partner_id=partner.get("id"),
                conn=tx_conn,
                tenant_id=tenant_id,
            )

    def transmit_invoice(
        self,
        invoice_id: int,
        delivery_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> EdiInvoiceTransmitResponse:
        """
        Convenience wrapper around generate_invoice for transmitting an EDI tax invoice.
        """
        req = EdiInvoiceTransmitRequest(
            invoice_id=invoice_id,
            delivery_id=delivery_id,
            partner_id=partner_id,
            business_id=tenant_id,
        )
        return self.generate_invoice(req, conn=conn, tenant_id=tenant_id)


# Default singleton instance
edi_810_service = Edi810Service()


