"""
Comprehensive Unit Tests for EDI Parsers, SSCC-18 Calculation, and SKU/Price Discrepancy Resolution
(Subtask 7-1 of Phase 7).

Tests edge cases, syntax variations, delimiter handling, Modulo-10 validation,
and complex multi-level pricing resolution matrices.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

# Core EDI & SSCC
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiStandard,
    EdiSegment,
    EdiInterchange,
    EdiFunctionalGroup,
    EdiTransactionSet,
    X12Builder,
    EdifactBuilder,
    parse_edi,
    serialize_edi,
    detect_edi_standard,
)
from modules.integrations.services.edi.sscc_service import (
    calculate_modulo10_check_digit,
    validate_modulo10,
    generate_sscc18,
    parse_sscc_gs1_128,
    format_sscc_gs1_128,
    decompose_sscc18,
    PackagingItem,
    PackagingBox,
    PackagingPallet,
    PackagingHierarchy,
    format_gs1_logistics_label,
    SsccService,
)

# Cross Reference & Pricing
from modules.integrations.services.edi.cross_reference_service import (
    normalize_sku_type,
    CrossReferenceService,
    SkuResolutionResult,
    UomConversionResult,
    PriceVerificationResult,
    LineCrossReferenceResult,
)

# 850/ORDERS
from modules.integrations.services.edi.edi_850_service import (
    parse_x12_850,
    parse_edifact_orders,
    parse_inbound_order_edi,
    Edi850Header,
    Edi850LineItem,
    ParsedEdi850Order,
)

# 856/DESADV
from modules.integrations.services.edi.edi_856_service import (
    EdiAsnShipmentHeader,
    EdiAsnItemDetail,
    EdiAsnBoxDetail,
    EdiAsnPalletDetail,
    EdiAsnDocument,
    generate_x12_856,
    generate_edifact_desadv,
    parse_x12_856,
    parse_edifact_desadv,
    parse_inbound_asn,
)

# 810/INVOIC
from modules.integrations.services.edi.edi_810_service import (
    EdiInvoiceHeader,
    EdiInvoiceLine,
    EdiInvoiceTaxSummary,
    EdiInvoiceAllowanceCharge,
    EdiInvoiceDocument,
    generate_x12_810,
    generate_edifact_invoic,
    parse_x12_810,
    parse_edifact_invoic,
    parse_inbound_invoice,
)


# ===========================================================================
# 1. Modulo-10 SSCC-18 Calculation & Edge Case Tests
# ===========================================================================

class TestSsccModulo10AndPackagingEdgeCases:
    """Tests for GS1 Modulo-10 algorithm and SSCC container packaging structures."""

    @pytest.mark.parametrize("payload, expected_check_digit", [
        ("00614141123456789", 0),
        ("10614141123456789", 7),
        ("0061414100003", 6),
        ("00000000000000000", 0),
        ("12345678901234567", 5),
    ])
    def test_modulo10_vectors(self, payload: str, expected_check_digit: int):
        """Test Modulo-10 calculation with standard GS1 test vectors."""
        assert calculate_modulo10_check_digit(payload) == expected_check_digit
        full_code = f"{payload}{expected_check_digit}"
        assert validate_modulo10(full_code) is True

    def test_modulo10_invalid_checksums(self):
        """Test that mutated check digits are rejected."""
        valid_sscc = "006141411234567890"
        assert validate_modulo10(valid_sscc) is True
        # Mutate check digit
        assert validate_modulo10("006141411234567895") is False
        assert validate_modulo10("006141411234567891") is False
        # Mutate body
        assert validate_modulo10("006141411234567880") is False

    def test_generate_sscc18_prefix_lengths(self):
        """Test generating SSCC-18 with 7, 8, 9, and 10 digit GS1 company prefixes."""
        # 7-digit prefix -> 9 serial digits
        sscc_7 = generate_sscc18("0614141", 1, 0)
        assert len(sscc_7) == 18
        assert sscc_7.startswith("00614141")
        assert validate_modulo10(sscc_7) is True

        # 9-digit prefix -> 7 serial digits
        sscc_9 = generate_sscc18("061414100", 42, 1)
        assert len(sscc_9) == 18
        assert sscc_9.startswith("1061414100")
        assert validate_modulo10(sscc_9) is True

        # 10-digit prefix -> 6 serial digits
        sscc_10 = generate_sscc18("0614141001", 999, 2)
        assert len(sscc_10) == 18
        assert sscc_10.startswith("20614141001")
        assert validate_modulo10(sscc_10) is True

    def test_parse_and_decompose_sscc(self):
        """Test parsing SSCC with AI (00) and decomposing components."""
        raw = "(00) 0 0614141 000000001 7"
        parsed = parse_sscc_gs1_128(raw)
        assert parsed == "006141410000000017"

        decomp = decompose_sscc18("006141410000000017", company_prefix_len=7)
        assert decomp["extension_digit"] == "0"
        assert decomp["company_prefix"] == "0614141"
        assert decomp["serial_reference"] == "000000001"
        assert decomp["check_digit"] == 7

    def test_packaging_hierarchy_calculations(self):
        """Test packaging weight and volume rollups from item -> box -> pallet."""
        item1 = PackagingItem(
            sku="RICE-1KG",
            gtin="629104100001",
            quantity=10,
            net_weight_kg=10.0,
            gross_weight_kg=10.0,
        )
        item2 = PackagingItem(
            sku="OIL-1L",
            gtin="629104100002",
            quantity=5,
            net_weight_kg=4.5,
            gross_weight_kg=4.5,
        )
        box = PackagingBox(
            box_number="BX-01",
            items=[item1, item2],
            tare_weight_kg=0.5,
            length_cm=40,
            width_cm=30,
            height_cm=20,
        )
        box.calculate_weights()
        assert box.net_weight_kg == 14.5
        assert box.gross_weight_kg == 15.0 # 14.5 + 0.5

        pallet = PackagingPallet(
            pallet_number="PLT-01",
            sscc_barcode="006141410000000017",
            boxes=[box],
            tare_weight_kg=25.0,
        )
        pallet.calculate_weights()
        assert pallet.net_weight_kg == 14.5
        assert pallet.gross_weight_kg == 40.0 # 15.0 + 25.0

        label = format_gs1_logistics_label(pallet)
        assert label["sscc"]["raw_18"] == "006141410000000017"
        assert label["sscc"]["formatted_gs1_128"] == "(00)006141410000000017"
        assert label["item_details"]["gross_weight_kg"] == 40.0


# ===========================================================================
# 2. SKU & Price Discrepancy Resolution Tests
# ===========================================================================

class TestSkuAndPriceDiscrepancyResolution:
    """Tests SKU cross-referencing and contract/price list discrepancy resolution."""

    def test_price_tolerance_exact_boundaries(self):
        """Test price verification at exact tolerance boundary percentages."""
        svc = CrossReferenceService()

        # 1. Exact match (0% discrepancy)
        res_exact = svc.verify_line_price(
            ordered_price=100.00,
            expected_price=100.00,
            tolerance_percent=2.0,
        )
        assert res_exact.is_valid is True
        assert res_exact.is_discrepancy is False
        assert res_exact.discrepancy_percent == 0.0

        # 2. Within tolerance (+1.5% overpayment) -> accepted
        res_over = svc.verify_line_price(
            ordered_price=101.50,
            expected_price=100.00,
            tolerance_percent=2.0,
        )
        assert res_over.is_valid is True
        assert res_over.is_discrepancy is False
        assert res_over.discrepancy_percent == 1.5

        # 3. Within tolerance (-1.8% underpayment) -> accepted
        res_under = svc.verify_line_price(
            ordered_price=98.20,
            expected_price=100.00,
            tolerance_percent=2.0,
        )
        assert res_under.is_valid is True
        assert res_under.is_discrepancy is False
        assert pytest.approx(res_under.discrepancy_percent, 0.01) == 1.8

        # 4. Out of tolerance (-5.0% underpayment) -> discrepancy flag
        res_flagged = svc.verify_line_price(
            ordered_price=95.00,
            expected_price=100.00,
            tolerance_percent=2.0,
        )
        assert res_flagged.is_valid is False
        assert res_flagged.is_discrepancy is True
        assert res_flagged.discrepancy_percent == 5.0
        assert res_flagged.discrepancy_amount == -5.00
        assert res_flagged.discrepancy_type == 'UNDERPAYMENT'

    def test_uom_conversion_and_cross_reference_summary(self):
        """Test UOM conversion factor calculation and line summary discrepancies."""
        mock_sku_repo = MagicMock()
        mock_prod_repo = MagicMock()
        mock_contract_repo = MagicMock()

        # Mapping: 1 Case (CA) = 12 Each (EA)
        mock_sku_repo.list.return_value = [
            {
                'id': 1,
                'partner_id': 2,
                'product_id': 50,
                'partner_sku': 'CRF-JUICE-1L',
                'partner_sku_type': 'BUYER_PART_NO',
                'gtin': '6291041005555',
                'partner_uom': 'CA',
                'internal_uom': 'EA',
                'uom_conversion_factor': 12.0,
                'catalog_price': 60.00,
                'is_active': True,
            }
        ]
        mock_prod_repo.get.return_value = {
            'id': 50,
            'sku': 'NOVA-JUICE-1L',
            'name': 'Orange Juice 1L Bottle',
            'price': 5.00,
        }
        mock_contract_repo.list.return_value = []

        svc = CrossReferenceService(
            sku_mapping_repo=mock_sku_repo,
            product_repo=mock_prod_repo,
            contract_repo=mock_contract_repo,
        )

        uom_res = svc.convert_uom_quantity(quantity=5.0, partner_uom='CA', internal_uom='EA', uom_conversion_factor=12.0)
        assert uom_res.converted_quantity == 60.0
        assert uom_res.conversion_factor == 12.0
        assert uom_res.is_converted is True

        # Line cross reference with price mismatch (ordered $50.00 vs expected $60.00)
        line_res = svc.cross_reference_line(
            partner_id=2,
            customer_id=1,
            line_number=1,
            buyer_sku='CRF-JUICE-1L',
            ordered_qty=5.0,
            partner_uom='CA',
            ordered_price=50.00,
            price_tolerance_percent=1.0,
        )
        assert line_res.product_id == 50
        assert line_res.has_discrepancy is True
        assert line_res.discrepancy_info is not None
        assert line_res.discrepancy_info.discrepancy_type == 'UNDERPAYMENT'


# ===========================================================================
# 3. ANSI X12 850 / 856 / 810 Roundtrip & Parser Tests
# ===========================================================================

class TestAnsiX12ParsersAndGenerators:
    """Tests for ANSI X12 850 (PO), 856 (ASN), and 810 (Invoice) generation and parsing."""

    def test_x12_850_order_parser_with_pid_and_ref(self):
        """Test parsing ANSI X12 850 with multiple line items, PID descriptions, and REF loops."""
        edi_text = (
            "ISA*00*          *00*          *ZZ*BUYER          *ZZ*SELLER         *260908*1000*U*00401*000000001*0*P*>~\n"
            "GS*PO*BUYER*SELLER*20260908*1000*1*X*004010~\n"
            "ST*850*0001~\n"
            "BEG*00*NE*PO-887766**20260908~\n"
            "CUR*BY*AED~\n"
            "REF*DP*FMCG-DAIRY~\n"
            "DTM*002*20260912~\n"
            "N1*BY*Lulu Supermarket*91*LULU-HQ~\n"
            "N1*ST*Store 42 Al Barsha*92*STORE-42~\n"
            "PO1*1*20*CA*45.00**CB*BUYER-SKU-1*UP*629104100001*VN*VEND-SKU-1~\n"
            "PID*F****Full Cream Milk 1L 12pk~\n"
            "PO1*2*10*EA*15.50**CB*BUYER-SKU-2*UP*629104100002*VN*VEND-SKU-2~\n"
            "PID*F****Cheddar Cheese 500g~\n"
            "CTT*2*30~\n"
            "SE*14*0001~\n"
            "GE*1*1~\n"
            "IEA*1*000000001~"
        )

        orders = parse_x12_850(edi_text)
        assert len(orders) == 1
        order = orders[0]
        assert order.header.po_number == "PO-887766"
        assert order.header.currency == "AED"
        assert order.header.buyer_name == "Lulu Supermarket"
        assert order.header.ship_to_id == "STORE-42"
        assert len(order.lines) == 2

        line1 = order.lines[0]
        assert line1.line_number == 1
        assert line1.ordered_qty == 20.0
        assert line1.ordered_uom == "CA"
        assert line1.ordered_price == 45.00
        assert line1.buyer_sku == "BUYER-SKU-1"
        assert line1.gtin == "629104100001"
        assert line1.description == "Full Cream Milk 1L 12pk"

        line2 = order.lines[1]
        assert line2.line_number == 2
        assert line2.ordered_qty == 10.0
        assert line2.ordered_price == 15.50

    def test_x12_856_asn_generator_and_parser_roundtrip(self):
        """Test generating ANSI X12 856 ASN and parsing back hierarchical levels."""
        header = EdiAsnShipmentHeader(
            delivery_id=1,
            delivery_number="DEL-001",
            sales_order_number="SO-100",
            buyer_po_number="PO-999",
            ship_date=date(2026, 9, 8),
            carrier_code="FEDEX",
            carrier_name="Federal Express",
            tracking_number="TRK-123456",
            total_pallets=1,
            total_boxes=2,
            total_weight_kg=150.0,
        )
        item = EdiAsnItemDetail(
            line_number=1,
            product_id=10,
            sku="NOVA-TEA-100",
            product_name="Black Tea Bags 100s",
            qty_shipped=50.0,
            qty_ordered=50.0,
            uom="CA",
            batch_number="LOT-2026A",
            expiry_date=date(2028, 9, 8),
        )
        pallet = EdiAsnPalletDetail(
            pallet_number="PLT-01",
            sscc_barcode="000614141999900013",
            gross_weight_kg=150.0,
            direct_items=[item],
        )
        doc = EdiAsnDocument(
            standard="ANSI_X12",
            document_type="856",
            control_number="0001",
            sender_id="NOVADIST",
            receiver_id="CARREFOUR",
            header=header,
            pallets=[pallet],
            direct_items=[],
        )

        edi_content = generate_x12_856(doc)
        assert "ST*856*" in edi_content
        assert "BSN*00*DEL-001*" in edi_content
        assert "HL*1**S~" in edi_content

        # Roundtrip parse
        parsed_doc = parse_x12_856(edi_content)
        assert parsed_doc.header.delivery_number == "DEL-001"
        assert parsed_doc.header.buyer_po_number == "PO-999"
        assert len(parsed_doc.pallets) == 1
        assert parsed_doc.pallets[0].sscc_barcode == "000614141999900013"

    def test_x12_810_invoice_generator_and_parser_roundtrip(self):
        """Test generating ANSI X12 810 Sales Invoice and parsing back line items and tax summary."""
        header = EdiInvoiceHeader(
            invoice_id=1,
            invoice_number="INV-2026-001",
            issue_date=date(2026, 9, 8),
            due_date=date(2026, 10, 8),
            delivery_number="DEL-001",
            sales_order_number="SO-100",
            buyer_po_number="PO-999",
            currency="USD",
            subtotal=1000.00,
            tax_amount=150.00,
            tax_rate_percent=15.00,
            freight_amount=25.00,
            discount_amount=10.00,
            grand_total=1165.00,
            seller_name="Nova Wholesale",
            seller_id="NOVA-HQ",
            buyer_name="Hypermarket Chain",
            buyer_id="HYPER-01",
        )
        line = EdiInvoiceLine(
            line_number=1,
            product_id=5,
            sku="NOVA-COFFEE-500G",
            product_name="Arabica Roast 500g",
            qty_invoiced=20.0,
            qty_delivered=20.0,
            qty_ordered=20.0,
            uom="CA",
            unit_price=50.00,
            gross_amount=1000.00,
            net_amount=1000.00,
            tax_amount=150.00,
            tax_rate_percent=15.00,
        )
        tax = EdiInvoiceTaxSummary(
            tax_type="VAT",
            tax_rate_percent=15.00,
            taxable_amount=1000.00,
            tax_amount=150.00,
        )
        charge = EdiInvoiceAllowanceCharge(
            indicator="C",
            code="D240",
            amount=25.00,
            description="Refrigerated Truck Freight",
        )
        doc = EdiInvoiceDocument(
            standard="ANSI_X12",
            document_type="810",
            control_number="0001",
            sender_id="NOVADIST",
            receiver_id="BUYER",
            header=header,
            lines=[line],
            taxes=[tax],
            allowances_charges=[charge],
        )

        edi_content = generate_x12_810(doc)
        assert "ST*810*" in edi_content
        assert "BIG*20260908*INV-2026-001*" in edi_content
        assert "IT1*1*20*CA*50" in edi_content
        assert "TDS*1165" in edi_content

        # Roundtrip parse
        parsed_inv = parse_x12_810(edi_content)
        assert parsed_inv.header.invoice_number == "INV-2026-001"
        assert parsed_inv.header.grand_total == 1165.00
        assert len(parsed_inv.lines) == 1
        assert parsed_inv.lines[0].qty_invoiced == 20.0
        assert parsed_inv.lines[0].unit_price == 50.00


# ===========================================================================
# 4. UN/EDIFACT ORDERS / DESADV / INVOIC Roundtrip & Parser Tests
# ===========================================================================

class TestUnEdifactParsersAndGenerators:
    """Tests for UN/EDIFACT ORDERS, DESADV, and INVOIC parsing and formatting."""

    def test_edifact_orders_parser_with_pia_and_imd(self):
        """Test parsing UN/EDIFACT ORDERS message with LIN/PIA/IMD/QTY/PRI loops."""
        edi_text = (
            "UNA:+.? '\n"
            "UNB+UNOA:2+CARREFOUR:ZZ+NOVADIST:ZZ+260908:1430+1001'\n"
            "UNH+M001+ORDERS:D:96A:UN:EAN008'\n"
            "BGM+220+CRF-ORD-5544+9'\n"
            "DTM+137:20260908:102'\n"
            "CUX+2:USD:4'\n"
            "NAD+BY+CRF-HQ::9++Carrefour Supermarkets'\n"
            "NAD+DP+STORE-DXB::9++Dubai Mall Branch'\n"
            "LIN+1++6291041009999:SRV'\n"
            "PIA+1+BUYER-ITEM-99:IN+VEND-ITEM-99:SA'\n"
            "IMD+F++:::Organic Extra Virgin Olive Oil 1L'\n"
            "QTY+21:30:CA'\n"
            "PRI+AAA:80.00:::NTP'\n"
            "MOA+203:2400.00'\n"
            "UNS+S'\n"
            "CNT+2:1'\n"
            "UNT+15+M001'\n"
            "UNZ+1+1001'"
        )

        orders = parse_edifact_orders(edi_text)
        assert len(orders) == 1
        order = orders[0]
        assert order.header.po_number == "CRF-ORD-5544"
        assert order.header.currency == "USD"
        assert order.header.buyer_id == "CRF-HQ"
        assert order.header.ship_to_id == "STORE-DXB"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.line_number == 1
        assert line.gtin == "6291041009999"
        assert line.buyer_sku == "BUYER-ITEM-99"
        assert line.vendor_sku == "VEND-ITEM-99"
        assert line.description == "Organic Extra Virgin Olive Oil 1L"
        assert line.ordered_qty == 30.0
        assert line.ordered_uom == "CA"
        assert line.ordered_price == 80.00

    def test_edifact_desadv_generator_and_parser_roundtrip(self):
        """Test generating UN/EDIFACT DESADV dispatch advice and parsing it back."""
        header = EdiAsnShipmentHeader(
            delivery_id=2,
            delivery_number="DES-2026-002",
            sales_order_number="SO-200",
            buyer_po_number="PO-LULU-77",
            ship_date=date(2026, 9, 8),
            carrier_code="ARAMEX",
            carrier_name="Aramex Logistics",
            tracking_number="AWB-998877",
            total_pallets=1,
            total_weight_kg=220.0,
        )
        item = EdiAsnItemDetail(
            line_number=1,
            product_id=20,
            sku="NOVA-FLOUR-10K",
            product_name="Wheat Flour 10kg Bag",
            qty_shipped=22.0,
            qty_ordered=22.0,
            uom="BAG",
            batch_number="BATCH-FL-99",
            expiry_date=date(2027, 3, 31),
        )
        pallet = EdiAsnPalletDetail(
            pallet_number="PLT-02",
            sscc_barcode="000614141999900020",
            gross_weight_kg=220.0,
            direct_items=[item],
        )
        doc = EdiAsnDocument(
            standard="EDIFACT",
            document_type="DESADV",
            control_number="0002",
            sender_id="NOVADIST",
            receiver_id="LULU",
            header=header,
            pallets=[pallet],
            direct_items=[],
        )

        edi_content = generate_edifact_desadv(doc)
        assert "UNH+" in edi_content
        assert "DESADV:D:96A:UN" in edi_content
        assert "BGM+351+DES-2026-002+9'" in edi_content

        # Roundtrip parse
        parsed_doc = parse_edifact_desadv(edi_content)
        assert parsed_doc.header.delivery_number == "DES-2026-002"
        assert parsed_doc.header.buyer_po_number == "PO-LULU-77"
        assert len(parsed_doc.pallets) == 1
        assert parsed_doc.pallets[0].sscc_barcode == "000614141999900020"

    def test_edifact_invoic_generator_and_parser_roundtrip(self):
        """Test generating UN/EDIFACT INVOIC message and parsing it back."""
        header = EdiInvoiceHeader(
            invoice_id=2,
            invoice_number="INV-EDIFACT-002",
            issue_date=date(2026, 9, 8),
            due_date=date(2026, 10, 8),
            delivery_number="DES-2026-002",
            sales_order_number="SO-200",
            buyer_po_number="PO-LULU-77",
            currency="AED",
            subtotal=2200.00,
            tax_amount=110.00,
            tax_rate_percent=5.00,
            freight_amount=50.00,
            discount_amount=0.00,
            grand_total=2360.00,
            seller_name="Nova Distributorship",
            seller_id="NOVADIST",
            buyer_name="Lulu Hypermarkets",
            buyer_id="LULU-HQ",
        )
        line = EdiInvoiceLine(
            line_number=1,
            product_id=20,
            sku="NOVA-FLOUR-10K",
            product_name="Wheat Flour 10kg Bag",
            qty_invoiced=22.0,
            qty_delivered=22.0,
            qty_ordered=22.0,
            uom="BAG",
            unit_price=100.00,
            gross_amount=2200.00,
            net_amount=2200.00,
            tax_amount=110.00,
            tax_rate_percent=5.00,
        )
        tax = EdiInvoiceTaxSummary(
            tax_type="VAT",
            tax_rate_percent=5.00,
            taxable_amount=2200.00,
            tax_amount=110.00,
        )
        doc = EdiInvoiceDocument(
            standard="EDIFACT",
            document_type="INVOIC",
            control_number="0002",
            sender_id="NOVADIST",
            receiver_id="LULU",
            header=header,
            lines=[line],
            taxes=[tax],
            allowances_charges=[],
        )

        edi_content = generate_edifact_invoic(doc)
        assert "UNH+" in edi_content
        assert "INVOIC:D:96A:UN" in edi_content
        assert "BGM+380+INV-EDIFACT-002+9'" in edi_content
        assert "MOA+77:2360" in edi_content

        # Roundtrip parse
        parsed_inv = parse_edifact_invoic(edi_content)
        assert parsed_inv.header.invoice_number == "INV-EDIFACT-002"
        assert parsed_inv.header.grand_total == 2360.00
        assert len(parsed_inv.lines) == 1
        assert parsed_inv.lines[0].qty_invoiced == 22.0
        assert parsed_inv.lines[0].unit_price == 100.00
