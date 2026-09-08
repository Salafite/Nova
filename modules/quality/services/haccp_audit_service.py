"""
Nova ERP — HACCP Quality Audit & Temperature Excursion Monitoring Service
Manages real-time thermal excursion alerts, multi-stage HACCP checkpoint logs,
and automated receipt-to-delivery HACCP compliance audit reports.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from fastapi import HTTPException, status

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
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
from packages.database.sequence import (
    generate_excursion_alert_number,
    generate_haccp_log_number,
)
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

ALERT_REPO = CrudRepository(
    'T0127',
    business_columns=[
        'id', 'alert_number', 'alert_type', 'severity', 'status',
        'warehouse_id', 'zone_id', 'bin_id', 'vehicle_id', 'compartment_id',
        'delivery_run_id', 'product_id', 'batch_number', 'recorded_temperature',
        'min_threshold', 'max_threshold', 'deviation_degrees', 'duration_minutes',
        'haccp_critical_limit', 'haccp_violation', 'quarantine_recommended',
        'is_quarantined', 'quarantine_notes', 'acknowledged_at', 'acknowledged_by',
        'resolved_at', 'resolved_by', 'resolution_action', 'notes',
        'is_active', 'business_id'
    ]
)

LOG_REPO = CrudRepository(
    'T0128',
    business_columns=[
        'id', 'log_number', 'checkpoint_stage', 'checkpoint_name',
        'stage_reference_type', 'stage_reference_id', 'warehouse_id',
        'zone_id', 'bin_id', 'vehicle_id', 'compartment_id', 'delivery_run_id',
        'delivery_stop_id', 'product_id', 'batch_number', 'recorded_temperature',
        'critical_limit_min', 'critical_limit_max', 'is_compliant',
        'ambient_temperature', 'humidity_pct', 'logged_by_id', 'logged_at',
        'verified_by_id', 'verified_at', 'location_gps', 'sensor_device_id',
        'corrective_action', 'notes', 'is_active', 'business_id'
    ]
)

PRODUCT_REPO = CrudRepository(
    'T0003',
    business_columns=[
        'id', 'name', 'sku', 'barcode', 'is_cold_chain', 'temp_zone_type',
        'min_temperature', 'max_temperature', 'critical_temp_limit',
        'thermal_priority_rank', 'is_active', 'business_id'
    ]
)

WH_REPO = CrudRepository(
    'T0008',
    business_columns=['id', 'name', 'location', 'is_active', 'business_id']
)

ZONE_REPO = CrudRepository(
    'T0124',
    business_columns=['id', 'zone_code', 'name', 'zone_type', 'is_active', 'business_id']
)

BIN_REPO = CrudRepository(
    'T0125',
    business_columns=['id', 'bin_code', 'temperature_profile', 'is_active', 'business_id']
)

VEHICLE_REPO = CrudRepository(
    'T0114',
    business_columns=['id', 'vehicle_code', 'plate_number', 'is_active', 'business_id']
)

COMPARTMENT_REPO = CrudRepository(
    'T0126',
    business_columns=['id', 'compartment_code', 'name', 'is_active', 'business_id']
)

DELIVERY_RUN_REPO = CrudRepository(
    'T0112',
    business_columns=['id', 'run_number', 'zone', 'status', 'is_active', 'business_id']
)

USER_REPO = CrudRepository(
    'T0021',
    business_columns=['id', 'username', 'full_name', 'email', 'is_active']
)


def _conn_kwargs(conn):
    return {'conn': conn} if conn is not None else {}


class HaccpAuditService(CrudService):
    """
    Domain service layer managing cold-chain HACCP checkpoint audits,
    thermal excursion incidents, quarantine workflows, and compliance certifications.
    """

    def __init__(
        self,
        alert_repo: Optional[CrudRepository] = None,
        log_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        wh_repo: Optional[CrudRepository] = None,
        zone_repo: Optional[CrudRepository] = None,
        bin_repo: Optional[CrudRepository] = None,
        vehicle_repo: Optional[CrudRepository] = None,
        compartment_repo: Optional[CrudRepository] = None,
        delivery_run_repo: Optional[CrudRepository] = None,
        user_repo: Optional[CrudRepository] = None,
    ):
        super().__init__(alert_repo or ALERT_REPO)
        self.alert_repo = self.repo
        self.log_repo = log_repo or LOG_REPO
        self.product_repo = product_repo or PRODUCT_REPO
        self.wh_repo = wh_repo or WH_REPO
        self.zone_repo = zone_repo or ZONE_REPO
        self.bin_repo = bin_repo or BIN_REPO
        self.vehicle_repo = vehicle_repo or VEHICLE_REPO
        self.compartment_repo = compartment_repo or COMPARTMENT_REPO
        self.delivery_run_repo = delivery_run_repo or DELIVERY_RUN_REPO
        self.user_repo = user_repo or USER_REPO

    # -------------------------------------------------------------------------
    # Temperature Excursion Alerts (T0127)
    # -------------------------------------------------------------------------

    def list_alerts(self, filters: Optional[Dict[str, Any]] = None, conn=None) -> List[Dict[str, Any]]:
        """List excursion alerts with enriched entity labels."""
        f = dict(filters or {})
        if 'is_active' not in f:
            f['is_active'] = True
        alerts = self.alert_repo.list(filters=f, **_conn_kwargs(conn))

        prod_map = {p['id']: p for p in self.product_repo.list(**_conn_kwargs(conn))}
        wh_map = {w['id']: w['name'] for w in self.wh_repo.list(**_conn_kwargs(conn))}
        zone_map = {z['id']: z['name'] for z in self.zone_repo.list(**_conn_kwargs(conn))}
        bin_map = {b['id']: b['bin_code'] for b in self.bin_repo.list(**_conn_kwargs(conn))}
        veh_map = {v['id']: v.get('vehicle_code') for v in self.vehicle_repo.list(**_conn_kwargs(conn))}
        comp_map = {c['id']: c.get('name') for c in self.compartment_repo.list(**_conn_kwargs(conn))}
        run_map = {r['id']: r.get('run_number') for r in self.delivery_run_repo.list(**_conn_kwargs(conn))}
        user_map = {u['id']: u.get('full_name') or u.get('username') for u in self.user_repo.list(**_conn_kwargs(conn))}

        for a in alerts:
            if a.get('product_id'):
                p = prod_map.get(a['product_id'])
                if p:
                    a['product_name'] = p.get('name')
                    a['product_sku'] = p.get('sku')
            if a.get('warehouse_id'):
                a['warehouse_name'] = wh_map.get(a['warehouse_id'])
            if a.get('zone_id'):
                a['zone_name'] = zone_map.get(a['zone_id'])
            if a.get('bin_id'):
                a['bin_code'] = bin_map.get(a['bin_id'])
            if a.get('vehicle_id'):
                a['vehicle_code'] = veh_map.get(a['vehicle_id'])
            if a.get('compartment_id'):
                a['compartment_name'] = comp_map.get(a['compartment_id'])
            if a.get('delivery_run_id'):
                a['delivery_run_number'] = run_map.get(a['delivery_run_id'])
            if a.get('acknowledged_by'):
                a['acknowledged_by_name'] = user_map.get(a['acknowledged_by'])
            if a.get('resolved_by'):
                a['resolved_by_name'] = user_map.get(a['resolved_by'])

        return alerts

    def get_alert(self, alert_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Get excursion alert by ID with details."""
        a = self.alert_repo.get(alert_id, **_conn_kwargs(conn))
        if not a:
            return None
        if a.get('product_id'):
            p = self.product_repo.get(a['product_id'], **_conn_kwargs(conn))
            if p:
                a['product_name'] = p.get('name')
                a['product_sku'] = p.get('sku')
        return a

    def create_alert(self, data: Union[Dict[str, Any], ExcursionAlertCreate], conn=None) -> Dict[str, Any]:
        """Create a new temperature excursion alert."""
        payload = data.model_dump(exclude_unset=True) if isinstance(data, ExcursionAlertCreate) else dict(data)
        if not payload.get('alert_number') or not str(payload.get('alert_number')).strip():
            try:
                payload['alert_number'] = generate_excursion_alert_number(**_conn_kwargs(conn))
            except Exception:
                payload['alert_number'] = f"EXC-{datetime.utcnow().strftime('%M%S')}"

        if not payload.get('status'):
            payload['status'] = 'Open'
        if 'is_active' not in payload:
            payload['is_active'] = True

        # Calculate deviation degrees if threshold provided
        rec_temp = float(payload.get('recorded_temperature', 0))
        max_t = float(payload['max_threshold']) if payload.get('max_threshold') is not None else None
        min_t = float(payload['min_threshold']) if payload.get('min_threshold') is not None else None

        if payload.get('deviation_degrees') is None:
            if max_t is not None and rec_temp > max_t:
                payload['deviation_degrees'] = round(rec_temp - max_t, 2)
            elif min_t is not None and rec_temp < min_t:
                payload['deviation_degrees'] = round(min_t - rec_temp, 2)
            else:
                payload['deviation_degrees'] = 0.0

        return self.alert_repo.create(payload, **_conn_kwargs(conn))

    def acknowledge_alert(
        self,
        alert_id: int,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Acknowledge an open excursion alert."""
        alert = self.alert_repo.get(alert_id, **_conn_kwargs(conn))
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{alert_id} not found")

        updates = {
            'status': 'Acknowledged',
            'acknowledged_at': datetime.utcnow(),
            'acknowledged_by': user_id or 1,
        }
        if notes:
            existing_notes = alert.get('notes') or ''
            updates['notes'] = f"{existing_notes}\n[Ack]: {notes}".strip()

        return self.alert_repo.update(alert_id, updates, **_conn_kwargs(conn))

    def resolve_alert(
        self,
        alert_id: int,
        resolution_action: str,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Resolve an excursion alert with action documentation."""
        alert = self.alert_repo.get(alert_id, **_conn_kwargs(conn))
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{alert_id} not found")

        updates = {
            'status': 'Resolved',
            'resolved_at': datetime.utcnow(),
            'resolved_by': user_id or 1,
            'resolution_action': resolution_action,
        }
        if notes:
            existing_notes = alert.get('notes') or ''
            updates['notes'] = f"{existing_notes}\n[Resolution]: {notes}".strip()

        return self.alert_repo.update(alert_id, updates, **_conn_kwargs(conn))

    def quarantine_lot(
        self,
        alert_id: int,
        quarantine_notes: str,
        user_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Place inventory batch into quarantine status following thermal breach."""
        alert = self.alert_repo.get(alert_id, **_conn_kwargs(conn))
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Excursion alert #{alert_id} not found")

        updates = {
            'status': 'Quarantined',
            'is_quarantined': True,
            'quarantine_notes': quarantine_notes,
            'acknowledged_at': alert.get('acknowledged_at') or datetime.utcnow(),
            'acknowledged_by': alert.get('acknowledged_by') or (user_id or 1),
        }
        return self.alert_repo.update(alert_id, updates, **_conn_kwargs(conn))

    # -------------------------------------------------------------------------
    # HACCP Checkpoint Logs (T0128)
    # -------------------------------------------------------------------------

    def list_logs(self, filters: Optional[Dict[str, Any]] = None, conn=None) -> List[Dict[str, Any]]:
        """List checkpoint temperature logs with entity labels."""
        f = dict(filters or {})
        if 'is_active' not in f:
            f['is_active'] = True
        logs = self.log_repo.list(filters=f, **_conn_kwargs(conn))

        prod_map = {p['id']: p for p in self.product_repo.list(**_conn_kwargs(conn))}
        wh_map = {w['id']: w['name'] for w in self.wh_repo.list(**_conn_kwargs(conn))}
        zone_map = {z['id']: z['name'] for z in self.zone_repo.list(**_conn_kwargs(conn))}
        bin_map = {b['id']: b['bin_code'] for b in self.bin_repo.list(**_conn_kwargs(conn))}
        veh_map = {v['id']: v.get('vehicle_code') for v in self.vehicle_repo.list(**_conn_kwargs(conn))}
        comp_map = {c['id']: c.get('name') for c in self.compartment_repo.list(**_conn_kwargs(conn))}
        run_map = {r['id']: r.get('run_number') for r in self.delivery_run_repo.list(**_conn_kwargs(conn))}
        user_map = {u['id']: u.get('full_name') or u.get('username') for u in self.user_repo.list(**_conn_kwargs(conn))}

        for lg in logs:
            if lg.get('product_id'):
                p = prod_map.get(lg['product_id'])
                if p:
                    lg['product_name'] = p.get('name')
                    lg['product_sku'] = p.get('sku')
            if lg.get('warehouse_id'):
                lg['warehouse_name'] = wh_map.get(lg['warehouse_id'])
            if lg.get('zone_id'):
                lg['zone_name'] = zone_map.get(lg['zone_id'])
            if lg.get('bin_id'):
                lg['bin_code'] = bin_map.get(lg['bin_id'])
            if lg.get('vehicle_id'):
                lg['vehicle_code'] = veh_map.get(lg['vehicle_id'])
            if lg.get('compartment_id'):
                lg['compartment_name'] = comp_map.get(lg['compartment_id'])
            if lg.get('delivery_run_id'):
                lg['delivery_run_number'] = run_map.get(lg['delivery_run_id'])
            if lg.get('logged_by_id'):
                lg['logged_by_name'] = user_map.get(lg['logged_by_id'])
            if lg.get('verified_by_id'):
                lg['verified_by_name'] = user_map.get(lg['verified_by_id'])

        return logs

    def get_log(self, log_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Get checkpoint log by ID."""
        lg = self.log_repo.get(log_id, **_conn_kwargs(conn))
        if not lg:
            return None
        if lg.get('product_id'):
            p = self.product_repo.get(lg['product_id'], **_conn_kwargs(conn))
            if p:
                lg['product_name'] = p.get('name')
                lg['product_sku'] = p.get('sku')
        return lg

    def log_checkpoint(
        self,
        data: Union[Dict[str, Any], HACCPCheckpointLogCreate],
        conn=None,
    ) -> Dict[str, Any]:
        """
        Record a physical temperature checkpoint log across the cold supply chain.
        Automatically verifies compliance against HACCP critical limits and triggers
        excursion alert (T0127) when thresholds are breached.
        """
        payload = data.model_dump(exclude_unset=True) if isinstance(data, HACCPCheckpointLogCreate) else dict(data)
        if not payload.get('log_number') or not str(payload.get('log_number')).strip():
            try:
                payload['log_number'] = generate_haccp_log_number(**_conn_kwargs(conn))
            except Exception:
                payload['log_number'] = f"CCP-{datetime.utcnow().strftime('%M%S')}"

        if not payload.get('logged_at'):
            payload['logged_at'] = datetime.utcnow()

        rec_temp = float(payload['recorded_temperature'])
        crit_max = float(payload['critical_limit_max']) if payload.get('critical_limit_max') is not None else None
        crit_min = float(payload['critical_limit_min']) if payload.get('critical_limit_min') is not None else None

        # If critical limits not explicitly passed, infer from product
        product = None
        if payload.get('product_id'):
            product = self.product_repo.get(payload['product_id'], **_conn_kwargs(conn))
            if product:
                if crit_max is None and product.get('critical_temp_limit') is not None:
                    crit_max = float(product['critical_temp_limit'])
                    payload['critical_limit_max'] = crit_max
                elif crit_max is None and product.get('max_temperature') is not None:
                    crit_max = float(product['max_temperature'])
                    payload['critical_limit_max'] = crit_max
                if crit_min is None and product.get('min_temperature') is not None:
                    crit_min = float(product['min_temperature'])
                    payload['critical_limit_min'] = crit_min

        # Verify compliance
        is_compliant = True
        deviation = 0.0
        if crit_max is not None and rec_temp > crit_max:
            is_compliant = False
            deviation = round(rec_temp - crit_max, 2)
        elif crit_min is not None and rec_temp < crit_min:
            is_compliant = False
            deviation = round(crit_min - rec_temp, 2)

        payload['is_compliant'] = is_compliant

        # Save checkpoint log
        created_log = self.log_repo.create(payload, **_conn_kwargs(conn))

        # If non-compliant, automatically trigger an excursion alert (T0127)
        if not is_compliant:
            alert_payload = {
                'alert_type': 'CriticalLimitExceeded' if (product and product.get('critical_temp_limit') is not None and rec_temp > float(product['critical_temp_limit'])) else 'TemperatureExcursion',
                'severity': 'Critical',
                'status': 'Open',
                'warehouse_id': payload.get('warehouse_id'),
                'zone_id': payload.get('zone_id'),
                'bin_id': payload.get('bin_id'),
                'vehicle_id': payload.get('vehicle_id'),
                'compartment_id': payload.get('compartment_id'),
                'delivery_run_id': payload.get('delivery_run_id'),
                'product_id': payload.get('product_id'),
                'batch_number': payload.get('batch_number'),
                'recorded_temperature': rec_temp,
                'min_threshold': crit_min,
                'max_threshold': crit_max,
                'deviation_degrees': deviation,
                'haccp_critical_limit': crit_max,
                'haccp_violation': True,
                'quarantine_recommended': True,
                'notes': f"Auto-generated from HACCP Checkpoint '{payload.get('checkpoint_name')}' at stage '{payload.get('checkpoint_stage')}'. Recorded {rec_temp}°C (Critical Limit: {crit_max}°C).",
                'business_id': payload.get('business_id'),
            }
            try:
                self.create_alert(alert_payload, conn=conn)
                logger.warning(f"Excursion alert generated for non-compliant checkpoint reading {rec_temp}°C")
            except Exception as e:
                logger.error(f"Failed to auto-generate excursion alert: {e}")

        return created_log

    # -------------------------------------------------------------------------
    # HACCP Compliance Audit Report Compiler
    # -------------------------------------------------------------------------

    def compile_compliance_report(
        self,
        product_id: Optional[int] = None,
        batch_number: Optional[str] = None,
        delivery_run_id: Optional[int] = None,
        conn=None,
    ) -> HACCPComplianceReportResponse:
        """
        Aggregate all logged checkpoints for a batch, product, or delivery run,
        compute statistics (min, max, average, compliance percentage), verify HACCP
        thermal standards (e.g. <= -18°C for frozen meat), and generate compliance certificate.
        """
        filters = {}
        if product_id:
            filters['product_id'] = product_id
        if batch_number:
            filters['batch_number'] = batch_number
        if delivery_run_id:
            filters['delivery_run_id'] = delivery_run_id

        logs = self.log_repo.list(filters=filters, order_by="logged_at ASC", **_conn_kwargs(conn))

        product = self.product_repo.get(product_id, **_conn_kwargs(conn)) if product_id else None
        if not product and logs and logs[0].get('product_id'):
            product = self.product_repo.get(logs[0]['product_id'], **_conn_kwargs(conn))

        prod_name = product.get('name') if product else None
        prod_sku = product.get('sku') if product else None
        prod_profile = product.get('temp_zone_type') if product else 'Ambient'
        prod_crit = float(product['critical_temp_limit']) if (product and product.get('critical_temp_limit') is not None) else None

        delivery_run = self.delivery_run_repo.get(delivery_run_id, **_conn_kwargs(conn)) if delivery_run_id else None
        run_number = delivery_run.get('run_number') if delivery_run else None

        user_map = {u['id']: u.get('full_name') or u.get('username') for u in self.user_repo.list(**_conn_kwargs(conn))}

        readings: List[HACCPStageReading] = []
        temps: List[float] = []
        stages = set()
        compliant_count = 0
        excursion_count = 0

        for lg in logs:
            t_val = float(lg['recorded_temperature'])
            temps.append(t_val)
            stage = lg.get('checkpoint_stage', 'Unknown')
            stages.add(stage)

            is_comp = bool(lg.get('is_compliant', True))
            if is_comp:
                compliant_count += 1
            else:
                excursion_count += 1

            readings.append(HACCPStageReading(
                checkpoint_stage=stage,
                checkpoint_name=lg.get('checkpoint_name', 'Reading'),
                recorded_temperature=t_val,
                critical_limit_max=float(lg['critical_limit_max']) if lg.get('critical_limit_max') is not None else prod_crit,
                critical_limit_min=float(lg['critical_limit_min']) if lg.get('critical_limit_min') is not None else None,
                is_compliant=is_comp,
                logged_at=lg.get('logged_at'),
                logged_by_name=user_map.get(lg.get('logged_by_id')),
                location_label=lg.get('location_gps') or f"Warehouse #{lg.get('warehouse_id')}" if lg.get('warehouse_id') else None,
                sensor_device_id=lg.get('sensor_device_id'),
                corrective_action=lg.get('corrective_action'),
            ))

        total_logs = len(readings)
        min_temp = min(temps) if temps else None
        max_temp = max(temps) if temps else None
        avg_temp = round(sum(temps) / total_logs, 2) if total_logs > 0 else None

        is_fully_compliant = (total_logs > 0 and excursion_count == 0)
        overall_status = 'COMPLIANT' if is_fully_compliant else ('NON_COMPLIANT' if excursion_count > 0 else 'WARNING')

        cert_num = None
        if is_fully_compliant:
            id_tag = batch_number or f"RUN-{delivery_run_id}" or f"PROD-{product_id}" or "AUDIT"
            cert_num = f"HACCP-CERT-{id_tag}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

        if is_fully_compliant:
            notes = (
                f"CERTIFIED COMPLIANT: All {total_logs} temperature checkpoints satisfied HACCP critical safety limits "
                f"(Product profile: {prod_profile}, Critical limit: {prod_crit}°C). Average recorded temperature: {avg_temp}°C."
            )
        elif total_logs == 0:
            notes = "No HACCP checkpoint readings recorded for the specified criteria."
        else:
            notes = (
                f"NON-COMPLIANT: {excursion_count} temperature excursion(s) detected out of {total_logs} checkpoints. "
                f"Maximum recorded temperature reached {max_temp}°C. Corrective action review required."
            )

        # Excursions summary from alerts
        alert_filters = {}
        if batch_number:
            alert_filters['batch_number'] = batch_number
        if product_id:
            alert_filters['product_id'] = product_id
        if delivery_run_id:
            alert_filters['delivery_run_id'] = delivery_run_id

        excursions = self.alert_repo.list(filters=alert_filters, **_conn_kwargs(conn))

        return HACCPComplianceReportResponse(
            report_title=f"HACCP Cold-Chain Quality Audit Report: {batch_number or prod_name or 'General Audit'}",
            generated_at=datetime.utcnow(),
            product_id=product_id,
            product_name=prod_name,
            product_sku=prod_sku,
            batch_number=batch_number,
            delivery_run_id=delivery_run_id,
            delivery_run_number=run_number,
            required_temperature_profile=prod_profile,
            critical_temperature_limit=prod_crit,
            overall_compliance_status=overall_status,
            is_fully_compliant=is_fully_compliant,
            total_checkpoints_logged=total_logs,
            compliant_checkpoints=compliant_count,
            excursion_checkpoints=excursion_count,
            min_recorded_temperature=min_temp,
            max_recorded_temperature=max_temp,
            average_recorded_temperature=avg_temp,
            stages_covered=sorted(list(stages)),
            checkpoint_readings=readings,
            excursions_summary=excursions,
            compliance_certificate_number=cert_num,
            summary_notes=notes,
        )
