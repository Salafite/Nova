"""
Unit tests for Delivery Route Planning & Driver Dispatch Pydantic models.
"""
from datetime import date, datetime
import pytest
from modules.sales.models.delivery_route import (
    DeliveryRunCreate,
    DeliveryRunUpdate,
    DeliveryRunResponse,
    DeliveryRunStopCreate,
    DeliveryRunStopUpdate,
    DeliveryRunStopResponse,
    VehicleAssignmentRequest,
    VehicleAssignmentResponse,
    DriverManifestItem,
    DriverManifestResponse,
    LIFOItemDetail,
    LIFOStagingStop,
    LIFOPickListResponse,
    RoutePlanningQuery,
    UnassignedOrderResponse,
)


def test_delivery_run_create_defaults():
    run = DeliveryRunCreate(
        zone_name="North Zone"
    )
    assert run.zone_name == "North Zone"
    assert run.status == "Draft"
    assert run.total_orders == 0
    assert run.total_weight == 0.0
    assert run.total_volume == 0.0


def test_delivery_run_response():
    now = datetime.now()
    res = DeliveryRunResponse(
        id=1,
        run_number="RUN-20260903-001",
        run_date=date(2026, 9, 3),
        zone_name="North Zone",
        vehicle_code="TRK-01",
        driver_name="John Driver",
        status="Planned",
        total_orders=3,
        total_weight=150.5,
        total_volume=12.0,
        max_weight_capacity=1000.0,
        max_volume_capacity=50.0,
        created_at=now,
    )
    assert res.id == 1
    assert res.run_number == "RUN-20260903-001"
    assert res.zone_name == "North Zone"
    assert res.total_orders == 3


def test_delivery_run_stop_create():
    stop = DeliveryRunStopCreate(
        stop_number=1,
        sales_order_id=10,
        sales_order_number="SO-1001",
        customer_id=5,
        customer_name="Acme Corp",
        delivery_address="123 Industrial Parkway, Zone A",
        customer_phone="+1-555-0192",
    )
    assert stop.stop_number == 1
    assert stop.customer_name == "Acme Corp"
    assert stop.status == "Pending"


def test_vehicle_assignment():
    req = VehicleAssignmentRequest(
        vehicle_id=100,
        vehicle_code="TRK-99",
        driver_id=20,
        driver_name="Jane Doe",
        max_weight_capacity=5000.0,
        max_volume_capacity=100.0,
    )
    assert req.vehicle_code == "TRK-99"
    assert req.driver_name == "Jane Doe"

    resp = VehicleAssignmentResponse(
        run_id=1,
        run_number="RUN-001",
        vehicle_code="TRK-99",
        driver_name="Jane Doe",
        status="Assigned",
        total_weight=4500.0,
        total_volume=80.0,
        max_weight_capacity=5000.0,
        max_volume_capacity=100.0,
        capacity_warning=None,
    )
    assert resp.status == "Assigned"
    assert resp.capacity_warning is None


def test_lifo_pick_list_models():
    item = LIFOItemDetail(
        product_id=50,
        product_name="Widgets Box",
        sku="WDG-01",
        qty=10.0,
        uom_name="Box",
        location_code="A-01-02",
    )
    staging_stop = LIFOStagingStop(
        staging_sequence=1,  # loaded first
        stop_number=3,       # last customer drop-off
        sales_order_id=100,
        sales_order_number="SO-100",
        customer_name="Beta Retail",
        delivery_address="456 Main St",
        items=[item],
    )
    pick_list = LIFOPickListResponse(
        run_id=1,
        run_number="RUN-001",
        run_date=date(2026, 9, 3),
        zone_name="North Zone",
        total_stops=3,
        staging_sequence=[staging_stop],
    )
    assert pick_list.staging_sequence[0].staging_sequence == 1
    assert pick_list.staging_sequence[0].stop_number == 3
    assert pick_list.staging_sequence[0].items[0].product_name == "Widgets Box"


def test_driver_manifest_response():
    manifest_item = DriverManifestItem(
        stop_number=1,
        sales_order_id=10,
        sales_order_number="SO-1001",
        customer_id=5,
        customer_name="Acme Corp",
        delivery_address="123 Industrial Parkway",
        customer_phone="+1-555-0192",
        status="Pending",
        items_count=5,
        total_weight=50.0,
    )
    manifest = DriverManifestResponse(
        run_id=1,
        run_number="RUN-001",
        run_date=date(2026, 9, 3),
        zone_name="North Zone",
        vehicle_code="TRK-01",
        driver_name="John Driver",
        status="Dispatched",
        total_stops=1,
        stops=[manifest_item],
    )
    assert manifest.total_stops == 1
    assert manifest.stops[0].sales_order_number == "SO-1001"
