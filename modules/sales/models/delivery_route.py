"""
Nova ERP — Delivery Route Planning & Driver Dispatch Management Pydantic Models
"""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin


# ---------------------------------------------------------------------------
# 1. Delivery Run Models (T0111 Header)
# ---------------------------------------------------------------------------

class DeliveryRunCreate(BaseModel):
    run_number: Optional[str] = Field(None, max_length=50, description="Optional custom run number; generated automatically if omitted")
    run_date: Optional[date] = Field(None, description="Scheduled delivery date")
    zone_name: str = Field(..., max_length=100, description="Geographic delivery territory / customer zone")
    warehouse_id: Optional[int] = Field(None, description="Origin warehouse ID")
    vehicle_id: Optional[int] = Field(None, description="Vehicle ID")
    vehicle_code: Optional[str] = Field(None, max_length=50, description="Vehicle license plate / code")
    driver_id: Optional[int] = Field(None, description="Driver employee/user ID")
    driver_name: Optional[str] = Field(None, max_length=100, description="Driver full name")
    status: str = Field("Draft", max_length=30, description="Status: Draft | Planned | Dispatched | In Transit | Completed | Cancelled")
    total_orders: int = Field(default=0, ge=0)
    total_weight: float = Field(default=0.0, ge=0)
    total_volume: float = Field(default=0.0, ge=0)
    max_weight_capacity: Optional[float] = Field(None, ge=0)
    max_volume_capacity: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    business_id: Optional[int] = None


class DeliveryRunUpdate(BaseModel):
    run_date: Optional[date] = None
    zone_name: Optional[str] = Field(None, max_length=100)
    warehouse_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    vehicle_code: Optional[str] = Field(None, max_length=50)
    driver_id: Optional[int] = None
    driver_name: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=30)
    total_orders: Optional[int] = Field(None, ge=0)
    total_weight: Optional[float] = Field(None, ge=0)
    total_volume: Optional[float] = Field(None, ge=0)
    max_weight_capacity: Optional[float] = Field(None, ge=0)
    max_volume_capacity: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class DeliveryRunResponse(AuditMixin):
    id: int
    run_number: str
    run_date: date
    zone_name: str
    warehouse_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    vehicle_code: Optional[str] = None
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    status: str = "Draft"
    total_orders: int = 0
    total_weight: float = 0.0
    total_volume: float = 0.0
    max_weight_capacity: Optional[float] = None
    max_volume_capacity: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# 2. Delivery Run Stops / Manifest Items (T0112 Line Items)
# ---------------------------------------------------------------------------

class DeliveryRunStopCreate(BaseModel):
    delivery_run_id: Optional[int] = Field(None, description="Parent delivery run ID")
    stop_number: int = Field(1, ge=1, description="Sequential drop-off stop number (1..N)")
    delivery_id: Optional[int] = Field(None, description="Delivery note ID reference")
    sales_order_id: Optional[int] = Field(None, description="Sales order ID reference")
    sales_order_number: Optional[str] = Field(None, max_length=50)
    customer_id: Optional[int] = Field(None, description="Customer ID reference")
    customer_name: str = Field(..., max_length=200, description="Customer name")
    delivery_address: str = Field(..., description="Full street delivery address")
    customer_phone: Optional[str] = Field(None, max_length=50, description="Customer contact phone")
    contact_person: Optional[str] = Field(None, max_length=100, description="Customer contact person")
    estimated_arrival: Optional[datetime] = Field(None, description="Estimated arrival time")
    actual_arrival: Optional[datetime] = Field(None, description="Actual drop-off timestamp")
    status: str = Field("Pending", max_length=30, description="Stop status: Pending | Delivered | Failed | Skipped")
    notes: Optional[str] = None
    business_id: Optional[int] = None


