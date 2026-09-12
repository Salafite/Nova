"""
Unit tests for Inbound EDI 850 (Purchase Order) & UN/EDIFACT ORDERS Ingestion Service
(modules/integrations/services/edi/edi_850_service.py).
Tests X12 850 parsing, EDIFACT ORDERS parsing, partner resolution, automated SKU & price cross-referencing,
credit limit evaluation, sales order creation in T0012/T0013, 997/CONTRL ACK generation, and transaction reprocessing.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from modules.integrations.services.edi.edi_850_service import (
    Edi850Header,
    Edi850LineItem,
    ParsedEdi850Order,
    parse_x12_850,
    parse_edifact_orders,
    parse_inbound_order_edi,
    Edi850Service,
    edi_850_service,
)
from modules.integrations.models.edi import (
    EdiStandard,
    EdiTransactionStatus,
    EdiAckStatus,
    EdiIngestResult,
    EdiLineDiscrepancy,
)
from modules.integrations.services.edi.cross_reference_service import (
    CrossReferenceService,
    OrderCrossReferenceSummary,
    LineCrossReferenceResult,
    SkuResolutionResult,
    UomConversionResult,
    PriceVerificationResult,
)


# ===========================================================================
# Sample EDI Documents
# ===========================================================================

SAMPLE_X12_850 = (
    "ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVADIST       *260908*1200*U*00401*000000101*0*P*>~\n"
    "GS*PO*CARREFOUR*NOVADIST*20260908*1200*101*X*004010~\n"
    "ST*850*0001~\n"
    "BEG*00*NE*CRF-PO-99001**20260908~\n"
    "CUR*BY*USD~\n"
    "REF*DP*GROCERY-01~\n"
    "REF*IA*VEND-NOVA-88~\n"
    "DTM*002*20260915~\n"
    "N1*BY*Carrefour Hypermarket*91*CRF-UAE-01~\n"
    "N1*ST*Carrefour Store Mall of Emirates*92*STORE-MOE-101~\n"
    "N3*Sheikh Zayed Road~\n"
    "N1*VN*Nova Distribution Inc*91*NOVA-HQ~\n"
    "PO1*1*50*CA*120.00**CB*CRF-RICE-5KG*UP*6291041000101*VN*NV-RICE-5K~\n"
    "PID*F****Basmati Rice 5kg Bag~\n"
    "PO1*2*100*EA*8.50**CB*CRF-OIL-1L*UP*6291041000202*VN*NV-OIL-1L~\n"
    "PID*F****Sunflower Cooking Oil 1L~\n"
    "CTT*2*150~\n"
    "SE*16*0001~\n"
    "GE*1*101~\n"
    "IEA*1*000000101~"
)

SAMPLE_EDIFACT_ORDERS = (
    "UNA:+.? '\n"
    "UNB+UNOA:2+LULU_HYPER:ZZ+NOVADIST:ZZ+260908:1430+20260002'\n"
    "UNH+MSG001+ORDERS:D:96A:UN:EAN008'\n"
    "BGM+220+LULU-PO-77441+9'\n"
    "DTM+137:20260908:102'\n"
    "DTM+2:20260916:102'\n"
    "CUX+2:AED:4'\n"
    "FTX+ZZZ+++Priority Supermarket Restock Order'\n"
    "NAD+BY+6291041000001::9++Lulu Hypermarket LLC+Al Barsha+Dubai++AE'\n"
    "NAD+DP+6291041000099::9++Lulu Al Barsha Central DC+Warehouse 4+Dubai++AE'\n"
    "LIN+1++6291041000101:SRV'\n"
    "PIA+1+LULU-RICE-5KG:IN+NV-RICE-5K:SA'\n"
    "IMD+F++:::Basmati Rice 5kg'\n"
    "QTY+21:40:CA'\n"
    "PRI+AAA:120.00:::NTP'\n"
    "MOA+203:4800.00'\n"
    "LIN+2++6291041000202:SRV'\n"
    "PIA+1+LULU-OIL-1L:IN+NV-OIL-1L:SA'\n"
    "IMD+F++:::Sunflower Oil 1L'\n"
    "QTY+21:80:EA'\n"
    "PRI+AAA:8.50:::NTP'\n"
    "MOA+203:680.00'\n"
    "UNS+S'\n"
    "CNT+2:2'\n"
    "UNT+19+MSG001'\n"
    "UNZ+1+20260002'"
)


# ===========================================================================
# 1. Parsing Tests (ANSI X12 850 & UN/EDIFACT ORDERS)
# ===========================================================================

def test_parse_x12_850_structure():
    """
    Test parsing an ANSI X12 850 PO into structured ParsedEdi850Order.
    """
    orders = parse_x12_850(SAMPLE_X12_850)
    assert len(orders) == 1
    order = orders[0]

    assert order.standard == "ANSI_X12"
    assert order.document_type == "850"
    assert order.control_number == "0001"
    assert order.sender_id.strip() == "CARREFOUR"
    assert order.receiver_id.strip() == "NOVADIST"

    # Header fields
    assert order.header.po_number == "CRF-PO-99001"
    assert order.header.order_date == date(2026, 9, 8)
    assert order.header.requested_delivery_date == date(2026, 9, 15)
    assert order.header.currency == "USD"
    assert order.header.department == "GROCERY-01"
    assert order.header.vendor_id == "VEND-NOVA-88"
    assert order.header.buyer_name == "Carrefour Hypermarket"
    assert order.header.ship_to_name == "Carrefour Store Mall of Emirates"
    assert order.header.ship_to_address == "Sheikh Zayed Road"

    # Lines
    assert len(order.lines) == 2
    line1 = order.lines[0]
    assert line1.line_number == 1
    assert line1.ordered_qty == 50.0
    assert line1.ordered_uom == "CA"
    assert line1.ordered_price == 120.00
    assert line1.buyer_sku == "CRF-RICE-5KG"
    assert line1.gtin == "6291041000101"
    assert line1.vendor_sku == "NV-RICE-5K"
    assert line1.description == "Basmati Rice 5kg Bag"

    line2 = order.lines[1]
    assert line2.line_number == 2
    assert line2.ordered_qty == 100.0
    assert line2.ordered_uom == "EA"
    assert line2.ordered_price == 8.50
    assert line2.buyer_sku == "CRF-OIL-1L"
    assert line2.gtin == "6291041000202"


def test_parse_edifact_orders_structure():
    """
    Test parsing a UN/EDIFACT ORDERS message into structured ParsedEdi850Order.
    """
    orders = parse_edifact_orders(SAMPLE_EDIFACT_ORDERS)
    assert len(orders) == 1
    order = orders[0]

    assert order.standard == "EDIFACT"
    assert order.document_type == "ORDERS"
    assert order.control_number == "MSG001"
    assert order.sender_id.strip() == "LULU_HYPER"
    assert order.receiver_id.strip() == "NOVADIST"

    # Header fields
    assert order.header.po_number == "LULU-PO-77441"
    assert order.header.order_date == date(2026, 9, 8)
    assert order.header.requested_delivery_date == date(2026, 9, 16)
    assert order.header.currency == "AED"
    assert order.header.buyer_name == "Lulu Hypermarket LLC"
    assert order.header.ship_to_name == "Lulu Al Barsha Central DC"
    assert order.header.ship_to_address == "Warehouse 4"
    assert "Priority Supermarket Restock Order" in (order.header.notes or "")

    # Lines
    assert len(order.lines) == 2
    line1 = order.lines[0]
    assert line1.line_number == 1
    assert line1.ordered_qty == 40.0
    assert line1.ordered_uom == "CA"
    assert line1.ordered_price == 120.00
    assert line1.gtin == "6291041000101"
    assert line1.buyer_sku == "LULU-RICE-5KG"
    assert line1.vendor_sku == "NV-RICE-5K"
    assert line1.description == "Basmati Rice 5kg"

    line2 = order.lines[1]
    assert line2.line_number == 2
    assert line2.ordered_qty == 80.0
    assert line2.ordered_uom == "EA"
    assert line2.ordered_price == 8.50
    assert line2.gtin == "6291041000202"
    assert line2.buyer_sku == "LULU-OIL-1L"


def test_parse_inbound_order_edi_auto_detect():
    """
    Test universal parser auto-detection for both standards.
    """
    x12_orders = parse_inbound_order_edi(SAMPLE_X12_850)
    assert len(x12_orders) == 1
    assert x12_orders[0].standard == "ANSI_X12"

    edifact_orders = parse_inbound_order_edi(SAMPLE_EDIFACT_ORDERS)
    assert len(edifact_orders) == 1
    assert edifact_orders[0].standard == "EDIFACT"


# ===========================================================================
# 2. Trading Partner Resolution Tests
# ===========================================================================

def test_resolve_partner():
    """
    Test partner resolution via explicit ID and sender_id.
    """
    mock_partner_repo = MagicMock()
    mock_partner = {
        'id': 10,
        'partner_code': 'CRF-UAE',
        'partner_name': 'Carrefour UAE',
        'interchange_sender_id': 'CARREFOUR',
        'customer_id': 100,
        'auto_confirm_orders': True,
        'price_tolerance_percent': 2.0,
        'is_active': True,
    }

    mock_partner_repo.get.return_value = mock_partner
    mock_partner_repo.list.return_value = [mock_partner]

    service = Edi850Service(partner_repo=mock_partner_repo)
    orders = parse_x12_850(SAMPLE_X12_850)

    # 1. By ID
    p1 = service.resolve_partner(orders[0], partner_id=10)
    assert p1['id'] == 10
    mock_partner_repo.get.assert_called_with(10, conn=None)

    # 2. By sender_id
    p2 = service.resolve_partner(orders[0], partner_id=None)
    assert p2['id'] == 10
    mock_partner_repo.list.assert_called_with(
        filters={'interchange_sender_id': 'CARREFOUR', 'is_active': True},
        limit=1,
        conn=None,
    )


# ===========================================================================
# 3. Inbound Ingestion Pipeline Tests
# ===========================================================================

def test_process_inbound_850_clean_auto_confirm():
    """
    Test clean 850 PO ingestion resulting in an auto-confirmed sales order (T0012)
    and an accepted 997 Functional Acknowledgment.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_line_repo = MagicMock()
    mock_customer_repo = MagicMock()
    mock_xref = MagicMock()
    mock_credit = MagicMock()

    mock_partner = {
        'id': 1,
        'partner_code': 'CRF-UAE',
        'partner_name': 'Carrefour UAE',
        'interchange_sender_id': 'CARREFOUR',
        'customer_id': 50,
        'auto_confirm_orders': True,
        'price_tolerance_percent': 1.0,
        'is_active': True,
    }
    mock_partner_repo.list.return_value = [mock_partner]
    mock_partner_repo.get.return_value = mock_partner

    # TX repo mocks
    mock_tx_repo.create.return_value = {'id': 1001, 'transaction_number': 'TXN-850-0001'}
    mock_tx_repo.update.return_value = {'id': 1001}

    # Order repo mocks
    mock_order_repo.list.return_value = []
    mock_order_repo.create.return_value = {
        'id': 5001,
        'order_number': 'SO-EDI-CRF-PO-99001',
        'status': 'Confirmed',
        'customer_id': 50,
        'grand_total': 6850.0,
    }
    mock_line_repo.create.return_value = {'id': 7001}

    # Cross-reference summary (Clean, 2 lines matched, 0 discrepancies)
    line1_res = LineCrossReferenceResult(
        line_number=1,
        buyer_sku="CRF-RICE-5KG",
        product_id=101,
        product_name="Basmati Rice 5kg",
        ordered_qty=50.0,
        ordered_uom="CA",
        converted_qty=200.0,
        internal_uom="EA",
        uom_factor=4.0,
        ordered_price=120.0,
        expected_price=30.0,
        line_total=6000.0,
        sku_resolution=SkuResolutionResult(matched=True, product_id=101, partner_sku="CRF-RICE-5KG"),
        uom_conversion=UomConversionResult(original_quantity=50.0, original_uom="CA", converted_quantity=200.0, converted_uom="EA"),
        price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=120.0, expected_unit_price=30.0, effective_ordered_unit_price=30.0),
    )
    line2_res = LineCrossReferenceResult(
        line_number=2,
        buyer_sku="CRF-OIL-1L",
        product_id=102,
        product_name="Sunflower Oil 1L",
        ordered_qty=100.0,
        ordered_uom="EA",
        converted_qty=100.0,
        internal_uom="EA",
        uom_factor=1.0,
        ordered_price=8.50,
        expected_price=8.50,
        line_total=850.0,
        sku_resolution=SkuResolutionResult(matched=True, product_id=102, partner_sku="CRF-OIL-1L"),
        uom_conversion=UomConversionResult(original_quantity=100.0, original_uom="EA", converted_quantity=100.0, converted_uom="EA"),
        price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=8.50, expected_unit_price=8.50, effective_ordered_unit_price=8.50),
    )
    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=2,
        matched_lines=2,
        unmatched_lines=0,
        discrepancy_lines=0,
        is_clean=True,
        recommended_status="Confirmed",
        total_ordered_amount=6850.0,
        total_expected_amount=6850.0,
        line_results=[line1_res, line2_res],
    )

    # Credit evaluation clean
    mock_credit.evaluate_order_credit.return_value = {
        'is_hold_required': False,
        'hold_reason': None,
        'credit_limit_exceeded': False,
        'has_overdue_invoices': False,
    }

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        line_repo=mock_line_repo,
        customer_repo=mock_customer_repo,
        xref_service=mock_xref,
        credit_svc=mock_credit,
    )

    result = service.process_inbound_850(SAMPLE_X12_850)

    assert result.status == EdiTransactionStatus.PROCESSED.value
    assert result.sales_order_id == 5001
    assert result.sales_order_number == "SO-EDI-CRF-PO-99001"
    assert result.partner_id == 1
    assert result.partner_code == "CRF-UAE"
    assert result.ack_generated is True
    assert "AK9*A" in result.ack_payload  # Accepted 997 FA
    assert len(result.price_discrepancies) == 0
    assert len(result.errors) == 0

    # Verify T0012 sales order was created with status Confirmed
    mock_order_repo.create.assert_called_once()
    so_create_call = mock_order_repo.create.call_args[0][0]
    assert so_create_call['status'] == 'Confirmed'
    assert so_create_call['customer_id'] == 50
    assert so_create_call['subtotal'] == 6850.0

    # Verify T0013 line items created
    assert mock_line_repo.create.call_count == 2


