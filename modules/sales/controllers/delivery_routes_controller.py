"""
Nova ERP — Delivery Route Planning & Driver Dispatch Management Controller
Exposes API endpoints for filtering unassigned delivery orders by zone/date, creating delivery runs,
assigning vehicles/drivers, generating driver manifests, and retrieving LIFO staging pick lists.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response

from packages.auth.deps import require_permission, get_current_user
from modules.sales.models.delivery_route import (
    DeliveryRunCreate,
    DeliveryRunUpdate,
    DeliveryRunResponse,
    VehicleAssignmentRequest,
    VehicleAssignmentResponse,
    DriverManifestResponse,
    LIFOPickListResponse,
    UnassignedOrderResponse,
)
from modules.sales.services.delivery_route_service import (
    DeliveryRouteService,
    delivery_route_service as default_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sales/delivery-routes",
    tags=["Delivery Route Planning & Driver Dispatch"],
)

# Secondary router for standard /api/delivery-routes path alias
alias_router = APIRouter(
    prefix="/api/delivery-routes",
    tags=["Delivery Route Planning & Driver Dispatch"],
)

_service: DeliveryRouteService = default_service


# ---------------------------------------------------------------------------
# 1. Unassigned Orders Filtering for Route Planning
# ---------------------------------------------------------------------------

@router.get(
    "/unassigned-orders",
    response_model=List[UnassignedOrderResponse],
    summary="Get unassigned confirmed delivery orders",
    description="Retrieve confirmed delivery sales orders grouped by zone/territory available for route building.",
)
@alias_router.get(
    "/unassigned-orders",
    response_model=List[UnassignedOrderResponse],
    include_in_schema=False,
)
def get_unassigned_orders(
    delivery_date: Optional[date] = Query(None, description="Filter by scheduled delivery date (YYYY-MM-DD)"),
    zone_name: Optional[str] = Query(None, description="Filter by geographic zone / territory name"),
    warehouse_id: Optional[int] = Query(None, description="Filter by origin warehouse ID"),
    current_user: dict = Depends(get_current_user),
) -> List[UnassignedOrderResponse]:
    """Fetch unassigned delivery sales orders."""
    try:
        return _service.get_unassigned_orders(
            delivery_date=delivery_date,
            zone_name=zone_name,
            warehouse_id=warehouse_id,
        )
    except Exception as e:
        logger.error(f"Error fetching unassigned delivery orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unassigned delivery orders: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 2. Delivery Runs CRUD & Listing
# ---------------------------------------------------------------------------

@router.get(
    "/runs",
    summary="List delivery runs",
    description="Retrieve delivery runs header records with vehicle, driver, and stop count details.",
)
@alias_router.get(
    "/runs",
    include_in_schema=False,
)
def list_delivery_runs(
    response: Response,
    run_date: Optional[date] = Query(None, description="Filter by delivery run date"),
    zone_name: Optional[str] = Query(None, description="Filter by zone/territory"),
    status_val: Optional[str] = Query(None, alias="status", description="Filter by status (Draft, Planned, Dispatched, In Transit, Completed)"),
    driver_id: Optional[int] = Query(None, description="Filter by assigned driver user ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List delivery runs with pagination."""
    try:
        runs, total = _service.list_delivery_runs(
            run_date=run_date,
            zone_name=zone_name,
            status_val=status_val,
            driver_id=driver_id,
            limit=limit,
            offset=offset,
        )
        response.headers["X-Total-Count"] = str(total)
        return runs
    except Exception as e:
        logger.error(f"Error listing delivery runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list delivery runs: {str(e)}",
        ) from e


