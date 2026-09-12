"""
Unit tests for Supplier Catalog Sync (EDI 832 / PRICAT) Engine
(modules/integrations/services/edi/edi_catalog_service.py).
Tests X12 832 parsing, UN/EDIFACT PRICAT parsing, universal inbound parser,
outbound X12/EDIFACT generation, product/GTIN matching, price change detection,
T0138 catalog item sync, T0135 SKU matrix upsert, and transaction audit logging.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from modules.integrations.services.edi.edi_catalog_service import (
    EdiCatalogHeader,
    EdiCatalogLine,
    ParsedEdiCatalog,
    CatalogItemSyncDetail,
    CatalogSyncResult,
    CatalogExportResult,
    parse_x12_832,
    parse_edifact_pricat,
    parse_inbound_catalog_edi,
    generate_x12_832,
    generate_edifact_pricat,
    EdiCatalogService,
    edi_catalog_service,
)
from modules.integrations.models.edi import (
    EdiStandard,
    EdiCatalogSyncStatus,
    EdiTransactionStatus,
    EdiDirection,
)


# ===========================================================================
# Sample EDI Documents
# ===========================================================================

SAMPLE_X12_832 = (
    "ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVADIST       *260908*1200*U*00401*000000832*0*P*>~\n"
    "GS*SC*CARREFOUR*NOVADIST*20260908*1200*83201*X*004010~\n"
    "ST*832*0001~\n"
    "BCT*00*CAT-2026-Q3***004010*20260908~\n"
    "CUR*BY*USD~\n"
    "DTM*007*20260908~\n"
    "DTM*194*20261231~\n"
    "N1*VN*Nova Distribution Inc*91*NOVA-HQ~\n"
    "N1*BY*Carrefour Hypermarket*92*CRF-UAE-01~\n"
    "LIN*1*BP*CRF-MILK-1L*VN*NV-MILK-1L*UP*6291041000101~\n"
    "PID*F****Full Cream Fresh Milk 1L~\n"
    "PID*F*08***Dairy~\n"
    "CTP*WS*RES*4.50*12*CA~\n"
    "PO4*12****KG*13.200*M3*0.0250*30*20*15*CM~\n"
    "LIN*2*BP*CRF-YOGURT-500G*VN*NV-YOG-500*UP*6291041000202~\n"
    "PID*F****Greek Style Yogurt 500g~\n"
    "CTP*WS*RES*6.25*6*CA~\n"
    "PO4*6****KG*3.500*M3*0.0100~\n"
    "CTT*2~\n"
    "SE*18*0001~\n"
    "GE*1*83201~\n"
    "IEA*1*000000832~"
)

SAMPLE_EDIFACT_PRICAT = (
    "UNA:+.? '\n"
    "UNB+UNOA:2+CARREFOUR:ZZ+NOVADIST:ZZ+260908:1200+PRICAT001++++++1'\n"
    "UNH+1+PRICAT:D:96A:UN:EAN008'\n"
    "BGM+9+CAT-2026-EDIF+9'\n"
    "DTM+137:20260908:102'\n"
    "DTM+194:20261231:102'\n"
    "CUX+2:EUR:4'\n"
    "NAD+SU+NOVA-HQ::92++Nova Distribution HQ'\n"
    "NAD+BY+CRF-UAE-01::9++Carrefour Hypermarket'\n"
    "LIN+1++6291041000303:SRV'\n"
    "PIA+1+NV-CHEESE-200G:SA+CRF-CHEESE-200:BP'\n"
    "IMD+F++:::Cheddar Cheese Block 200g'\n"
    "IMD+C++CAT:::Dairy & Cheese'\n"
    "PRI+AAA:8.75:CAL:EA'\n"
    "PAC+24++CT'\n"
    "MEA+WT+G+KGM:5.400'\n"
    "LIN+2++6291041000404:SRV'\n"
    "PIA+1+NV-BUTTER-500G:SA+CRF-BUTTER-500:BP'\n"
    "IMD+F++:::Unsalted Sweet Cream Butter 500g'\n"
    "PRI+AAA:14.20:CAL:EA'\n"
    "PAC+12++CT'\n"
    "UNT+17+1'\n"
    "UNZ+1+PRICAT001'"
)


# ===========================================================================
# 1. ANSI X12 832 Parsing Tests
# ===========================================================================

def test_parse_x12_832_header():
    """Verify parsing of ANSI X12 832 catalog header."""
    catalog = parse_x12_832(SAMPLE_X12_832)

    assert catalog.standard == "ANSI_X12"
    assert catalog.header.catalog_code == "CAT-2026-Q3"
    assert catalog.header.currency == "USD"
    assert catalog.header.effective_start_date == date(2026, 9, 8)
    assert catalog.header.effective_end_date == date(2026, 12, 31)
    assert catalog.header.buyer_code == "CRF-UAE-01"
    assert catalog.header.supplier_code == "NOVA-HQ"


def test_parse_x12_832_line_items():
    """Verify parsing of ANSI X12 832 catalog line items and packaging."""
    catalog = parse_x12_832(SAMPLE_X12_832)

    assert len(catalog.items) == 2

    item1 = catalog.items[0]
    assert item1.line_number == 1
    assert item1.buyer_sku == "CRF-MILK-1L"
    assert item1.supplier_sku == "NV-MILK-1L"
    assert item1.gtin == "6291041000101"
    assert item1.product_name == "Full Cream Fresh Milk 1L"
    assert item1.category == "Dairy"
    assert item1.list_price == 4.50
    assert item1.pack_size == 12
    assert item1.uom == "CA"
    assert item1.gross_weight_kg == 13.200
    assert item1.volume_cbm == 0.0250

    item2 = catalog.items[1]
    assert item2.line_number == 2
    assert item2.buyer_sku == "CRF-YOGURT-500G"
    assert item2.supplier_sku == "NV-YOG-500"
    assert item2.gtin == "6291041000202"
    assert item2.product_name == "Greek Style Yogurt 500g"
    assert item2.list_price == 6.25
    assert item2.pack_size == 6
    assert item2.gross_weight_kg == 3.500


# ===========================================================================
# 2. UN/EDIFACT PRICAT Parsing Tests
# ===========================================================================

def test_parse_edifact_pricat_header():
    """Verify parsing of UN/EDIFACT PRICAT catalogue header."""
    catalog = parse_edifact_pricat(SAMPLE_EDIFACT_PRICAT)

    assert catalog.standard == "EDIFACT"
    assert catalog.header.catalog_code == "CAT-2026-EDIF"
    assert catalog.header.currency == "EUR"
    assert catalog.header.effective_start_date == date(2026, 9, 8)
    assert catalog.header.effective_end_date == date(2026, 12, 31)
    assert "Carrefour" in catalog.header.partner_code or "CRF-UAE-01" in catalog.header.partner_code


def test_parse_edifact_pricat_line_items():
    """Verify parsing of UN/EDIFACT PRICAT catalogue line items."""
    catalog = parse_edifact_pricat(SAMPLE_EDIFACT_PRICAT)

    assert len(catalog.items) == 2

    item1 = catalog.items[0]
    assert item1.line_number == 1
    assert item1.buyer_sku == "CRF-CHEESE-200"
    assert item1.supplier_sku == "NV-CHEESE-200G"
    assert item1.gtin == "6291041000303"
    assert item1.product_name == "Cheddar Cheese Block 200g"
    assert item1.category == "Dairy & Cheese"
    assert item1.list_price == 8.75
    assert item1.pack_size == 24
    assert item1.gross_weight_kg == 5.400

    item2 = catalog.items[1]
    assert item2.line_number == 2
    assert item2.buyer_sku == "CRF-BUTTER-500"
    assert item2.supplier_sku == "NV-BUTTER-500G"
    assert item2.gtin == "6291041000404"
    assert item2.product_name == "Unsalted Sweet Cream Butter 500g"
    assert item2.list_price == 14.20
    assert item2.pack_size == 12


# ===========================================================================
# 3. Universal Inbound Parser Tests
# ===========================================================================

def test_universal_inbound_catalog_parser_autodetect():
    """Verify universal parser correctly identifies and parses X12 and EDIFACT."""
    parsed_x12 = parse_inbound_catalog_edi(SAMPLE_X12_832)
    assert parsed_x12.standard == "ANSI_X12"
    assert len(parsed_x12.items) == 2

    parsed_edifact = parse_inbound_catalog_edi(SAMPLE_EDIFACT_PRICAT)
    assert parsed_edifact.standard == "EDIFACT"
    assert len(parsed_edifact.items) == 2


# ===========================================================================
# 4. Outbound Document Generation Tests
# ===========================================================================

def test_generate_x12_832_document():
    """Verify outbound ANSI X12 832 generation."""
    partner_data = {
        "id": 1,
        "partner_name": "Lulu Hypermarket",
        "interchange_sender_id": "LULU-HQ",
        "interchange_receiver_id": "NOVADIST",
        "sender_qualifier": "ZZ",
        "receiver_qualifier": "ZZ",
        "edi_standard": "ANSI_X12",
        "segment_terminator": "~",
        "element_separator": "*",
    }
    items = [
        {
            "buyer_sku": "LULU-RICE-5KG",
            "supplier_sku": "NV-RICE-5K",
            "gtin": "6291041000505",
            "product_name": "Premium Basmati Rice 5kg",
            "list_price": 25.50,
            "uom": "EA",
            "pack_size": 1,
            "gross_weight_kg": 5.10,
        },
        {
            "buyer_sku": "LULU-OIL-1L",
            "supplier_sku": "NV-OIL-1L",
            "gtin": "6291041000606",
            "product_name": "Pure Sunflower Oil 1L",
            "list_price": 8.90,
            "uom": "CA",
            "pack_size": 12,
            "gross_weight_kg": 11.50,
        }
    ]

    edi_text = generate_x12_832(
        partner=partner_data,
        catalog_code="CAT-LULU-2026-Q3",
        items=items,
        control_number="000000999",
        currency="USD",
    )

    assert "ISA*" in edi_text
    assert "GS*SC*NOVADIST*LULU-HQ*" in edi_text
    assert "ST*832*0001~" in edi_text
    assert "BCT*00*CAT-LULU-2026-Q3" in edi_text
    assert "LIN*1*BP*LULU-RICE-5KG*VN*NV-RICE-5K*UP*6291041000505~" in edi_text
    assert "PID*F****Premium Basmati Rice 5kg~" in edi_text
    assert "CTP*WS*RES*25.50*1*EA~" in edi_text
    assert "CTT*2~" in edi_text
    assert "SE*16*0001~" in edi_text
    assert "IEA*1*000000999~" in edi_text

    # Re-parse to ensure syntax round-trip integrity
    parsed_back = parse_x12_832(edi_text)
    assert len(parsed_back.items) == 2
    assert parsed_back.items[0].buyer_sku == "LULU-RICE-5KG"
    assert parsed_back.items[0].list_price == 25.50


def test_generate_edifact_pricat_document():
    """Verify outbound UN/EDIFACT PRICAT generation."""
    partner_data = {
        "id": 2,
        "partner_name": "Carrefour France",
        "interchange_sender_id": "CRF-FR",
        "interchange_receiver_id": "NOVADIST",
        "sender_qualifier": "ZZ",
        "receiver_qualifier": "ZZ",
        "edi_standard": "EDIFACT",
        "segment_terminator": "'",
        "element_separator": "+",
        "subelement_separator": ":",
    }
    items = [
        {
            "buyer_sku": "CRF-PASTA-500G",
            "supplier_sku": "NV-PASTA-500",
            "gtin": "6291041000707",
            "product_name": "Italian Penne Rigate 500g",
            "list_price": 2.20,
            "uom": "EA",
            "pack_size": 20,
            "gross_weight_kg": 10.5,
        }
    ]

    edi_text = generate_edifact_pricat(
        partner=partner_data,
        catalog_code="CAT-CRF-FR-01",
        items=items,
        control_number="PRICAT999",
        currency="EUR",
    )

    assert "UNA:+.? '" in edi_text
    assert "UNB+UNOA:2+NOVADIST:ZZ+CRF-FR:ZZ+" in edi_text
    assert "UNH+1+PRICAT:D:96A:UN:EAN008'" in edi_text
    assert "BGM+9+CAT-CRF-FR-01+9'" in edi_text
    assert "LIN+1++6291041000707:SRV'" in edi_text
    assert "IMD+F++:::Italian Penne Rigate 500g'" in edi_text
    assert "PRI+AAA:2.20:CAL:EA'" in edi_text
    assert "UNT*13*1'" in edi_text or "UNT+13+1'" in edi_text
    assert "UNZ+1+PRICAT999'" in edi_text

    # Re-parse to verify round-trip
    parsed_back = parse_edifact_pricat(edi_text)
    assert len(parsed_back.items) == 1
    assert parsed_back.items[0].gtin == "6291041000707"
    assert parsed_back.items[0].list_price == 2.20


# ===========================================================================
# 5. Product & SKU Matching Tests
# ===========================================================================

def test_match_catalog_item_via_t0135_matrix():
    """Test matching catalog item against EDI SKU matrix (T0135)."""
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = [
        {"id": 101, "partner_id": 1, "product_id": 42, "partner_sku": "BUYER-MILK-1L", "gtin": "6291041000101", "is_active": True}
    ]

    service = EdiCatalogService(sku_mapping_repo=mock_sku_repo)

    item = EdiCatalogLine(
        line_number=1,
        buyer_sku="BUYER-MILK-1L",
        product_name="Fresh Milk",
        list_price=5.0,
    )

    prod_id, source = service.match_catalog_item(item, partner_id=1)
    assert prod_id == 42
    assert source == "CROSS_REFERENCE_MATRIX_T0135"


def test_match_catalog_item_via_gtin_barcode():
    """Test matching catalog item via GTIN barcode in T0004 or T0001."""
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_barcode_repo = MagicMock()
    mock_barcode_repo.list.return_value = [{"id": 1, "product_id": 77, "barcode": "6291041000999"}]
    mock_product_repo = MagicMock()

    service = EdiCatalogService(
        sku_mapping_repo=mock_sku_repo,
        barcode_repo=mock_barcode_repo,
        product_repo=mock_product_repo,
    )

    item = {"buyer_sku": "CRF-NEW-SKU", "gtin": "6291041000999", "product_name": "New Item"}
    prod_id, source = service.match_catalog_item(item, partner_id=1)

    assert prod_id == 77
    assert source == "PRODUCT_BARCODE_T0004"


def test_match_catalog_item_via_supplier_sku():
    """Test matching catalog item via internal supplier SKU in T0001."""
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_barcode_repo = MagicMock()
    mock_barcode_repo.list.return_value = []
    mock_product_repo = MagicMock()
    mock_product_repo.list.return_value = [{"id": 88, "sku": "NV-OIL-1L", "name": "Cooking Oil"}]

    service = EdiCatalogService(
        sku_mapping_repo=mock_sku_repo,
        barcode_repo=mock_barcode_repo,
        product_repo=mock_product_repo,
    )

    item = {"buyer_sku": "CRF-OIL", "supplier_sku": "NV-OIL-1L", "product_name": "Cooking Oil"}
    prod_id, source = service.match_catalog_item(item, partner_id=1)

    assert prod_id == 88
    assert source == "PRODUCT_SKU_T0001"


# ===========================================================================
# 6. Catalog Synchronization & Price Change Detection Tests
# ===========================================================================

def test_sync_catalog_price_change_and_matrix_upsert():
    """Test catalog synchronization detects price changes and updates T0135 matrix."""
    mock_catalog_repo = MagicMock()
    # Existing item had list_price = 10.00
    mock_catalog_repo.list.return_value = [
        {"id": 201, "partner_id": 1, "catalog_code": "CAT-2026", "buyer_sku": "CRF-RICE-5K", "list_price": 10.00}
    ]

    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = [
        {"id": 301, "partner_id": 1, "partner_sku": "CRF-RICE-5K", "product_id": 50, "catalog_price": 10.00}
    ]

    service = EdiCatalogService(
        catalog_repo=mock_catalog_repo,
        sku_mapping_repo=mock_sku_repo,
    )

    # New item with price increased to 12.50
    items = [
        {
            "buyer_sku": "CRF-RICE-5K",
            "gtin": "6291041000111",
            "product_name": "Basmati Rice 5kg",
            "list_price": 12.50,
            "uom": "EA",
            "pack_size": 1,
            "matched_product_id": 50,
        }
    ]

    result = service.sync_catalog(
        partner_id=1,
        catalog_code="CAT-2026",
        items=items,
        auto_match_skus=False,
        update_cross_reference_matrix=True,
    )

    assert result.total_items == 1
    assert result.matched_items == 1
    assert result.price_updated_items == 1
    assert result.sync_status == "PRICE_CHANGED"

    detail = result.details[0]
    assert detail.buyer_sku == "CRF-RICE-5K"
    assert detail.old_price == 10.00
    assert detail.new_price == 12.50
    assert detail.price_changed is True
    assert detail.sync_status == EdiCatalogSyncStatus.PRICE_CHANGED.value

    # Verify T0138 update called
    mock_catalog_repo.update.assert_called_once()
    # Verify T0135 matrix update called with new price
    mock_sku_repo.update.assert_called_once()


def test_sync_catalog_unmatched_items():
    """Test catalog synchronization handles unmatched items gracefully."""
    mock_catalog_repo = MagicMock()
    mock_catalog_repo.list.return_value = []
    mock_catalog_repo.create.return_value = {"id": 999}
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_barcode_repo = MagicMock()
    mock_barcode_repo.list.return_value = []
    mock_product_repo = MagicMock()
    mock_product_repo.list.return_value = []

    service = EdiCatalogService(
        catalog_repo=mock_catalog_repo,
        sku_mapping_repo=mock_sku_repo,
        barcode_repo=mock_barcode_repo,
        product_repo=mock_product_repo,
    )

    items = [
        {
            "buyer_sku": "CRF-UNKNOWN-999",
            "product_name": "Unidentified Product",
            "list_price": 99.00,
        }
    ]

    result = service.sync_catalog(
        partner_id=1,
        catalog_code="CAT-2026",
        items=items,
        auto_match_skus=True,
    )

    assert result.total_items == 1
    assert result.matched_items == 0
    assert result.unmatched_items == 1
    assert result.sync_status == "UNMATCHED"
    assert result.details[0].sync_status == EdiCatalogSyncStatus.UNMATCHED.value
    assert result.details[0].matched_product_id is None


# ===========================================================================
# 7. Inbound Ingestion Pipeline & Transaction Logging Tests
# ===========================================================================

def test_ingest_catalog_document_end_to_end():
    """Test full ingestion pipeline from raw X12 payload to sync & transaction log."""
    mock_partner_repo = MagicMock()
    mock_partner_repo.list.return_value = [
        {"id": 10, "partner_name": "Carrefour Hypermarket", "partner_code": "CRF-UAE-01", "interchange_sender_id": "CARREFOUR"}
    ]
    mock_catalog_repo = MagicMock()
    mock_catalog_repo.list.return_value = []
    mock_catalog_repo.create.return_value = {"id": 101}
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_barcode_repo = MagicMock()
    mock_barcode_repo.list.return_value = []
    mock_product_repo = MagicMock()
    mock_product_repo.list.return_value = [{"id": 55, "sku": "NV-MILK-1L", "name": "Full Cream Fresh Milk 1L"}]
    mock_tx_repo = MagicMock()
    mock_tx_repo.create.return_value = {"id": 888}

    service = EdiCatalogService(
        partner_repo=mock_partner_repo,
        catalog_repo=mock_catalog_repo,
        sku_mapping_repo=mock_sku_repo,
        barcode_repo=mock_barcode_repo,
        product_repo=mock_product_repo,
        transaction_repo=mock_tx_repo,
    )

    ingest_result = service.ingest_catalog_document(
        payload=SAMPLE_X12_832,
        partner_id=10,
        auto_match_skus=True,
        update_cross_reference_matrix=True,
    )

    assert ingest_result["transaction_id"] == 888
    assert ingest_result["partner_id"] == 10
    assert ingest_result["standard"] == "ANSI_X12"
    assert ingest_result["document_type"] == "832"
    assert ingest_result["sync_result"]["total_items"] == 2

    # Check that T0136 transaction log was created
    mock_tx_repo.create.assert_called_once()
    call_args = mock_tx_repo.create.call_args[0][0]
    assert call_args["direction"] == EdiDirection.INBOUND.value
    assert call_args["document_type"] == "832"
    assert call_args["status"] == EdiTransactionStatus.PROCESSED.value
