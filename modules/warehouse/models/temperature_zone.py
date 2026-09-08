from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


# ---------------------------------------------------------------------------
# T0124 — Warehouse Temperature Zones Models
# ---------------------------------------------------------------------------

class TemperatureZoneCreate(TenantMixin):
    zone_code: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=100)
    warehouse_id: int
    zone_type: str = Field(default="Ambient", max_length=50, description="Ambient | Chilled | Frozen | Deep Freeze")
    min_temperature: float = Field(default=15.00)
    max_temperature: float = Field(default=25.00)
    target_temperature: float = Field(default=20.00)
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    current_temperature: Optional[float] = None
    current_humidity: Optional[float] = None
    last_monitored_at: Optional[datetime] = None
    status: str = Field(default="Normal", max_length=30)
    sensor_id: Optional[str] = Field(None, max_length=100)
    capacity_m3: Optional[float] = 0.0
    notes: Optional[str] = None
    is_active: bool = True


class TemperatureZoneUpdate(TenantMixin):
    zone_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    warehouse_id: Optional[int] = None
    zone_type: Optional[str] = Field(None, max_length=50)
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    target_temperature: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    current_temperature: Optional[float] = None
    current_humidity: Optional[float] = None
    last_monitored_at: Optional[datetime] = None
    status: Optional[str] = Field(None, max_length=30)
    sensor_id: Optional[str] = Field(None, max_length=100)
    capacity_m3: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class TemperatureZoneResponse(AuditMixin):
    id: int
    zone_code: str
    name: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    zone_type: str
    min_temperature: float
    max_temperature: float
    target_temperature: float
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    current_temperature: Optional[float] = None
    current_humidity: Optional[float] = None
    last_monitored_at: Optional[datetime] = None
    status: str
    sensor_id: Optional[str] = None
    capacity_m3: Optional[float] = 0.0
    notes: Optional[str] = None
    is_active: bool = True
    bins_count: Optional[int] = None


# ---------------------------------------------------------------------------
# T0125 — Warehouse Bins & Staging Areas Models
# ---------------------------------------------------------------------------

class WarehouseBinCreate(TenantMixin):
    bin_code: Optional[str] = Field(None, max_length=50)
    warehouse_id: int
    zone_id: Optional[int] = None
    bin_type: str = Field(default="Storage", max_length=50, description="Storage | Staging Dock | Quarantine | Inspection | Inbound Dock | Outbound Dock")
    temperature_profile: str = Field(default="Ambient", max_length=50, description="Ambient | Chilled | Frozen | Deep Freeze")
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    aisle: Optional[str] = Field(None, max_length=20)
    rack: Optional[str] = Field(None, max_length=20)
    shelf: Optional[str] = Field(None, max_length=20)
    position: Optional[str] = Field(None, max_length=20)
    max_weight_capacity_kg: Optional[float] = 1000.0
    max_volume_capacity_m3: Optional[float] = 10.0
    current_weight_kg: Optional[float] = 0.0
    current_volume_m3: Optional[float] = 0.0
    status: str = Field(default="Available", max_length=30)
    is_active: bool = True


class WarehouseBinUpdate(TenantMixin):
    bin_code: Optional[str] = Field(None, max_length=50)
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    bin_type: Optional[str] = Field(None, max_length=50)
    temperature_profile: Optional[str] = Field(None, max_length=50)
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    aisle: Optional[str] = Field(None, max_length=20)
    rack: Optional[str] = Field(None, max_length=20)
    shelf: Optional[str] = Field(None, max_length=20)
    position: Optional[str] = Field(None, max_length=20)
    max_weight_capacity_kg: Optional[float] = None
    max_volume_capacity_m3: Optional[float] = None
    current_weight_kg: Optional[float] = None
    current_volume_m3: Optional[float] = None
    status: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


class WarehouseBinResponse(AuditMixin):
    id: int
    bin_code: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None
    bin_type: str
    temperature_profile: str
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    position: Optional[str] = None
    max_weight_capacity_kg: Optional[float] = 1000.0
    max_volume_capacity_m3: Optional[float] = 10.0
    current_weight_kg: Optional[float] = 0.0
    current_volume_m3: Optional[float] = 0.0
    status: str
    is_active: bool = True


# ---------------------------------------------------------------------------
# T0126 — Vehicle Temperature Compartments Models
# ---------------------------------------------------------------------------

class VehicleCompartmentCreate(TenantMixin):
    vehicle_id: int
    compartment_code: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=100)
    temperature_zone_type: str = Field(default="Chilled", max_length=50, description="Ambient | Chilled | Frozen | Deep Freeze")
    min_temperature: float = Field(default=2.00)
    max_temperature: float = Field(default=4.00)
    target_temperature: float = Field(default=3.00)
    max_weight_capacity_kg: float = Field(default=500.00)
    max_volume_capacity_m3: float = Field(default=5.00)
    current_temperature: Optional[float] = None
    sensor_id: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="Available", max_length=30)
    is_active: bool = True


class VehicleCompartmentUpdate(TenantMixin):
    vehicle_id: Optional[int] = None
    compartment_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    temperature_zone_type: Optional[str] = Field(None, max_length=50)
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    target_temperature: Optional[float] = None
    max_weight_capacity_kg: Optional[float] = None
    max_volume_capacity_m3: Optional[float] = None
    current_temperature: Optional[float] = None
    sensor_id: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


class VehicleCompartmentResponse(AuditMixin):
    id: int
    vehicle_id: int
    vehicle_code: Optional[str] = None
    compartment_code: str
    name: str
    temperature_zone_type: str
    min_temperature: float
    max_temperature: float
    target_temperature: float
    max_weight_capacity_kg: float
    max_volume_capacity_m3: float
    current_temperature: Optional[float] = None
    sensor_id: Optional[str] = None
    status: str
    is_active: bool = True


# ---------------------------------------------------------------------------
# Compatibility & Thermal Pick Helper Models
# ---------------------------------------------------------------------------

class TemperatureCheckRequest(BaseModel):
    product_id: int
    target_zone_id: Optional[int] = None
    target_bin_id: Optional[int] = None
    target_compartment_id: Optional[int] = None
    warehouse_id: Optional[int] = None


class TemperatureCheckResponse(BaseModel):
    is_compatible: bool
    product_id: int
    product_name: Optional[str] = None
    product_temp_zone_type: Optional[str] = None
    product_min_temp: Optional[float] = None
    product_max_temp: Optional[float] = None
    product_critical_limit: Optional[float] = None
    destination_type: str  # 'zone' | 'bin' | 'compartment'
    destination_id: Optional[int] = None
    destination_label: Optional[str] = None
    destination_min_temp: Optional[float] = None
    destination_max_temp: Optional[float] = None
    current_destination_temp: Optional[float] = None
    severity: Optional[str] = None  # None | 'Warning' | 'Critical'
    is_haccp_violation: bool = False
    quarantine_recommended: bool = False
    message: str


class ZoneReadingLogRequest(BaseModel):
    recorded_temperature: float
    humidity_pct: Optional[float] = None
    sensor_id: Optional[str] = None
    notes: Optional[str] = None


class ThermalPickSequenceItem(BaseModel):
    item_id: int
    product_id: int
    product_name: str
    temp_zone_type: str
    thermal_priority_rank: int
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    critical_temp_limit: Optional[float] = None
    suggested_picking_order: int
    zone_label: str
