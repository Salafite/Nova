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
    EdiInvoiceParty,
    EdiInvoiceItemDetail,
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
    supplier = EdiInvoiceParty(
        party_type="SF",
        name="Nova Distribution HQ",
        id_code="NOVA-HQ",
        id_qualifier="92",
        address="100 Logistics Blvd",
        city="Riyadh",
        state="RD",
        postal_code="11564",
        country="SA",
        vat_number="SA300123456700003",
    )
    buyer = EdiInvoiceParty(
        party_type="BT",
        name="Carrefour Central Accounts",
        id_code="CRF-AP-01",
        id_qualifier="92",
        address="King Fahd Road",
        city="Riyadh",
        postal_code="11421",
        country="SA",
    )
    ship_to = EdiInvoiceParty(
        party_type="ST",
        name="Carrefour Hypermarket Store #12",
        id_code="CRF-ST-012",
        id_qualifier="92",
        address="Exit 5 North Ring",
        city="Riyadh",
        postal_code="11432",
        country="SA",
    )

    header = EdiInvoiceHeader(
        invoice_id=101,
        invoice_number="INV-2026-0089",
        invoice_type="380",
        invoice_date=date(2026, 9, 8),
        due_date=date(2026, 10, 8),
        discount_due_date=date(2026, 9, 18),
        discount_percentage=2.0,
        discount_days=10,
        net_days=30,
        early_discount_amount=24.50,
        delivery_id=55,
        delivery_number="DEL-2026-0055",
        delivery_date=date(2026, 9, 8),
        ship_date=date(2026, 9, 7),
        sales_order_id=42,
        sales_order_number="SO-2026-0042",
        buyer_po_number="PO-CRF-99412",
        buyer_po_date=date(2026, 9, 5),
        currency="USD",
        subtotal=1225.00,
        tax_amount=183.75,
        tax_rate=15.00,
        tax_taxable_amount=1225.00,
        freight_amount=50.00,
        discount_amount=25.00,
        total_amount=1433.75,
        payment_terms_desc="2/10 Net 30",
        supplier_party=supplier,
        buyer_party=buyer,
        ship_to_party=ship_to,
        vat_registration_number="SA300123456700003",
    )

    items = [
        EdiInvoiceItemDetail(
            line_number=1,
            product_id=10,
            sku="ALM-MILK-1L",
            buyer_sku="CRF-SKU-9901",
            vendor_sku="ALM-MILK-1L",
            gtin="6281001234567",
            product_name="Almarai Fresh Milk Full Fat 1L",
            qty_invoiced=50.0,
            qty_delivered=50.0,
            uom="EA",
            unit_price=12.50,
            price_basis="PE",
            line_total=625.00,
            tax_rate=15.00,
            tax_amount=93.75,
            discount_amount=10.00,
            discount_percent=1.60,
            batch_number="BAT-2026-09A",
            expiry_date=date(2026, 9, 20),
        ),
        EdiInvoiceItemDetail(
            line_number=2,
            product_id=11,
            sku="ALM-CHSE-500G",
            buyer_sku="CRF-SKU-9902",
            vendor_sku="ALM-CHSE-500G",
            gtin="6281007654321",
            product_name="Almarai Cheddar Cheese 500g",
            qty_invoiced=30.0,
            qty_delivered=30.0,
            uom="EA",
            unit_price=20.00,
            price_basis="PE",
            line_total=600.00,
            tax_rate=15.00,
            tax_amount=90.00,
            discount_amount=15.00,
            discount_percent=2.50,
            batch_number="BAT-2026-09B",
            expiry_date=date(2026, 12, 31),
        ),
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
        items=items,
    )