def test_process_inbound_850_with_price_discrepancy():
    """
    Test 850 PO ingestion with price discrepancy exceeding tolerance.
    Should place order on hold, mark transaction PRICE_DISCREPANCY_HOLD, and report line error.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_line_repo = MagicMock()
    mock_customer_repo = MagicMock()
    mock_xref = MagicMock()
    mock_credit = MagicMock()

    mock_partner = {
        'id': 2,
        'partner_code': 'CRF-UAE',
        'partner_name': 'Carrefour UAE',
        'interchange_sender_id': 'CARREFOUR',
        'customer_id': 50,
        'auto_confirm_orders': True,
        'price_tolerance_percent': 0.0,
        'is_active': True,
    }
    mock_partner_repo.list.return_value = [mock_partner]
    mock_partner_repo.get.return_value = mock_partner

    mock_tx_repo.create.return_value = {'id': 1002, 'transaction_number': 'TXN-850-0002'}
    mock_order_repo.list.return_value = []
    mock_order_repo.create.return_value = {
        'id': 5002,
        'order_number': 'SO-EDI-CRF-PO-99001',
        'status': 'Pending',
        'customer_id': 50,
    }
    mock_line_repo.create.return_value = {'id': 7002}

    disc_info = EdiLineDiscrepancy(
        line_number=1,
        buyer_sku="CRF-RICE-5KG",
        ordered_price=100.0,
        contract_price=120.0,
        discrepancy_percent=16.67,
        discrepancy_type="UNDERPAYMENT",
        details="Price discrepancy of 16.67% exceeds 0% tolerance",
    )

    line1_res = LineCrossReferenceResult(
        line_number=1,
        buyer_sku="CRF-RICE-5KG",
        product_id=101,
        ordered_qty=50.0,
        converted_qty=50.0,
        ordered_price=100.0,
        expected_price=120.0,
        line_total=5000.0,
        has_discrepancy=True,
        discrepancy_info=disc_info,
        sku_resolution=SkuResolutionResult(matched=True, product_id=101, partner_sku="CRF-RICE-5KG"),
        uom_conversion=UomConversionResult(original_quantity=50.0, original_uom="CA", converted_quantity=50.0, converted_uom="CA"),
        price_verification=PriceVerificationResult(is_valid=False, is_discrepancy=True, discrepancy_type="UNDERPAYMENT", ordered_unit_price=100.0, expected_unit_price=120.0, effective_ordered_unit_price=100.0),
    )

    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=1,
        matched_lines=1,
        unmatched_lines=0,
        discrepancy_lines=1,
        is_clean=False,
        recommended_status="PRICE_DISCREPANCY_HOLD",
        total_ordered_amount=5000.0,
        total_expected_amount=6000.0,
        price_discrepancies=[disc_info],
        line_results=[line1_res],
    )

    mock_credit.evaluate_order_credit.return_value = {'is_hold_required': False}

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        line_repo=mock_line_repo,
        customer_repo=mock_customer_repo,
        xref_service=mock_xref,
        credit_svc=mock_credit,
    )

    result = service.process_inbound_850(SAMPLE_X12_850)

    assert result.status == EdiTransactionStatus.PRICE_DISCREPANCY_HOLD.value
    assert len(result.price_discrepancies) == 1
    assert result.price_discrepancies[0].discrepancy_type == "UNDERPAYMENT"

    # Verify T0012 sales order created with Pending status and hold reason
    so_create_call = mock_order_repo.create.call_args[0][0]
    assert so_create_call['status'] == 'Pending'
    assert "Price discrepancies on 1 line(s)" in so_create_call['hold_reason']


def test_process_inbound_850_with_credit_hold():
    """
    Test 850 PO ingestion when customer exceeds credit limit or has overdue invoices.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_line_repo = MagicMock()
    mock_customer_repo = MagicMock()
    mock_xref = MagicMock()
    mock_credit = MagicMock()

    mock_partner = {
        'id': 3,
        'partner_code': 'CRF-UAE',
        'partner_name': 'Carrefour UAE',
        'interchange_sender_id': 'CARREFOUR',
        'customer_id': 50,
        'auto_confirm_orders': True,
        'price_tolerance_percent': 5.0,
        'is_active': True,
    }
    mock_partner_repo.list.return_value = [mock_partner]
    mock_partner_repo.get.return_value = mock_partner

    mock_tx_repo.create.return_value = {'id': 1003, 'transaction_number': 'TXN-850-0003'}
    mock_order_repo.list.return_value = []
    mock_order_repo.create.return_value = {
        'id': 5003,
        'order_number': 'SO-EDI-CRF-PO-99001',
        'status': 'Pending',
        'customer_id': 50,
    }

    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=1,
        matched_lines=1,
        unmatched_lines=0,
        discrepancy_lines=0,
        is_clean=True,
        recommended_status="Confirmed",
        total_ordered_amount=15000.0,
        total_expected_amount=15000.0,
        line_results=[],
    )

    # Customer credit limit exceeded
    mock_credit.evaluate_order_credit.return_value = {
        'is_hold_required': True,
        'hold_reason': "Customer credit limit exceeded: Total exposure $25,000 > Limit $10,000",
        'credit_limit_exceeded': True,
        'has_overdue_invoices': False,
    }

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        line_repo=mock_line_repo,
        customer_repo=mock_customer_repo,
        xref_service=mock_xref,
        credit_svc=mock_credit,
    )

    result = service.process_inbound_850(SAMPLE_X12_850)

    assert result.status == EdiTransactionStatus.PRICE_DISCREPANCY_HOLD.value
    assert any("Credit Hold" in err for err in result.errors)

    so_create_call = mock_order_repo.create.call_args[0][0]
    assert so_create_call['status'] == 'Pending'
    assert "Customer credit limit exceeded" in so_create_call['hold_reason']


