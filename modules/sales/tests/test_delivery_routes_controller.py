"""
Nova ERP — Unit & Integration Tests for Delivery Route Planning & Driver Dispatch Controller
Tests API endpoints in modules/sales/controllers/delivery_routes_controller.py
"""
from datetime import date
from unittest.mock import patch, MagicMock
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from modules.sales.controllers import delivery_routes_controller
from modules.sales.models.delivery_route import (
    UnassignedOrderResponse,
    VehicleAssignmentResponse,
    DriverManifestResponse,
    DriverManifestItem,
    LIFOPickListResponse,
    LIFOStagingStop,
    LIFOItemDetail,
)
from packages.auth.deps import get_current_user


app = FastAPI()
app.dependency_overrides[get_current_user] = lambda: {
    "id": 1,
    "username": "logistics_admin",
    "role": "Logistics Supervisor",
    "business_id": 10,
}
app.include_router(delivery_routes_controller.router)
app.include_router(delivery_routes_controller.alias_router)
client = TestClient(app)


class TestDeliveryRoutesController:
    """Test suite for Delivery Route Planning REST API endpoints."""

    def test_get_unassigned_orders_endpoint(self):
        mock_orders = [
            UnassignedOrderResponse(
                sales_order_id=1,
                sales_order_number="SO-1001",
                order_date=date(2026, 9, 3),
                customer_id=10,
                customer_name="Alpha Retail",
                delivery_address="100 Main St, Zone A",
                customer_phone="555-0100",
                zone_name="Zone A",
                total_weight=150.0,
                total_volume=10.0,
                total_amount=2500.0,
            )
        ]

        with patch.object(
            delivery_routes_controller._service,
            "get_unassigned_orders",
            return_value=mock_orders,
        ) as mock_get:
            resp = client.get("/api/sales/delivery-routes/unassigned-orders?zone_name=Zone+A")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert len(data) == 1
            assert data[0]["sales_order_number"] == "SO-1001"
            assert data[0]["zone_name"] == "Zone A"
            mock_get.assert_called_once_with(
                delivery_date=None,
                zone_name="Zone A",
                warehouse_id=None,
            )

    def test_get_unassigned_orders_alias(self):
        mock_orders = []
        with patch.object(
            delivery_routes_controller._service,
            "get_unassigned_orders",
            return_value=mock_orders,
        ):
            resp = client.get("/api/delivery-routes/unassigned-orders")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json() == []

    def test_get_unassigned_orders_error_handling(self):
        with patch.object(
            delivery_routes_controller._service,
            "get_unassigned_orders",
            side_effect=Exception("Database failure"),
        ):
            resp = client.get("/api/sales/delivery-routes/unassigned-orders")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to fetch unassigned delivery orders" in resp.json()["detail"]

    def test_list_delivery_runs_endpoint(self):
        mock_runs = [
            {
                "id": 1,
                "run_number": "RUN-20260903-001",
                "run_date": "2026-09-03",
                "zone_name": "Zone A",
                "status": "Planned",
                "total_orders": 3,
                "total_weight": 450.0,
                "total_volume": 25.0,
                "vehicle_code": "TRK-01",
                "driver_name": "John Driver",
            }
        ]
        with patch.object(
            delivery_routes_controller._service,
            "list_delivery_runs",
            return_value=(mock_runs, 1),
        ) as mock_list:
            resp = client.get("/api/sales/delivery-routes/runs?zone_name=Zone+A&limit=50")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.headers["X-Total-Count"] == "1"
            data = resp.json()
            assert len(data) == 1
            assert data[0]["run_number"] == "RUN-20260903-001"
            mock_list.assert_called_once_with(
                run_date=None,
                zone_name="Zone A",
                status_val=None,
                driver_id=None,
                limit=50,
                offset=0,
            )

    def test_create_delivery_run_endpoint(self):
        mock_created_run = {
            "id": 5,
            "run_number": "RUN-20260903-005",
            "run_date": "2026-09-03",
            "zone_name": "Zone B",
            "status": "Draft",
            "total_orders": 2,
            "total_weight": 200.0,
            "total_volume": 12.0,
            "stops": [
                {"id": 1, "stop_number": 1, "sales_order_id": 10},
                {"id": 2, "stop_number": 2, "sales_order_id": 11},
            ],
        }
        payload = {
            "run_date": "2026-09-03",
            "zone_name": "Zone B",
            "sales_order_ids": [10, 11],
        }
        with patch.object(
            delivery_routes_controller._service,
            "create_delivery_run",
            return_value=mock_created_run,
        ) as mock_create:
            resp = client.post("/api/sales/delivery-routes/runs", json=payload)
            assert resp.status_code == status.HTTP_201_CREATED
            data = resp.json()
            assert data["id"] == 5
            assert data["run_number"] == "RUN-20260903-005"
            mock_create.assert_called_once()
            called_payload = mock_create.call_args[0][0]
            assert called_payload["business_id"] == 10

    def test_get_delivery_run_details_endpoint(self):
        mock_run = {
            "id": 5,
            "run_number": "RUN-20260903-005",
            "zone_name": "Zone B",
            "status": "Draft",
            "stops": [],
        }
        with patch.object(
            delivery_routes_controller._service,
            "get_delivery_run",
            return_value=mock_run,
        ) as mock_get_run:
            resp = client.get("/api/sales/delivery-routes/runs/5")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["id"] == 5
            assert data["run_number"] == "RUN-20260903-005"
            mock_get_run.assert_called_once_with(5)

    def test_update_delivery_run_endpoint(self):
        mock_updated = {
            "id": 5,
            "run_number": "RUN-20260903-005",
            "notes": "Updated instructions",
        }
        payload = {"notes": "Updated instructions"}
        with patch.object(
            delivery_routes_controller._service,
            "update_delivery_run",
            return_value=mock_updated,
        ) as mock_update:
            resp = client.put("/api/sales/delivery-routes/runs/5", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json()["notes"] == "Updated instructions"
            mock_update.assert_called_once_with(5, payload)

    def test_assign_vehicle_to_run_endpoint(self):
        mock_assignment = VehicleAssignmentResponse(
            run_id=5,
            run_number="RUN-20260903-005",
            vehicle_code="TRK-99",
            driver_name="Jane Driver",
            status="Planned",
            total_weight=500.0,
            total_volume=30.0,
            max_weight_capacity=1000.0,
            max_volume_capacity=50.0,
            capacity_warning=None,
        )
        payload = {
            "vehicle_id": 2,
            "vehicle_code": "TRK-99",
            "driver_id": 12,
            "driver_name": "Jane Driver",
        }
        with patch.object(
            delivery_routes_controller._service,
            "assign_vehicle",
            return_value=mock_assignment,
        ) as mock_assign:
            resp = client.post("/api/sales/delivery-routes/runs/5/assign-vehicle", json=payload)
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["vehicle_code"] == "TRK-99"
            assert data["driver_name"] == "Jane Driver"
            assert data["status"] == "Planned"
            mock_assign.assert_called_once_with(5, {**payload, "max_weight_capacity": None, "max_volume_capacity": None})

    def test_get_driver_manifest_endpoint(self):
        mock_manifest = DriverManifestResponse(
            run_id=5,
            run_number="RUN-20260903-005",
            run_date=date(2026, 9, 3),
            zone_name="Zone B",
            vehicle_code="TRK-99",
            driver_name="Jane Driver",
            status="Dispatched",
            total_stops=1,
            stops=[
                DriverManifestItem(
                    stop_number=1,
                    sales_order_id=10,
                    sales_order_number="SO-1001",
                    customer_id=1,
                    customer_name="Acme Corp",
                    delivery_address="123 Industrial Rd",
                    customer_phone="555-9900",
                    status="Pending",
                    items_count=4,
                    total_weight=120.0,
                )
            ],
        )
        with patch.object(
            delivery_routes_controller._service,
            "get_driver_manifest",
            return_value=mock_manifest,
        ) as mock_get_manifest:
            resp = client.get("/api/sales/delivery-routes/runs/5/manifest")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["run_number"] == "RUN-20260903-005"
            assert len(data["stops"]) == 1
            assert data["stops"][0]["customer_name"] == "Acme Corp"
            mock_get_manifest.assert_called_once_with(5)

    def test_get_lifo_staging_pick_list_endpoint(self):
        mock_lifo = LIFOPickListResponse(
            run_id=5,
            run_number="RUN-20260903-005",
            run_date=date(2026, 9, 3),
            zone_name="Zone B",
            warehouse_id=1,
            vehicle_code="TRK-99",
            driver_name="Jane Driver",
            total_stops=1,
            staging_sequence=[
                LIFOStagingStop(
                    staging_sequence=1,  # Loaded first into vehicle
                    stop_number=2,       # Last drop off stop
                    sales_order_id=11,
                    sales_order_number="SO-1002",
                    customer_name="Beta Store",
                    delivery_address="456 Market St",
                    items=[
                        LIFOItemDetail(
                            product_id=5,
                            product_name="Product A",
                            sku="PROD-A",
                            qty=10.0,
                            uom_name="Box",
                            location_code="MAIN-STAGE",
                        )
                    ],
                )
            ],
        )
        with patch.object(
            delivery_routes_controller._service,
            "get_lifo_staging_pick_list",
            return_value=mock_lifo,
        ) as mock_get_lifo:
            resp = client.get("/api/sales/delivery-routes/runs/5/lifo-staging")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["run_number"] == "RUN-20260903-005"
            assert len(data["staging_sequence"]) == 1
            assert data["staging_sequence"][0]["staging_sequence"] == 1
            assert data["staging_sequence"][0]["stop_number"] == 2
            mock_get_lifo.assert_called_once_with(5)

    def test_resequence_run_stops_endpoint(self):
        mock_resequenced = {
            "id": 5,
            "run_number": "RUN-20260903-005",
            "total_stops": 2,
        }
        stop_ids = [2, 1]
        with patch.object(
            delivery_routes_controller._service,
            "resequence_stops",
            return_value=mock_resequenced,
        ) as mock_resequence:
            resp = client.post("/api/sales/delivery-routes/runs/5/resequence", json=stop_ids)
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json()["id"] == 5
            mock_resequence.assert_called_once_with(5, stop_ids)

    def test_update_run_status_endpoint(self):
        mock_res = {"id": 5, "status": "Dispatched"}
        with patch.object(
            delivery_routes_controller._service,
            "update_run_status",
            return_value=mock_res,
        ) as mock_update_status:
            resp = client.put("/api/sales/delivery-routes/runs/5/status?status=Dispatched")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json()["status"] == "Dispatched"
            mock_update_status.assert_called_once_with(5, "Dispatched")

    def test_update_stop_status_endpoint(self):
        mock_stop = {"id": 101, "status": "Delivered"}
        with patch.object(
            delivery_routes_controller._service,
            "update_stop_status",
            return_value=mock_stop,
        ) as mock_update_stop:
            resp = client.put("/api/sales/delivery-routes/stops/101/status?status=Delivered")
            assert resp.status_code == status.HTTP_200_OK
            assert resp.json()["status"] == "Delivered"
            mock_update_stop.assert_called_once_with(101, "Delivered")
