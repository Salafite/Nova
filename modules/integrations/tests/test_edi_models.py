"""
Unit tests for EDI domain models (T0124-T0128) and multi-tenant validation.
"""

import pytest
from datetime import date, datetime, timezone
from modules.core.models.base import TenantMixin, AuditMixin
from modules.integrations.models.edi import (
    EdiStandard,
    EdiCommunicationMethod,
    EdiDirection,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiAckStatus,
    EdiPackageType,
    EdiPalletStatus,
    EdiCatalogSyncStatus,
    EdiPartnerCreate,
    EdiPartnerUpdate,
    EdiPartnerResponse,
    EdiPartner,
    EdiSkuMappingCreate,
    EdiSkuMappingUpdate,
    EdiSkuMappingResponse,
    EdiSkuMapping,
    EdiTransactionCreate,
    EdiTransactionUpdate,
    EdiTransactionResponse,
    EdiTransaction,
    EdiSsccPalletCreate,
    EdiSsccPalletUpdate,
    EdiSsccPalletResponse,
    EdiSsccPallet,
    EdiCatalogItemCreate,
    EdiCatalogItemUpdate,
    EdiCatalogItemResponse,
    EdiCatalogItem,
    EdiIngestRequest,
    EdiLineDiscrepancy,
    EdiIngestResult,
    EdiReprocessRequest,
    EdiAsnGenerateRequest,
    EdiAsnGenerateResponse,
    EdiInvoiceTransmitRequest,
    EdiInvoiceTransmitResponse,
    EdiCatalogSyncRequest,
    EdiCatalogSyncResponse,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_TRANSACTION_REPO,
    EDI_SSCC_PALLET_REPO,
    EDI_CATALOG_ITEM_REPO,
)


def test_edi_enums():
    assert EdiStandard.ANSI_X12 == "ANSI_X12"
    assert EdiStandard.EDIFACT == "EDIFACT"
    assert EdiDirection.INBOUND == "INBOUND"
    assert EdiDirection.OUTBOUND == "OUTBOUND"
    assert EdiDocumentType.X12_850 == "850"
    assert EdiDocumentType.X12_856 == "856"
    assert EdiDocumentType.X12_810 == "810"
    assert EdiDocumentType.ORDERS == "ORDERS"
    assert EdiDocumentType.DESADV == "DESADV"
    assert EdiDocumentType.INVOIC == "INVOIC"
    assert EdiTransactionStatus.PRICE_DISCREPANCY_HOLD == "PRICE_DISCREPANCY_HOLD"


def test_edi_partner_models_and_tenant_support():
    partner_create = EdiPartnerCreate(
        partner_name="Carrefour Hypermarkets UAE",
        partner_code="CRF-UAE",
        edi_standard="ANSI_X12",
        interchange_sender_id="CARREFOUR_ISA",
        interchange_receiver_id="NOVA_DIST_ISA",
        sender_qualifier="ZZ",
        receiver_qualifier="ZZ",
        customer_id=10,
        auto_confirm_orders=True,
        price_tolerance_percent=2.50,
        gs1_company_prefix="6291041",
        business_id=5,
    )
    assert partner_create.partner_code == "CRF-UAE"
    assert partner_create.business_id == 5
    assert partner_create.auto_confirm_orders is True
    assert partner_create.price_tolerance_percent == 2.50

    partner_update = EdiPartnerUpdate(
        auto_confirm_orders=False,
        price_tolerance_percent=1.00,
        business_id=5,
    )
    assert partner_update.auto_confirm_orders is False
    assert partner_update.price_tolerance_percent == 1.00

    now = datetime.now(timezone.utc)
    partner_resp = EdiPartnerResponse(
        id=1,
        partner_name="Carrefour Hypermarkets UAE",
        partner_code="CRF-UAE",
        edi_standard="ANSI_X12",
        interchange_sender_id="CARREFOUR_ISA",
        interchange_receiver_id="NOVA_DIST_ISA",
        sender_qualifier="ZZ",
        receiver_qualifier="ZZ",
        communication_method="MANUAL",
        customer_id=10,
        segment_terminator="~",
        element_separator="*",
        subelement_separator=">",
        auto_confirm_orders=True,
        price_tolerance_percent=2.50,
        gs1_company_prefix="6291041",
        is_active=True,
        business_id=5,
        created_at=now,
        created_by=1,
        updated_at=now,
        updated_by=1,
        update_number=1,
    )
    assert partner_resp.id == 1
    assert partner_resp.business_id == 5
    assert isinstance(partner_resp, AuditMixin)
    assert isinstance(partner_resp, TenantMixin)


