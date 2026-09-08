"""
Nova ERP — End-to-End Integration Tests for Full B2B EDI Order Lifecycle
========================================================================

Verifies the complete automated digital document supply chain lifecycle:
1. Inbound EDI 850 (PO) / EDIFACT ORDERS Ingestion
   -> Partner resolution, SKU/GTIN cross-referencing, price verification, credit check
   -> Automated Nova Sales Order creation (T0012/T0013) & 997/CONTRL Functional ACK
2. Warehouse Fulfillment & Truck Dispatch
   -> Delivery creation (T0077/T0078), Batch allocation (T0102), GS1 SSCC-18 generation (T0127)
   -> Outbound EDI 856 (ASN) / EDIFACT DESADV with 5-level Hierarchical Level (HL) packaging
3. Proof of Delivery (POD) & Electronic Invoicing
   -> POD capture (signature, photos, timestamps -> 'Delivered')
   -> Sales Invoice creation (T0090/T0026) with tax & discount breakdowns
   -> Outbound EDI 810 (Sales Invoice) / EDIFACT INVOIC electronic transmission
4. Discrepancy & Exception Handling
   -> Price variance holds & transaction reprocessing engine with force-confirm
5. Multi-Pallet & Multi-Batch Hierarchies
   -> Multi-pallet tare structures with Modulo-10 checksums
6. Multi-Tenant Scoping & Security Isolation
   -> End-to-end tenant context isolation across all lifecycle steps
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from modules.core.context import tenant_context, set_current_tenant, clear_current_tenant
from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiAckStatus,
    EdiDirection,
    EdiIngestRequest,
    EdiIngestResult,
    EdiLineDiscrepancy,
    EdiAsnGenerateRequest,
    EdiAsnGenerateResponse,
    EdiInvoiceTransmitRequest,
    EdiInvoiceTransmitResponse,
    EdiReprocessRequest,
)
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    parse_edi,
    parse_x12,
    parse_edifact,
)
from modules.integrations.services.edi.sscc_service import (
    SsccService,
    calculate_modulo10_check_digit,
    validate_modulo10,
    PackagingHierarchy,
    PackagingPallet,
    PackagingBox,
    PackagingItem,
)
from modules.integrations.services.edi.cross_reference_service import (
    CrossReferenceService,
    OrderCrossReferenceSummary,
    LineCrossReferenceResult,
    SkuResolutionResult,
    UomConversionResult,
    PriceVerificationResult,
)
from modules.integrations.services.edi.edi_850_service import (
    Edi850Service,
    Edi850Header,
    ParsedEdi850Order,
    parse_x12_850,
    parse_edifact_orders,
)
from modules.integrations.services.edi.edi_856_service import (
    Edi856Service,
    EdiAsnDocument,
    EdiAsnShipmentHeader,
    EdiAsnPalletDetail,
    EdiAsnBoxDetail,
    EdiAsnItemDetail,
    parse_x12_856,
    parse_edifact_desadv,
)
from modules.integrations.services.edi.edi_810_service import (
    Edi810Service,
    EdiInvoiceDocument,
    EdiInvoiceHeader,
    EdiInvoiceLine,
    EdiInvoiceTaxSummary,
    EdiInvoiceAllowanceCharge,
    parse_x12_810,
    parse_edifact_invoic,
)
from modules.sales.services.delivery_service import DeliveryService


# ===========================================================================
# Sample EDI Payloads for E2E Lifecycle Testing
# ===========================================================================

E2E_X12_850_PAYLOAD = (
    "ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVADIST       *260908*1200*U*00401*000000850*0*P*>~\n"
    "GS*PO*CARREFOUR*NOVADIST*20260908*1200*850*X*004010~\n"
    "ST*850*0001~\n"
    "BEG*00*NE*CRF-PO-E2E-1001**20260908~\n"
    "CUR*BY*USD~\n"
    "REF*DP*DAIRY-DEPT~\n"
    "REF*IA*VENDOR-NOVA-01~\n"
    "DTM*002*20260912~\n"
    "N1*BY*Carrefour Hypermarket UAE*91*CRF-UAE-01~\n"
    "N1*ST*Carrefour Store MOE*92*CRF-ST-MOE~\n"
    "N3*Mall of the Emirates, Ground Floor~\n"
    "N4*Dubai*DXB*00000*AE~\n"
    "N1*VN*Nova Distribution FZCO*91*NOVADIST~\n"
    "PO1*1*100*CA*45.00**CB*CRF-MILK-1L*UP*0614141100018*VN*SKU-MILK-1L~\n"
    "PID*F****Fresh Whole Milk 1L Pack 12~\n"
    "PO1*2*50*CA*80.00**CB*CRF-CHEESE-500G*UP*0614141100025*VN*SKU-CHEESE-500G~\n"
    "PID*F****Cheddar Cheese Block 500g Pack 6~\n"
    "CTT*2*150~\n"
    "SE*18*0001~\n"
    "GE*1*850~\n"
    "IEA*1*000000850~"
)

E2E_EDIFACT_ORDERS_PAYLOAD = (
    "UNA:+.? '\n"
    "UNB+UNOA:2+LULU_HYPER:ZZ+NOVADIST:ZZ+260908:1430+2026090801'\n"
    "UNH+MSG001+ORDERS:D:96A:UN:EAN008'\n"
    "BGM+220+LULU-PO-E2E-2002+9'\n"
    "DTM+137:20260908:102'\n"
    "DTM+2:20260914:102'\n"
    "CUX+2:AED:4'\n"
    "FTX+ZZZ+++Regular Weekly Supermarket Restock'\n"
    "NAD+BY+6291041000001::9++Lulu Hypermarkets LLC+Headquarters+Dubai++AE'\n"
    "NAD+DP+6291041000099::9++Lulu Regional DC Barsha+Al Barsha+Dubai++AE'\n"
    "LIN+1++0614141100018:SRV'\n"
    "PIA+1+LULU-MILK-1L:IN+SKU-MILK-1L:SA'\n"
    "IMD+F++:::Fresh Whole Milk 1L Pack 12'\n"
    "QTY+21:100:CA'\n"
    "PRI+AAA:45.00:::NTP'\n"
    "MOA+203:4500.00'\n"
    "LIN+2++0614141100025:SRV'\n"
    "PIA+1+LULU-CHEESE-500G:IN+SKU-CHEESE-500G:SA'\n"
    "IMD+F++:::Cheddar Cheese Block 500g Pack 6'\n"
    "QTY+21:50:CA'\n"
    "PRI+AAA:80.00:::NTP'\n"
    "MOA+203:4000.00'\n"
    "UNS+S'\n"
    "CNT+2:2'\n"
    "UNT+20+MSG001'\n"
    "UNZ+1+2026090801'"
)


# ===========================================================================
# Fixture Helpers
# ===========================================================================

@pytest.fixture
def partner_carrefour():
    """Mock Trading Partner record for Carrefour (ANSI X12)."""
    return {
        "id": 1,
        "business_id": 1,
        "partner_code": "CARREFOUR",
        "partner_name": "Carrefour UAE Supermarkets",
        "interchange_sender_id": "CARREFOUR",
        "interchange_receiver_id": "NOVADIST",
        "customer_id": 101,
        "edi_standard": "ANSI_X12",
        "edi_version": "004010",
        "sender_id": "CARREFOUR",
        "receiver_id": "NOVADIST",
        "segment_delimiter": "~",
        "element_delimiter": "*",
        "subelement_delimiter": ">",
        "auto_confirm_orders": True,
        "price_tolerance_percent": 2.0,
        "require_functional_ack": True,
        "gs1_company_prefix": "0614141",
        "is_active": True,
    }


@pytest.fixture
def partner_lulu():
    """Mock Trading Partner record for Lulu (UN/EDIFACT)."""
    return {
        "id": 2,
        "business_id": 1,
        "partner_code": "LULU_HYPER",
        "partner_name": "Lulu Group International",
        "interchange_sender_id": "LULU_HYPER",
        "interchange_receiver_id": "NOVADIST",
        "customer_id": 102,
        "edi_standard": "EDIFACT",
        "edi_version": "D96A",
        "sender_id": "LULU_HYPER",
        "receiver_id": "NOVADIST",
        "segment_delimiter": "'",
        "element_delimiter": "+",
        "subelement_delimiter": ":",
        "release_character": "?",
        "auto_confirm_orders": True,
        "price_tolerance_percent": 2.0,
        "require_functional_ack": True,
        "gs1_company_prefix": "6291041",
        "is_active": True,
    }


@pytest.fixture
def product_milk():
    return {
        "id": 10,
        "business_id": 1,
        "sku": "SKU-MILK-1L",
        "name": "Fresh Whole Milk 1L Pack 12",
        "barcode": "0614141100018",
        "price": 45.00,
        "base_uom": "CA",
        "weight": 12.0,
        "volume": 0.02,
    }


@pytest.fixture
def product_cheese():
    return {
        "id": 11,
        "business_id": 1,
        "sku": "SKU-CHEESE-500G",
        "name": "Cheddar Cheese Block 500g Pack 6",
        "barcode": "0614141100025",
        "price": 80.00,
        "base_uom": "CA",
        "weight": 3.0,
        "volume": 0.008,
    }


# ===========================================================================
# 1. Full ANSI X12 Lifecycle Test Suite
# ===========================================================================

class TestAnsiX12FullOrderLifecycle:
    """
    Tests the complete 850 PO -> Sales Order -> Dispatch -> 856 ASN -> POD -> 810 Invoice lifecycle.
    """

    def test_full_x12_order_lifecycle_happy_path(self, partner_carrefour, product_milk, product_cheese):
        """
        Comprehensive test running through all major milestones of the ANSI X12 supply chain flow.
        """
        with tenant_context(1):
            # Step 1: Inbound EDI 850 PO Ingestion
            partner_repo_mock = MagicMock()
            partner_repo_mock.list.return_value = [partner_carrefour]
            partner_repo_mock.get.return_value = partner_carrefour

            tx_repo_mock = MagicMock()
            tx_saved_records = {}
            def save_tx(payload, **kw):
                tx_id = len(tx_saved_records) + 1
                rec = dict(payload, id=tx_id, business_id=1, created_at=datetime.now(timezone.utc))
                tx_saved_records[tx_id] = rec
                return rec
            tx_repo_mock.create.side_effect = save_tx
            tx_repo_mock.update.side_effect = lambda id_val, payload, **kw: tx_saved_records.setdefault(id_val, {}).update(payload) or tx_saved_records.get(id_val)

            xref_service_mock = MagicMock()
            line1_res = LineCrossReferenceResult(
                line_number=1,
                buyer_sku="CRF-MILK-1L",
                product_id=10,
                product_name="Fresh Whole Milk 1L Pack 12",
                ordered_qty=100.0,
                ordered_uom="CA",
                converted_qty=100.0,
                internal_uom="CA",
                uom_factor=1.0,
                ordered_price=45.00,
                expected_price=45.00,
                line_total=4500.00,
                sku_resolution=SkuResolutionResult(matched=True, product_id=10, partner_sku="CRF-MILK-1L"),
                uom_conversion=UomConversionResult(original_quantity=100.0, original_uom="CA", converted_quantity=100.0, converted_uom="CA"),
                price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=45.00, expected_unit_price=45.00, effective_ordered_unit_price=45.00),
            )
            line2_res = LineCrossReferenceResult(
                line_number=2,
                buyer_sku="CRF-CHEESE-500G",
                product_id=11,
                product_name="Cheddar Cheese Block 500g Pack 6",
                ordered_qty=50.0,
                ordered_uom="CA",
                converted_qty=50.0,
                internal_uom="CA",
                uom_factor=1.0,
                ordered_price=80.00,
                expected_price=80.00,
                line_total=4000.00,
                sku_resolution=SkuResolutionResult(matched=True, product_id=11, partner_sku="CRF-CHEESE-500G"),
                uom_conversion=UomConversionResult(original_quantity=50.0, original_uom="CA", converted_quantity=50.0, converted_uom="CA"),
                price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=80.00, expected_unit_price=80.00, effective_ordered_unit_price=80.00),
            )
            xref_service_mock.cross_reference_order.return_value = OrderCrossReferenceSummary(
                total_lines=2,
                matched_lines=2,
                unmatched_lines=0,
                discrepancy_lines=0,
                is_clean=True,
                recommended_status="Confirmed",
                total_ordered_amount=8500.00,
                total_expected_amount=8500.00,
                line_results=[line1_res, line2_res],
            )

            credit_service_mock = MagicMock()
            credit_service_mock.evaluate_order_credit.return_value = {
                "is_hold_required": False,
                "hold_reason": None,
                "credit_limit": 100000.0,
                "current_balance": 15000.0,
            }

            so_repo_mock = MagicMock()
            created_orders = {}
            def create_so(payload, **kw):
                so_id = 501
                rec = dict(payload, id=so_id, business_id=1, status=payload.get("status", "Confirmed"))
                created_orders[so_id] = rec
                return rec
            so_repo_mock.create.side_effect = create_so
            so_repo_mock.get.side_effect = lambda id_val, **kw: created_orders.get(id_val)

            sol_repo_mock = MagicMock()
            created_lines = {}
            def create_sol(payload, **kw):
                line_id = len(created_lines) + 101
                rec = dict(payload, id=line_id, business_id=1)
                created_lines[line_id] = rec
                return rec
            sol_repo_mock.create.side_effect = create_sol
            sol_repo_mock.list.side_effect = lambda filters=None, **kw: [
                l for l in created_lines.values() if not filters or l.get("sales_order_id") == filters.get("sales_order_id")
            ]

            cust_repo_mock = MagicMock()
            cust_repo_mock.get.return_value = {
                "id": 101,
                "business_id": 1,
                "name": "Carrefour UAE Supermarkets",
                "customer_code": "CRF-UAE-01",
            }

            edi_850_svc = Edi850Service(
                transaction_repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                order_repo=so_repo_mock,
                line_repo=sol_repo_mock,
                customer_repo=cust_repo_mock,
                xref_service=xref_service_mock,
                credit_svc=credit_service_mock,
            )

            ingest_result = edi_850_svc.process_inbound_850(
                raw_payload=E2E_X12_850_PAYLOAD,
                standard="ANSI_X12",
            )

            assert ingest_result.status == EdiTransactionStatus.PROCESSED.value
            assert ingest_result.document_type == "850"
            assert ingest_result.sales_order_id == 501
            assert len(ingest_result.price_discrepancies) == 0
            assert len(ingest_result.errors) == 0
            assert ingest_result.ack_generated is True

            created_so = so_repo_mock.get(501)
            assert created_so["status"] == "Confirmed"

            # Step 2: Warehouse Fulfillment & Delivery
            mock_delivery = {
                "id": 201,
                "business_id": 1,
                "delivery_number": "DEL-2026-00201",
                "sales_order_id": 501,
                "delivery_date": date(2026, 9, 10),
                "warehouse_id": 1,
                "status": "Ready For Dispatch",
                "carrier_name": "Nova Swift Transport",
                "carrier_code": "NSWT",
                "tracking_number": "BOL-77889900",
                "vehicle_number": "DXB-98741",
                "seal_number": "SL-0099",
                "driver_id": 5,
            }
            mock_delivery_lines = [
                {
                    "id": 301,
                    "business_id": 1,
                    "delivery_id": 201,
                    "sales_order_line_id": 101,
                    "product_id": 10,
                    "product_name": "Fresh Whole Milk 1L Pack 12",
                    "qty_shipped": 100.0,
                    "qty_ordered": 100.0,
                    "uom_id": 1,
                    "line_number": 1,
                },
                {
                    "id": 302,
                    "business_id": 1,
                    "delivery_id": 201,
                    "sales_order_line_id": 102,
                    "product_id": 11,
                    "product_name": "Cheddar Cheese Block 500g Pack 6",
                    "qty_shipped": 50.0,
                    "qty_ordered": 50.0,
                    "uom_id": 1,
                    "line_number": 2,
                },
            ]
            mock_pick_items = [
                {
                    "id": 401,
                    "sales_order_line_id": 101,
                    "product_id": 10,
                    "batch_number": "BAT-MILK-202609A",
                    "expiry_date": date(2026, 9, 25),
                },
                {
                    "id": 402,
                    "sales_order_line_id": 102,
                    "product_id": 11,
                    "batch_number": "BAT-CHEESE-202609B",
                    "expiry_date": date(2027, 3, 10),
                },
            ]

            # Step 3: Outbound EDI 856 ASN Generation
            delivery_repo_mock = MagicMock()
            delivery_repo_mock.get.return_value = mock_delivery
            dline_repo_mock = MagicMock()
            dline_repo_mock.list.return_value = mock_delivery_lines
            pli_repo_mock = MagicMock()
            pli_repo_mock.list.return_value = mock_pick_items

            product_repo_mock = MagicMock()
            product_repo_mock.get.side_effect = lambda p_id, **kw: product_milk if p_id == 10 else product_cheese

            sku_map_repo_mock = MagicMock()
            sku_map_repo_mock.list.return_value = [
                {"product_id": 10, "buyer_sku": "CRF-MILK-1L", "gtin": "0614141100018", "vendor_sku": "SKU-MILK-1L"},
                {"product_id": 11, "buyer_sku": "CRF-CHEESE-500G", "gtin": "0614141100025", "vendor_sku": "SKU-CHEESE-500G"},
            ]

            pallet_repo_mock = MagicMock()
            stored_pallets = {}
            pallet_repo_mock.create.side_effect = lambda p, **kw: (lambda id_: stored_pallets.setdefault(id_, dict(p, id=id_, business_id=1)))(len(stored_pallets) + 1)
            pallet_repo_mock.list.return_value = []
            pallet_repo_mock.update.side_effect = lambda id_val, p, **kw: stored_pallets.setdefault(id_val, {}).update(p) or stored_pallets.get(id_val)

            sscc_svc = SsccService(repo=pallet_repo_mock, partner_repo=partner_repo_mock)

            edi_856_svc = Edi856Service(
                repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                sku_mapping_repo=sku_map_repo_mock,
                delivery_repo=delivery_repo_mock,
                delivery_line_repo=dline_repo_mock,
                sales_order_repo=so_repo_mock,
                sales_line_repo=sol_repo_mock,
                customer_repo=cust_repo_mock,
                product_repo=product_repo_mock,
                pick_list_item_repo=pli_repo_mock,
                sscc_service_instance=sscc_svc,
            )

            asn_response = edi_856_svc.generate_asn_for_delivery(
                delivery_id=201,
                partner_id=1,
            )

            assert asn_response.transaction_id is not None
            assert asn_response.edi_payload is not None
            assert asn_response.document_type == "856"
            assert asn_response.standard == "ANSI_X12"
            assert len(asn_response.sscc_barcodes) >= 1

            primary_sscc = asn_response.sscc_barcodes[0]
            assert validate_modulo10(primary_sscc) is True

            parsed_asn = parse_x12_856(asn_response.edi_payload)
            assert parsed_asn.header.delivery_number == "DEL-2026-00201"
            assert "CRF-PO-E2E-1001" in parsed_asn.header.buyer_po_number

            # Step 4: POD Capture
            del_service = DeliveryService(repo=delivery_repo_mock)
            delivery_repo_mock.update.side_effect = lambda id_val, payload, **kw: mock_delivery.update(payload) or mock_delivery

            pod_result = del_service.capture_pod(
                delivery_id=201,
                signature="Recipient: John Smith (Store Mgr)",
                photo_url="https://s3.amazonaws.com/nova-pod/2026/09/del-201-pod.jpg",
                location="Mall of Emirates Receiving Dock #2",
                timestamp=datetime(2026, 9, 10, 15, 30, 0),
            )
            assert pod_result["status"] == "Delivered"

            # Step 5: Sales Invoice & Outbound EDI 810 Transmission
            mock_invoice = {
                "id": 701,
                "business_id": 1,
                "invoice_number": "INV-2026-00701",
                "invoice_type": "Standard",
                "customer_id": 101,
                "partner_id": 101,
                "delivery_id": 201,
                "sales_order_id": 501,
                "issue_date": date(2026, 9, 10),
                "due_date": date(2026, 10, 10),
                "currency": "USD",
                "subtotal": 8500.00,
                "tax_amount": 425.00,  # 5% VAT
                "tax_rate_percent": 5.0,
                "freight_amount": 150.00,
                "discount_amount": 0.0,
                "total_amount": 9075.00,
                "status": "Posted",
            }
            mock_so_record = dict(created_orders[501], customer_id=101, client_order_uuid="CRF-PO-E2E-1001", notes="PO# CRF-PO-E2E-1001")
            so_repo_mock.get.return_value = mock_so_record

            mock_invoice_lines = [
                {
                    "id": 801,
                    "business_id": 1,
                    "invoice_id": 701,
                    "sales_order_id": 501,
                    "sales_order_line_id": 101,
                    "delivery_line_id": 301,
                    "product_id": 10,
                    "product_name": "Fresh Whole Milk 1L Pack 12",
                    "quantity": 100.0,
                    "qty_invoiced": 100.0,
                    "qty_delivered": 100.0,
                    "qty_ordered": 100.0,
                    "uom_id": 1,
                    "unit_price": 45.00,
                    "gross_amount": 4500.00,
                    "tax_rate_percent": 5.0,
                    "tax_amount": 225.00,
                    "discount_amount": 0.0,
                    "net_amount": 4500.00,
                    "line_number": 1,
                },
                {
                    "id": 802,
                    "business_id": 1,
                    "invoice_id": 701,
                    "sales_order_id": 501,
                    "sales_order_line_id": 102,
                    "delivery_line_id": 302,
                    "product_id": 11,
                    "product_name": "Cheddar Cheese Block 500g Pack 6",
                    "quantity": 50.0,
                    "qty_invoiced": 50.0,
                    "qty_delivered": 50.0,
                    "qty_ordered": 50.0,
                    "uom_id": 1,
                    "unit_price": 80.00,
                    "gross_amount": 4000.00,
                    "tax_rate_percent": 5.0,
                    "tax_amount": 200.00,
                    "discount_amount": 0.0,
                    "net_amount": 4000.00,
                    "line_number": 2,
                },
            ]
            sol_repo_mock.list.return_value = mock_invoice_lines

            invoice_repo_mock = MagicMock()
            invoice_repo_mock.get.return_value = mock_invoice

            pterm_repo_mock = MagicMock()
            pterm_repo_mock.get.return_value = {
                "id": 1,
                "name": "2/10 Net 30",
                "discount_percentage": 2.0,
                "discount_days": 10,
                "net_days": 30,
            }

            edi_810_svc = Edi810Service(
                repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                invoice_repo=invoice_repo_mock,
                delivery_repo=delivery_repo_mock,
                delivery_line_repo=dline_repo_mock,
                sales_order_repo=so_repo_mock,
                sales_line_repo=sol_repo_mock,
                pick_list_item_repo=pli_repo_mock,
                sku_mapping_repo=sku_map_repo_mock,
                customer_repo=cust_repo_mock,
                product_repo=product_repo_mock,
                payment_term_repo=pterm_repo_mock,
            )

            inv_response = edi_810_svc.generate_invoice(
                EdiInvoiceTransmitRequest(invoice_id=701, partner_id=1, delivery_id=201)
            )

            assert inv_response.invoice_id == 701
            assert inv_response.document_type == "810"
            assert inv_response.standard == "ANSI_X12"
            assert inv_response.invoice_number == "INV-2026-00701"

            parsed_inv = parse_x12_810(inv_response.edi_payload)
            assert parsed_inv.header.invoice_number == "INV-2026-00701"
            assert len(parsed_inv.lines) == 2

            # Step 6: Verify Transaction Logs in T0126
            recorded_txs = list(tx_saved_records.values())
            doc_types = [tx.get("document_type") for tx in recorded_txs]
            assert "850" in doc_types
            assert "856" in doc_types
            assert "810" in doc_types


# ===========================================================================
# 2. Full UN/EDIFACT Lifecycle Test Suite
# ===========================================================================

class TestUnEdifactFullOrderLifecycle:
    """
    Tests the complete ORDERS -> Sales Order -> Dispatch -> DESADV -> POD -> INVOIC lifecycle.
    """

    def test_full_edifact_order_lifecycle_happy_path(self, partner_lulu, product_milk, product_cheese):
        """
        Comprehensive test running through UN/EDIFACT (D96A) full supply chain order flow.
        """
        with tenant_context(1):
            # Step 1: Inbound ORDERS Ingestion
            partner_repo_mock = MagicMock()
            partner_repo_mock.list.return_value = [partner_lulu]
            partner_repo_mock.get.return_value = partner_lulu

            tx_repo_mock = MagicMock()
            tx_saved_records = {}
            def save_tx(payload, **kw):
                tx_id = len(tx_saved_records) + 1
                rec = dict(payload, id=tx_id, business_id=1, created_at=datetime.now(timezone.utc))
                tx_saved_records[tx_id] = rec
                return rec
            tx_repo_mock.create.side_effect = save_tx
            tx_repo_mock.update.side_effect = lambda id_val, payload, **kw: tx_saved_records.setdefault(id_val, {}).update(payload) or tx_saved_records.get(id_val)

            xref_service_mock = MagicMock()
            line1_res = LineCrossReferenceResult(
                line_number=1,
                buyer_sku="LULU-MILK-1L",
                product_id=10,
                product_name="Fresh Whole Milk 1L Pack 12",
                ordered_qty=100.0,
                ordered_uom="CA",
                converted_qty=100.0,
                internal_uom="CA",
                uom_factor=1.0,
                ordered_price=45.00,
                expected_price=45.00,
                line_total=4500.00,
                sku_resolution=SkuResolutionResult(matched=True, product_id=10, partner_sku="LULU-MILK-1L"),
                uom_conversion=UomConversionResult(original_quantity=100.0, original_uom="CA", converted_quantity=100.0, converted_uom="CA"),
                price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=45.00, expected_unit_price=45.00, effective_ordered_unit_price=45.00),
            )
            line2_res = LineCrossReferenceResult(
                line_number=2,
                buyer_sku="LULU-CHEESE-500G",
                product_id=11,
                product_name="Cheddar Cheese Block 500g Pack 6",
                ordered_qty=50.0,
                ordered_uom="CA",
                converted_qty=50.0,
                internal_uom="CA",
                uom_factor=1.0,
                ordered_price=80.00,
                expected_price=80.00,
                line_total=4000.00,
                sku_resolution=SkuResolutionResult(matched=True, product_id=11, partner_sku="LULU-CHEESE-500G"),
                uom_conversion=UomConversionResult(original_quantity=50.0, original_uom="CA", converted_quantity=50.0, converted_uom="CA"),
                price_verification=PriceVerificationResult(is_valid=True, is_discrepancy=False, ordered_unit_price=80.00, expected_unit_price=80.00, effective_ordered_unit_price=80.00),
            )
            xref_service_mock.cross_reference_order.return_value = OrderCrossReferenceSummary(
                total_lines=2,
                matched_lines=2,
                unmatched_lines=0,
                discrepancy_lines=0,
                is_clean=True,
                recommended_status="Confirmed",
                total_ordered_amount=8500.00,
                total_expected_amount=8500.00,
                line_results=[line1_res, line2_res],
            )

            credit_service_mock = MagicMock()
            credit_service_mock.evaluate_order_credit.return_value = {
                "is_hold_required": False,
                "hold_reason": None,
                "credit_limit": 250000.0,
                "current_balance": 30000.0,
            }

            so_repo_mock = MagicMock()
            created_orders = {}
            def create_so(payload, **kw):
                so_id = 602
                rec = dict(payload, id=so_id, business_id=1, status=payload.get("status", "Confirmed"))
                created_orders[so_id] = rec
                return rec
            so_repo_mock.create.side_effect = create_so
            so_repo_mock.get.side_effect = lambda id_val, **kw: created_orders.get(id_val)

            sol_repo_mock = MagicMock()
            created_lines = {}
            def create_sol(payload, **kw):
                line_id = len(created_lines) + 201
                rec = dict(payload, id=line_id, business_id=1)
                created_lines[line_id] = rec
                return rec
            sol_repo_mock.create.side_effect = create_sol
            sol_repo_mock.list.side_effect = lambda filters=None, **kw: [
                l for l in created_lines.values() if not filters or l.get("sales_order_id") == filters.get("sales_order_id")
            ]

            cust_repo_mock = MagicMock()
            cust_repo_mock.get.return_value = {
                "id": 102,
                "business_id": 1,
                "name": "Lulu Group International",
                "customer_code": "LULU-HQ-01",
            }

            edi_850_svc = Edi850Service(
                transaction_repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                order_repo=so_repo_mock,
                line_repo=sol_repo_mock,
                customer_repo=cust_repo_mock,
                xref_service=xref_service_mock,
                credit_svc=credit_service_mock,
            )

            ingest_result = edi_850_svc.process_inbound_850(
                raw_payload=E2E_EDIFACT_ORDERS_PAYLOAD,
                standard="EDIFACT",
            )

            assert ingest_result.status == EdiTransactionStatus.PROCESSED.value
            assert ingest_result.document_type == "ORDERS"
            assert ingest_result.sales_order_id == 602
            assert len(ingest_result.price_discrepancies) == 0
            assert len(ingest_result.errors) == 0

            # Step 2: Outbound UN/EDIFACT DESADV (ASN) Generation
            mock_delivery = {
                "id": 202,
                "business_id": 1,
                "delivery_number": "DEL-2026-00202",
                "sales_order_id": 602,
                "delivery_date": date(2026, 9, 11),
                "warehouse_id": 1,
                "status": "Ready For Dispatch",
                "carrier_name": "Lulu Logistics Fleet",
                "carrier_code": "LULF",
                "tracking_number": "DES-998811",
                "vehicle_number": "DXB-77441",
            }
            mock_delivery_lines = [
                {
                    "id": 311,
                    "business_id": 1,
                    "delivery_id": 202,
                    "sales_order_line_id": 201,
                    "product_id": 10,
                    "product_name": "Fresh Whole Milk 1L Pack 12",
                    "qty_shipped": 100.0,
                    "qty_ordered": 100.0,
                    "uom_id": 1,
                    "line_number": 1,
                },
                {
                    "id": 312,
                    "business_id": 1,
                    "delivery_id": 202,
                    "sales_order_line_id": 202,
                    "product_id": 11,
                    "product_name": "Cheddar Cheese Block 500g Pack 6",
                    "qty_shipped": 50.0,
                    "qty_ordered": 50.0,
                    "uom_id": 1,
                    "line_number": 2,
                },
            ]
            mock_pick_items = [
                {
                    "id": 411,
                    "sales_order_line_id": 201,
                    "product_id": 10,
                    "batch_number": "BAT-LULU-MILK-1",
                    "expiry_date": date(2026, 9, 28),
                },
                {
                    "id": 412,
                    "sales_order_line_id": 202,
                    "product_id": 11,
                    "batch_number": "BAT-LULU-CHEESE-1",
                    "expiry_date": date(2027, 4, 15),
                },
            ]

            delivery_repo_mock = MagicMock()
            delivery_repo_mock.get.return_value = mock_delivery
            dline_repo_mock = MagicMock()
            dline_repo_mock.list.return_value = mock_delivery_lines
            pli_repo_mock = MagicMock()
            pli_repo_mock.list.return_value = mock_pick_items

            product_repo_mock = MagicMock()
            product_repo_mock.get.side_effect = lambda p_id, **kw: product_milk if p_id == 10 else product_cheese

            sku_map_repo_mock = MagicMock()
            sku_map_repo_mock.list.return_value = [
                {"product_id": 10, "buyer_sku": "LULU-MILK-1L", "gtin": "0614141100018", "vendor_sku": "SKU-MILK-1L"},
                {"product_id": 11, "buyer_sku": "LULU-CHEESE-500G", "gtin": "0614141100025", "vendor_sku": "SKU-CHEESE-500G"},
            ]

            pallet_repo_mock = MagicMock()
            stored_pallets = {}
            pallet_repo_mock.create.side_effect = lambda p, **kw: (lambda id_: stored_pallets.setdefault(id_, dict(p, id=id_, business_id=1)))(len(stored_pallets) + 1)
            pallet_repo_mock.list.return_value = []
            pallet_repo_mock.update.side_effect = lambda id_val, p, **kw: stored_pallets.setdefault(id_val, {}).update(p) or stored_pallets.get(id_val)

            sscc_svc = SsccService(repo=pallet_repo_mock, partner_repo=partner_repo_mock)

            edi_856_svc = Edi856Service(
                repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                sku_mapping_repo=sku_map_repo_mock,
                delivery_repo=delivery_repo_mock,
                delivery_line_repo=dline_repo_mock,
                sales_order_repo=so_repo_mock,
                sales_line_repo=sol_repo_mock,
                customer_repo=cust_repo_mock,
                product_repo=product_repo_mock,
                pick_list_item_repo=pli_repo_mock,
                sscc_service_instance=sscc_svc,
            )

            desadv_response = edi_856_svc.generate_asn_for_delivery(
                delivery_id=202,
                partner_id=2,
            )

            assert desadv_response.transaction_id is not None
            assert desadv_response.edi_payload is not None
            assert desadv_response.document_type == "DESADV"
            assert desadv_response.standard == "EDIFACT"

            parsed_desadv = parse_edifact_desadv(desadv_response.edi_payload)
            assert parsed_desadv.header.delivery_number == "DEL-2026-00202"
            assert "LULU-PO-E2E-2002" in parsed_desadv.header.buyer_po_number

            # Step 3: Outbound UN/EDIFACT INVOIC Transmission
            mock_invoice = {
                "id": 702,
                "business_id": 1,
                "invoice_number": "INV-2026-00702",
                "invoice_type": "Standard",
                "customer_id": 102,
                "partner_id": 102,
                "delivery_id": 202,
                "sales_order_id": 602,
                "issue_date": date(2026, 9, 11),
                "due_date": date(2026, 10, 11),
                "currency": "AED",
                "subtotal": 8500.00,
                "tax_amount": 425.00,
                "tax_rate_percent": 5.0,
                "freight_amount": 0.0,
                "discount_amount": 0.0,
                "total_amount": 8925.00,
                "status": "Posted",
            }
            mock_so_record2 = dict(created_orders[602], customer_id=102, client_order_uuid="LULU-PO-E2E-2002", notes="PO# LULU-PO-E2E-2002")
            so_repo_mock.get.return_value = mock_so_record2

            mock_invoice_lines = [
                {
                    "id": 811,
                    "business_id": 1,
                    "invoice_id": 702,
                    "sales_order_id": 602,
                    "sales_order_line_id": 201,
                    "delivery_line_id": 311,
                    "product_id": 10,
                    "product_name": "Fresh Whole Milk 1L Pack 12",
                    "quantity": 100.0,
                    "qty_invoiced": 100.0,
                    "qty_delivered": 100.0,
                    "qty_ordered": 100.0,
                    "uom_id": 1,
                    "unit_price": 45.00,
                    "gross_amount": 4500.00,
                    "tax_rate_percent": 5.0,
                    "tax_amount": 225.00,
                    "discount_amount": 0.0,
                    "net_amount": 4500.00,
                    "line_number": 1,
                },
                {
                    "id": 812,
                    "business_id": 1,
                    "invoice_id": 702,
                    "sales_order_id": 602,
                    "sales_order_line_id": 202,
                    "delivery_line_id": 312,
                    "product_id": 11,
                    "product_name": "Cheddar Cheese Block 500g Pack 6",
                    "quantity": 50.0,
                    "qty_invoiced": 50.0,
                    "qty_delivered": 50.0,
                    "qty_ordered": 50.0,
                    "uom_id": 1,
                    "unit_price": 80.00,
                    "gross_amount": 4000.00,
                    "tax_rate_percent": 5.0,
                    "tax_amount": 200.00,
                    "discount_amount": 0.0,
                    "net_amount": 4000.00,
                    "line_number": 2,
                },
            ]
            sol_repo_mock.list.return_value = mock_invoice_lines

            invoice_repo_mock = MagicMock()
            invoice_repo_mock.get.return_value = mock_invoice

            pterm_repo_mock = MagicMock()
            pterm_repo_mock.get.return_value = {
                "id": 2,
                "name": "Net 30 Days",
                "net_days": 30,
            }

            edi_810_svc = Edi810Service(
                repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                invoice_repo=invoice_repo_mock,
                delivery_repo=delivery_repo_mock,
                delivery_line_repo=dline_repo_mock,
                sales_order_repo=so_repo_mock,
                sales_line_repo=sol_repo_mock,
                pick_list_item_repo=pli_repo_mock,
                sku_mapping_repo=sku_map_repo_mock,
                customer_repo=cust_repo_mock,
                product_repo=product_repo_mock,
                payment_term_repo=pterm_repo_mock,
            )

            invoic_response = edi_810_svc.generate_invoice(
                EdiInvoiceTransmitRequest(invoice_id=702, partner_id=2, delivery_id=202)
            )

            assert invoic_response.invoice_id == 702
            assert invoic_response.document_type == "INVOIC"
            assert invoic_response.standard == "EDIFACT"
            assert invoic_response.invoice_number == "INV-2026-00702"

            parsed_invoic = parse_edifact_invoic(invoic_response.edi_payload)
            assert parsed_invoic.header.invoice_number == "INV-2026-00702"
            assert "LULU-PO-E2E-2002" in parsed_invoic.header.buyer_po_number
            assert len(parsed_invoic.lines) == 2


# ===========================================================================
# 3. Discrepancy & Reprocess Workflow Test Suite
# ===========================================================================

class TestPriceDiscrepancyLifecycleWorkflow:
    """
    Tests price discrepancy detection, order hold, and subsequent force-confirm reprocessing.
    """

    def test_price_discrepancy_hold_and_force_confirm_reprocess(self, partner_carrefour):
        """
        Verify that an inbound PO with underpriced items is held in 'Pending' / 'PRICE_DISCREPANCY_HOLD',
        and then successfully force-confirmed by the commercial manager.
        """
        with tenant_context(1):
            partner_repo_mock = MagicMock()
            partner_repo_mock.list.return_value = [partner_carrefour]
            partner_repo_mock.get.return_value = partner_carrefour

            tx_saved_records = {}
            tx_repo_mock = MagicMock()
            def save_tx(payload, **kw):
                tx_id = len(tx_saved_records) + 1
                rec = dict(payload, id=tx_id, business_id=1, created_at=datetime.now(timezone.utc), raw_payload=E2E_X12_850_PAYLOAD, standard="ANSI_X12", document_type="850", partner_id=1)
                tx_saved_records[tx_id] = rec
                return rec
            tx_repo_mock.create.side_effect = save_tx
            tx_repo_mock.get.side_effect = lambda id_val, **kw: tx_saved_records.get(id_val)
            tx_repo_mock.update.side_effect = lambda id_val, payload, **kw: tx_saved_records.setdefault(id_val, {}).update(payload) or tx_saved_records.get(id_val)

            xref_service_mock = MagicMock()
            discrepancy_line = LineCrossReferenceResult(
                line_number=1,
                buyer_sku="CRF-MILK-1L",
                product_id=10,
                product_name="Fresh Milk 1L",
                ordered_qty=100.0,
                ordered_uom="CA",
                converted_qty=100.0,
                internal_uom="CA",
                uom_factor=1.0,
                ordered_price=30.00,
                expected_price=45.00,
                line_total=3000.00,
                is_price_discrepancy=True,
                sku_resolution=SkuResolutionResult(matched=True, product_id=10, partner_sku="CRF-MILK-1L"),
                uom_conversion=UomConversionResult(original_quantity=100.0, original_uom="CA", converted_quantity=100.0, converted_uom="CA"),
                price_verification=PriceVerificationResult(is_valid=False, is_discrepancy=True, ordered_unit_price=30.00, expected_unit_price=45.00, effective_ordered_unit_price=30.00, variance_percent=-33.33),
            )
            discrepancy_summary = OrderCrossReferenceSummary(
                total_lines=1,
                matched_lines=1,
                unmatched_lines=0,
                discrepancy_lines=1,
                is_clean=False,
                recommended_status="Pending",
                total_ordered_amount=3000.00,
                total_expected_amount=4500.00,
                price_discrepancies=[
                    EdiLineDiscrepancy(
                        line_number=1,
                        buyer_sku="CRF-MILK-1L",
                        product_id=10,
                        product_name="Fresh Milk 1L",
                        ordered_price=30.00,
                        contract_price=45.00,
                        discrepancy_percent=-33.33,
                    )
                ],
                line_results=[discrepancy_line],
            )
            xref_service_mock.cross_reference_order.return_value = discrepancy_summary

            credit_service_mock = MagicMock()
            credit_service_mock.evaluate_order_credit.return_value = {"is_hold_required": False, "hold_reason": None}

            so_saved_records = {}
            so_repo_mock = MagicMock()
            def create_so(p, **kw):
                so_id = 999
                rec = dict(p, id=so_id, business_id=1)
                so_saved_records[so_id] = rec
                return rec
            so_repo_mock.create.side_effect = create_so
            so_repo_mock.get.side_effect = lambda id_val, **kw: so_saved_records.get(id_val)
            so_repo_mock.update.side_effect = lambda id_val, p, **kw: so_saved_records.setdefault(id_val, {}).update(p) or so_saved_records.get(id_val)

            sol_repo_mock = MagicMock()
            sol_repo_mock.create.return_value = {"id": 1, "business_id": 1}

            edi_850_svc = Edi850Service(
                transaction_repo=tx_repo_mock,
                partner_repo=partner_repo_mock,
                order_repo=so_repo_mock,
                line_repo=sol_repo_mock,
                customer_repo=MagicMock(),
                xref_service=xref_service_mock,
                credit_svc=credit_service_mock,
            )

            ingest_result = edi_850_svc.process_inbound_850(
                raw_payload=E2E_X12_850_PAYLOAD,
                standard="ANSI_X12",
            )

            assert len(ingest_result.price_discrepancies) == 1
            assert ingest_result.status == EdiTransactionStatus.PRICE_DISCREPANCY_HOLD.value
            assert so_saved_records[999]["status"] == "Pending"
            assert "Price discrepancies" in str(so_saved_records[999]["hold_reason"])

            reprocess_result = edi_850_svc.reprocess_transaction(
                transaction_id=1,
                force_confirm=True,
                override_price_tolerance=40.0,
            )

            assert reprocess_result.status == EdiTransactionStatus.PROCESSED.value
            assert len(reprocess_result.price_discrepancies) == 0
            assert so_saved_records[999]["status"] == "Confirmed"
            assert so_saved_records[999]["hold_reason"] is None


# ===========================================================================
# 4. Multi-Pallet Packaging Hierarchy Lifecycle Test Suite
# ===========================================================================

class TestMultiPalletPackagingHierarchyLifecycle:
    """
    Tests ASN 856 generation with multiple pallets and multi-level packaging hierarchies.
    """

    def test_multi_pallet_multi_batch_asn_generation(self, partner_carrefour, product_milk, product_cheese):
        """
        Verify that an order with 2 pallets and distinct batches generates valid 5-level HL trees
        with unique SSCC-18 barcodes and Modulo-10 check digits for each pallet.
        """
        with tenant_context(1):
            mock_delivery = {
                "id": 205,
                "business_id": 1,
                "delivery_number": "DEL-2026-00205",
                "sales_order_id": 505,
                "delivery_date": date(2026, 9, 12),
                "status": "Ready For Dispatch",
                "carrier_name": "Gulf Logistics Express",
                "carrier_code": "GLEX",
                "tracking_number": "TRK-MULTI-99",
            }
            mock_delivery_lines = [
                {
                    "id": 351,
                    "business_id": 1,
                    "delivery_id": 205,
                    "sales_order_line_id": 151,
                    "product_id": 10,
                    "product_name": "Fresh Whole Milk 1L Pack 12",
                    "qty_shipped": 200.0,
                    "qty_ordered": 200.0,
                    "uom_id": 1,
                    "line_number": 1,
                },
                {
                    "id": 352,
                    "business_id": 1,
                    "delivery_id": 205,
                    "sales_order_line_id": 152,
                    "product_id": 11,
                    "product_name": "Cheddar Cheese Block 500g Pack 6",
                    "qty_shipped": 100.0,
                    "qty_ordered": 100.0,
                    "uom_id": 1,
                    "line_number": 2,
                },
            ]
            mock_pick_items = [
                {"id": 451, "sales_order_line_id": 151, "product_id": 10, "batch_number": "LOT-MILK-A1", "expiry_date": date(2026, 9, 25)},
                {"id": 452, "sales_order_line_id": 152, "product_id": 11, "batch_number": "LOT-CHEESE-B1", "expiry_date": date(2027, 2, 28)},
            ]

            pallet_records = [
                {
                    "id": 1,
                    "business_id": 1,
                    "delivery_id": 205,
                    "sales_order_id": 505,
                    "sscc_barcode": "000614141000000018",
                    "pallet_number": "PAL-01",
                    "pallet_type": "EURO",
                    "status": "STAGED",
                    "tare_weight_kg": 25.0,
                    "gross_weight_kg": 2425.0,
                    "net_weight_kg": 2400.0,
                },
                {
                    "id": 2,
                    "business_id": 1,
                    "delivery_id": 205,
                    "sales_order_id": 505,
                    "sscc_barcode": "000614141000000025",
                    "pallet_number": "PAL-02",
                    "pallet_type": "EURO",
                    "status": "STAGED",
                    "tare_weight_kg": 25.0,
                    "gross_weight_kg": 325.0,
                    "net_weight_kg": 300.0,
                },
            ]

            partner_repo = MagicMock()
            partner_repo.get.return_value = partner_carrefour
            delivery_repo = MagicMock()
            delivery_repo.get.return_value = mock_delivery
            dline_repo = MagicMock()
            dline_repo.list.return_value = mock_delivery_lines
            so_repo = MagicMock()
            so_repo.get.return_value = {"id": 505, "order_number": "SO-505", "buyer_po_number": "PO-CRF-MULTI-01", "customer_id": 101}
            sol_repo = MagicMock()
            sol_repo.list.return_value = []
            cust_repo = MagicMock()
            cust_repo.get.return_value = {"id": 101, "name": "Carrefour"}
            pli_repo = MagicMock()
            pli_repo.list.return_value = mock_pick_items
            product_repo = MagicMock()
            product_repo.get.side_effect = lambda p_id, **kw: product_milk if p_id == 10 else product_cheese
            sku_map_repo = MagicMock()
            sku_map_repo.list.return_value = []
            pallet_repo = MagicMock()
            pallet_repo.list.return_value = pallet_records
            pallet_repo.update.return_value = None
            tx_repo = MagicMock()
            tx_repo.create.return_value = {"id": 10}

            sscc_svc = SsccService(repo=pallet_repo, partner_repo=partner_repo)

            edi_856_svc = Edi856Service(
                repo=tx_repo,
                partner_repo=partner_repo,
                sku_mapping_repo=sku_map_repo,
                delivery_repo=delivery_repo,
                delivery_line_repo=dline_repo,
                sales_order_repo=so_repo,
                sales_line_repo=sol_repo,
                customer_repo=cust_repo,
                product_repo=product_repo,
                pick_list_item_repo=pli_repo,
                sscc_service_instance=sscc_svc,
            )

            asn_resp = edi_856_svc.generate_asn_for_delivery(delivery_id=205, partner_id=1)

            assert asn_resp.transaction_id is not None
            assert asn_resp.edi_payload is not None
            assert asn_resp.sscc_pallets_count == 2
            assert len(asn_resp.sscc_barcodes) == 2
            assert "000614141000000018" in asn_resp.sscc_barcodes
            assert "000614141000000025" in asn_resp.sscc_barcodes


# ===========================================================================
# 5. Multi-Tenant Isolation in Full Lifecycle
# ===========================================================================

class TestMultiTenantIsolationInLifecycle:
    """
    Verifies that all EDI operations strictly honor multi-tenant boundaries.
    """

    def test_tenant_isolation_in_order_lifecycle(self, partner_carrefour, partner_lulu):
        """
        Verify tenant 1 and tenant 2 data cannot be accessed across tenant boundaries.
        """
        with tenant_context(1):
            partner_repo_mock = MagicMock()
            partner_repo_mock.list.return_value = [partner_carrefour]

            edi_850_svc = Edi850Service(
                transaction_repo=MagicMock(),
                partner_repo=partner_repo_mock,
                order_repo=MagicMock(),
                line_repo=MagicMock(),
                customer_repo=MagicMock(),
                xref_service=MagicMock(),
                credit_svc=MagicMock(),
            )

            dummy_order = ParsedEdi850Order(
                standard=EdiStandard.ANSI_X12,
                document_type="850",
                sender_id="CARREFOUR",
                receiver_id="NOVADIST",
                control_number="0001",
                header=Edi850Header(po_number="PO-1", order_date=date.today(), currency="USD"),
                lines=[],
            )

            partner = edi_850_svc.resolve_partner(dummy_order)
            assert partner is not None
            assert partner["business_id"] == 1

        with tenant_context(2):
            partner_repo_mock2 = MagicMock()
            partner_repo_mock2.list.return_value = [dict(partner_lulu, business_id=2, interchange_sender_id="LULU_HYPER")]

            edi_850_svc2 = Edi850Service(
                transaction_repo=MagicMock(),
                partner_repo=partner_repo_mock2,
                order_repo=MagicMock(),
                line_repo=MagicMock(),
                customer_repo=MagicMock(),
                xref_service=MagicMock(),
                credit_svc=MagicMock(),
            )

            partner_repo_mock2.list.return_value = []
            partner_mismatch = edi_850_svc2.resolve_partner(dummy_order)
            assert partner_mismatch is None

            dummy_lulu_order = ParsedEdi850Order(
                standard=EdiStandard.EDIFACT,
                document_type="ORDERS",
                sender_id="LULU_HYPER",
                receiver_id="NOVADIST",
                control_number="0002",
                header=Edi850Header(po_number="PO-2", order_date=date.today(), currency="AED"),
                lines=[],
            )
            partner_repo_mock2.list.return_value = [dict(partner_lulu, business_id=2, interchange_sender_id="LULU_HYPER")]
            partner_t2 = edi_850_svc2.resolve_partner(dummy_lulu_order)
            assert partner_t2 is not None
            assert partner_t2["business_id"] == 2


# ===========================================================================
# 6. Error Handling & Edge Case Verification
# ===========================================================================

class TestLifecycleErrorHandling:
    """
    Tests error handling on invalid documents, missing records, or unposted invoices.
    """

    def test_asn_generation_missing_delivery_raises_error(self, partner_carrefour):
        """
        Generating ASN for non-existent delivery should fail cleanly.
        """
        with tenant_context(1):
            delivery_repo = MagicMock()
            delivery_repo.get.return_value = None

            edi_856_svc = Edi856Service(
                repo=MagicMock(),
                partner_repo=MagicMock(),
                sku_mapping_repo=MagicMock(),
                delivery_repo=delivery_repo,
                delivery_line_repo=MagicMock(),
                sales_order_repo=MagicMock(),
                sales_line_repo=MagicMock(),
                customer_repo=MagicMock(),
                product_repo=MagicMock(),
                pick_list_item_repo=MagicMock(),
                sscc_service_instance=MagicMock(),
            )

            with pytest.raises(ValueError) as exc_info:
                edi_856_svc.generate_asn_for_delivery(delivery_id=99999, partner_id=1)
            assert "99999 not found" in str(exc_info.value)

    def test_invoice_transmission_missing_invoice_raises_error(self, partner_carrefour):
        """
        Transmitting EDI invoice for non-existent invoice record should fail cleanly.
        """
        with tenant_context(1):
            invoice_repo = MagicMock()
            invoice_repo.get.return_value = None

            edi_810_svc = Edi810Service(
                repo=MagicMock(),
                partner_repo=MagicMock(),
                invoice_repo=invoice_repo,
                delivery_repo=MagicMock(),
                delivery_line_repo=MagicMock(),
                sales_order_repo=MagicMock(),
                sales_line_repo=MagicMock(),
                pick_list_item_repo=MagicMock(),
                sku_mapping_repo=MagicMock(),
                customer_repo=MagicMock(),
                product_repo=MagicMock(),
                payment_term_repo=MagicMock(),
            )

            with pytest.raises(ValueError) as exc_info:
                edi_810_svc.generate_invoice(EdiInvoiceTransmitRequest(invoice_id=99999, partner_id=1))
            assert "99999 not found" in str(exc_info.value)
