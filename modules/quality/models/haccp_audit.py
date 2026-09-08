from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


# ---------------------------------------------------------------------------
# T0127 — Temperature Excursion Alerts Models
# ---------------------------------------------------------------------------

class ExcursionAlertCreate(TenantMixin):
    alert_number: Optional[str] = Field(None, max_length=50)
    alert_type: str = Field(default="TemperatureExcursion", max_length=50, description="TemperatureExcursion | IncompatibleZonePutaway | TransitExcursion | SensorFailure | CriticalLimitExceeded")
    severity: str = Field(default="Warning", max_length=30, description="Warning | Critical | Emergency")
    status: str = Field(default="Open", max_length=30, description="Open | Acknowledged | Investigating | Resolved | Quarantined | Dismissed")
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    bin_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    compartment_id: Optional[int] = None
    delivery_run_id: Optional[int] = None
    product_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    recorded_temperature: float
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    deviation_degrees: Optional[float] = None
    duration_minutes: Optional[int] = 0
    haccp_critical_limit: Optional[float] = None
    haccp_violation: bool = False
    quarantine_recommended: bool = False
    is_quarantined: bool = False
    quarantine_notes: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ExcursionAlertUpdate(TenantMixin):
    alert_type: Optional[str] = Field(None, max_length=50)
    severity: Optional[str] = Field(None, max_length=30)
    status: Optional[str] = Field(None, max_length=30)
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    bin_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    compartment_id: Optional[int] = None
    delivery_run_id: Optional[int] = None
    product_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    recorded_temperature: Optional[float] = None
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    deviation_degrees: Optional[float] = None
    duration_minutes: Optional[int] = None
    haccp_critical_limit: Optional[float] = None
    haccp_violation: Optional[bool] = None
    quarantine_recommended: Optional[bool] = None
    is_quarantined: Optional[bool] = None
    quarantine_notes: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ExcursionAlertResponse(AuditMixin):
    id: int
    alert_number: str
    alert_type: str
    severity: str
    status: str
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    bin_id: Optional[int] = None
    bin_code: Optional[str] = None
    vehicle_id: Optional[int] = None
    vehicle_code: Optional[str] = None
    compartment_id: Optional[int] = None
    compartment_name: Optional[str] = None
    delivery_run_id: Optional[int] = None
    delivery_run_number: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_number: Optional[str] = None
    recorded_temperature: float
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    deviation_degrees: Optional[float] = None
    duration_minutes: Optional[int] = 0
    haccp_critical_limit: Optional[float] = None
    haccp_violation: bool = False
    quarantine_recommended: bool = False
    is_quarantined: bool = False
    quarantine_notes: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    acknowledged_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolution_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ExcursionAlertAcknowledgeRequest(BaseModel):
    user_id: Optional[int] = None
    notes: Optional[str] = None


class ExcursionAlertResolveRequest(BaseModel):
    user_id: Optional[int] = None
    resolution_action: str
    notes: Optional[str] = None


class ExcursionAlertQuarantineRequest(BaseModel):
    user_id: Optional[int] = None
    quarantine_notes: str


# ---------------------------------------------------------------------------
# T0128 — HACCP Checkpoint Logs Models
# ---------------------------------------------------------------------------

