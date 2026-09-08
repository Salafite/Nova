"""
Unit Tests for Outbound EDI 810 (Sales Invoice) & UN/EDIFACT INVOIC Generator
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiInvoiceTransmitRequest,
    EdiInvoiceTransmitResponse,
)
from modules.integrations.services.edi.edi_core import EdiDelimiters
from modules.integrations.services.edi.edi_810_service import (
    EdiInvoiceAllowanceCharge,
    EdiInvoiceTaxSummary,
    EdiInvoiceLine,
    EdiInvoiceHeader,
    EdiInvoiceDocument,
    generate_x12_810,
    generate_edifact_invoic,
    parse_x12_810,
    parse_edifact_invoic,
    parse_inbound_invoice,
    Edi810Service,
)


@pytest.fixture
def sample_invoice_document():
    """Provides a fully-populated EdiInvoiceDocument for testing."""
    header = EdiInvoiceHeader(
        invoice_id=101,
        invoice_number="INV-2026-0089",
        invoice_type="Standard",
        issue_date=date(2026, 9, 8),
        due_date=date(2026, 10, 8),
        discount_due_date=date(2026, 9, 18),
        discount_percentage=2.0,
        discount_days=10,
        net_days=30,
        early_discount_amount=24.50,
        delivery_id=55,
        delivery_number="DEL-2026-0055",
        sales_order_id=42,
        sales_order_number="SO-2026-0042",
        buyer_po_number="PO-CRF-99412",
        currency="USD",
        subtotal=1225.00,
        tax_amount=183.75,
        tax_rate_percent=15.00,
        freight_amount=50.00,
        discount_amount=25.00,
        grand_total=1433.75,
        payment_term_name="2/10 Net 30",
        seller_name="Nova Distribution Hub",
        seller_id="NOVA-HQ",
        seller_vat_id="SA300123456700003",
        seller_address="100 Logistics Blvd",
        seller_city="Riyadh",
        seller_country="SA",
        buyer_name="Carrefour Central Accounts",
        buyer_id="CRF-AP-01",
        buyer_address="King Fahd Road",
        buyer_city="Riyadh",
        buyer_country="SA",
        ship_to_name="Carrefour Hypermarket Store #12",
        ship_to_id="CRF-ST-012",
        ship_to_address="Exit 5 North Ring",
        ship_to_city="Riyadh",
        ship_to_country="SA",
    )

    lines = [
        EdiInvoiceLine(
            line_number=1,
            product_id=10,
            sku="ALM-MILK-1L",
            buyer_sku="CRF-SKU-9901",
            vendor_sku="ALM-MILK-1L",
            gtin="6281001234567",
            product_name="Almarai Fresh Milk Full Fat 1L",
            qty_invoiced=50.0,
            qty_delivered=50.0,
            qty_ordered=50.0,
            uom="EA",
            unit_price=12.50,
            gross_amount=625.00,
            tax_rate_percent=15.00,
            tax_amount=93.75,
            discount_amount=10.00,
            discount_percentage=1.60,
            net_amount=615.00,
            batch_number="BAT-2026-09A",
            expiry_date=date(2026, 9, 20),
        ),
        EdiInvoiceLine(
            line_number=2,
            product_id=11,
            sku="ALM-CHSE-500G",
            buyer_sku="CRF-SKU-9902",
            vendor_sku="ALM-CHSE-500G",
            gtin="6281007654321",
            product_name="Almarai Cheddar Cheese 500g",
            qty_invoiced=30.0,
            qty_delivered=30.0,
            qty_ordered=30.0,
            uom="EA",
            unit_price=20.00,
            gross_amount=600.00,
            tax_rate_percent=15.00,
            tax_amount=90.00,
            discount_amount=15.00,
            discount_percentage=2.50,
            net_amount=585.00,
            batch_number="BAT-2026-09B",
            expiry_date=date(2026, 12, 31),
        ),
    ]

    allowances_charges = [
        EdiInvoiceAllowanceCharge(
            indicator="C",
            code="D240",
            description="Freight Charge",
            amount=50.00,
        ),
        EdiInvoiceAllowanceCharge(
            indicator="A",
            code="F800",
            description="Order Discount",
            amount=25.00,
        ),
    ]

    taxes = [
        EdiInvoiceTaxSummary(
            tax_type="VAT",
            tax_rate_percent=15.00,
            taxable_amount=1225.00,
            tax_amount=183.75,
        )
    ]

    return EdiInvoiceDocument(
        standard="ANSI_X12",
        document_type="810",
        control_number="000123456",
        sender_id="NOVAERP",
        sender_qualifier="ZZ",
        receiver_id="CARREFOUR",
        receiver_qualifier="ZZ",
        header=header,
        lines=lines,
        allowances_charges=allowances_charges,
        taxes=taxes,
    )


def test_generate_x12_810_structure(sample_invoice_document):
    """Verifies ANSI X12 810 invoice structure and required segments."""
    edi_text = generate_x12_810(sample_invoice_document)

    # Verify Envelope
    assert "ISA*" in edi_text
    assert "GS*IN*NOVAERP*CARREFOUR*" in edi_text
    assert "ST*810*" in edi_text

    # Verify BIG Segment
    assert "BIG*20260908*INV-2026-0089**PO-CRF-99412***DI~" in edi_text

    # Verify CUR & REF Segments
    assert "CUR*SE*USD~" in edi_text
    assert "REF*VN*SO-2026-0042~" in edi_text
    assert "REF*SI*DEL-2026-0055~" in edi_text
    assert "REF*IV*SA300123456700003~" in edi_text

    # Verify N1 Party Segments
    assert "N1*SE*Nova Distribution Hub*92*NOVA-HQ~" in edi_text
    assert "N3*100 Logistics Blvd~" in edi_text
    assert "N4*Riyadh****SA~" in edi_text
    assert "N1*BT*Carrefour Central Accounts*92*CRF-AP-01~" in edi_text
    assert "N1*ST*Carrefour Hypermarket Store #12*92*CRF-ST-012~" in edi_text

    # Verify ITD Terms Segment
    assert "ITD*01*3*2.00*20260918*10*20261008*30*24.50****2/10 Net 30~" in edi_text

    # Verify IT1 Item Segments
    assert "IT1*1*50*EA*12.5*PE*CB*CRF-SKU-9901*VN*ALM-MILK-1L*UP*6281001234567~" in edi_text
    assert "PID*F****Almarai Fresh Milk Full Fat 1L~" in edi_text
    assert "SAC*A*F800***10.00*****02*Line Discount~" in edi_text
    assert "TXI*VA*93.75*15.00~" in edi_text

    assert "IT1*2*30*EA*20*PE*CB*CRF-SKU-9902*VN*ALM-CHSE-500G*UP*6281007654321~" in edi_text
    assert "PID*F****Almarai Cheddar Cheese 500g~" in edi_text

    # Verify TDS & Summary Segments
    assert "TDS*1433.75~" in edi_text
    assert "TXI*VA*183.75*15.00~" in edi_text
    assert "SAC*C*D240***50.00*****02*Freight Charge~" in edi_text
    assert "SAC*A*F800***25.00*****02*Order Discount~" in edi_text
    assert "ISS*80*EA~" in edi_text
    assert "CTT*2*80~" in edi_text

    # Verify Trailers
    assert "SE*" in edi_text
    assert "GE*1*" in edi_text
    assert "IEA*1*" in edi_text


def test_parse_x12_810_roundtrip(sample_invoice_document):
    """Verifies round-trip parsing of generated ANSI X12 810."""
    edi_text = generate_x12_810(sample_invoice_document)
    parsed = parse_x12_810(edi_text)

    assert parsed.standard == "ANSI_X12"
    assert parsed.document_type == "810"
    assert parsed.sender_id.strip() == "NOVAERP"
    assert parsed.receiver_id.strip() == "CARREFOUR"
    assert parsed.header.invoice_number == "INV-2026-0089"
    assert parsed.header.buyer_po_number == "PO-CRF-99412"
    assert parsed.header.issue_date == date(2026, 9, 8)
    assert parsed.header.due_date == date(2026, 10, 8)
    assert parsed.header.discount_percentage == 2.0
    assert parsed.header.grand_total == 1433.75
    assert parsed.header.delivery_number == "DEL-2026-0055"
    assert parsed.header.sales_order_number == "SO-2026-0042"
    assert parsed.header.seller_name == "Nova Distribution Hub"
    assert parsed.header.buyer_name == "Carrefour Central Accounts"

    assert len(parsed.lines) == 2
    l1 = parsed.lines[0]
    assert l1.line_number == 1
    assert l1.qty_invoiced == 50.0
    assert l1.unit_price == 12.5
    assert l1.buyer_sku == "CRF-SKU-9901"
    assert l1.vendor_sku == "ALM-MILK-1L"
    assert l1.gtin == "6281001234567"
    assert l1.product_name == "Almarai Fresh Milk Full Fat 1L"
    assert l1.discount_amount == 10.0
    assert l1.tax_amount == 93.75


def test_generate_edifact_invoic_structure(sample_invoice_document):
    """Verifies UN/EDIFACT INVOIC D96A structure and required segments."""
    sample_invoice_document.standard = "EDIFACT"
    sample_invoice_document.document_type = "INVOIC"
    edi_text = generate_edifact_invoic(sample_invoice_document)

    # Verify Envelope
    assert "UNB+UNOA:2+NOVAERP:14+CARREFOUR:14+" in edi_text
    assert "UNH+1+INVOIC:D:96A:UN:EAN008'" in edi_text

    # Verify BGM & DTM
    assert "BGM+380+INV-2026-0089+9'" in edi_text
    assert "DTM+137:20260908:102'" in edi_text  # Invoice date
    assert "DTM+140:20261008:102'" in edi_text  # Due date

    # Verify RFF References
    assert "RFF+ON:PO-CRF-99412'" in edi_text
    assert "RFF+VN:SO-2026-0042'" in edi_text
    assert "RFF+DQ:DEL-2026-0055'" in edi_text
    assert "RFF+VA:SA300123456700003'" in edi_text

    # Verify NAD Parties
    assert "NAD+SU+NOVA-HQ::9++Nova Distribution Hub+100 Logistics Blvd+Riyadh++++SA'" in edi_text
    assert "NAD+BY+CRF-AP-01::9++Carrefour Central Accounts+King Fahd Road+Riyadh++++SA'" in edi_text
    assert "NAD+DP+CRF-ST-012::9++Carrefour Hypermarket Store #12+Exit 5 North Ring+Riyadh++++SA'" in edi_text

    # Verify Currency & Terms
    assert "CUX+2:USD:4'" in edi_text
    assert "PAT+1++5:3:D:30'" in edi_text
    assert "PCD+12:2.00'" in edi_text

    # Verify LIN Item Loops
    assert "LIN+1++6281001234567:EN'" in edi_text
    assert "PIA+1+CRF-SKU-9901:IN+ALM-MILK-1L:SA'" in edi_text
    assert "IMD+F++:::Almarai Fresh Milk Full Fat 1L'" in edi_text
    assert "QTY+47:50.0:PCE'" in edi_text
    assert "QTY+46:50.0:PCE'" in edi_text
    assert "MOA+203:615.00'" in edi_text
    assert "PRI+AAA:12.5000:PCE:NTP'" in edi_text
    assert "TAX+7+VAT+++:::15.00+S'" in edi_text
    assert "ALC+A+++1'" in edi_text
    assert "MOA+204:10.00'" in edi_text

    assert "LIN+2++6281007654321:EN'" in edi_text
    assert "PIA+1+CRF-SKU-9902:IN+ALM-CHSE-500G:SA'" in edi_text
    assert "IMD+F++:::Almarai Cheddar Cheese 500g'" in edi_text
    assert "QTY+47:30.0:PCE'" in edi_text

    # Verify Section Control & Summaries
    assert "UNS+S'" in edi_text
    assert "CNT+2:2'" in edi_text
    assert "CNT+1:80.0'" in edi_text
    assert "MOA+77:1433.75'" in edi_text
    assert "MOA+79:1225.00'" in edi_text
    assert "MOA+176:183.75'" in edi_text
    assert "MOA+131:50.00'" in edi_text
    assert "MOA+52:25.00'" in edi_text

    # Verify Trailers
    assert "UNT+" in edi_text
    assert "UNZ+1+" in edi_text


def test_parse_edifact_invoic_roundtrip(sample_invoice_document):
    """Verifies round-trip parsing of generated UN/EDIFACT INVOIC."""
    sample_invoice_document.standard = "EDIFACT"
    sample_invoice_document.document_type = "INVOIC"
    edi_text = generate_edifact_invoic(sample_invoice_document)
    parsed = parse_edifact_invoic(edi_text)

    assert parsed.standard == "EDIFACT"
    assert parsed.document_type == "INVOIC"
    assert parsed.sender_id == "NOVAERP"
    assert parsed.receiver_id == "CARREFOUR"
    assert parsed.header.invoice_number == "INV-2026-0089"
    assert parsed.header.buyer_po_number == "PO-CRF-99412"
    assert parsed.header.issue_date == date(2026, 9, 8)
    assert parsed.header.due_date == date(2026, 10, 8)
    assert parsed.header.delivery_number == "DEL-2026-0055"
    assert parsed.header.sales_order_number == "SO-2026-0042"
    assert parsed.header.seller_vat_id == "SA300123456700003"
    assert parsed.header.grand_total == 1433.75
    assert parsed.header.tax_amount == 183.75
    assert parsed.header.freight_amount == 50.00
    assert parsed.header.discount_amount == 25.00

    assert len(parsed.lines) == 2
    l1 = parsed.lines[0]
    assert l1.line_number == 1
    assert l1.gtin == "6281001234567"
    assert l1.buyer_sku == "CRF-SKU-9901"
    assert l1.vendor_sku == "ALM-MILK-1L"
    assert l1.product_name == "Almarai Fresh Milk Full Fat 1L"
    assert l1.qty_invoiced == 50.0
    assert l1.unit_price == 12.5
    assert l1.discount_amount == 10.0


def test_parse_inbound_invoice_autodetect(sample_invoice_document):
    """Verifies automatic standard detection in parse_inbound_invoice."""
    # X12 detection
    x12_payload = generate_x12_810(sample_invoice_document)
    doc_x12 = parse_inbound_invoice(x12_payload)
    assert doc_x12.standard == "ANSI_X12"
    assert doc_x12.header.invoice_number == "INV-2026-0089"

    # EDIFACT detection
    sample_invoice_document.standard = "EDIFACT"
    sample_invoice_document.document_type = "INVOIC"
    edifact_payload = generate_edifact_invoic(sample_invoice_document)
    doc_edi = parse_inbound_invoice(edifact_payload)
    assert doc_edi.standard == "EDIFACT"
    assert doc_edi.header.invoice_number == "INV-2026-0089"


def test_edi_810_credit_invoice_generation(sample_invoice_document):
    """Verifies credit memo / credit note generation in both X12 and EDIFACT."""
    sample_invoice_document.header.invoice_type = "Credit Note"

    # X12 credit invoice
    x12_txt = generate_x12_810(sample_invoice_document)
    assert "BIG*20260908*INV-2026-0089**PO-CRF-99412***CR~" in x12_txt

    # EDIFACT credit invoice
    edifact_txt = generate_edifact_invoic(sample_invoice_document)
    assert "BGM+381+INV-2026-0089+9'" in edifact_txt


def test_edi_810_service_transmit_lifecycle_x12():
    """Verifies end-to-end service generation for ANSI X12 with database repos mocked."""
    mock_partner_repo = MagicMock()
    mock_invoice_repo = MagicMock()
    mock_delivery_repo = MagicMock()
    mock_delivery_line_repo = MagicMock()
    mock_sales_order_repo = MagicMock()
    mock_sales_line_repo = MagicMock()
    mock_pick_repo = MagicMock()
    mock_sku_repo = MagicMock()
    mock_cust_repo = MagicMock()
    mock_prod_repo = MagicMock()
    mock_pay_repo = MagicMock()
    mock_trx_repo = MagicMock()

    service = Edi810Service(
        repo=mock_trx_repo,
        partner_repo=mock_partner_repo,
        invoice_repo=mock_invoice_repo,
        delivery_repo=mock_delivery_repo,
        delivery_line_repo=mock_delivery_line_repo,
        sales_order_repo=mock_sales_order_repo,
        sales_line_repo=mock_sales_line_repo,
        pick_list_item_repo=mock_pick_repo,
        sku_mapping_repo=mock_sku_repo,
        customer_repo=mock_cust_repo,
        product_repo=mock_prod_repo,
        payment_term_repo=mock_pay_repo,
    )

    # Setup mocks
    mock_invoice_repo.get.return_value = {
        'id': 101,
        'invoice_number': 'INV-NOVA-8812',
        'partner_id': 500,
        'sales_order_id': 200,
        'delivery_id': 300,
        'issue_date': '2026-09-08',
        'due_date': '2026-10-08',
        'total_amount': 500.00,
        'freight_amount': 25.00,
        'discount_amount': 10.00,
    }

    mock_delivery_repo.get.return_value = {
        'id': 300,
        'delivery_number': 'DEL-8812',
        'delivery_date': '2026-09-08',
        'delivery_location': 'Riyadh DC #2',
    }

    mock_delivery_line_repo.list.return_value = [{
        'id': 1,
        'delivery_id': 300,
        'sales_order_line_id': 1,
        'product_id': 10,
        'qty_shipped': 100.0,
    }]

    mock_sales_order_repo.get.return_value = {
        'id': 200,
        'order_number': 'SO-8812',
        'customer_id': 500,
        'notes': 'PO# PO-WALMART-8812',
    }

    mock_cust_repo.get.return_value = {
        'id': 500,
        'name': 'Walmart Gulf LLC',
    }

    mock_partner_repo.list.return_value = [{
        'id': 1,
        'partner_name': 'Walmart Gulf EDI',
        'edi_standard': 'ANSI_X12',
        'interchange_sender_id': 'NOVAERP',
        'interchange_receiver_id': 'WALMART',
        'sender_qualifier': 'ZZ',
        'receiver_qualifier': 'ZZ',
        'segment_terminator': '~',
        'element_separator': '*',
        'subelement_separator': '>',
    }]

    mock_sales_line_repo.list.return_value = [{
        'id': 1,
        'sales_order_id': 200,
        'product_id': 10,
        'product_name': 'Sunflower Oil 1.5L',
        'qty': 100.0,
        'unit_price': 5.0,
        'discount': 0.0,
        'line_total': 500.0,
        'uom_id': 'EA',
    }]

    mock_sku_repo.list.return_value = [{
        'product_id': 10,
        'partner_sku': 'WMT-OIL-15',
        'gtin': '6281009998887',
        'partner_uom': 'EA',
    }]

    mock_prod_repo.get.return_value = {
        'id': 10,
        'sku': 'OIL-SUN-15L',
        'name': 'Sunflower Oil 1.5L',
        'barcode': '6281009998887',
    }

    mock_pay_repo.get.return_value = {'id': 1, 'name': 'Net 30 Days', 'net_days': 30}
    mock_trx_repo.create.return_value = {
        'id': 7001,
        'transaction_number': 'TRX-810-001',
    }

    req = EdiInvoiceTransmitRequest(invoice_id=101)
    res = service.generate_invoice(req)

    assert isinstance(res, EdiInvoiceTransmitResponse)
    assert res.transaction_id == 7001
    assert res.standard == "ANSI_X12"
    assert res.document_type == "810"
    assert res.invoice_number == "INV-NOVA-8812"

    assert "BIG*20260908*INV-NOVA-8812**PO-WALMART-8812***DI~" in res.edi_payload
    assert "IT1*1*100*EA*5*PE*CB*WMT-OIL-15*VN*OIL-SUN-15L*UP*6281009998887~" in res.edi_payload


def test_edi_810_service_transmit_lifecycle_edifact():
    """Verifies end-to-end service generation for UN/EDIFACT INVOIC."""
    mock_partner_repo = MagicMock()
    mock_invoice_repo = MagicMock()
    mock_delivery_repo = MagicMock()
    mock_delivery_line_repo = MagicMock()
    mock_sales_order_repo = MagicMock()
    mock_sales_line_repo = MagicMock()
    mock_pick_repo = MagicMock()
    mock_sku_repo = MagicMock()
    mock_cust_repo = MagicMock()
    mock_prod_repo = MagicMock()
    mock_pay_repo = MagicMock()
    mock_trx_repo = MagicMock()

    service = Edi810Service(
        repo=mock_trx_repo,
        partner_repo=mock_partner_repo,
        invoice_repo=mock_invoice_repo,
        delivery_repo=mock_delivery_repo,
        delivery_line_repo=mock_delivery_line_repo,
        sales_order_repo=mock_sales_order_repo,
        sales_line_repo=mock_sales_line_repo,
        pick_list_item_repo=mock_pick_repo,
        sku_mapping_repo=mock_sku_repo,
        customer_repo=mock_cust_repo,
        product_repo=mock_prod_repo,
        payment_term_repo=mock_pay_repo,
    )

    mock_invoice_repo.get.return_value = {
        'id': 102,
        'invoice_number': 'INV-LULU-9901',
        'partner_id': 600,
        'sales_order_id': 201,
        'issue_date': '2026-09-08',
        'due_date': '2026-10-08',
        'total_amount': 1000.00,
        'freight_amount': 0.00,
        'discount_amount': 0.00,
    }

    mock_delivery_repo.get.return_value = None
    mock_delivery_line_repo.list.return_value = []
    mock_sales_order_repo.get.return_value = {
        'id': 201,
        'order_number': 'SO-9901',
        'customer_id': 600,
        'client_order_uuid': 'PO-LULU-9901',
        'notes': 'PO# PO-LULU-9901',
    }
    mock_cust_repo.get.return_value = {'id': 600, 'name': 'Lulu Hypermarket LLC'}

    mock_partner_repo.list.return_value = [{
        'id': 2,
        'partner_name': 'Lulu EDI Hub',
        'edi_standard': 'EDIFACT',
        'interchange_sender_id': 'NOVAERP',
        'interchange_receiver_id': 'LULUHYPER',
        'sender_qualifier': '14',
        'receiver_qualifier': '14',
        'segment_terminator': "'",
        'element_separator': '+',
        'subelement_separator': ':',
    }]

    mock_sales_line_repo.list.return_value = [{
        'id': 1,
        'sales_order_id': 201,
        'product_id': 20,
        'product_name': 'Basmati Rice 5KG',
        'qty': 50.0,
        'unit_price': 20.0,
        'line_total': 1000.0,
        'uom_id': 'EA',
    }]

    mock_sku_repo.list.return_value = [{
        'product_id': 20,
        'partner_sku': 'LULU-RICE-5K',
        'gtin': '6282001112223',
        'partner_uom': 'EA',
    }]

    mock_prod_repo.get.return_value = {
        'id': 20,
        'sku': 'RICE-BAS-5KG',
        'name': 'Basmati Rice 5KG',
        'barcode': '6282001112223',
    }

    mock_pay_repo.get.return_value = None
    mock_trx_repo.create.return_value = {'id': 7002, 'transaction_number': 'TRX-INVOIC-002'}

    res = service.transmit_invoice(invoice_id=102)

    assert res.standard == "EDIFACT"
    assert res.document_type == "INVOIC"
    assert "BGM+380+INV-LULU-9901+9'" in res.edi_payload
    assert "RFF+ON:PO-LULU-9901'" in res.edi_payload
    assert "LIN+1++6282001112223:EN'" in res.edi_payload
    assert "PIA+1+LULU-RICE-5K:IN+RICE-BAS-5KG:SA'" in res.edi_payload


def test_edi_810_service_missing_invoice_raises_error():
    """Verifies that referencing a non-existent invoice raises ValueError."""
    mock_invoice_repo = MagicMock()
    mock_invoice_repo.get.return_value = None

    service = Edi810Service(invoice_repo=mock_invoice_repo)
    with pytest.raises(ValueError, match="Invoice #999 not found"):
        service.generate_invoice(EdiInvoiceTransmitRequest(invoice_id=999))


def test_edi_810_service_missing_partner_raises_error():
    """Verifies that missing trading partner configuration raises ValueError."""
    mock_invoice_repo = MagicMock()
    mock_invoice_repo.get.return_value = {'id': 100, 'partner_id': 999, 'sales_order_id': 1}
    mock_so_repo = MagicMock()
    mock_so_repo.get.return_value = {'id': 1, 'customer_id': 999}
    mock_cust_repo = MagicMock()
    mock_cust_repo.get.return_value = {'id': 999, 'name': 'Unknown Customer'}
    mock_partner_repo = MagicMock()
    mock_partner_repo.list.return_value = []

    service = Edi810Service(
        invoice_repo=mock_invoice_repo,
        sales_order_repo=mock_so_repo,
        customer_repo=mock_cust_repo,
        partner_repo=mock_partner_repo,
    )
    with pytest.raises(ValueError, match="No EDI Trading Partner found"):
        service.generate_invoice(EdiInvoiceTransmitRequest(invoice_id=100))
