"""
Nova ERP — Unit & Integration Tests for B2B EDI Gateway & T-Code Controllers (T0124I-T0128I)
Tests endpoints in:
- modules/integrations/controllers/T0124I.py (Trading Partners)
- modules/integrations/controllers/T0125I.py (SKU Cross-Reference Matrix)
- modules/integrations/controllers/T0126I.py (EDI Transactions)
- modules/integrations/controllers/T0127I.py (SSCC Pallet Logistics)
- modules/integrations/controllers/T0128I.py (Supplier Catalog Sync)
- modules/integrations/controllers/edi_controller.py (EDI Gateway API)
"""

import io
from unittest.mock import patch
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from packages.auth.deps import get_current_user
from modules.integrations.controllers.T0124I import router as t0124_router
from modules.integrations.controllers.T0125I import router as t0125_router
from modules.integrations.controllers.T0126I import router as t0126_router
from modules.integrations.controllers.T0127I import router as t0127_router
from modules.integrations.controllers.T0128I import router as t0128_router
from modules.integrations.controllers.edi_controller import (
    router as edi_router,
    edi_850_service,
    edi_856_service,
    edi_810_service,
    edi_catalog_service,
    cross_reference_service,
    EDI_TRANSACTION_REPO,
    EDI_SSCC_PALLET_REPO,
)
from modules.integrations.models.edi import (
    EdiIngestResult,
    EdiAsnGenerateResponse,
    EdiInvoiceTransmitResponse,
)
from modules.integrations.services.edi.cross_reference_service import (
    LineCrossReferenceResult,
    SkuResolutionResult,
    UomConversionResult,
    PriceVerificationResult,
)
from modules.integrations.services.edi.edi_catalog_service import CatalogSyncResult, CatalogExportResult

app = FastAPI()
app.dependency_overrides[get_current_user] = lambda: {
    "id": 1,
    "username": "edi_admin",
    "role": "EDI Integration Admin",
    "business_id": 10,
}

app.include_router(t0124_router)
app.include_router(t0125_router)
app.include_router(t0126_router)
app.include_router(t0127_router)
app.include_router(t0128_router)
app.include_router(edi_router)

client = TestClient(app)


class TestTCodeCrudControllers:
    """Test suite for T-Code CRUD controllers (T0124I - T0128I)."""

    def test_t0124i_router_routes(self):
        """Verify T0124I router prefix and routes."""
        assert t0124_router.prefix == "/api/T0124I"
        route_paths = [r.path for r in t0124_router.routes]
        assert "/api/T0124I/" in route_paths
        assert "/api/T0124I/{id}" in route_paths

    def test_t0125i_router_routes(self):
        """Verify T0125I router prefix and routes."""
        assert t0125_router.prefix == "/api/T0125I"
        route_paths = [r.path for r in t0125_router.routes]
        assert "/api/T0125I/" in route_paths
        assert "/api/T0125I/{id}" in route_paths

    def test_t0126i_router_routes(self):
        """Verify T0126I router prefix and routes."""
        assert t0126_router.prefix == "/api/T0126I"
        route_paths = [r.path for r in t0126_router.routes]
        assert "/api/T0126I/" in route_paths
        assert "/api/T0126I/{id}" in route_paths

    def test_t0127i_router_routes(self):
        """Verify T0127I router prefix and routes."""
        assert t0127_router.prefix == "/api/T0127I"
        route_paths = [r.path for r in t0127_router.routes]
        assert "/api/T0127I/" in route_paths
        assert "/api/T0127I/{id}" in route_paths

    def test_t0128i_router_routes(self):
        """Verify T0128I router prefix and routes."""
        assert t0128_router.prefix == "/api/T0128I"
        route_paths = [r.path for r in t0128_router.routes]
        assert "/api/T0128I/" in route_paths
        assert "/api/T0128I/{id}" in route_paths