def test_edi_sku_mapping_models_and_tenant_support():
    sku_create = EdiSkuMappingCreate(
        partner_id=1,
        product_id=100,
        partner_sku="CRF-OVO-500",
        partner_sku_type="BUYER_PART_NO",
        gtin="6291041001234",
        partner_uom="CA",
        internal_uom="PCS",
        uom_conversion_factor=12.0000,
        catalog_price=45.50,
        business_id=5,
    )
    assert sku_create.partner_sku == "CRF-OVO-500"
    assert sku_create.uom_conversion_factor == 12.0000
    assert sku_create.business_id == 5

    sku_resp = EdiSkuMappingResponse(
        id=1,
        partner_id=1,
        product_id=100,
        partner_sku="CRF-OVO-500",
        partner_sku_type="BUYER_PART_NO",
        gtin="6291041001234",
        partner_uom="CA",
        internal_uom="PCS",
        uom_conversion_factor=12.0000,
        catalog_price=45.50,
        is_active=True,
        business_id=5,
    )
    assert sku_resp.id == 1
    assert sku_resp.business_id == 5


def test_edi_transaction_models_and_tenant_support():
    txn_create = EdiTransactionCreate(
        transaction_number="EDI-TXN-2026-00001",
        partner_id=1,
        standard="ANSI_X12",
        document_type="850",
        direction="INBOUND",
        control_number="000001234",
        status="PENDING",
        raw_payload="ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVADIST       *260908*1200*U*00401*000001234*0*P*>~GS*PO*CARREFOUR*NOVADIST*20260908*1200*1*X*004010~ST*850*0001~BEG*00*NE*PO-CRF-9901**20260908~SE*4*0001~GE*1*1~IEA*1*000001234~",
        parsed_data={"po_number": "PO-CRF-9901", "lines": 5},
        business_id=5,
    )
    assert txn_create.transaction_number == "EDI-TXN-2026-00001"
    assert txn_create.business_id == 5

    txn_resp = EdiTransactionResponse(
        id=1,
        transaction_number="EDI-TXN-2026-00001",
        partner_id=1,
        standard="ANSI_X12",
        document_type="850",
        direction="INBOUND",
        control_number="000001234",
        status="PROCESSED",
        sales_order_id=42,
        raw_payload="ISA*...",
        parsed_data={"po_number": "PO-CRF-9901"},
        ack_status="ACCEPTED",
        business_id=5,
    )
    assert txn_resp.id == 1
    assert txn_resp.sales_order_id == 42
    assert txn_resp.business_id == 5


def test_edi_sscc_pallet_models_and_tenant_support():
    pallet_create = EdiSsccPalletCreate(
        sscc_barcode="006291041000000018",
        delivery_id=15,
        sales_order_id=42,
        pallet_number="PLT-001",
        package_type="PALLET",
        gross_weight_kg=450.500,
        net_weight_kg=420.000,
        tare_weight_kg=30.500,
        volume_cbm=1.8000,
        items_count=60,
        contents_summary={"items": [{"product_id": 100, "qty": 60, "batch_number": "BAT-2026-01"}]},
        status="PACKED",
        business_id=5,
    )
    assert pallet_create.sscc_barcode == "006291041000000018"
    assert pallet_create.items_count == 60
    assert pallet_create.business_id == 5

    pallet_resp = EdiSsccPalletResponse(
        id=1,
        sscc_barcode="006291041000000018",
        delivery_id=15,
        sales_order_id=42,
        pallet_number="PLT-001",
        package_type="PALLET",
        gross_weight_kg=450.500,
        items_count=60,
        status="PACKED",
        business_id=5,
    )
    assert pallet_resp.id == 1
    assert pallet_resp.business_id == 5


