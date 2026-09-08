"""
Nova ERP — Unit Tests for Outbound EDI 856 (ASN) & UN/EDIFACT DESADV Generator
Tests Hierarchical Level (HL) structures, SSCC-18 barcodes, batch numbers,
expiry dates, carrier routing, and Edi856Service lifecycle.
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiDirection,
    EdiAsnGenerateResponse,
)
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
    Edi856Service,
)
from modules.integrations.services.edi.edi_core import EdiDelimiters, parse_edi


@pytest.fixture
def sample_asn_document() -> EdiAsnDocument:
    """Fixture providing a sample structured ASN document with 5-level packaging hierarchy."""
    header = EdiAsnShipmentHeader(
        delivery_id=101,
        delivery_number="DEL-2026-00101",
        sales_order_id=501,
        sales_order_number="SO-501",
        buyer_po_number="PO-CRF-9988",
        ship_date=date(2026, 9, 8),
        ship_time="1430",
        estimated_delivery_date=date(2026, 9, 9),
        carrier_name="Gulf Logistics Express",
        carrier_code="GLEX",
        tracking_number="BOL-987654321",
        vehicle_number="DXB-T-44552",
        seal_number="SL-8877",
        driver_id=7,
        total_pallets=1,
        ship_from_name="Nova Food Hub 1",
        ship_from_id="NOVA-DXB",
        ship_to_name="Carrefour Central DC",
        ship_to_id="CRF-DIP",
    )

    item1 = EdiAsnItemDetail(
        line_number=1,
        product_id=10,
        sku="SKU-CHEDDAR-200G",
        buyer_sku="CRF-CHD-200",
        vendor_sku="NOVA-CHD-200",
        gtin="0614141100018",
        product_name="Cheddar Cheese Block 200g",
        qty_shipped=50.0,
        qty_ordered=50.0,
        uom="CA",
        batch_number="LOT-202609A",
        expiry_date=date(2027, 3, 15),
        gross_weight_kg=75.0,
        net_weight_kg=70.0,
    )

    box1 = EdiAsnBoxDetail(
        box_number="BX-01",
        sscc_barcode="000614141999900013",
        package_type="BOX",
        gross_weight_kg=75.5,
        net_weight_kg=70.0,
        items=[item1],
    )

    item2 = EdiAsnItemDetail(
        line_number=2,
        product_id=11,
        sku="SKU-BUTTER-500G",
        buyer_sku="CRF-BTR-500",
        vendor_sku="NOVA-BTR-500",
        gtin="0614141100025",
        product_name="Salted Butter 500g",
        qty_shipped=20.0,
        qty_ordered=20.0,
        uom="CA",
        batch_number="LOT-202609B",
        expiry_date=date(2027, 4, 20),
        gross_weight_kg=30.0,
        net_weight_kg=28.0,
    )

    pallet1 = EdiAsnPalletDetail(
        pallet_id=1,
        pallet_number="PLT-01",
        sscc_barcode="006141411234567895",
        package_type="PALLET",
        gross_weight_kg=130.5,
        net_weight_kg=98.0,
        tare_weight_kg=25.0,
        volume_cbm=1.2,
        boxes=[box1],
        direct_items=[item2],
    )

    return EdiAsnDocument(
        standard="ANSI_X12",
        document_type="856",
        control_number="100000042",
        sender_id="NOVAERP",
        sender_qualifier="ZZ",
        receiver_id="CARREFOUR",
        receiver_qualifier="ZZ",
        header=header,
        pallets=[pallet1],
    )


# ===========================================================================
# 1. ANSI X12 856 ASN Generation Tests
# ===========================================================================

def test_generate_x12_856_structure(sample_asn_document):
    """Test generating standard ANSI X12 856 with HL loops and envelopes."""
    x12_text = generate_x12_856(sample_asn_document)

    assert "ISA*" in x12_text
    assert "GS*SH*NOVAERP*CARREFOUR*" in x12_text
    assert "ST*856*0042~" in x12_text or "ST*856*" in x12_text
    assert "BSN*00*DEL-2026-00101*20260908*1430*0001~" in x12_text
    assert "DTM*011*20260908~" in x12_text
    assert "DTM*017*20260909~" in x12_text

    # HL Level 1: Shipment
    assert "HL*1**S~" in x12_text
    assert "TD1*PLT90*1~" in x12_text
    assert "TD5*B*2*GLEX*M*Gulf Logistics Express~" in x12_text
    assert "TD3*TL**DXB-T-44552~" in x12_text
    assert "REF*BM*BOL-987654321~" in x12_text
    assert "REF*CN*SL-8877~" in x12_text
    assert "N1*SF*Nova Food Hub 1*92*NOVA-DXB~" in x12_text
    assert "N1*ST*Carrefour Central DC*92*CRF-DIP~" in x12_text

    # HL Level 2: Order
    assert "HL*2*1*O~" in x12_text
    assert "PRF*PO-CRF-9988~" in x12_text
    assert "REF*SO*SO-501~" in x12_text

    # HL Level 3: Tare / Pallet with SSCC-18
    assert "HL*3*2*T~" in x12_text
    assert "MAN*GM*00006141411234567895~" in x12_text or "MAN*GM*006141411234567895~" in x12_text
    assert "MEA*PD*G*130.5*KG~" in x12_text

    # HL Level 4: Pack / Box
    assert "HL*4*3*P~" in x12_text
    assert "MAN*GM*000614141999900013~" in x12_text

    # HL Level 5: Items
    assert "LIN*1*BP*CRF-CHD-200*VP*NOVA-CHD-200*UP*0614141100018~" in x12_text
    assert "SN1*1*50*CA~" in x12_text
    assert "PID*F****Cheddar Cheese Block 200g~" in x12_text
    assert "DTM*036*20270315~" in x12_text
    assert "REF*LT*LOT-202609A~" in x12_text

    # CTT, SE, GE, IEA Trailers
    assert "CTT*" in x12_text
    assert "SE*" in x12_text
    assert "GE*1*" in x12_text
    assert "IEA*1*" in x12_text


def test_parse_x12_856_roundtrip(sample_asn_document):
    """Test serializing to X12 856 and parsing back into EdiAsnDocument."""
    x12_text = generate_x12_856(sample_asn_document)
    parsed = parse_x12_856(x12_text)

    assert parsed.standard == "ANSI_X12"
    assert parsed.document_type == "856"
    assert parsed.header.delivery_number == "DEL-2026-00101"
    assert parsed.header.buyer_po_number == "PO-CRF-9988"
    assert parsed.header.ship_date == date(2026, 9, 8)
    assert parsed.header.tracking_number == "BOL-987654321"
    assert parsed.header.vehicle_number == "DXB-T-44552"
    assert parsed.header.carrier_name == "Gulf Logistics Express"

    assert len(parsed.pallets) >= 1
    pallet = parsed.pallets[0]
    assert "006141411234567895" in pallet.sscc_barcode

    assert len(pallet.boxes) >= 1
    box = pallet.boxes[0]
    assert len(box.items) >= 1
    item = box.items[0]
    assert item.buyer_sku == "CRF-CHD-200"
    assert item.qty_shipped == 50.0
    assert item.batch_number == "LOT-202609A"
    assert item.expiry_date == date(2027, 3, 15)


# ===========================================================================
# 2. UN/EDIFACT DESADV Generation Tests
# ===========================================================================

def test_generate_edifact_desadv_structure(sample_asn_document):
    """Test generating standard UN/EDIFACT DESADV with CPS packaging hierarchy."""
    sample_asn_document.standard = "EDIFACT"
    sample_asn_document.document_type = "DESADV"
    desadv_text = generate_edifact_desadv(sample_asn_document)

    assert "UNB+UNOA:2+NOVAERP:ZZ+CARREFOUR:ZZ+" in desadv_text
    assert "UNH+100000042+DESADV:D:96A:UN:EAN008'" in desadv_text or "UNH+" in desadv_text
    assert "BGM+351+DEL-2026-00101+9'" in desadv_text
    assert "DTM+11:20260908:102'" in desadv_text
    assert "RFF+ON:PO-CRF-9988'" in desadv_text
    assert "RFF+DQ:DEL-2026-00101'" in desadv_text
    assert "RFF+AAS:BOL-987654321'" in desadv_text

    # Parties
    assert "NAD+CZ+NOVA-DXB::92++Nova Food Hub 1'" in desadv_text
    assert "NAD+CN+CRF-DIP::92++Carrefour Central DC'" in desadv_text
    assert "NAD+CA+GLEX::92++Gulf Logistics Express'" in desadv_text
    assert "TDT+20++30+31+Gulf Logistics Express+++DXB-T-44552'" in desadv_text

    # Packaging CPS Loops
    assert "CPS+1'" in desadv_text
    assert "CPS+2+1'" in desadv_text
    assert "PAC+1++201'" in desadv_text
    assert "MEA+WT+G+KGM:130.5'" in desadv_text
    assert "PCI+33E'" in desadv_text
    assert "GIN+ML+006141411234567895'" in desadv_text

    # Items
    assert "LIN+1++0614141100018:SRV'" in desadv_text or "LIN+1++SKU-CHEDDAR-200G:SRV'" in desadv_text
    assert "PIA+1+CRF-CHD-200:IN'" in desadv_text
    assert "QTY+12:50:CA'" in desadv_text
    assert "DTM+361:20270315:102'" in desadv_text
    assert "GIR+3+LOT-202609A:BX'" in desadv_text

    # Trailer
    assert "CNT+2:2'" in desadv_text
    assert "UNT+" in desadv_text
    assert "UNZ+1+" in desadv_text


def test_parse_edifact_desadv_roundtrip(sample_asn_document):
    """Test serializing to EDIFACT DESADV and parsing back into EdiAsnDocument."""
    desadv_text = generate_edifact_desadv(sample_asn_document)
    parsed = parse_edifact_desadv(desadv_text)

    assert parsed.standard == "EDIFACT"
    assert parsed.document_type == "DESADV"
    assert parsed.header.delivery_number == "DEL-2026-00101"
    assert parsed.header.buyer_po_number == "PO-CRF-9988"
    assert parsed.header.ship_date == date(2026, 9, 8)
    assert parsed.header.tracking_number == "BOL-987654321"

    assert len(parsed.pallets) >= 1
    pallet = parsed.pallets[0]
    assert "006141411234567895" in pallet.sscc_barcode

    assert len(pallet.boxes) >= 1
    box = pallet.boxes[0]
    assert len(box.items) >= 1
    item = box.items[0]
    assert item.buyer_sku == "CRF-CHD-200"
    assert item.qty_shipped == 50.0
    assert item.batch_number == "LOT-202609A"
    assert item.expiry_date == date(2027, 3, 15)


def test_parse_inbound_asn_auto_detect(sample_asn_document):
    """Test universal parse_inbound_asn auto-detecting standard."""
    x12_payload = generate_x12_856(sample_asn_document)
    parsed_x12 = parse_inbound_asn(x12_payload)
    assert parsed_x12.standard == "ANSI_X12"
    assert parsed_x12.header.delivery_number == "DEL-2026-00101"

    edifact_payload = generate_edifact_desadv(sample_asn_document)
    parsed_edifact = parse_inbound_asn(edifact_payload)
    assert parsed_edifact.standard == "EDIFACT"
    assert parsed_edifact.header.delivery_number == "DEL-2026-00101"


# ===========================================================================
# 3. Edi856Service Business Operations & Lifecycle Tests
# ===========================================================================

def test_edi_856_service_generate_asn_lifecycle():
    """
    Test Edi856Service.generate_asn_for_delivery with mock repositories:
    Verifies partner resolution, SKU mapping, batch lookup, SSCC pallet generation,
    T0126 transaction persistence, and pallet status update.
    """
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_sku_repo = MagicMock()
    mock_delivery_repo = MagicMock()
    mock_del_line_repo = MagicMock()
    mock_so_repo = MagicMock()
    mock_sol_repo = MagicMock()
    mock_cust_repo = MagicMock()
    mock_prod_repo = MagicMock()
    mock_pli_repo = MagicMock()
    mock_sscc_svc = MagicMock()

    # Setup Delivery & SO mock data
    mock_delivery_repo.get.return_value = {
        "id": 101,
        "delivery_number": "DEL-101",
        "sales_order_id": 501,
        "delivery_date": date(2026, 9, 8),
        "actual_delivery_date": date(2026, 9, 8),
        "delivery_route": "ROUTE-NORTH-01",
        "driver_id": 12,
        "status": "Dispatched",
    }
    mock_so_repo.get.return_value = {
        "id": 501,
        "order_number": "SO-501",
        "customer_id": 20,
        "notes": "EDI Supermarket Order PO-LULU-4411",
    }
    mock_cust_repo.get.return_value = {
        "id": 20,
        "name": "LuLu Hypermarket UAE",
    }

    # Setup Partner mock data (ANSI X12)
    mock_partner_repo.get.return_value = {
        "id": 1,
        "partner_name": "LuLu Group International",
        "partner_code": "LULU-UAE",
        "edi_standard": "ANSI_X12",
        "interchange_sender_id": "NOVAERP",
        "interchange_receiver_id": "LULUHQ",
        "sender_qualifier": "ZZ",
        "receiver_qualifier": "ZZ",
        "gs1_company_prefix": "0614141",
        "is_active": True,
    }
    mock_partner_repo.list.return_value = [mock_partner_repo.get.return_value]

    # Setup Delivery Line and Product
    mock_del_line_repo.list.return_value = [
        {
            "id": 1,
            "delivery_id": 101,
            "sales_order_line_id": 1001,
            "product_id": 55,
            "product_name": "Organic Milk 1L",
            "qty_shipped": 100.0,
            "qty_ordered": 100.0,
            "line_number": 1,
        }
    ]
    mock_prod_repo.get.return_value = {
        "id": 55,
        "sku": "SKU-MILK-1L",
        "name": "Organic Milk 1L",
        "barcode": "6291041000551",
    }

    # Setup Pick List Item with Batch and Expiry
    mock_pli_repo.list.return_value = [
        {
            "id": 1,
            "sales_order_line_id": 1001,
            "product_id": 55,
            "batch_number": "LOT-MILK-2609",
            "picked_batch_number": "LOT-MILK-2609",
            "expiry_date": "2026-12-31",
        }
    ]

    # Setup SKU Cross-Reference Mapping
    mock_sku_repo.list.return_value = [
        {
            "id": 1,
            "partner_id": 1,
            "product_id": 55,
            "partner_sku": "LULU-MLK-01",
            "gtin": "6291041000551",
            "partner_uom": "EA",
            "is_active": True,
        }
    ]

    # Setup SSCC pallet mock
    mock_sscc_svc.get_pallets_for_delivery.return_value = [
        {
            "id": 88,
            "pallet_number": "PLT-101-01",
            "sscc_barcode": "006141411234567895",
            "package_type": "PALLET",
            "gross_weight_kg": 150.0,
            "net_weight_kg": 125.0,
            "status": "PACKED",
        }
    ]

    # Setup Transaction creation mock
    mock_tx_repo.create.return_value = {
        "id": 999,
        "transaction_number": "TX-ASN-123456",
        "status": "PROCESSED",
    }

    service = Edi856Service(
        repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        sku_mapping_repo=mock_sku_repo,
        delivery_repo=mock_delivery_repo,
        delivery_line_repo=mock_del_line_repo,
        sales_order_repo=mock_so_repo,
        sales_line_repo=mock_sol_repo,
        customer_repo=mock_cust_repo,
        product_repo=mock_prod_repo,
        pick_list_item_repo=mock_pli_repo,
        sscc_service_instance=mock_sscc_svc,
    )

    response = service.generate_asn_for_delivery(
        delivery_id=101,
        carrier_name="Nova Express Fleet",
        tracking_number="TRACK-999000",
        vehicle_number="TRK-DXB-99",
        seal_number="SEAL-007",
    )

    assert isinstance(response, EdiAsnGenerateResponse)
    assert response.transaction_id == 999
    assert response.delivery_id == 101
    assert response.standard == "ANSI_X12"
    assert response.document_type == "856"
    assert "006141411234567895" in response.sscc_barcodes[0]

    # Verify transaction was persisted
    mock_tx_repo.create.assert_called_once()
    saved_payload = mock_tx_repo.create.call_args[0][0]
    assert saved_payload["direction"] == EdiDirection.OUTBOUND.value
    assert saved_payload["document_type"] == "856"
    assert saved_payload["status"] == EdiTransactionStatus.PROCESSED.value
    assert "BSN*00*DEL-101*" in saved_payload["raw_payload"]
    assert "LULU-MLK-01" in saved_payload["raw_payload"]
    assert "LOT-MILK-2609" in saved_payload["raw_payload"]

    # Verify pallet was updated to DISPATCHED
    assert mock_sscc_svc.update_pallet_status.call_count == 1
    call_args, call_kwargs = mock_sscc_svc.update_pallet_status.call_args
    assert call_args[0] == 88
    assert call_args[1] == "DISPATCHED"
    assert call_kwargs.get("tenant_id") is None


def test_edi_856_service_edifact_partner_dispatch():
    """Test generating EDIFACT DESADV when trading partner uses EDIFACT standard."""
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_sku_repo = MagicMock()
    mock_delivery_repo = MagicMock()
    mock_del_line_repo = MagicMock()
    mock_so_repo = MagicMock()
    mock_sol_repo = MagicMock()
    mock_cust_repo = MagicMock()
    mock_prod_repo = MagicMock()
    mock_pli_repo = MagicMock()
    mock_sscc_svc = MagicMock()

    mock_delivery_repo.get.return_value = {
        "id": 202,
        "delivery_number": "DEL-202",
        "sales_order_id": 602,
        "delivery_date": date(2026, 9, 8),
        "delivery_route": "ROUTE-DUBAI-DIP",
    }
    mock_so_repo.get.return_value = {
        "id": 602,
        "order_number": "SO-602",
        "customer_id": 30,
        "notes": "PO-CARREFOUR-8800",
    }
    mock_cust_repo.get.return_value = {"id": 30, "name": "Carrefour UAE"}

    mock_partner_repo.get.return_value = {
        "id": 2,
        "partner_name": "Carrefour France/UAE",
        "partner_code": "CRF-FR",
        "edi_standard": "EDIFACT",
        "interchange_sender_id": "NOVAERP",
        "interchange_receiver_id": "CRFFR",
        "sender_qualifier": "ZZ",
        "receiver_qualifier": "ZZ",
        "is_active": True,
    }
    mock_partner_repo.list.return_value = [mock_partner_repo.get.return_value]

    mock_del_line_repo.list.return_value = [
        {
            "id": 10,
            "delivery_id": 202,
            "sales_order_line_id": 2001,
            "product_id": 80,
            "product_name": "French Gouda 250g",
            "qty_shipped": 40.0,
            "line_number": 1,
        }
    ]
    mock_prod_repo.get.return_value = {"id": 80, "sku": "SKU-GOUDA-250G", "barcode": "3012345678901"}
    mock_pli_repo.list.return_value = []
    mock_sku_repo.list.return_value = []
    mock_sscc_svc.get_pallets_for_delivery.return_value = [
        {
            "id": 90,
            "pallet_number": "PLT-202-01",
            "sscc_barcode": "006141419876543211",
            "package_type": "PALLET",
            "gross_weight_kg": 80.0,
            "net_weight_kg": 60.0,
        }
    ]
    mock_tx_repo.create.return_value = {"id": 1000, "transaction_number": "TX-ASN-202"}

    service = Edi856Service(
        repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        sku_mapping_repo=mock_sku_repo,
        delivery_repo=mock_delivery_repo,
        delivery_line_repo=mock_del_line_repo,
        sales_order_repo=mock_so_repo,
        sales_line_repo=mock_sol_repo,
        customer_repo=mock_cust_repo,
        product_repo=mock_prod_repo,
        pick_list_item_repo=mock_pli_repo,
        sscc_service_instance=mock_sscc_svc,
    )

    response = service.generate_asn_for_delivery(delivery_id=202)
    assert response.standard == "EDIFACT"
    assert response.document_type == "DESADV"
    assert "UNB+UNOA:2+NOVAERP:ZZ+CRFFR:ZZ+" in response.edi_payload
    assert "BGM+351+DEL-202+9'" in response.edi_payload
    assert "GIN+ML+006141419876543211'" in response.edi_payload


def test_generate_x12_856_direct_items_no_pallets():
    """Test generating ANSI X12 856 when goods are shipped directly without pallets."""
    header = EdiAsnShipmentHeader(
        delivery_id=303,
        delivery_number="DEL-303",
        sales_order_number="SO-303",
        buyer_po_number="PO-DIR-01",
        ship_date=date(2026, 9, 8),
        carrier_name="Direct Fleet",
        total_units=10,
    )
    item = EdiAsnItemDetail(
        line_number=1,
        sku="SKU-WATER-500ML",
        buyer_sku="WTR-500",
        qty_shipped=10.0,
        uom="CS",
        batch_number="LOT-WTR-01",
    )
    doc = EdiAsnDocument(
        standard="ANSI_X12",
        document_type="856",
        control_number="30303",
        sender_id="NOVAERP",
        receiver_id="BUYER",
        header=header,
        direct_items=[item],
    )
    x12 = generate_x12_856(doc)
    assert "HL*1**S~" in x12
    assert "HL*2*1*O~" in x12
    assert "HL*3*2*I~" in x12
    assert "LIN*1*BP*WTR-500*IN*SKU-WATER-500ML~" in x12
    assert "SN1*1*10*CS~" in x12
    assert "REF*LT*LOT-WTR-01~" in x12


def test_generate_edifact_desadv_direct_items_no_pallets():
    """Test generating UN/EDIFACT DESADV when goods are shipped directly without pallets."""
    header = EdiAsnShipmentHeader(
        delivery_id=304,
        delivery_number="DEL-304",
        buyer_po_number="PO-DIR-02",
        ship_date=date(2026, 9, 8),
    )
    item = EdiAsnItemDetail(
        line_number=1,
        sku="SKU-JUICE-1L",
        buyer_sku="JCE-100",
        qty_shipped=25.0,
        uom="PCE",
    )
    doc = EdiAsnDocument(
        standard="EDIFACT",
        document_type="DESADV",
        control_number="30404",
        sender_id="NOVAERP",
        receiver_id="BUYER",
        header=header,
        direct_items=[item],
    )
    desadv = generate_edifact_desadv(doc)
    assert "CPS+1'" in desadv
    assert "CPS+2+1'" in desadv
    assert "LIN+1++SKU-JUICE-1L:SRV'" in desadv
    assert "PIA+1+JCE-100:IN'" in desadv
    assert "QTY+12:25:PCE'" in desadv


def test_edi_856_service_auto_generates_sscc_when_none_exist():
    """Test that Edi856Service automatically generates SSCC pallets if none exist for the delivery."""
    mock_tx_repo = MagicMock()
    mock_partner_repo = MagicMock()
    mock_sku_repo = MagicMock()
    mock_delivery_repo = MagicMock()
    mock_del_line_repo = MagicMock()
    mock_so_repo = MagicMock()
    mock_sol_repo = MagicMock()
    mock_cust_repo = MagicMock()
    mock_prod_repo = MagicMock()
    mock_pli_repo = MagicMock()
    mock_sscc_svc = MagicMock()

    mock_delivery_repo.get.return_value = {
        "id": 404,
        "delivery_number": "DEL-404",
        "sales_order_id": 704,
        "delivery_date": date(2026, 9, 8),
    }
    mock_so_repo.get.return_value = {"id": 704, "order_number": "SO-704", "customer_id": 40}
    mock_cust_repo.get.return_value = {"id": 40, "name": "Supermarket Partner"}
    mock_partner_repo.get.return_value = {
        "id": 4,
        "partner_name": "Supermarket Partner",
        "edi_standard": "ANSI_X12",
        "interchange_sender_id": "NOVA",
        "interchange_receiver_id": "SUPER",
        "gs1_company_prefix": "0614141",
    }
    mock_del_line_repo.list.return_value = [
        {"id": 1, "product_id": 99, "product_name": "Fresh Yogurt", "qty_shipped": 20.0, "line_number": 1}
    ]
    mock_prod_repo.get.return_value = {"id": 99, "sku": "SKU-YOGURT"}
    mock_pli_repo.list.return_value = []
    mock_sku_repo.list.return_value = []

    # First call returns empty list (no pallets yet), second call inside create_pallet_hierarchy returns created pallet
    mock_sscc_svc.get_pallets_for_delivery.return_value = []
    mock_sscc_svc.create_pallet_hierarchy.return_value = [
        {
            "id": 991,
            "pallet_number": "PLT-404-01",
            "sscc_barcode": "006141419999999992",
            "package_type": "PALLET",
            "gross_weight_kg": 55.0,
            "net_weight_kg": 28.0,
        }
    ]
    mock_tx_repo.create.return_value = {"id": 1004, "transaction_number": "TX-404"}

    service = Edi856Service(
        repo=mock_tx_repo,
        partner_repo=mock_partner_repo,
        sku_mapping_repo=mock_sku_repo,
        delivery_repo=mock_delivery_repo,
        delivery_line_repo=mock_del_line_repo,
        sales_order_repo=mock_so_repo,
        sales_line_repo=mock_sol_repo,
        customer_repo=mock_cust_repo,
        product_repo=mock_prod_repo,
        pick_list_item_repo=mock_pli_repo,
        sscc_service_instance=mock_sscc_svc,
    )

    response = service.generate_asn_for_delivery(delivery_id=404, partner_id=4, auto_generate_sscc=True)
    assert response.sscc_pallets_count == 1
    assert "006141419999999992" in response.sscc_barcodes[0]
    mock_sscc_svc.create_pallet_hierarchy.assert_called_once()


def test_edi_856_service_missing_delivery_raises_error():
    """Test that Edi856Service raises ValueError when delivery ID does not exist."""
    mock_delivery_repo = MagicMock()
    mock_delivery_repo.get.return_value = None

    service = Edi856Service(delivery_repo=mock_delivery_repo)
    with pytest.raises(ValueError, match="Delivery record 9999 not found"):
        service.generate_asn_for_delivery(delivery_id=9999)


def test_edi_856_service_missing_partner_raises_error():
    """Test that Edi856Service raises ValueError when no partner is found for customer/delivery."""
    mock_delivery_repo = MagicMock()
    mock_delivery_repo.get.return_value = {"id": 500, "sales_order_id": 800}
    mock_so_repo = MagicMock()
    mock_so_repo.get.return_value = {"id": 800, "customer_id": 999}
    mock_partner_repo = MagicMock()
    mock_partner_repo.list.return_value = []
    mock_cust_repo = MagicMock()
    mock_cust_repo.get.return_value = {"id": 999, "name": "Unknown Customer"}

    service = Edi856Service(
        delivery_repo=mock_delivery_repo,
        sales_order_repo=mock_so_repo,
        partner_repo=mock_partner_repo,
        customer_repo=mock_cust_repo,
    )
    with pytest.raises(ValueError, match="No active EDI Trading Partner"):
        service.generate_asn_for_delivery(delivery_id=500)