def test_generate_x12_810_structure(sample_invoice_document):
    """Verifies ANSI X12 810 invoice structure and required segments."""
    edi_text = generate_x12_810(sample_invoice_document)

    # Verify Envelope
    assert "ISA*" in edi_text
    assert "GS*IN*NOVAERP*CARREFOUR*" in edi_text
    assert "ST*810*" in edi_text

    # Verify BIG Segment
    assert "BIG*20260908*INV-2026-0089*20260905*PO-CRF-99412***DI~" in edi_text

    # Verify CUR & REF Segments
    assert "CUR*SE*USD~" in edi_text
    assert "REF*BM*DEL-2026-0055~" in edi_text
    assert "REF*SO*SO-2026-0042~" in edi_text
    assert "REF*TX*SA300123456700003~" in edi_text

    # Verify N1 Party Segments
    assert "N1*SF*Nova Distribution HQ*92*NOVA-HQ~" in edi_text
    assert "N3*100 Logistics Blvd~" in edi_text
    assert "N4*Riyadh*RD*11564*SA~" in edi_text
    assert "N1*ST*Carrefour Hypermarket Store #12*92*CRF-ST-012~" in edi_text
    assert "N1*BT*Carrefour Central Accounts*92*CRF-AP-01~" in edi_text

    # Verify ITD Terms Segment
    assert "ITD*08*3*2.00*20260918*10*20261008*30*24.50****2/10 Net 30~" in edi_text

    # Verify DTM Segments
    assert "DTM*011*20260907~" in edi_text  # Ship date
    assert "DTM*002*20260908~" in edi_text  # Delivery date
    assert "DTM*003*20260908~" in edi_text  # Invoice date

    # Verify IT1 Item Segments
    assert "IT1*1*50*EA*12.5*PE*BP*CRF-SKU-9901*VP*ALM-MILK-1L*UP*6281001234567~" in edi_text
    assert "PID*F****Almarai Fresh Milk Full Fat 1L~" in edi_text
    assert "REF*LT*BAT-2026-09A~" in edi_text
    assert "DTM*036*20260920~" in edi_text
    assert "SAC*A*F800***10.00**1.60*******Line Discount~" in edi_text
    assert "TXI*VA*93.75*15.00~" in edi_text

    assert "IT1*2*30*EA*20*PE*BP*CRF-SKU-9902*VP*ALM-CHSE-500G*UP*6281007654321~" in edi_text
    assert "PID*F****Almarai Cheddar Cheese 500g~" in edi_text
    assert "REF*LT*BAT-2026-09B~" in edi_text
    assert "DTM*036*20261231~" in edi_text

    # Verify TDS & Summary Segments
    assert "TDS*1433.75~" in edi_text
    assert "TXI*VA*183.75*15.00****1225.00**SA300123456700003~" in edi_text
    assert "SAC*C*D240***50.00*****02***Freight Charge~" in edi_text
    assert "SAC*A*F800***25.00*****02***Order Discount~" in edi_text
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
    assert parsed.header.invoice_date == date(2026, 9, 8)
    assert parsed.header.due_date == date(2026, 10, 8)
    assert parsed.header.discount_percentage == 2.0
    assert parsed.header.total_amount == 1433.75
    assert parsed.header.delivery_number == "DEL-2026-0055"
    assert parsed.header.sales_order_number == "SO-2026-0042"

    assert parsed.header.supplier_party is not None
    assert parsed.header.supplier_party.name == "Nova Distribution HQ"
    assert parsed.header.buyer_party is not None
    assert parsed.header.buyer_party.name == "Carrefour Central Accounts"

    assert len(parsed.items) == 2
    item1 = parsed.items[0]
    assert item1.line_number == 1
    assert item1.qty_invoiced == 50.0
    assert item1.unit_price == 12.5
    assert item1.buyer_sku == "CRF-SKU-9901"
    assert item1.vendor_sku == "ALM-MILK-1L"
    assert item1.gtin == "6281001234567"
    assert item1.product_name == "Almarai Fresh Milk Full Fat 1L"
    assert item1.batch_number == "BAT-2026-09A"
    assert item1.expiry_date == date(2026, 9, 20)
    assert item1.tax_amount == 93.75