def test_process_inbound_edifact_orders_clean():
    """
    Test end-to-end UN/EDIFACT ORDERS message ingestion and CONTRL ACK generation.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_line_repo = MagicMock()
    mock_customer_repo = MagicMock()
    mock_xref = MagicMock()
    mock_credit = MagicMock()

    mock_partner = {
        'id': 4,
        'partner_code': 'LULU-AE',
        'partner_name': 'Lulu Hypermarket',
        'interchange_sender_id': 'LULU_HYPER',
        'customer_id': 60,
        'auto_confirm_orders': True,
        'price_tolerance_percent': 0.0,
        'is_active': True,
    }
    mock_partner_repo.list.return_value = [mock_partner]
    mock_partner_repo.get.return_value = mock_partner

    mock_tx_repo.create.return_value = {'id': 1004, 'transaction_number': 'TXN-850-0004'}
    mock_order_repo.list.return_value = []
    mock_order_repo.create.return_value = {
        'id': 5004,
        'order_number': 'SO-EDI-LULU-PO-77441',
        'status': 'Confirmed',
        'customer_id': 60,
    }
    mock_line_repo.create.return_value = {'id': 7004}

    line1_res = LineCrossReferenceResult(
        line_number=1,
        buyer_sku="LULU-RICE-5KG",
        product_id=101,
        product_name="Basmati Rice 5kg",
        ordered_qty=40.0,
        ordered_uom="CA",
        converted_qty=160.0,
        internal_uom="EA",
        uom_factor=4.0,
        ordered_price=120.0,
        expected_price=30.0,
        line_total=4800.0,
        sku_resolution=SkuResolutionResult(matched=True, product_id=101, partner_sku="LULU-RICE-5KG"),
        uom_conversion=UomConversionResult(original_quantity=40.0, original_uom="CA", converted_quantity=160.0, converted_uom="EA"),
        price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=120.0, expected_unit_price=30.0, effective_ordered_unit_price=30.0),
    )
    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=1,
        matched_lines=1,
        unmatched_lines=0,
        discrepancy_lines=0,
        is_clean=True,
        recommended_status="Confirmed",
        total_ordered_amount=4800.0,
        total_expected_amount=4800.0,
        line_results=[line1_res],
    )
    mock_credit.evaluate_order_credit.return_value = {'is_hold_required': False}

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        line_repo=mock_line_repo,
        customer_repo=mock_customer_repo,
        xref_service=mock_xref,
        credit_svc=mock_credit,
    )

    result = service.process_inbound_850(SAMPLE_EDIFACT_ORDERS)

    assert result.status == EdiTransactionStatus.PROCESSED.value
    assert result.standard == "EDIFACT"
    assert result.document_type == "ORDERS"
    assert result.sales_order_id == 5004
    assert result.ack_generated is True
    assert "UCI+" in result.ack_payload  # CONTRL ACK segment
    assert "+7'" in result.ack_payload   # Action code 7 (Accepted)


# ===========================================================================
# 4. Reprocessing Engine Tests
# ===========================================================================

def test_reprocess_transaction_force_confirm():
    """
    Test reprocessing a previously held EDI transaction with force_confirm=True.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_line_repo = MagicMock()
    mock_customer_repo = MagicMock()
    mock_xref = MagicMock()

    mock_partner = {
        'id': 1,
        'partner_code': 'CRF-UAE',
        'customer_id': 50,
        'price_tolerance_percent': 0.0,
        'is_active': True,
    }
    mock_partner_repo.get.return_value = mock_partner
    mock_partner_repo.list.return_value = [mock_partner]

    mock_tx_repo.get.return_value = {
        'id': 1005,
        'transaction_number': 'TXN-850-0005',
        'partner_id': 1,
        'standard': 'ANSI_X12',
        'document_type': '850',
        'direction': 'INBOUND',
        'control_number': '0005',
        'status': 'PRICE_DISCREPANCY_HOLD',
        'sales_order_id': 5005,
        'raw_payload': SAMPLE_X12_850,
        'ack_payload': 'ISA*...~',
    }

    mock_order_repo.get.return_value = {
        'id': 5005,
        'order_number': 'SO-EDI-CRF-PO-99001',
        'status': 'Pending',
        'hold_reason': 'Price Discrepancy Hold',
    }

    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=2,
        matched_lines=2,
        unmatched_lines=0,
        discrepancy_lines=1,
        is_clean=False,
        recommended_status="PRICE_DISCREPANCY_HOLD",
        total_ordered_amount=6850.0,
        line_results=[],
    )

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        line_repo=mock_line_repo,
        customer_repo=mock_customer_repo,
        xref_service=mock_xref,
    )

    reprocess_result = service.reprocess_transaction(
        transaction_id=1005,
        force_confirm=True,
    )

    assert reprocess_result.status == EdiTransactionStatus.PROCESSED.value
    assert reprocess_result.sales_order_id == 5005
    assert len(reprocess_result.price_discrepancies) == 0

    # Verify order was updated to Confirmed
    mock_order_repo.update.assert_called_with(
        5005,
        {'status': 'Confirmed', 'hold_reason': None},
        conn=None,
    )


