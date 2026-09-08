"""
Tests for Cold Chain and HACCP FastAPI controllers (T0124I, T0125I, T0126I, T0127I, T0128I).
Verifies route registration, authentication, RBAC permission enforcement, and custom endpoint handling.
"""
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.auth.jwt import create_access_token
from modules.core.context import clear_current_tenant
from modules.warehouse.models.temperature_zone import TemperatureCheckResponse
from modules.quality.models.haccp_audit import HACCPComplianceReportResponse


@pytest.fixture(autouse=True)
def cleanup_tenant():
    clear_current_tenant()
    yield
    clear_current_tenant()


@pytest.fixture
def client():
    return TestClient(app)


def test_cold_chain_routes_registered():
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # T0124I (Temperature Zones)
    assert "/api/T0124I/" in paths
    assert "/api/T0124I/{id}/reading" in paths
    assert "/api/T0124I/{id}/bins" in paths

    # T0125I (Warehouse Bins & Compatibility)
    assert "/api/T0125I/" in paths
    assert "/api/T0125I/check-compatibility" in paths

    # T0126I (Vehicle Compartments)
    assert "/api/T0126I/" in paths

    # T0127I (Excursion Alerts)
    assert "/api/T0127I/" in paths
    assert "/api/T0127I/{id}/acknowledge" in paths
    assert "/api/T0127I/{id}/resolve" in paths
    assert "/api/T0127I/{id}/quarantine" in paths

    # T0128I (HACCP Checkpoints & Reports)
    assert "/api/T0128I/" in paths
    assert "/api/T0128I/checkpoint" in paths
    assert "/api/T0128I/compliance-report" in paths


def test_cold_chain_unauthenticated_rejected(client):
    resp = client.get("/api/T0124I/")
    assert resp.status_code in (401, 403)

    resp = client.get("/api/T0127I/")
    assert resp.status_code in (401, 403)


def test_cold_chain_authenticated_with_permission(client):
    token = create_access_token(user_id=1, business_id=1)
    mock_user = {
        "id": 1,
        "username": "cold_chain_mgr",
        "role": "Manager",
        "permissions": ["WAREHOUSE_VIEW", "QUALITY_VIEW"],
        "business_id": 1,
    }

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user), \
         patch("modules.warehouse.controllers.T0124I.service.list", return_value=[]):
        resp = client.get("/api/T0124I/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []


def test_temperature_compatibility_endpoint(client):
    token = create_access_token(user_id=1, business_id=1)
    mock_user = {
        "id": 1,
        "username": "wh_user",
        "role": "Operator",
        "permissions": ["WAREHOUSE_VIEW"],
        "business_id": 1,
    }
    mock_check_res = TemperatureCheckResponse(
        product_id=10,
        product_name="Frozen Fish",
        required_profile="Frozen",
        destination_type="Zone",
        destination_id=2,
        destination_label="Freezer Zone 2",
        is_compatible=True,
        message="Compatible with target zone",
        is_haccp_violation=False,
        quarantine_recommended=False,
    )

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user), \
         patch("modules.warehouse.controllers.T0125I.cold_chain_service.check_temperature_compatibility", return_value=mock_check_res):
        resp = client.post(
            "/api/T0125I/check-compatibility",
            json={"product_id": 10, "target_zone_id": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_compatible"] is True
        assert data["destination_type"] == "Zone"


def test_haccp_compliance_report_endpoint(client):
    token = create_access_token(user_id=1, business_id=1)
    mock_user = {
        "id": 1,
        "username": "qa_auditor",
        "role": "Quality Inspector",
        "permissions": ["QUALITY_VIEW"],
        "business_id": 1,
    }
    mock_report = HACCPComplianceReportResponse(
        report_title="HACCP Cold-Chain Quality Audit Report",
        is_fully_compliant=True,
        overall_compliance_status="COMPLIANT",
        total_checkpoints_logged=4,
        compliant_checkpoints=4,
        excursion_checkpoints=0,
        compliance_certificate_number="HACCP-CERT-2026-001",
        stages_covered=["GoodsReceipt", "DestinationDelivery"],
        checkpoint_readings=[],
        excursions_summary=[],
        summary_notes="All compliant",
        min_recorded_temperature=-20.0,
        max_recorded_temperature=-18.5,
        average_recorded_temperature=-19.2,
        product_id=5,
        product_name="Frozen Fish",
        product_sku="SKU-FISH",
        batch_number="LOT-FISH-01",
        delivery_run_id=None,
        delivery_run_number=None,
        required_temperature_profile="Frozen",
        critical_temperature_limit=-18.0,
        generated_at=datetime.utcnow(),
    )

    with patch("packages.auth.deps.get_user_by_id", return_value=mock_user), \
         patch("modules.quality.controllers.T0128I.haccp_service.compile_compliance_report", return_value=mock_report):
        resp = client.get(
            "/api/T0128I/compliance-report?batch_number=LOT-FISH-01",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_compliance_status"] == "COMPLIANT"
        assert data["compliance_certificate_number"] == "HACCP-CERT-2026-001"