def test_generate_edifact_invoic_structure(sample_invoice_document):
    """Verifies UN/EDIFACT INVOIC D96A structure and required segments."""
    sample_invoice_document.standard = "EDIFACT"
    sample_invoice_document.document_type = "INVOIC"
    edi_text = generate_edifact_invoic(sample_invoice_document)

    # Verify Envelope
    assert "UNB+UNOA:2+NOVAERP:ZZ+CARREFOUR:ZZ+" in edi_text
    assert "UNH+0001+INVOIC:D:96A:UN:EAN008'" in edi_text

    # Verify BGM & DTM
    assert "BGM+380+INV-2026-0089+9'" in edi_text
    assert "DTM+137:20260908:102'" in edi_text  # Document date
    assert "DTM+35:20260908:102'" in edi_text   # Delivery date
    assert "DTM+140:20261008:102'" in edi_text  # Due date
    assert "DTM+11:20260907:102'" in edi_text   # Ship date

    # Verify RFF References
    assert "RFF+ON:PO-CRF-99412'" in edi_text
    assert "RFF+VN:SO-2026-0042'" in edi_text
    assert "RFF+DQ:DEL-2026-0055'" in edi_text
    assert "RFF+VA:SA300123456700003'" in edi_text

    # Verify NAD Parties
    assert "NAD+SU+NOVA-HQ::92++Nova Distribution HQ+100 Logistics Blvd+Riyadh++11564+SA'" in edi_text
    assert "NAD+BY+CRF-AP-01::92++Carrefour Central Accounts+King Fahd Road+Riyadh++11421+SA'" in edi_text
    assert "NAD+DP+CRF-ST-012::92++Carrefour Hypermarket Store #12+Exit 5 North Ring+Riyadh++11432+SA'" in edi_text

    # Verify Currency & Terms
    assert "CUX+2:USD:4'" in edi_text
    assert "PAT+1++5:3:D:30'" in edi_text
    assert "PCD+12:2.00'" in edi_text

    # Verify LIN Item Loops
    assert "LIN+1++6281001234567:EN'" in edi_text
    assert "PIA+1+CRF-SKU-9901:BP+ALM-MILK-1L:VN'" in edi_text
    assert "IMD+F+ANM+:::Almarai Fresh Milk Full Fat 1L'" in edi_text
    assert "QTY+47:50:EA'" in edi_text
    assert "QTY+46:50:EA'" in edi_text
    assert "MOA+203:625.00'" in edi_text
    assert "PRI+AAA:12.5000::CA'" in edi_text
    assert "TAX+7+VAT+++++15.00'" in edi_text
    assert "MOA+124:93.75'" in edi_text
    assert "ALC+A++++DI'" in edi_text
    assert "MOA+204:10.00'" in edi_text
    assert "GIR+3+BAT-2026-09A:BX'" in edi_text
    assert "DTM+361:20260920:102'" in edi_text

    assert "LIN+2++6281007654321:EN'" in edi_text
    assert "PIA+1+CRF-SKU-9902:BP+ALM-CHSE-500G:VN'" in edi_text
    assert "IMD+F+ANM+:::Almarai Cheddar Cheese 500g'" in edi_text
    assert "QTY+47:30:EA'" in edi_text

    # Verify Section Control & Summaries
    assert "UNS+S'" in edi_text
    assert "CNT+2:2'" in edi_text
    assert "MOA+77:1433.75'" in edi_text
    assert "MOA+79:1225.00'" in edi_text
    assert "MOA+124:183.75'" in edi_text
    assert "MOA+131:50.00'" in edi_text
    assert "MOA+204:25.00'" in edi_text
    assert "MOA+125:1225.00'" in edi_text

    # Verify Trailers
    assert "UNT*" not in edi_text
    assert "UNT+38+0001'" in edi_text or "UNT+" in edi_text
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
    assert parsed.header.invoice_date == date(2026, 9, 8)
    assert parsed.header.due_date == date(2026, 10, 8)
    assert parsed.header.delivery_number == "DEL-2026-0055"
    assert parsed.header.sales_order_number == "SO-2026-0042"
    assert parsed.header.vat_registration_number == "SA300123456700003"
    assert parsed.header.total_amount == 1433.75
    assert parsed.header.tax_amount == 183.75
    assert parsed.header.freight_amount == 50.00
    assert parsed.header.discount_amount == 25.00

    assert len(parsed.items) == 2
    it1 = parsed.items[0]
    assert it1.line_number == 1
    assert it1.gtin == "6281001234567"
    assert it1.buyer_sku == "CRF-SKU-9901"
    assert it1.vendor_sku == "ALM-MILK-1L"
    assert it1.product_name == "Almarai Fresh Milk Full Fat 1L"
    assert it1.qty_invoiced == 50.0
    assert it1.unit_price == 12.5
    assert it1.batch_number == "BAT-2026-09A"
    assert it1.expiry_date == date(2026, 9, 20)
    assert it1.tax_amount == 93.75
    assert it1.discount_amount == 10.0


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
    sample_invoice_document.header.invoice_type = "381"

    # X12 credit invoice
    x12_txt = generate_x12_810(sample_invoice_document)
    assert "BIG*20260908*INV-2026-0089*20260905*PO-CRF-99412***CR~" in x12_txt

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
    }]

    mock_prod_repo.get.return_value = {
        'id': 10,
        'sku': 'OIL-SUN-15L',
        'name': 'Sunflower Oil 1.5L',
        'barcode': '6281009998887',
    }

    mock_pick_repo.list.return_value = [{
        'sales_order_line_id': 1,
        'product_id': 10,
        'picked_batch_number': 'BATCH-OIL-2026',
        'expiry_date': '2027-06-30',
    }]

    mock_trx_repo.create.return_value = {
        'id': 7001,
        'transaction_number': 'TRX-810-001',
    }

    req = EdiInvoiceTransmitRequest(invoice_id=101)
    res = service.transmit_invoice(req)

    assert isinstance(res, EdiInvoiceTransmitResponse)
    assert res.transaction_id == 7001
    assert res.standard == "ANSI_X12"
    assert res.document_type == "810"
    assert res.invoice_number == "INV-NOVA-8812"

    assert "BIG*20260908*INV-NOVA-8812**PO-WALMART-8812***DI~" in res.edi_payload
    assert "IT1*1*100*EA*5*PE*BP*WMT-OIL-15*VP*OIL-SUN-15L*UP*6281009998887~" in res.edi_payload
    assert "REF*LT*BATCH-OIL-2026~" in res.edi_payload
    assert "DTM*036*20270630~" in res.edi_payload


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
    mock_sales_order_repo.get.return_value = {
        'id': 201,
        'order_number': 'SO-9901',
        'customer_id': 600,
        'client_order_uuid': 'PO-LULU-9901',
    }
    mock_cust_repo.get.return_value = {'id': 600, 'name': 'Lulu Hypermarket LLC'}

    mock_partner_repo.list.return_value = [{
        'id': 2,
        'partner_name': 'Lulu EDI Hub',
        'edi_standard': 'EDIFACT',
        'interchange_sender_id': 'NOVAERP',
        'interchange_receiver_id': 'LULUHYPER',
        'sender_qualifier': 'ZZ',
        'receiver_qualifier': 'ZZ',
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
    }]

    mock_prod_repo.get.return_value = {
        'id': 20,
        'sku': 'RICE-BAS-5KG',
        'name': 'Basmati Rice 5KG',
        'barcode': '6282001112223',
    }

    mock_pick_repo.list.return_value = []
    mock_trx_repo.create.return_value = {'id': 7002, 'transaction_number': 'TRX-INVOIC-002'}

    res = service.transmit_invoice(EdiInvoiceTransmitRequest(invoice_id=102))

    assert res.standard == "EDIFACT"
    assert res.document_type == "INVOIC"
    assert "BGM+380+INV-LULU-9901+9'" in res.edi_payload
    assert "RFF+ON:PO-LULU-9901'" in res.edi_payload
    assert "LIN+1++6282001112223:EN'" in res.edi_payload
    assert "PIA+1+LULU-RICE-5K:BP+RICE-BAS-5KG:VN'" in res.edi_payload


