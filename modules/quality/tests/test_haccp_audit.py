"""
Unit and integration tests for HACCP Quality Audit & Temperature Excursion Monitoring Service (T0127, T0128).
Covers multi-stage checkpoint logging, automated excursion alert triggers, quarantine workflows,
and receipt-to-delivery HACCP compliance report compilation.
"""
from datetime import datetime
import pytest
from unittest.mock import MagicMock

from modules.quality.models.haccp_audit import (
    ExcursionAlertCreate,
    ExcursionAlertUpdate,
    ExcursionAlertResponse,
    HACCPCheckpointLogCreate,
    HACCPCheckpointLogUpdate,
    HACCPCheckpointLogResponse,
    HACCPStageReading,
    HACCPComplianceReportResponse,
)
from modules.quality.services.haccp_audit_service import HaccpAuditService


class InMemoryRepo:
    def __init__(self, data=None):
        self._data = dict(data or {})
        self._next_id = max(self._data.keys(), default=0) + 1

    def list(self, filters=None, order_by=None, limit=50, offset=0, **kwargs):
        res = list(self._data.values())
        if filters:
            for k, v in filters.items():
                res = [r for r in res if r.get(k) == v]
        return res[offset:offset + limit]

    def get(self, id_val, **kwargs):
        return self._data.get(id_val)

    def create(self, payload, **kwargs):
        obj = dict(payload)
        new_id = obj.get('id') or self._next_id
        self._next_id = max(self._next_id, new_id + 1)
        obj['id'] = new_id
        self._data[new_id] = obj
        return obj

    def update(self, id_val, payload, **kwargs):
        if id_val not in self._data:
            return None
        self._data[id_val].update(payload)
        return self._data[id_val]

    def delete(self, id_val, **kwargs):
        if id_val in self._data:
            del self._data[id_val]
            return True
        return False


def test_haccp_model_instantiations():
    alert_req = ExcursionAlertCreate(
        alert_type="CriticalLimitExceeded",
        severity="Critical",
        recorded_temperature=9.5,
        max_threshold=4.0,
        min_threshold=2.0,
        product_id=1,
        batch_number="LOT-DAIRY-001",
        notes="Chiller compressor failure",
    )
    assert alert_req.alert_type == "CriticalLimitExceeded"
    assert alert_req.severity == "Critical"
    assert alert_req.recorded_temperature == 9.5

    log_req = HACCPCheckpointLogCreate(
        checkpoint_stage="WarehouseStorage",
        checkpoint_name="Cold Room 1 Core Probe",
        recorded_temperature=-19.5,
        critical_limit_max=-18.0,
        product_id=2,
        batch_number="LOT-BEEF-88",
    )
    assert log_req.checkpoint_stage == "WarehouseStorage"
    assert log_req.recorded_temperature == -19.5