@router.post(
    "/runs",
    summary="Create delivery run",
    description="Create a delivery run header and assign sales orders into sequential drop-off stops.",
    status_code=status.HTTP_201_CREATED,
)
@alias_router.post(
    "/runs",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_delivery_run(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create delivery run."""
    try:
        if current_user and 'business_id' in current_user:
            payload['business_id'] = current_user.get('business_id')
        return _service.create_delivery_run(payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating delivery run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create delivery run: {str(e)}",
        ) from e


@router.get(
    "/runs/{run_id}",
    summary="Get delivery run details",
    description="Retrieve single delivery run header and sequential stop details.",
)
@alias_router.get(
    "/runs/{run_id}",
    include_in_schema=False,
)
def get_delivery_run(
    run_id: int,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get delivery run by ID."""
    return _service.get_delivery_run(run_id)


@router.put(
    "/runs/{run_id}",
    summary="Update delivery run",
    description="Update delivery run header fields (status, vehicle, driver, date, notes).",
)
@alias_router.put(
    "/runs/{run_id}",
    include_in_schema=False,
)
def update_delivery_run(
    run_id: int,
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update delivery run."""
    return _service.update_delivery_run(run_id, payload)


# ---------------------------------------------------------------------------
# 3. Vehicle & Driver Assignment Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/runs/{run_id}/assign-vehicle",
    response_model=VehicleAssignmentResponse,
    summary="Assign vehicle and driver to run",
    description="Assign fleet vehicle and driver to delivery run. Validates payload weight/volume against vehicle capacity limits.",
)
@alias_router.post(
    "/runs/{run_id}/assign-vehicle",
    response_model=VehicleAssignmentResponse,
    include_in_schema=False,
)
def assign_vehicle_to_run(
    run_id: int,
    request_data: VehicleAssignmentRequest,
    current_user: dict = Depends(get_current_user),
) -> VehicleAssignmentResponse:
    """Assign vehicle and driver with capacity check."""
    try:
        return _service.assign_vehicle(run_id, request_data.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning vehicle to run #{run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign vehicle: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 4. Driver Manifest Generation Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/runs/{run_id}/manifest",
    response_model=DriverManifestResponse,
    summary="Get driver delivery manifest",
    description="Generate sequential daily drop-off manifest for driver's mobile device or printable run sheet.",
)
@alias_router.get(
    "/runs/{run_id}/manifest",
    response_model=DriverManifestResponse,
    include_in_schema=False,
)
def get_driver_manifest(
    run_id: int,
    current_user: dict = Depends(get_current_user),
) -> DriverManifestResponse:
    """Fetch driver manifest."""
    return _service.get_driver_manifest(run_id)


# ---------------------------------------------------------------------------
# 5. Warehouse LIFO Staging Pick List Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/runs/{run_id}/lifo-staging",
    response_model=LIFOPickListResponse,
    summary="Get LIFO staging pick list",
    description="Retrieve warehouse pick list sorted by Last-In, First-Out (LIFO) vehicle loading sequence.",
)
@alias_router.get(
    "/runs/{run_id}/lifo-staging",
    response_model=LIFOPickListResponse,
    include_in_schema=False,
)
def get_lifo_staging_pick_list(
    run_id: int,
    current_user: dict = Depends(get_current_user),
) -> LIFOPickListResponse:
    """Fetch LIFO vehicle loading pick list."""
    return _service.get_lifo_staging_pick_list(run_id)


@router.post(
    "/runs/{run_id}/resequence",
    summary="Resequence delivery run stops",
    description="Resequence drop-off stops order and recalculate LIFO vehicle loading sequence.",
)
@alias_router.post(
    "/runs/{run_id}/resequence",
    include_in_schema=False,
)
def resequence_run_stops(
    run_id: int,
    stop_ids_in_order: List[int],
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resequence stops."""
    return _service.resequence_stops(run_id, stop_ids_in_order)


# ---------------------------------------------------------------------------
# 6. Status Update Endpoints
# ---------------------------------------------------------------------------

@router.put(
    "/runs/{run_id}/status",
    summary="Update delivery run status",
    description="Transition delivery run status (Draft, Planned, Dispatched, In Transit, Completed, Cancelled).",
)
@alias_router.put(
    "/runs/{run_id}/status",
    include_in_schema=False,
)
def update_run_status(
    run_id: int,
    status_val: str = Query(..., alias="status", description="New status string"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update run status."""
    return _service.update_run_status(run_id, status_val)


@router.put(
    "/stops/{stop_id}/status",
    summary="Update run stop status",
    description="Transition stop status (Pending, Staged, Loaded, Delivered, Failed, Skipped).",
)
@alias_router.put(
    "/stops/{stop_id}/status",
    include_in_schema=False,
)
def update_stop_status(
    stop_id: int,
    status_val: str = Query(..., alias="status", description="New stop status string"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update stop status."""
    return _service.update_stop_status(stop_id, status_val)