def test_edi_810_service_generate_from_delivery():
    """Verifies generating an invoice directly from a delivery without an invoice ID."""
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
    )

    mock_delivery_repo.get.return_value = {
        'id': 501,
        'delivery_number': 'DEL-DIRECT-01',
        'sales_order_id': 301,
        'freight_cost': 40.0,
        'delivery_date': '2026-09-08',
    }

    mock_sales_order_repo.get.return_value = {
        'id': 301,
        'order_number': 'SO-301',
        'customer_id': 700,
        'client_order_uuid': 'PO-AMAZON-01',
    }

    mock_cust_repo.get.return_value = {'id': 700, 'name': 'Amazon Fresh'}

    mock_partner_repo.list.return_value = [{
        'id': 3,
        'partner_name': 'Amazon Retail EDI',
        'edi_standard': 'ANSI_X12',
        'interchange_sender_id': 'NOVAERP',
        'interchange_receiver_id': 'AMAZON',
        'sender_qualifier': 'ZZ',
        'receiver_qualifier': 'ZZ',
    }]

    mock_delivery_line_repo.list.return_value = [{
        'id': 1,
        'delivery_id': 501,
        'product_id': 30,
        'product_name': 'Orange Juice 1L',
        'qty_shipped': 20.0,
        'unit_price': 8.0,
        'line_total': 160.0,
        'uom_id': 'EA',
    }]

    mock_sku_repo.list.return_value = []
    mock_prod_repo.get.return_value = {'id': 30, 'sku': 'JUICE-ORG-1L', 'name': 'Orange Juice 1L'}
    mock_pick_repo.list.return_value = []
    mock_trx_repo.create.return_value = {'id': 7003, 'transaction_number': 'TRX-810-003'}

    res = service.generate_invoice_for_delivery_or_order(delivery_id=501)
    assert res.standard == "ANSI_X12"
    assert res.document_type == "810"
    assert "REF*BM*DEL-DIRECT-01~" in res.edi_payload
    assert "REF*SO*SO-301~" in res.edi_payload


def test_edi_810_service_missing_invoice_raises_error():
    """Verifies that referencing a non-existent invoice raises ValueError."""
    mock_invoice_repo = MagicMock()
    mock_invoice_repo.get.return_value = None

    service = Edi810Service(invoice_repo=mock_invoice_repo)
    with pytest.raises(ValueError, match="Invoice #999 not found"):
        service.transmit_invoice(EdiInvoiceTransmitRequest(invoice_id=999))


def test_edi_810_service_missing_partner_raises_error():
    """Verifies that missing trading partner configuration raises ValueError."""
    mock_invoice_repo = MagicMock()
    mock_invoice_repo.get.return_value = {'id': 100, 'partner_id': 999}
    mock_partner_repo = MagicMock()
    mock_partner_repo.list.return_value = []

    service = Edi810Service(invoice_repo=mock_invoice_repo, partner_repo=mock_partner_repo)
    with pytest.raises(ValueError, match="No active EDI Trading Partner found"):
        service.transmit_invoice(EdiInvoiceTransmitRequest(invoice_id=100))