def test_excursion_alert_lifecycle_and_quarantine():
    alert_repo = InMemoryRepo()
    prod_repo = InMemoryRepo({
        1: {'id': 1, 'name': 'Frozen Beef Ribeye', 'sku': 'SKU-FROZ-BEEF', 'critical_temp_limit': -18.0}
    })
    wh_repo = InMemoryRepo({10: {'id': 10, 'name': 'Distribution Center A'}})
    zone_repo = InMemoryRepo({20: {'id': 20, 'name': 'Deep Freezer Zone 1'}})
    user_repo = InMemoryRepo({5: {'id': 5, 'full_name': 'Quality Inspector John'}})

    service = HaccpAuditService(
        alert_repo=alert_repo,
        product_repo=prod_repo,
        wh_repo=wh_repo,
        zone_repo=zone_repo,
        user_repo=user_repo,
    )

    # 1. Create Alert with deviation calculation
    created = service.create_alert({
        'alert_type': 'TemperatureExcursion',
        'severity': 'Critical',
        'warehouse_id': 10,
        'zone_id': 20,
        'product_id': 1,
        'batch_number': 'LOT-BEEF-101',
        'recorded_temperature': -12.0,
        'max_threshold': -18.0,
        'min_threshold': -25.0,
    })
    assert created['id'] is not None
    assert created['alert_number'].startswith('EXC-')
    assert created['deviation_degrees'] == 6.0  # -12.0 - (-18.0) = 6.0 deg excursion
    assert created['status'] == 'Open'

    # 2. List Alerts with enrichment
    alerts = service.list_alerts()
    assert len(alerts) == 1
    assert alerts[0]['product_name'] == 'Frozen Beef Ribeye'
    assert alerts[0]['product_sku'] == 'SKU-FROZ-BEEF'
    assert alerts[0]['warehouse_name'] == 'Distribution Center A'
    assert alerts[0]['zone_name'] == 'Deep Freezer Zone 1'

    # 3. Acknowledge Alert
    acked = service.acknowledge_alert(created['id'], user_id=5, notes="Investigating dock door seal")
    assert acked['status'] == 'Acknowledged'
    assert acked['acknowledged_by'] == 5
    assert acked['acknowledged_at'] is not None
    assert "Investigating dock door seal" in acked['notes']

    # 4. Quarantine Lot
    quarantined = service.quarantine_lot(
        created['id'],
        quarantine_notes="Moved 50 boxes to quarantine staging pending microbiological inspection",
        user_id=5,
    )
    assert quarantined['status'] == 'Quarantined'
    assert quarantined['is_quarantined'] is True
    assert "quarantine staging" in quarantined['quarantine_notes']

    # 5. Resolve Alert
    resolved = service.resolve_alert(
        created['id'],
        resolution_action="Core temperature confirmed -20C, lab cleared lot for dispatch",
        user_id=5,
    )
    assert resolved['status'] == 'Resolved'
    assert resolved['resolved_by'] == 5
    assert "Core temperature confirmed" in resolved['resolution_action']


def test_haccp_checkpoint_logging_and_auto_excursion():
    alert_repo = InMemoryRepo()
    log_repo = InMemoryRepo()
    prod_repo = InMemoryRepo({
        1: {
            'id': 1,
            'name': 'Fresh Milk 1L',
            'sku': 'MILK-001',
            'temp_zone_type': 'Chilled',
            'min_temperature': 2.0,
            'max_temperature': 4.0,
            'critical_temp_limit': 6.0,
        }
    })

    service = HaccpAuditService(
        alert_repo=alert_repo,
        log_repo=log_repo,
        product_repo=prod_repo,
    )

    # 1. Compliant reading (3.5°C <= 6.0°C critical limit)
    log_ok = service.log_checkpoint({
        'checkpoint_stage': 'GoodsReceipt',
        'checkpoint_name': 'Inbound Delivery Gate 3',
        'recorded_temperature': 3.5,
        'product_id': 1,
        'batch_number': 'LOT-MILK-99',
    })
    assert log_ok['is_compliant'] is True
    assert log_ok['critical_limit_max'] == 6.0
    assert len(alert_repo.list()) == 0  # No alert generated

    # 2. Non-compliant reading (8.2°C > 6.0°C critical limit)
    log_breach = service.log_checkpoint({
        'checkpoint_stage': 'DestinationDelivery',
        'checkpoint_name': 'Customer Dock Handover',
        'recorded_temperature': 8.2,
        'product_id': 1,
        'batch_number': 'LOT-MILK-99',
    })
    assert log_breach['is_compliant'] is False
    assert log_breach['critical_limit_max'] == 6.0

    # Verify that an excursion alert was automatically generated
    alerts = alert_repo.list()
    assert len(alerts) == 1
    excursion_alert = alerts[0]
    assert excursion_alert['alert_type'] == 'CriticalLimitExceeded'
    assert excursion_alert['severity'] == 'Critical'
    assert excursion_alert['haccp_violation'] is True
    assert excursion_alert['quarantine_recommended'] is True
    assert excursion_alert['recorded_temperature'] == 8.2
    assert excursion_alert['deviation_degrees'] == 2.2  # 8.2 - 6.0 = 2.2


