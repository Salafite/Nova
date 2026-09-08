"""
Unit and execution tests for Cold Chain and HACCP MCP tools registered in warehouse_mcp.py.
"""
from unittest.mock import patch, MagicMock
from packages.mcp.servers import warehouse_mcp
from packages.mcp.servers.warehouse_mcp import register_tools
from packages.mcp.registry import get_tools


class TestColdChainMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        register_tools()

    def test_cold_chain_tools_registered(self):
        tools = [t.name for t in get_tools()]
        assert "list_warehouse_temperature_zones" in tools
        assert "check_temperature_compatibility" in tools
        assert "log_haccp_temperature_checkpoint" in tools
        assert "get_haccp_compliance_audit_report" in tools
        assert "list_temperature_excursion_alerts" in tools
        assert "get_thermal_pick_sequence" in tools

    def test_list_warehouse_temperature_zones(self):
        mod = warehouse_mcp
        mock_zones = [
            {"id": 1, "zone_code": "ZONE-001", "name": "Freezer 1", "zone_type": "Frozen", "status": "Normal"}
        ]
        with patch.object(mod, "_cold_chain_svc", MagicMock()) as mock:
            mock.list_zones.return_value = mock_zones
            result = mod._list_warehouse_temperature_zones(warehouse_id=1, zone_type="Frozen")
            assert result == mock_zones
            mock.list_zones.assert_called_once_with(filters={"warehouse_id": 1, "zone_type": "Frozen"})

    def test_check_temperature_compatibility(self):
        mod = warehouse_mcp
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = {
            "product_id": 10,
            "product_name": "Frozen Beef",
            "is_compatible": False,
            "severity": "Critical",
            "is_haccp_violation": True,
            "quarantine_recommended": True,
            "message": "Critical HACCP Violation: Frozen product cannot be stored in Ambient zone",
        }
        with patch.object(mod, "_cold_chain_svc", MagicMock()) as mock:
            mock.check_temperature_compatibility.return_value = mock_resp
            result = mod._check_temperature_compatibility(product_id=10, target_zone_id=2)
            assert result["is_compatible"] is False
            assert result["severity"] == "Critical"
            assert result["is_haccp_violation"] is True
            mock.check_temperature_compatibility.assert_called_once_with(
                product_id=10,
                target_zone_id=2,
                target_bin_id=None,
                target_compartment_id=None,
                warehouse_id=None,
            )

    def test_log_haccp_temperature_checkpoint(self):
        mod = warehouse_mcp
        mock_log = {
            "id": 1,
            "log_number": "CCP-00001",
            "checkpoint_stage": "GoodsReceipt",
            "checkpoint_name": "Inbound Gate 1 Probe",
            "recorded_temperature": 3.8,
            "is_compliant": True,
        }
        with patch.object(mod, "_haccp_svc", MagicMock()) as mock:
            mock.log_checkpoint.return_value = mock_log
            result = mod._log_haccp_temperature_checkpoint(
                checkpoint_stage="GoodsReceipt",
                checkpoint_name="Inbound Gate 1 Probe",
                recorded_temperature=3.8,
                product_id=5,
                batch_number="LOT-2026-001",
            )
            assert result == mock_log
            mock.log_checkpoint.assert_called_once_with({
                "checkpoint_stage": "GoodsReceipt",
                "checkpoint_name": "Inbound Gate 1 Probe",
                "recorded_temperature": 3.8,
                "product_id": 5,
                "batch_number": "LOT-2026-001",
                "warehouse_id": None,
                "zone_id": None,
                "bin_id": None,
                "vehicle_id": None,
                "compartment_id": None,
                "delivery_run_id": None,
                "delivery_stop_id": None,
                "ambient_temperature": None,
                "sensor_device_id": None,
                "corrective_action": None,
            })

    def test_get_haccp_compliance_audit_report(self):
        mod = warehouse_mcp
        mock_report = MagicMock()
        mock_report.model_dump.return_value = {
            "report_title": "HACCP Cold-Chain Quality Audit Report: LOT-BEEF-001",
            "overall_compliance_status": "COMPLIANT",
            "is_fully_compliant": True,
            "total_checkpoints_logged": 5,
            "compliant_checkpoints": 5,
            "excursion_checkpoints": 0,
            "compliance_certificate_number": "HACCP-CERT-LOT-BEEF-001-2026",
        }
        with patch.object(mod, "_haccp_svc", MagicMock()) as mock:
            mock.compile_compliance_report.return_value = mock_report
            result = mod._get_haccp_compliance_audit_report(batch_number="LOT-BEEF-001")
            assert result["is_fully_compliant"] is True
            assert result["compliance_certificate_number"] == "HACCP-CERT-LOT-BEEF-001-2026"
            mock.compile_compliance_report.assert_called_once_with(
                batch_number="LOT-BEEF-001",
                product_id=None,
                delivery_run_id=None,
            )

    def test_list_temperature_excursion_alerts(self):
        mod = warehouse_mcp
        mock_alerts = [
            {"id": 1, "alert_number": "EXC-001", "severity": "Critical", "status": "Open", "deviation_degrees": 4.5}
        ]
        with patch.object(mod, "_haccp_svc", MagicMock()) as mock:
            mock.list_alerts.return_value = mock_alerts
            result = mod._list_temperature_excursion_alerts(status="Open", severity="Critical")
            assert result == mock_alerts
            mock.list_alerts.assert_called_once_with(filters={"status": "Open", "severity": "Critical"})

    def test_get_thermal_pick_sequence(self):
        mod = warehouse_mcp
        mock_item1 = MagicMock()
        mock_item1.model_dump.return_value = {"product_name": "Dry Rice", "thermal_priority_rank": 1, "suggested_picking_order": 1}
        mock_item2 = MagicMock()
        mock_item2.model_dump.return_value = {"product_name": "Frozen Beef", "thermal_priority_rank": 3, "suggested_picking_order": 2}

        with patch.object(mod, "_cold_chain_svc", MagicMock()) as mock:
            mock.get_thermal_pick_sequence.return_value = [mock_item1, mock_item2]
            raw_input = [
                {"product_id": 2, "product_name": "Frozen Beef", "temp_zone_type": "Frozen"},
                {"product_id": 1, "product_name": "Dry Rice", "temp_zone_type": "Ambient"},
            ]
            result = mod._get_thermal_pick_sequence(items=raw_input)
            assert len(result) == 2
            assert result[0]["product_name"] == "Dry Rice"
            assert result[1]["product_name"] == "Frozen Beef"
            mock.get_thermal_pick_sequence.assert_called_once_with(raw_input)