def test_edi_catalog_item_models_and_tenant_support():
    cat_create = EdiCatalogItemCreate(
        partner_id=1,
        catalog_code="CAT-2026-Q1",
        buyer_sku="CRF-BEV-001",
        supplier_sku="NOV-BEV-001",
        gtin="6291041009999",
        product_name="Premium Sparkling Water 500ml",
        category="Beverages",
        brand="AquaPure",
        uom="EA",
        pack_size=24,
        list_price=18.50,
        currency="AED",
        effective_start_date=date(2026, 1, 1),
        effective_end_date=date(2026, 12, 31),
        matched_product_id=100,
        sync_status="SYNCED",
        is_active=True,
        business_id=5,
    )
    assert cat_create.buyer_sku == "CRF-BEV-001"
    assert cat_create.list_price == 18.50
    assert cat_create.business_id == 5

    cat_resp = EdiCatalogItemResponse(
        id=1,
        partner_id=1,
        catalog_code="CAT-2026-Q1",
        buyer_sku="CRF-BEV-001",
        product_name="Premium Sparkling Water 500ml",
        uom="EA",
        pack_size=24,
        list_price=18.50,
        currency="AED",
        matched_product_id=100,
        sync_status="SYNCED",
        is_active=True,
        business_id=5,
    )
    assert cat_resp.id == 1
    assert cat_resp.business_id == 5


def test_edi_workflow_request_response_models():
    ingest_req = EdiIngestRequest(
        partner_id=1,
        raw_payload="ISA*...~",
        auto_confirm=True,
        business_id=5,
    )
    assert ingest_req.partner_id == 1
    assert ingest_req.business_id == 5

    discrepancy = EdiLineDiscrepancy(
        line_number=1,
        buyer_sku="CRF-OVO-500",
        ordered_price=40.00,
        contract_price=45.00,
        discrepancy_percent=-11.11,
        discrepancy_type="PRICE_MISMATCH",
    )
    assert discrepancy.line_number == 1
    assert discrepancy.ordered_price == 40.00

    ingest_res = EdiIngestResult(
        transaction_id=1,
        transaction_number="EDI-TXN-2026-00001",
        status="PRICE_DISCREPANCY_HOLD",
        standard="ANSI_X12",
        document_type="850",
        price_discrepancies=[discrepancy],
    )
    assert ingest_res.status == "PRICE_DISCREPANCY_HOLD"
    assert len(ingest_res.price_discrepancies) == 1

    asn_req = EdiAsnGenerateRequest(
        delivery_id=15,
        carrier_name="DHL Freight",
        tracking_number="TRK-987654",
        vehicle_number="DXB-12345",
        business_id=5,
    )
    assert asn_req.delivery_id == 15
    assert asn_req.business_id == 5

    inv_req = EdiInvoiceTransmitRequest(
        invoice_id=20,
        delivery_id=15,
        business_id=5,
    )
    assert inv_req.invoice_id == 20
    assert inv_req.business_id == 5


def test_edi_crud_repositories():
    assert EDI_PARTNER_REPO.table_name == "t0124"
    assert "partner_code" in EDI_PARTNER_REPO.business_columns
    assert "edi_standard" in EDI_PARTNER_REPO.business_columns

    assert EDI_SKU_MAPPING_REPO.table_name == "t0125"
    assert "partner_sku" in EDI_SKU_MAPPING_REPO.business_columns
    assert "product_id" in EDI_SKU_MAPPING_REPO.business_columns

    assert EDI_TRANSACTION_REPO.table_name == "t0126"
    assert "transaction_number" in EDI_TRANSACTION_REPO.business_columns
    assert "raw_payload" in EDI_TRANSACTION_REPO.business_columns

    assert EDI_SSCC_PALLET_REPO.table_name == "t0127"
    assert "sscc_barcode" in EDI_SSCC_PALLET_REPO.business_columns
    assert "package_type" in EDI_SSCC_PALLET_REPO.business_columns

    assert EDI_CATALOG_ITEM_REPO.table_name == "t0128"
    assert "catalog_code" in EDI_CATALOG_ITEM_REPO.business_columns
    assert "buyer_sku" in EDI_CATALOG_ITEM_REPO.business_columns