def test_reprocess_transaction_override_price_tolerance():
    """
    Test reprocessing a transaction with override_price_tolerance widening tolerance.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_order_repo = MagicMock()
    mock_xref = MagicMock()

    mock_partner = {'id': 1, 'price_tolerance_percent': 0.0, 'customer_id': 50}
    mock_partner_repo.get.return_value = mock_partner
    mock_partner_repo.list.return_value = [mock_partner]

    mock_tx_repo.get.return_value = {
        'id': 1006,
        'transaction_number': 'TXN-850-0006',
        'partner_id': 1,
        'standard': 'ANSI_X12',
        'document_type': '850',
        'sales_order_id': 5006,
        'raw_payload': SAMPLE_X12_850,
    }

    mock_order_repo.get.return_value = {
        'id': 5006,
        'order_number': 'SO-EDI-CRF-PO-99001',
        'status': 'Pending',
    }

    # Cross-reference with 5% tolerance returns clean summary
    mock_xref.cross_reference_order.return_value = OrderCrossReferenceSummary(
        total_lines=2,
        matched_lines=2,
        unmatched_lines=0,
        discrepancy_lines=0,
        is_clean=True,
        recommended_status="Confirmed",
        total_ordered_amount=6850.0,
        line_results=[],
    )

    service = Edi850Service(
        transaction_repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        order_repo=mock_order_repo,
        xref_service=mock_xref,
    )

    result = service.reprocess_transaction(
        transaction_id=1006,
        override_price_tolerance=5.0,
    )

    assert result.status == EdiTransactionStatus.PROCESSED.value
    # Verify xref was called with price_tolerance_percent=5.0
    call_kwargs = mock_xref.cross_reference_order.call_args[1]
    assert call_kwargs['price_tolerance_percent'] == 5.0


def test_process_inbound_850_syntax_error():
    """
    Test handling corrupt/invalid EDI document syntax.
    """
    mock_tx_repo = MagicMock()
    mock_tx_repo.create.return_value = {'id': 1007, 'transaction_number': 'TXN-850-0007'}

    service = Edi850Service(transaction_repo=mock_tx_repo)
    corrupt_payload = "ISA*00*          *00*          *ZZ*BAD_DATA~"

    result = service.process_inbound_850(corrupt_payload)

    assert result.status == EdiTransactionStatus.FAILED.value
    assert len(result.errors) > 0
    assert result.ack_generated is True
    assert "AK9*R" in result.ack_payload  # Rejected 997 FA
