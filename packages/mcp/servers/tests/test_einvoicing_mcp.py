import pytest
from unittest.mock import patch, MagicMock
from packages.mcp import registry
from packages.mcp.servers import accounting_mcp
from packages.mcp.servers.accounting_mcp import register_tools
from modules.accounting.models.einvoice import ClearanceSubmissionResponse, QRCodeResponse


@pytest.fixture(autouse=True)
def clear_mcp_registry():
    registry._tools.clear()
    registry._resources.clear()
    yield
    registry._tools.clear()
    registry._resources.clear()


class TestEinvoicingMcp:
    def test_generate_einvoice_xml_handler(self):
        with patch.object(accounting_mcp._einvoice_svc, "generate_ubl_xml") as mock_gen, \
             patch.object(accounting_mcp._einvoice_svc, "get_by_invoice_id") as mock_get:
            mock_gen.return_value = "<Invoice>Generated XML</Invoice>"
            mock_get.return_value = {
                "invoice_id": 42,
                "invoice_uuid": "test-uuid-1234",
                "invoice_hash": "abc123hash",
                "qr_code_tlv": "AQZOYW1l...",
                "clearance_status": "Draft",
                "subtype": "0100000",
                "icv": 5,
            }

            res = accounting_mcp._generate_einvoice_xml(invoice_id=42, subtype="0100000")
            assert res["invoice_id"] == 42
            assert res["ubl_xml"] == "<Invoice>Generated XML</Invoice>"
            assert res["invoice_uuid"] == "test-uuid-1234"
            assert res["invoice_hash"] == "abc123hash"
            assert res["clearance_status"] == "Draft"
            mock_gen.assert_called_once_with(invoice_id=42, profile_id=None, subtype="0100000")

    def test_sign_einvoice_handler(self):
        with patch.object(accounting_mcp._einvoice_svc, "sign_einvoice") as mock_sign:
            mock_sign.return_value = {
                "id": 10,
                "invoice_id": 42,
                "invoice_hash": "signed_hash_123",
                "digital_signature": "MEQCIFyZ...",
                "clearance_status": "Draft",
            }
            res = accounting_mcp._sign_einvoice(invoice_id=42, profile_id=1)
            assert res["invoice_id"] == 42
            assert res["digital_signature"] == "MEQCIFyZ..."
            mock_sign.assert_called_once_with(invoice_id=42, profile_id=1)

    def test_submit_einvoice_clearance_handler(self):
        with patch.object(accounting_mcp._einvoice_svc, "submit_clearance") as mock_submit:
            mock_resp = ClearanceSubmissionResponse(
                success=True,
                invoice_id=42,
                invoice_uuid="uuid-42",
                clearance_status="Cleared",
                clearance_id="IRN-998877",
                qr_code_tlv="AQZOYW1l...",
                invoice_hash="hash-42",
                validation_results={"status": "PASS"},
            )
            mock_submit.return_value = mock_resp

            res = accounting_mcp._submit_einvoice_clearance(invoice_id=42, environment="Sandbox", auto_sign=True)
            assert res["success"] is True
            assert res["clearance_status"] == "Cleared"
            assert res["clearance_id"] == "IRN-998877"
            mock_submit.assert_called_once_with(invoice_id=42, profile_id=None, environment="Sandbox", auto_sign=True)

    def test_get_einvoice_status_found(self):
        with patch.object(accounting_mcp._einvoice_svc, "get_by_invoice_id") as mock_get:
            mock_get.return_value = {
                "id": 1,
                "invoice_id": 42,
                "clearance_status": "Cleared",
                "clearance_id": "IRN-001",
            }
            res = accounting_mcp._get_einvoice_status(invoice_id=42)
            assert res["invoice_id"] == 42
            assert res["clearance_status"] == "Cleared"
            mock_get.assert_called_once_with(invoice_id=42)

    def test_get_einvoice_status_not_found(self):
        with patch.object(accounting_mcp._einvoice_svc, "get_by_invoice_id") as mock_get:
            mock_get.return_value = None
            res = accounting_mcp._get_einvoice_status(invoice_id=999)
            assert res["invoice_id"] == 999
            assert res["clearance_status"] == "Not_Generated"

    def test_get_einvoice_qr_code_handler(self):
        with patch.object(accounting_mcp._einvoice_svc, "generate_qr_code") as mock_qr:
            mock_qr.return_value = QRCodeResponse(
                invoice_id=42,
                qr_code_tlv="AQZOYW1l...",
                seller_name="Nova Global Trading LLC",
                tax_id="300012345600003",
                timestamp="2026-09-05T12:00:00Z",
                total_amount=115.0,
                vat_total=15.0,
            )
            res = accounting_mcp._get_einvoice_qr_code(invoice_id=42)
            assert res["invoice_id"] == 42
            assert res["qr_code_tlv"] == "AQZOYW1l..."
            assert res["total_amount"] == 115.0
            mock_qr.assert_called_once_with(invoice_id=42)

    def test_get_fiscal_profile_handler(self):
        with patch.object(accounting_mcp._einvoice_svc, "get_active_fiscal_profile") as mock_prof:
            mock_prof.return_value = {
                "id": 1,
                "profile_name": "Main ZATCA Profile",
                "authority_code": "ZATCA",
                "seller_name": "Nova Global Trading LLC",
                "tax_id": "300012345600003",
            }
            res = accounting_mcp._get_fiscal_profile(profile_id=1)
            assert res["profile_name"] == "Main ZATCA Profile"
            mock_prof.assert_called_once_with(profile_id=1)

    def test_configure_fiscal_profile_create(self):
        with patch.object(accounting_mcp._fiscal_profile_repo, "create") as mock_create:
            mock_create.return_value = {
                "id": 2,
                "profile_name": "New Branch Profile",
                "authority_code": "ZATCA",
                "seller_name": "Nova Branch LLC",
                "tax_id": "300099999900003",
            }
            res = accounting_mcp._configure_fiscal_profile(
                profile_name="New Branch Profile",
                seller_name="Nova Branch LLC",
                tax_id="300099999900003",
            )
            assert res["id"] == 2
            assert res["seller_name"] == "Nova Branch LLC"
            mock_create.assert_called_once()

    def test_configure_fiscal_profile_update(self):
        with patch.object(accounting_mcp._fiscal_profile_repo, "update") as mock_update, \
             patch.object(accounting_mcp._fiscal_profile_repo, "get") as mock_get:
            mock_get.return_value = {
                "id": 1,
                "profile_name": "Updated Profile",
                "authority_code": "ZATCA",
                "seller_name": "Nova Global Trading LLC",
                "tax_id": "300012345600003",
            }
            res = accounting_mcp._configure_fiscal_profile(
                profile_id=1,
                profile_name="Updated Profile",
            )
            assert res["id"] == 1
            assert res["profile_name"] == "Updated Profile"
            mock_update.assert_called_once()

    def test_registered_einvoice_tools_in_registry(self):
        register_tools()
        tools = {t.name: t for t in registry.get_tools()}
        
        expected_tools = [
            "generate_einvoice_xml",
            "sign_einvoice",
            "submit_einvoice_clearance",
            "get_einvoice_status",
            "get_einvoice_qr_code",
            "get_fiscal_profile",
            "configure_fiscal_profile",
        ]
        for t_name in expected_tools:
            assert t_name in tools, f"Tool {t_name} is missing in registry"
            assert tools[t_name].tier == "tier1"

    def test_registered_resources_in_registry(self):
        register_tools()
        uris = [r.uri for r in registry.list_resources()]
        assert "nova://accounting/fiscal-profiles" in uris
        assert "nova://accounting/einvoices" in uris

    def test_call_tool_generate_einvoice_xml_via_registry(self):
        register_tools()
        with patch.object(accounting_mcp._einvoice_svc, "generate_ubl_xml") as mock_gen, \
             patch.object(accounting_mcp._einvoice_svc, "get_by_invoice_id") as mock_get:
            mock_gen.return_value = "<Invoice>XML</Invoice>"
            mock_get.return_value = {
                "invoice_id": 10,
                "invoice_uuid": "uuid-10",
                "invoice_hash": "hash-10",
                "qr_code_tlv": "qr-10",
                "clearance_status": "Draft",
            }
            res = registry.call_tool("generate_einvoice_xml", {"invoice_id": 10})
            assert res["invoice_id"] == 10
            assert res["ubl_xml"] == "<Invoice>XML</Invoice>"
