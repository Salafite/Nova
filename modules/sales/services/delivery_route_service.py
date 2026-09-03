"""
Nova ERP — Delivery Route Planning & Driver Dispatch Service
Implements business logic for territory/zone order grouping, vehicle & driver assignment,
driver manifest generation, and LIFO staging dock sequence calculation.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
from fastapi import HTTPException, status

from modules.sales.repositories.delivery_route_repo import (
    DeliveryRouteRepository,
    delivery_route_repo as default_repo,
)
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
    UnassignedOrderResponse,
)

logger = logging.getLogger(__name__)


class DeliveryRouteService:
    """
    Business service layer for delivery route planning, driver manifests, vehicle dispatching,
    and warehouse LIFO staging logic.
    """

    def __init__(self, repo: Optional[DeliveryRouteRepository] = None):
        self.repo = repo or default_repo

    def get_unassigned_orders(
        self,
        delivery_date: Optional[date] = None,
        zone_name: Optional[str] = None,
        warehouse_id: Optional[int] = None,
    ) -> List[UnassignedOrderResponse]:
        """Retrieve confirmed delivery orders available for route planning."""
        raw_orders = self.repo.get_unassigned_orders(
            delivery_date=delivery_date,
            zone_name=zone_name,
            warehouse_id=warehouse_id,
        )
        return [UnassignedOrderResponse(**o) for o in raw_orders]

    def create_delivery_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new delivery run header and assign sales orders into sequential stops.
        Calculates total stops, total weight, total volume, and LIFO staging sequences.
        """
        sales_order_ids = payload.pop('sales_order_ids', []) or []
        stops_input = payload.pop('stops', []) or []

        zone_name = payload.get('zone_name') or payload.get('zone') or 'General'
        run_date = payload.get('run_date') or date.today()

        header_data = {
            "run_number": payload.get('run_number'),
            "run_date": run_date,
            "zone": zone_name,
            "warehouse_id": payload.get('warehouse_id'),
            "vehicle_id": payload.get('vehicle_id'),
            "driver_id": payload.get('driver_id'),
            "status": payload.get('status') or "Draft",
            "notes": payload.get('notes'),
            "business_id": payload.get('business_id'),
        }

        # Create header record
        run = self.repo.create_delivery_run(header_data)
        run_id = run['id']

        # Process sales orders into stops
        total_stops = 0
        total_weight = 0.0
        total_volume = 0.0

        # If explicit sales_order_ids given, query unassigned order details
        if sales_order_ids:
            unassigned = self.repo.get_unassigned_orders(zone_name=zone_name)
            unassigned_map = {o['sales_order_id']: o for o in unassigned}

            num_orders = len(sales_order_ids)
            for idx, so_id in enumerate(sales_order_ids):
                order_info = unassigned_map.get(so_id)
                stop_sequence = idx + 1
                lifo_sequence = num_orders - idx  # Last customer drop-off is loaded first (LIFO = 1)

                cust_id = order_info['customer_id'] if order_info else 1
                cust_name = order_info['customer_name'] if order_info else f"Customer for SO #{so_id}"
                addr = order_info['delivery_address'] if order_info else "Delivery Destination Address"
                phone = order_info.get('customer_phone') if order_info else None

                stop_payload = {
                    "delivery_run_id": run_id,
                    "sales_order_id": so_id,
                    "customer_id": cust_id,
                    "stop_sequence": stop_sequence,
                    "lifo_staging_sequence": lifo_sequence,
                    "delivery_address": addr,
                    "contact_name": cust_name,
                    "contact_phone": phone,
                    "zone": zone_name,
                    "status": "Pending",
                    "business_id": payload.get('business_id'),
                }
                self.repo.create_run_stop(stop_payload)
                self.repo.link_sales_order_to_run(so_id, run_id, zone_name=zone_name)

                if order_info:
                    total_weight += order_info.get('total_weight', 0.0)
                    total_volume += order_info.get('total_volume', 0.0)
                total_stops += 1

        elif stops_input:
            num_stops = len(stops_input)
            for idx, stop_item in enumerate(stops_input):
                stop_sequence = idx + 1
                lifo_sequence = num_stops - idx
                stop_payload = dict(stop_item)
                stop_payload['delivery_run_id'] = run_id
                stop_payload['stop_sequence'] = stop_sequence
                stop_payload['lifo_staging_sequence'] = lifo_sequence
                stop_payload['zone'] = zone_name
                self.repo.create_run_stop(stop_payload)

                so_id = stop_payload.get('sales_order_id')
                if so_id:
                    self.repo.link_sales_order_to_run(so_id, run_id, zone_name=zone_name)
                total_stops += 1

        # Update totals on run header
        update_totals = {
            "total_stops": total_stops,
            "total_weight_kg": total_weight,
            "total_volume_m3": total_volume,
        }
        self.repo.update_delivery_run(run_id, update_totals)

        return self.get_delivery_run(run_id)

    def get_delivery_run(self, run_id: int) -> Dict[str, Any]:
        """Fetch delivery run header with list of assigned stops."""
        run = self.repo.get_delivery_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )
        stops = self.repo.get_run_stops(run_id)
        run['stops'] = stops
        return run

    def list_delivery_runs(
        self,
        run_date: Optional[date] = None,
        zone_name: Optional[str] = None,
        status_val: Optional[str] = None,
        driver_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List delivery runs matching filter parameters."""
        return self.repo.list_delivery_runs(
            run_date=run_date,
            zone_name=zone_name,
            status=status_val,
            driver_id=driver_id,
            limit=limit,
            offset=offset,
        )

    def update_delivery_run(self, run_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update fields on a delivery run."""
        existing = self.repo.get_delivery_run(run_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )

        clean_payload = {}
        for k in ('run_date', 'status', 'notes', 'vehicle_id', 'driver_id'):
            if k in payload and payload[k] is not None:
                clean_payload[k] = payload[k]

        if 'zone_name' in payload and payload['zone_name']:
            clean_payload['zone'] = payload['zone_name']

        if clean_payload:
            self.repo.update_delivery_run(run_id, clean_payload)

        return self.get_delivery_run(run_id)

    def assign_vehicle(self, run_id: int, request_data: Dict[str, Any]) -> VehicleAssignmentResponse:
        """
        Assign a vehicle and driver to a delivery run, checking maximum weight/volume payload capacities.
        Generates a warning if assigned cargo exceeds vehicle specifications.
        """
        run = self.repo.get_delivery_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )

        vehicle_id = request_data.get('vehicle_id')
        vehicle_code = request_data.get('vehicle_code')
        driver_id = request_data.get('driver_id')
        driver_name = request_data.get('driver_name')

        max_weight = request_data.get('max_weight_capacity')
        max_volume = request_data.get('max_volume_capacity')

        # Check vehicle master if vehicle_id or vehicle_code given
        if (not max_weight or not max_volume) and (vehicle_id or vehicle_code):
            veh = self.repo.get_vehicle_by_id_or_code(vehicle_id=vehicle_id, vehicle_code=vehicle_code)
            if veh:
                vehicle_id = vehicle_id or veh.get('id')
                vehicle_code = vehicle_code or veh.get('vehicle_code')
                driver_id = driver_id or veh.get('default_driver_id')
                max_weight = max_weight or float(veh.get('max_weight_capacity_kg', 1000.0))
                max_volume = max_volume or float(veh.get('max_volume_capacity_m3', 10.0))

        total_weight = float(run.get('total_weight', 0.0))
        total_volume = float(run.get('total_volume', 0.0))

        capacity_warning = None
        warnings = []
        if max_weight and total_weight > float(max_weight):
            warnings.append(f"Payload weight ({total_weight:.1f} kg) exceeds vehicle max capacity ({max_weight:.1f} kg)")
        if max_volume and total_volume > float(max_volume):
            warnings.append(f"Payload volume ({total_volume:.2f} m3) exceeds vehicle max volume ({max_volume:.2f} m3)")

        if warnings:
            capacity_warning = "; ".join(warnings)

        # Update run header
        update_data = {
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "status": "Planned" if run.get('status') == "Draft" else run.get('status'),
        }
        self.repo.update_delivery_run(run_id, update_data)

        return VehicleAssignmentResponse(
            run_id=run_id,
            run_number=run['run_number'],
            vehicle_code=vehicle_code or f"VEH-{vehicle_id or 'ASSIGNED'}",
            driver_name=driver_name or run.get('driver_name'),
            status="Planned" if run.get('status') == "Draft" else run.get('status'),
            total_weight=total_weight,
            total_volume=total_volume,
            max_weight_capacity=max_weight,
            max_volume_capacity=max_volume,
            capacity_warning=capacity_warning,
        )

    def resequence_stops(self, run_id: int, stop_ids_in_order: List[int]) -> Dict[str, Any]:
        """Resequence drop-off stops for a run and recalculate LIFO loading sequence numbers."""
        run = self.repo.get_delivery_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )
        total = len(stop_ids_in_order)
        for idx, stop_id in enumerate(stop_ids_in_order):
            stop_number = idx + 1
            lifo_sequence = total - idx
            self.repo.update_run_stop(stop_id, {
                "stop_sequence": stop_number,
                "lifo_staging_sequence": lifo_sequence,
            })
        return self.get_delivery_run(run_id)

    def get_driver_manifest(self, run_id: int) -> DriverManifestResponse:
        """Generate formatted driver delivery manifest with sequential drop-offs."""
        manifest_dict = self.repo.get_driver_manifest_details(run_id)
        if not manifest_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )
        return DriverManifestResponse(**manifest_dict)

    def get_lifo_staging_pick_list(self, run_id: int) -> LIFOPickListResponse:
        """
        Generate LIFO vehicle loading sequence pick list for warehouse staging docks.
        Sequence 1 = Last drop-off stop (first loaded into vehicle).
        Sequence N = First drop-off stop (last loaded into vehicle near doors).
        """
        lifo_dict = self.repo.get_lifo_staging_pick_list_details(run_id)
        if not lifo_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )
        return LIFOPickListResponse(**lifo_dict)

    def update_run_status(self, run_id: int, new_status: str) -> Dict[str, Any]:
        """Update run operational status (Draft -> Planned -> Dispatched -> In Transit -> Completed)."""
        run = self.repo.get_delivery_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery run #{run_id} not found",
            )

        update_data = {"status": new_status}
        if new_status in ("Dispatched", "In Transit") and not run.get('dispatched_at'):
            update_data['dispatched_at'] = datetime.now()
        elif new_status == "Completed" and not run.get('completed_at'):
            update_data['completed_at'] = datetime.now()

        self.repo.update_delivery_run(run_id, update_data)
        return self.get_delivery_run(run_id)

    def update_stop_status(self, stop_id: int, new_status: str) -> Dict[str, Any]:
        """Update stop status (Pending -> Staged -> Loaded -> Delivered -> Failed)."""
        stop = self.repo.stop_repo.get(stop_id)
        if not stop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run stop #{stop_id} not found",
            )

        update_data = {"status": new_status}
        if new_status == "Loaded" and not stop.get('loaded_at'):
            update_data['loaded_at'] = datetime.now()
        elif new_status == "Delivered" and not stop.get('delivered_at'):
            update_data['delivered_at'] = datetime.now()

        updated_stop = self.repo.update_run_stop(stop_id, update_data)
        return updated_stop


# Default singleton instance
delivery_route_service = DeliveryRouteService()