class HACCPCheckpointLogCreate(TenantMixin):
    log_number: Optional[str] = Field(None, max_length=50)
    checkpoint_stage: str = Field(..., max_length=50, description="GoodsReceipt | WarehouseStorage | StagingDock | VehicleDeparture | TransitCheckpoint | DestinationDelivery | QualityInspection")
    checkpoint_name: str = Field(..., max_length=150)
    stage_reference_type: Optional[str] = Field(None, max_length=50)
    stage_reference_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    bin_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    compartment_id: Optional[int] = None
    delivery_run_id: Optional[int] = None
    delivery_stop_id: Optional[int] = None
    product_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    recorded_temperature: float
    critical_limit_min: Optional[float] = None
    critical_limit_max: Optional[float] = None
    is_compliant: bool = True
    ambient_temperature: Optional[float] = None
    humidity_pct: Optional[float] = None
    logged_by_id: Optional[int] = None
    logged_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    location_gps: Optional[str] = Field(None, max_length=100)
    sensor_device_id: Optional[str] = Field(None, max_length=100)
    corrective_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class HACCPCheckpointLogUpdate(TenantMixin):
    checkpoint_stage: Optional[str] = Field(None, max_length=50)
    checkpoint_name: Optional[str] = Field(None, max_length=150)
    stage_reference_type: Optional[str] = Field(None, max_length=50)
    stage_reference_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    bin_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    compartment_id: Optional[int] = None
    delivery_run_id: Optional[int] = None
    delivery_stop_id: Optional[int] = None
    product_id: Optional[int] = None
    batch_number: Optional[str] = Field(None, max_length=100)
    recorded_temperature: Optional[float] = None
    critical_limit_min: Optional[float] = None
    critical_limit_max: Optional[float] = None
    is_compliant: Optional[bool] = None
    ambient_temperature: Optional[float] = None
    humidity_pct: Optional[float] = None
    logged_by_id: Optional[int] = None
    logged_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    location_gps: Optional[str] = Field(None, max_length=100)
    sensor_device_id: Optional[str] = Field(None, max_length=100)
    corrective_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class HACCPCheckpointLogResponse(AuditMixin):
    id: int
    log_number: str
    checkpoint_stage: str
    checkpoint_name: str
    stage_reference_type: Optional[str] = None
    stage_reference_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    bin_id: Optional[int] = None
    bin_code: Optional[str] = None
    vehicle_id: Optional[int] = None
    vehicle_code: Optional[str] = None
    compartment_id: Optional[int] = None
    compartment_name: Optional[str] = None
    delivery_run_id: Optional[int] = None
    delivery_run_number: Optional[str] = None
    delivery_stop_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_number: Optional[str] = None
    recorded_temperature: float
    critical_limit_min: Optional[float] = None
    critical_limit_max: Optional[float] = None
    is_compliant: bool = True
    ambient_temperature: Optional[float] = None
    humidity_pct: Optional[float] = None
    logged_by_id: Optional[int] = None
    logged_by_name: Optional[str] = None
    logged_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    location_gps: Optional[str] = None
    sensor_device_id: Optional[str] = None
    corrective_action: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# HACCP Audit Compliance Report Models
# ---------------------------------------------------------------------------

class HACCPStageReading(BaseModel):
    checkpoint_stage: str
    checkpoint_name: str
    recorded_temperature: float
    critical_limit_max: Optional[float] = None
    critical_limit_min: Optional[float] = None
    is_compliant: bool
    logged_at: Optional[datetime] = None
    logged_by_name: Optional[str] = None
    location_label: Optional[str] = None
    sensor_device_id: Optional[str] = None
    corrective_action: Optional[str] = None


class HACCPComplianceReportResponse(BaseModel):
    report_title: str
    generated_at: datetime
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_number: Optional[str] = None
    delivery_run_id: Optional[int] = None
    delivery_run_number: Optional[str] = None
    required_temperature_profile: Optional[str] = None
    critical_temperature_limit: Optional[float] = None
    overall_compliance_status: str  # 'COMPLIANT' | 'NON_COMPLIANT' | 'WARNING'
    is_fully_compliant: bool
    total_checkpoints_logged: int
    compliant_checkpoints: int
    excursion_checkpoints: int
    min_recorded_temperature: Optional[float] = None
    max_recorded_temperature: Optional[float] = None
    average_recorded_temperature: Optional[float] = None
    stages_covered: List[str] = []
    checkpoint_readings: List[HACCPStageReading] = []
    excursions_summary: List[Dict[str, Any]] = []
    compliance_certificate_number: Optional[str] = None
    summary_notes: str