class DeliveryRunStopUpdate(BaseModel):
    stop_number: Optional[int] = Field(None, ge=1)
    delivery_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = Field(None, max_length=50)
    customer_id: Optional[int] = None
    customer_name: Optional[str] = Field(None, max_length=200)
    delivery_address: Optional[str] = None
    customer_phone: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    estimated_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    status: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class DeliveryRunStopResponse(AuditMixin):
    id: int
    delivery_run_id: int
    stop_number: int
    delivery_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: str
    delivery_address: str
    customer_phone: Optional[str] = None
    contact_person: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    status: str = "Pending"
    notes: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# 3. Vehicle Assignment Models
# ---------------------------------------------------------------------------

class VehicleAssignmentRequest(BaseModel):
    vehicle_id: Optional[int] = Field(None, description="Vehicle ID")
    vehicle_code: str = Field(..., max_length=50, description="Vehicle plate number / identifier")
    driver_id: Optional[int] = Field(None, description="Driver ID")
    driver_name: Optional[str] = Field(None, max_length=100, description="Driver full name")
    max_weight_capacity: Optional[float] = Field(None, ge=0, description="Vehicle max payload weight capacity (kg)")
    max_volume_capacity: Optional[float] = Field(None, ge=0, description="Vehicle max volume capacity (m3)")


class VehicleAssignmentResponse(BaseModel):
    run_id: int
    run_number: str
    vehicle_code: str
    driver_name: Optional[str] = None
    status: str
    total_weight: float = 0.0
    total_volume: float = 0.0
    max_weight_capacity: Optional[float] = None
    max_volume_capacity: Optional[float] = None
    capacity_warning: Optional[str] = None


# ---------------------------------------------------------------------------
# 4. Driver Manifest Models
# ---------------------------------------------------------------------------

class DriverManifestItem(BaseModel):
    stop_number: int
    sales_order_id: Optional[int] = None
    sales_order_number: str
    customer_id: Optional[int] = None
    customer_name: str
    delivery_address: str
    customer_phone: Optional[str] = None
    contact_person: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    status: str = "Pending"
    special_instructions: Optional[str] = None
    items_count: int = 0
    total_weight: float = 0.0


class DriverManifestResponse(BaseModel):
    run_id: int
    run_number: str
    run_date: date
    zone_name: str
    vehicle_code: Optional[str] = None
    driver_name: Optional[str] = None
    status: str
    total_stops: int = 0
    stops: List[DriverManifestItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 5. LIFO Pick List & Staging Dock Models
# ---------------------------------------------------------------------------

class LIFOItemDetail(BaseModel):
    product_id: int
    product_name: str
    sku: Optional[str] = None
    qty: float = Field(..., gt=0)
    uom_name: Optional[str] = None
    location_code: Optional[str] = None


class LIFOStagingStop(BaseModel):
    staging_sequence: int = Field(..., ge=1, description="LIFO vehicle loading order (1 = first loaded into truck / last drop-off)")
    stop_number: int = Field(..., ge=1, description="Driver drop-off order (1 = first customer drop-off / last loaded)")
    sales_order_id: Optional[int] = None
    sales_order_number: str
    customer_name: str
    delivery_address: str
    items: List[LIFOItemDetail] = Field(default_factory=list)


class LIFOPickListResponse(BaseModel):
    run_id: int
    run_number: str
    run_date: date
    zone_name: str
    warehouse_id: Optional[int] = None
    vehicle_code: Optional[str] = None
    driver_name: Optional[str] = None
    total_stops: int = 0
    staging_sequence: List[LIFOStagingStop] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Route Planning & Unassigned Orders Models
# ---------------------------------------------------------------------------

class RoutePlanningQuery(BaseModel):
    delivery_date: Optional[date] = None
    zone_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    status: Optional[str] = None


class UnassignedOrderResponse(BaseModel):
    sales_order_id: int
    sales_order_number: str
    order_date: date
    customer_id: int
    customer_name: str
    delivery_address: str
    customer_phone: Optional[str] = None
    zone_name: str
    total_weight: float = 0.0
    total_volume: float = 0.0
    total_amount: float = 0.0