def test_haccp_compliance_report_compilation_all_compliant():
    alert_repo = InMemoryRepo()
    log_repo = InMemoryRepo()
    prod_repo = InMemoryRepo({
        10: {
            'id': 10,
            'name': 'Frozen Beef Halves',
            'sku': 'BEEF-HALVES',
            'temp_zone_type': 'Frozen',
            'critical_temp_limit': -18.0,
        }
    })
    run_repo = InMemoryRepo({100: {'id': 100, 'run_number': 'RUN-2026-0908'}})
    user_repo = InMemoryRepo({1: {'id': 1, 'full_name': 'Audit Inspector Alice'}})

    service = HaccpAuditService(
        alert_repo=alert_repo,
        log_repo=log_repo,
        product_repo=prod_repo,
        delivery_run_repo=run_repo,
        user_repo=user_repo,
    )

    # Log checkpoints across all 6 supply chain stages
    stages = [
        ('GoodsReceipt', 'Inbound Container Probe', -19.2),
        ('WarehouseStorage', 'Freezer Aisle 4 Continuous Sensor', -20.5),
        ('StagingDock', 'Dispatch Staging Cold Buffer', -18.8),
        ('VehicleDeparture', 'Reefer Truck Compartment A Departure', -19.0),
        ('TransitCheckpoint', 'Mid-Route GPS Logger Check', -18.5),
        ('DestinationDelivery', 'Supermarket Receiving Dock Handover', -18.2),
    ]

    for stage_name, ccp_name, temp_val in stages:
        service.log_checkpoint({
            'checkpoint_stage': stage_name,
            'checkpoint_name': ccp_name,
            'recorded_temperature': temp_val,
            'product_id': 10,
            'batch_number': 'LOT-BEEF-2026',
            'delivery_run_id': 100,
            'logged_by_id': 1,
        })

    # Compile report
    report = service.compile_compliance_report(
        product_id=10,
        batch_number='LOT-BEEF-2026',
        delivery_run_id=100,
    )

    assert report.is_fully_compliant is True
    assert report.overall_compliance_status == 'COMPLIANT'
    assert report.total_checkpoints_logged == 6
    assert report.compliant_checkpoints == 6
    assert report.excursion_checkpoints == 0
    assert report.min_recorded_temperature == -20.5
    assert report.max_recorded_temperature == -18.2
    assert report.compliance_certificate_number is not None
    assert report.compliance_certificate_number.startswith('HACCP-CERT-LOT-BEEF-2026-')
    assert len(report.stages_covered) == 6
    assert "CERTIFIED COMPLIANT" in report.summary_notes


def test_haccp_compliance_report_compilation_with_excursions():
    alert_repo = InMemoryRepo()
    log_repo = InMemoryRepo()
    prod_repo = InMemoryRepo({
        10: {
            'id': 10,
            'name': 'Frozen Beef Halves',
            'sku': 'BEEF-HALVES',
            'temp_zone_type': 'Frozen',
            'critical_temp_limit': -18.0,
        }
    })

    service = HaccpAuditService(
        alert_repo=alert_repo,
        log_repo=log_repo,
        product_repo=prod_repo,
    )

    # 1 Compliant log, 1 Breached log
    service.log_checkpoint({
        'checkpoint_stage': 'WarehouseStorage',
        'checkpoint_name': 'Cold Store 1',
        'recorded_temperature': -20.0,
        'product_id': 10,
        'batch_number': 'LOT-BEEF-FAIL',
    })
    service.log_checkpoint({
        'checkpoint_stage': 'TransitCheckpoint',
        'checkpoint_name': 'Truck Sensor',
        'recorded_temperature': -12.0,  # Exceeds -18.0°C limit!
        'product_id': 10,
        'batch_number': 'LOT-BEEF-FAIL',
    })

    report = service.compile_compliance_report(
        product_id=10,
        batch_number='LOT-BEEF-FAIL',
    )

    assert report.is_fully_compliant is False
    assert report.overall_compliance_status == 'NON_COMPLIANT'
    assert report.total_checkpoints_logged == 2
    assert report.compliant_checkpoints == 1
    assert report.excursion_checkpoints == 1
    assert report.compliance_certificate_number is None
    assert len(report.excursions_summary) == 1
    assert "NON-COMPLIANT" in report.summary_notes
