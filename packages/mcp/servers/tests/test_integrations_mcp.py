"""Unit and integration tests for packages/mcp/servers/integrations_mcp.py.

Tests:
1. Tool handler functions:
   - _list_edi_partners
   - _get_edi_partner
   - _ingest_edi_document (850 PO and 832 catalog)
   - _list_edi_transactions
   - _get_edi_transaction
   - _reprocess_edi_transaction
   - _generate_edi_asn
   - _transmit_edi_invoice (Tier 2)
   - _sync_supplier_catalog
2. Resource handler functions:
   - _resource_list_partners
   - _resource_list_transactions
3. Tool registration and metadata:
   - register_tools() registers all 9 tools with correct tiers and schemas
   - register_tools() registers resources
4. Propose/Confirm lifecycle for Tier 2 tools:
   - propose_action and confirm_action for transmit_edi_invoice
5. Registry call_tool execution and tenant context propagation:
   - User dict with business_id passed to MCP calls
"""

import pytest
from unittest.mock import patch, MagicMock

from modules.integrations.models.edi import (
    EdiIngestResult,
    EdiAsnGenerateResponse,
    EdiInvoiceTransmitResponse,
    EdiCatalogSyncResponse,
)
from packages.mcp.servers import integrations_mcp
from packages.mcp.servers.integrations_mcp import register_tools
from packages.mcp.registry import (
    call_tool,
    confirm_action,
    get_tools,
    list_resources,
    propose_action,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry tools, resources, and pending actions before and after each test."""
    from packages.mcp import registry
    registry._tools.clear()
    registry._resources.clear()
    registry._pending_actions.clear()
    yield
    registry._tools.clear()
    registry._resources.clear()
    registry._pending_actions.clear()


@pytest.fixture
def mock_partner_svc():
    with patch.object(integrations_mcp, "_partner_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_transaction_svc():
    with patch.object(integrations_mcp, "_transaction_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_sku_mapping_svc():
    with patch.object(integrations_mcp, "_sku_mapping_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_edi_850_svc():
    with patch.object(integrations_mcp, "_edi_850_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_edi_856_svc():
    with patch.object(integrations_mcp, "_edi_856_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_edi_810_svc():
    with patch.object(integrations_mcp, "_edi_810_svc", MagicMock()) as mock_svc:
        yield mock_svc


@pytest.fixture
def mock_edi_catalog_svc():
    with patch.object(integrations_mcp, "_edi_catalog_svc", MagicMock()) as mock_svc:
        yield mock_svc


class TestPartnerTools:
    """Tests for list_edi_partners and get_edi_partner tools."""

    def test_list_edi_partners(self, mock_partner_svc):
        mock_partner_svc.list.return_value = [
            {"id": 1, "partner_name": "Carrefour UAE", "partner_code": "CRF-UAE", "is_active": True},
            {"id": 2, "partner_name": "Lulu Hypermarket", "partner_code": "LULU-HQ", "is_active": True},
        ]

        res = integrations_mcp._list_edi_partners(is_active=True, standard="ANSI_X12", limit=10)
        assert len(res) == 2
        assert res[0]["partner_code"] == "CRF-UAE"
        mock_partner_svc.list.assert_called_with(
            filters={"is_active": True, "edi_standard": "ANSI_X12"},
            limit=10,
        )

    def test_get_edi_partner_by_id(self, mock_partner_svc, mock_sku_mapping_svc):
        mock_partner_svc.get.return_value = {
            "id": 1,
            "partner_name": "Carrefour UAE",
            "partner_code": "CRF-UAE",
            "edi_standard": "ANSI_X12",
        }
        mock_sku_mapping_svc.list.return_value = [{"id": 101}, {"id": 102}]

        res = integrations_mcp._get_edi_partner(id=1)
        assert res["id"] == 1
        assert res["partner_code"] == "CRF-UAE"
        assert res["sku_mappings_count"] == 2
        mock_partner_svc.get.assert_called_with(1)

    def test_get_edi_partner_by_code(self, mock_partner_svc, mock_sku_mapping_svc):
        mock_partner_svc.list.return_value = [{
            "id": 2,
            "partner_name": "Lulu Hypermarket",
            "partner_code": "LULU-HQ",
        }]
        mock_sku_mapping_svc.list.return_value = []

        res = integrations_mcp._get_edi_partner(partner_code="LULU-HQ")
        assert res["id"] == 2
        assert res["partner_code"] == "LULU-HQ"
        assert res["sku_mappings_count"] == 0
        mock_partner_svc.list.assert_called_with(filters={"partner_code": "LULU-HQ"}, limit=1)

    def test_get_edi_partner_not_found(self, mock_partner_svc):
        mock_partner_svc.get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            integrations_mcp._get_edi_partner(id=999)


class TestIngestionAndReprocessingTools:
    """Tests for ingest_edi_document and reprocess_edi_transaction tools."""

    def test_ingest_edi_document_850(self, mock_edi_850_svc):
        mock_res = EdiIngestResult(
            transaction_id=10,
            transaction_number="TXN-2026-001",
            status="PROCESSED",
            standard="ANSI_X12",
            document_type="850",
            sales_order_id=501,
            sales_order_number="SO-2026-001",
            ack_generated=True,
            ack_payload="ISA*...*997~",
        )
        mock_edi_850_svc.ingest_inbound_order.return_value = mock_res

        raw_x12 = "ISA*00*          *00*          *ZZ*CRF-UAE        *ZZ*NOVA           *260908*1200*U*00401*000000001*0*T*:~GS*PO*CRF-UAE*NOVA*20260908*1200*1*X*004010~ST*850*0001~BEG*00*NE*PO-998877**20260908~SE*4*0001~GE*1*1~IEA*1*000000001~"
        res = integrations_mcp._ingest_edi_document(
            raw_payload=raw_x12,
            auto_confirm=True,
        )
        assert res["transaction_id"] == 10
        assert res["status"] == "PROCESSED"
        assert res["sales_order_number"] == "SO-2026-001"
        mock_edi_850_svc.ingest_inbound_order.assert_called_once()

    def test_ingest_edi_document_catalog_routing(self, mock_edi_catalog_svc):
        mock_cat_res = MagicMock()
        mock_cat_res.transaction_id = 15
        mock_cat_res.catalog_code = "CAT-2026-01"
        mock_cat_res.sync_status = "SYNCED"
        mock_cat_res.partner_id = 2
        mock_cat_res.errors = []
        mock_cat_res.total_items = 20
        mock_cat_res.matched_items = 18
        mock_edi_catalog_svc.ingest_inbound_catalog.return_value = mock_cat_res

        res = integrations_mcp._ingest_edi_document(
            raw_payload="ISA*...~ST*832*0001~BCT*RC*CAT-2026-01~SE*3*0001~IEA*1*1~",
            document_type="832",
        )
        assert res["transaction_id"] == 15
        assert res["status"] == "SYNCED"
        assert res["document_type"] == "832"
        mock_edi_catalog_svc.ingest_inbound_catalog.assert_called_once()

    def test_ingest_edi_document_empty_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            integrations_mcp._ingest_edi_document(raw_payload="   ")

    def test_reprocess_edi_transaction(self, mock_edi_850_svc):
        mock_res = EdiIngestResult(
            transaction_id=12,
            transaction_number="TXN-2026-002",
            status="PROCESSED",
            standard="ANSI_X12",
            document_type="850",
            sales_order_id=502,
            sales_order_number="SO-2026-002",
        )
        mock_edi_850_svc.reprocess_transaction.return_value = mock_res

        res = integrations_mcp._reprocess_edi_transaction(
            id=12,
            force_confirm=True,
            override_price_tolerance=5.0,
        )
        assert res["transaction_id"] == 12
        assert res["status"] == "PROCESSED"
        mock_edi_850_svc.reprocess_transaction.assert_called_with(
            transaction_id=12,
            force_confirm=True,
            override_price_tolerance=5.0,
        )

    def test_reprocess_edi_transaction_missing_id(self):
        with pytest.raises(ValueError, match="Transaction id must be provided"):
            integrations_mcp._reprocess_edi_transaction()


class TestTransactionQueryTools:
    """Tests for list_edi_transactions and get_edi_transaction tools."""

    def test_list_edi_transactions(self, mock_transaction_svc):
        mock_transaction_svc.list.return_value = [
            {"id": 1, "transaction_number": "TXN-01", "status": "PROCESSED"},
            {"id": 2, "transaction_number": "TXN-02", "status": "FAILED"},
        ]

        res = integrations_mcp._list_edi_transactions(status="FAILED", limit=20)
        assert len(res) == 2
        mock_transaction_svc.list.assert_called_with(
            filters={"status": "FAILED"},
            limit=20,
        )

    def test_get_edi_transaction(self, mock_transaction_svc):
        mock_transaction_svc.get.return_value = {
            "id": 1,
            "transaction_number": "TXN-01",
            "raw_payload": "ISA*...~",
            "parsed_data": {"po_number": "PO-100"},
            "status": "PROCESSED",
        }

        res = integrations_mcp._get_edi_transaction(id=1)
        assert res["id"] == 1
        assert res["transaction_number"] == "TXN-01"
        mock_transaction_svc.get.assert_called_with(1)

    def test_get_edi_transaction_not_found(self, mock_transaction_svc):
        mock_transaction_svc.get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            integrations_mcp._get_edi_transaction(id=999)


class TestOutboundAndCatalogTools:
    """Tests for generate_edi_asn, transmit_edi_invoice, and sync_supplier_catalog."""

    def test_generate_edi_asn(self, mock_edi_856_svc):
        mock_res = EdiAsnGenerateResponse(
            transaction_id=20,
            transaction_number="TXN-856-001",
            delivery_id=77,
            control_number="000000001",
            standard="ANSI_X12",
            document_type="856",
            sscc_pallets_count=2,
            sscc_barcodes=["000123456700000018", "000123456700000025"],
            edi_payload="ISA*...*856*...~",
        )
        mock_edi_856_svc.generate_asn_for_delivery.return_value = mock_res

        res = integrations_mcp._generate_edi_asn(
            delivery_id=77,
            carrier_name="DHL Freight",
            tracking_number="TRK-99001",
            vehicle_number="DXB-12345",
        )
        assert res["transaction_id"] == 20
        assert res["delivery_id"] == 77
        assert res["sscc_pallets_count"] == 2
        mock_edi_856_svc.generate_asn_for_delivery.assert_called_with(
            delivery_id=77,
            partner_id=None,
            carrier_name="DHL Freight",
            tracking_number="TRK-99001",
            vehicle_number="DXB-12345",
            seal_number=None,
            auto_generate_sscc=True,
        )

    def test_transmit_edi_invoice(self, mock_edi_810_svc):
        mock_res = EdiInvoiceTransmitResponse(
            transaction_id=30,
            transaction_number="TXN-810-001",
            invoice_id=90,
            invoice_number="INV-2026-001",
            control_number="000000001",
            standard="ANSI_X12",
            document_type="810",
            edi_payload="ISA*...*810*...~",
        )
        mock_edi_810_svc.transmit_invoice.return_value = mock_res

        res = integrations_mcp._transmit_edi_invoice(
            invoice_id=90,
            delivery_id=77,
            partner_id=1,
        )
        assert res["transaction_id"] == 30
        assert res["invoice_id"] == 90
        assert res["invoice_number"] == "INV-2026-001"
        mock_edi_810_svc.transmit_invoice.assert_called_once()

    def test_sync_supplier_catalog(self, mock_edi_catalog_svc):
        mock_res = EdiCatalogSyncResponse(
            partner_id=1,
            catalog_code="CAT-2026-Q3",
            total_items=10,
            matched_items=9,
            unmatched_items=1,
            price_updated_items=2,
            sync_status="SYNCED",
        )
        mock_edi_catalog_svc.sync_catalog.return_value = mock_res

        items = [
            {"buyer_sku": "SKU-A", "product_name": "Product A", "list_price": 10.5},
            {"buyer_sku": "SKU-B", "product_name": "Product B", "list_price": 20.0},
        ]
        res = integrations_mcp._sync_supplier_catalog(
            partner_id=1,
            catalog_code="CAT-2026-Q3",
            items=items,
            auto_match_skus=True,
        )
        assert res["partner_id"] == 1
        assert res["total_items"] == 10
        assert res["matched_items"] == 9
        mock_edi_catalog_svc.sync_catalog.assert_called_with(
            partner_id=1,
            catalog_code="CAT-2026-Q3",
            items=items,
            auto_match_skus=True,
        )


class TestResources:
    """Tests for MCP integrations resources."""

    def test_resource_list_partners(self, mock_partner_svc):
        mock_partner_svc.list.return_value = [
            {"id": 1, "partner_name": "Carrefour", "is_active": True},
        ]
        res = integrations_mcp._resource_list_partners()
        assert len(res) == 1
        assert res[0]["partner_name"] == "Carrefour"
        mock_partner_svc.list.assert_called_with(filters={"is_active": True}, limit=100)

    def test_resource_list_transactions(self, mock_transaction_svc):
        mock_transaction_svc.list.return_value = [
            {"id": 10, "transaction_number": "TXN-01"},
        ]
        res = integrations_mcp._resource_list_transactions()
        assert len(res) == 1
        assert res[0]["transaction_number"] == "TXN-01"
        mock_transaction_svc.list.assert_called_with(limit=50)


class TestToolRegistrationAndRegistryIntegration:
    """Tests verifying tools and resources registration, safety tiers, and propose/confirm."""

    def test_register_tools_registers_all(self):
        register_tools()
        tools = get_tools()
        tool_names = [t.name for t in tools]
        expected = [
            "list_edi_partners",
            "get_edi_partner",
            "ingest_edi_document",
            "list_edi_transactions",
            "get_edi_transaction",
            "reprocess_edi_transaction",
            "generate_edi_asn",
            "transmit_edi_invoice",
            "sync_supplier_catalog",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} was not registered"

        tier2_tools = [t.name for t in tools if t.tier == "tier2"]
        assert "transmit_edi_invoice" in tier2_tools

        tier1_tools = [t.name for t in tools if t.tier == "tier1" and t.name != "confirm_action"]
        assert "list_edi_partners" in tier1_tools
        assert "get_edi_partner" in tier1_tools
        assert "ingest_edi_document" in tier1_tools
        assert "generate_edi_asn" in tier1_tools
        assert "sync_supplier_catalog" in tier1_tools

        resources = list_resources()
        resource_uris = [r.uri for r in resources]
        assert "nova://integrations/edi/partners" in resource_uris
        assert "nova://integrations/edi/transactions" in resource_uris

    def test_tier2_propose_and_confirm_transmit_invoice(self, mock_edi_810_svc):
        register_tools()
        mock_res = EdiInvoiceTransmitResponse(
            transaction_id=88,
            transaction_number="TXN-810-088",
            invoice_id=45,
            invoice_number="INV-45",
            control_number="000000088",
            standard="ANSI_X12",
            document_type="810",
            edi_payload="ISA*...~",
        )
        mock_edi_810_svc.transmit_invoice.return_value = mock_res

        # Step 1: Propose (Tier 2 should not execute handler)
        proposal = propose_action(
            "transmit_edi_invoice",
            {"invoice_id": 45, "delivery_id": 12},
            user={"id": 1, "business_id": 10},
        )
        assert "action_id" in proposal
        assert proposal["tool"] == "transmit_edi_invoice"
        mock_edi_810_svc.transmit_invoice.assert_not_called()

        # Step 2: Confirm (Executes proposed action)
        result = confirm_action(proposal["action_id"], user={"id": 1, "business_id": 10})
        assert result["transaction_id"] == 88
        assert result["invoice_number"] == "INV-45"
        mock_edi_810_svc.transmit_invoice.assert_called_once()

    def test_direct_call_tool_with_tenant_scoping(self, mock_partner_svc):
        register_tools()
        mock_partner_svc.list.return_value = [
            {"id": 1, "partner_name": "Carrefour", "business_id": 77},
        ]

        user_context = {"id": 42, "username": "admin", "business_id": 77}
        res = call_tool("list_edi_partners", {"is_active": True}, user=user_context)
        assert len(res) == 1
        assert res[0]["partner_name"] == "Carrefour"
