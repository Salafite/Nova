"""
Nova ERP — Real-Time Driver GPS Tracking & Customer Live ETA Notification Data Models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


# ---------------------------------------------------------------------------
# 1. Driver GPS Telemetry Ping Models (T0124)
# ---------------------------------------------------------------------------

class GPSLocationPing(BaseModel):
    run_id: Optional[int] = Field(None, description="Active delivery run ID")
    driver_id: Optional[int] = Field(None, description="Broadcasting driver user ID")
    vehicle_id: Optional[int] = Field(None, description="Vehicle ID")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS longitude coordinate")
    speed_kmh: float = Field(0.0, ge=0.0, description="Speed in km/h")
    heading: float = Field(0.0, ge=0.0, le=360.0, description="Compass bearing (0-360 degrees)")
    accuracy_meters: float = Field(5.0, ge=0.0, description="GPS accuracy in meters")
    battery_level: Optional[float] = Field(None, ge=0.0, le=100.0, description="Mobile device battery level percentage")
    recorded_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Hardware GPS fix timestamp")
    business_id: Optional[int] = None


class DriverLocationBatchRequest(BaseModel):
    driver_id: Optional[int] = Field(None, description="Driver ID")
    run_id: Optional[int] = Field(None, description="Delivery run ID")
    vehicle_id: Optional[int] = Field(None, description="Vehicle ID")
    pings: List[GPSLocationPing] = Field(..., min_length=1, description="List of recorded GPS pings")


class DriverCurrentLocationResponse(BaseModel):
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    run_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    vehicle_code: Optional[str] = None
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    heading: float = 0.0
    accuracy_meters: float = 5.0
    battery_level: Optional[float] = None
    recorded_at: datetime
    status: str = "Moving"  # Moving, Idle, At Stop, Delayed, Offline


# ---------------------------------------------------------------------------
# 2. Dispatcher Live Fleet Map Models
# ---------------------------------------------------------------------------

class FleetVehicleLiveStatus(BaseModel):
    vehicle_id: Optional[int] = None
    vehicle_code: str
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    run_id: Optional[int] = None
    run_number: Optional[str] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    speed_kmh: float = 0.0
    heading: float = 0.0
    status: str = "Idle"  # Moving | Idle | At Stop | Delayed | Offline
    last_ping_at: Optional[datetime] = None
    battery_level: Optional[float] = None
    total_stops: int = 0
    completed_stops: int = 0
    remaining_stops: int = 0
    current_stop_id: Optional[int] = None
    next_stop_customer: Optional[str] = None
    next_stop_address: Optional[str] = None
    next_stop_eta: Optional[datetime] = None
    next_stop_distance_km: Optional[float] = None


class FleetLiveMapResponse(BaseModel):
    active_vehicles: List[FleetVehicleLiveStatus] = Field(default_factory=list)
    total_active_runs: int = 0
    total_in_transit_orders: int = 0
    as_of: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# 3. Geofence Detection Models (T0126)
# ---------------------------------------------------------------------------

class GeofenceCheckRequest(BaseModel):
    run_id: int
    driver_id: Optional[int] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    speed_kmh: Optional[float] = Field(0.0, ge=0.0)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class GeofenceEventResponse(BaseModel):
    run_stop_id: int
    run_id: int
    event_type: str  # ENTER_GEOFENCE | EXIT_GEOFENCE | DWELL_THRESHOLD
    distance_meters: float
    customer_name: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    message: str
    status_updated: bool = False
    new_stop_status: Optional[str] = None
    dwell_duration_seconds: Optional[int] = 0


# ---------------------------------------------------------------------------
# 4. Customer Live Web Tracking & Notification Models (T0125)
# ---------------------------------------------------------------------------

class CustomerNotificationPayload(BaseModel):
    run_stop_id: int
    channel: str = Field("SMS", description="Notification channel: SMS | WhatsApp | Email")
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    custom_message: Optional[str] = None


class CustomerNotificationResult(BaseModel):
    run_stop_id: int
    customer_id: int
    tracking_token: str
    tracking_url: str
    channel: str
    status: str  # Sent | Pending | Failed
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    message_preview: str


class StopProgressItem(BaseModel):
    stop_sequence: int
    customer_name: str
    delivery_address: str
    status: str  # Pending | Arrived | Delivered | In Transit
    is_current_target: bool = False
    delivered_at: Optional[datetime] = None


class CustomerLiveTrackingResponse(BaseModel):
    tracking_token: str
    sales_order_number: Optional[str] = None
    customer_name: str
    delivery_address: str
    stop_status: str  # Pending | In Transit | Arrived | Delivered
    stop_sequence: int
    total_stops: int
    driver_name: Optional[str] = None
    vehicle_code: Optional[str] = None
    driver_latitude: Optional[float] = None
    driver_longitude: Optional[float] = None
    driver_speed_kmh: Optional[float] = 0.0
    driver_heading: Optional[float] = 0.0
    destination_latitude: Optional[float] = None
    destination_longitude: Optional[float] = None
    distance_remaining_km: Optional[float] = None
    estimated_arrival: Optional[datetime] = None
    eta_window_start: Optional[datetime] = None
    eta_window_end: Optional[datetime] = None
    eta_minutes_remaining: Optional[int] = None
    is_refrigerated_cargo: bool = False
    dock_preparation_alert: Optional[str] = None
    stops_progress: List[StopProgressItem] = Field(default_factory=list)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