class TestEdiGatewayController:
    """Test suite for EDI Gateway endpoints."""

    def test_ingest_order_success(self):
        """Test POST /api/edi/ingest with valid 850 PO payload."""
        mock_result = EdiIngestResult(
            transaction_id=101,
            transaction_number="TXN-850-000101",
            status="PROCESSED",
            standard="ANSI_X12",
            document_type="850",
            control_number="000000101",
            partner_id=1,
            partner_code="CRF-UAE",
            sales_order_id=50,
            sales_order_number="SO-1050",
            ack_generated=True,
            ack_payload="ISA*00*...*997*...",
            price_discrepancies=[],
            errors=[],
        )

        with patch.object(edi_850_service, "ingest_inbound_order", return_value=mock_result):
            resp = client.post(
                "/api/edi/ingest",
                json={
                    "partner_id": 1,
                    "raw_payload": "ISA*00*          *00*          *ZZ*CARREFOUR      *ZZ*NOVADIST       *260908*1200*U*00401*000000101*0*P*>~GS*PO*CARREFOUR*NOVADIST*20260908*1200*101*X*004010~ST*850*0001~BEG*00*NE*PO-99001**20260908~PO1*1*100*EA*12.50**CB*CRF-RICE-01~SE*4*0001~GE*1*101~IEA*1*000000101~",
                    "standard": "ANSI_X12",
                    "document_type": "850",
                },
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["transaction_id"] == 101
            assert data["status"] == "PROCESSED"
            assert data["sales_order_number"] == "SO-1050"

    def test_ingest_empty_payload_fails(self):
        """Test POST /api/edi/ingest with empty payload returns 400."""
        resp = client.post(
            "/api/edi/ingest",
            json={"raw_payload": "   "},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_edi_file_endpoint(self):
        """Test POST /api/edi/upload with file upload."""
        mock_result = EdiIngestResult(
            transaction_id=102,
            transaction_number="TXN-850-000102",
            status="PROCESSED",
            standard="EDIFACT",
            document_type="ORDERS",
            control_number="000000102",
            partner_id=2,
            partner_code="LULU-GRP",
            sales_order_id=51,
            sales_order_number="SO-1051",
            ack_generated=True,
            ack_payload="UNA:+.? 'UNB+UNOC:3+LULU+NOVA+260908:1200+102'UNH+1+CONTRL:D:96A:UN'...",
            errors=[],
        )

        with patch.object(edi_850_service, "ingest_inbound_order", return_value=mock_result):
            file_content = b"UNA:+.? 'UNB+UNOC:3+LULU+NOVA+260908:1200+102'UNH+1+ORDERS:D:96A:UN'BGM+220+PO-77001+9'UNT+4+1'UNZ+1+102'"
            resp = client.post(
                "/api/edi/upload",
                files={"file": ("order.edi", io.BytesIO(file_content), "application/octet-stream")},
                data={"partner_id": 2, "standard": "EDIFACT", "document_type": "ORDERS"},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["transaction_id"] == 102
            assert data["standard"] == "EDIFACT"

    def test_webhook_ingest_endpoint(self):
        """Test POST /api/edi/webhook and /api/edi/webhook/{partner_code}."""
        mock_result = EdiIngestResult(
            transaction_id=103,
            transaction_number="TXN-850-000103",
            status="PROCESSED",
            standard="ANSI_X12",
            document_type="850",
            sales_order_number="SO-1052",
            ack_payload="ISA*00*...",
            errors=[],
        )

        with patch.object(edi_850_service, "ingest_inbound_order", return_value=mock_result):
            # Test raw body webhook
            resp = client.post(
                "/api/edi/webhook/CRF-UAE",
                content="ISA*00*...~ST*850*0001~...~IEA*1*001~",
                headers={"content-type": "text/plain"},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["ok"] is True
            assert data["transaction_id"] == 103

    def test_reprocess_transaction_endpoint(self):
        """Test POST /api/edi/reprocess and /api/edi/transactions/{id}/reprocess."""
        mock_result = EdiIngestResult(
            transaction_id=105,
            transaction_number="TXN-850-000105",
            status="PROCESSED",
            standard="ANSI_X12",
            document_type="850",
            sales_order_id=55,
            sales_order_number="SO-1055",
            errors=[],
        )

        with patch.object(edi_850_service, "reprocess_transaction", return_value=mock_result):
            resp = client.post(
                "/api/edi/transactions/105/reprocess",
                json={"transaction_id": 105, "force_confirm": True, "override_price_tolerance": 5.0},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["transaction_id"] == 105
            assert data["status"] == "PROCESSED"

    def test_get_raw_and_ack_payload_endpoints(self):
        """Test GET /api/edi/transactions/{id}/raw and GET /api/edi/transactions/{id}/ack."""
        mock_tx = {
            "id": 105,
            "transaction_number": "TXN-850-000105",
            "standard": "ANSI_X12",
            "document_type": "850",
            "direction": "INBOUND",
            "status": "PROCESSED",
            "raw_payload": "ISA*00*...~IEA*1*001~",
            "parsed_data": {"header": {"po_number": "PO-123"}},
            "ack_status": "ACCEPTED",
            "ack_payload": "ISA*00*...*997*...~",
            "error_details": None,
        }

        with patch.object(EDI_TRANSACTION_REPO, "get", return_value=mock_tx):
            resp_raw = client.get("/api/edi/transactions/105/raw")
            assert resp_raw.status_code == status.HTTP_200_OK
            assert resp_raw.json()["raw_payload"] == "ISA*00*...~IEA*1*001~"

            resp_ack = client.get("/api/edi/transactions/105/ack")
            assert resp_ack.status_code == status.HTTP_200_OK
            assert resp_ack.json()["ack_status"] == "ACCEPTED"
            assert resp_ack.json()["ack_payload"] == "ISA*00*...*997*...~"

    def test_generate_asn_endpoint(self):
        """Test POST /api/edi/asn/generate and /api/edi/asn/{delivery_id}."""
        mock_asn_resp = EdiAsnGenerateResponse(
            transaction_id=201,
            transaction_number="TXN-856-000201",
            delivery_id=12,
            control_number="000000201",
            standard="ANSI_X12",
            document_type="856",
            sscc_pallets_count=2,
            sscc_barcodes=["001234567800000014", "001234567800000021"],
            edi_payload="ISA*00*...*856*...~",
        )

        with patch.object(edi_856_service, "generate_asn_for_delivery", return_value=mock_asn_resp):
            resp = client.post(
                "/api/edi/asn/generate",
                json={
                    "delivery_id": 12,
                    "carrier_name": "Swift Logistics",
                    "tracking_number": "TRK-9988",
                    "vehicle_number": "DXB-A-12345",
                },
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["delivery_id"] == 12
            assert data["sscc_pallets_count"] == 2
            assert len(data["sscc_barcodes"]) == 2

            # Test parameterized route /asn/{delivery_id}
            resp_by_id = client.post(
                "/api/edi/asn/12",
                json={"carrier_name": "Swift Logistics"},
            )
            assert resp_by_id.status_code == status.HTTP_200_OK

    def test_transmit_invoice_endpoint(self):
        """Test POST /api/edi/invoice/transmit and /api/edi/invoice/{invoice_id}."""
        mock_inv_resp = EdiInvoiceTransmitResponse(
            transaction_id=301,
            transaction_number="TXN-810-000301",
            invoice_id=25,
            invoice_number="INV-2026-0025",
            control_number="000000301",
            standard="ANSI_X12",
            document_type="810",
            edi_payload="ISA*00*...*810*...~",
        )

        with patch.object(edi_810_service, "transmit_invoice", return_value=mock_inv_resp):
            resp = client.post(
                "/api/edi/invoice/transmit",
                json={"invoice_id": 25, "delivery_id": 12},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["invoice_id"] == 25
            assert data["invoice_number"] == "INV-2026-0025"

            # Test parameterized route /invoice/{invoice_id}
            resp_by_id = client.post(
                "/api/edi/invoice/25",
                json={"delivery_id": 12},
            )
            assert resp_by_id.status_code == status.HTTP_200_OK

    def test_sync_catalog_endpoint(self):
        """Test POST /api/edi/catalog/sync."""
        mock_sync_resp = CatalogSyncResult(
            partner_id=1,
            catalog_code="CAT-2026-Q3",
            total_items=10,
            matched_items=8,
            unmatched_items=2,
            price_updated_items=3,
            sync_status="SYNCED",
        )

        with patch.object(edi_catalog_service, "sync_catalog", return_value=mock_sync_resp):
            resp = client.post(
                "/api/edi/catalog/sync",
                json={
                    "partner_id": 1,
                    "catalog_code": "CAT-2026-Q3",
                    "items": [
                        {"buyer_sku": "CRF-RICE-01", "product_name": "Basmati Rice 5kg", "list_price": 12.50}
                    ],
                },
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["catalog_code"] == "CAT-2026-Q3"
            assert data["matched_items"] == 8

    def test_export_catalog_endpoint(self):
        """Test POST /api/edi/catalog/export."""
        mock_exp_result = CatalogExportResult(
            partner_id=1,
            standard="ANSI_X12",
            catalog_code="EXP-2026",
            document_type="832",
            total_items=15,
            control_number="000000401",
            edi_payload="ISA*00*...*832*...~",
        )

        with patch.object(edi_catalog_service, "export_catalog", return_value=mock_exp_result):
            resp = client.post(
                "/api/edi/catalog/export",
                params={"partner_id": 1, "standard": "ANSI_X12", "catalog_code": "EXP-2026"},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["partner_id"] == 1
            assert data["total_items"] == 15

    def test_cross_reference_resolve_endpoint(self):
        """Test POST /api/edi/cross-reference/resolve."""
        mock_xref = LineCrossReferenceResult(
            line_number=1,
            buyer_sku="CRF-RICE-01",
            partner_sku_type="BUYER_PART_NO",
            product_id=5,
            product_name="Basmati Rice 5kg",
            internal_sku="SKU-RICE-5KG",
            ordered_qty=10.0,
            ordered_uom="CA",
            converted_qty=40.0,
            internal_uom="EA",
            uom_factor=4.0,
            ordered_price=48.00,
            expected_price=48.00,
            line_total=480.00,
            sku_resolution=SkuResolutionResult(matched=True, product_id=5, resolved_sku="SKU-RICE-5KG", partner_sku="CRF-RICE-01"),
            uom_conversion=UomConversionResult(original_quantity=10.0, original_uom="CA", converted_quantity=40.0, converted_uom="EA", conversion_factor=4.0, is_converted=True),
            price_verification=PriceVerificationResult(ordered_unit_price=48.0, expected_unit_price=48.0, effective_ordered_unit_price=48.0),
            has_discrepancy=False,
            discrepancy_info=None,
            errors=[],
        )

        with patch.object(cross_reference_service, "cross_reference_line", return_value=mock_xref):
            resp = client.post(
                "/api/edi/cross-reference/resolve",
                params={
                    "partner_id": 1,
                    "partner_sku": "CRF-RICE-01",
                    "partner_uom": "CA",
                    "ordered_price": 48.00,
                },
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["is_matched"] is True
            assert data["product_id"] == 5
            assert data["uom_conversion_factor"] == 4.0

    def test_bulk_import_mappings_endpoint(self):
        """Test POST /api/edi/sku-mappings/bulk-import."""
        mock_import_res = {
            "partner_id": 1,
            "total_submitted": 2,
            "imported_count": 2,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": [],
        }

        with patch.object(cross_reference_service, "bulk_import_mappings", return_value=mock_import_res):
            resp = client.post(
                "/api/edi/sku-mappings/bulk-import",
                params={"partner_id": 1, "overwrite_existing": False},
                json=[
                    {"product_id": 1, "partner_sku": "CRF-01", "partner_uom": "EA"},
                    {"product_id": 2, "partner_sku": "CRF-02", "partner_uom": "EA"},
                ],
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["imported_count"] == 2

    def test_sscc_generate_and_label_endpoint(self):
        """Test POST /api/edi/sscc/generate and GET /api/edi/sscc/{identifier}/label."""
        mock_created_pallet = {
            "id": 10,
            "sscc_barcode": "006291041000000017",
            "pallet_number": "PLT-000017",
            "package_type": "PALLET",
            "gross_weight_kg": 450.0,
            "status": "CREATED",
            "delivery_id": 8,
            "contents_summary": {"total_boxes": 20},
        }

        with patch.object(EDI_SSCC_PALLET_REPO, "create", return_value=mock_created_pallet), \
             patch.object(EDI_SSCC_PALLET_REPO, "get", return_value=mock_created_pallet):
            
            resp_gen = client.post(
                "/api/edi/sscc/generate",
                params={"delivery_id": 8, "gross_weight_kg": 450.0},
            )
            assert resp_gen.status_code == status.HTTP_200_OK
            data_gen = resp_gen.json()
            assert "sscc_barcode" in data_gen

            resp_lbl = client.get("/api/edi/sscc/10/label")
            assert resp_lbl.status_code == status.HTTP_200_OK
            data_lbl = resp_lbl.json()
            assert data_lbl["sscc_barcode"] == "006291041000000017"
            assert "label" in data_lbl
