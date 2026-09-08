"""
Nova ERP — Real-Time Driver GPS Tracking & Dispatcher Fleet Controller
Exposes endpoints for driver mobile telemetry ingestion, live fleet monitoring,
geofence boundary checking, and customer notification dispatch.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from packages.auth.deps import require_permission, get_current_user
from modules.sales.models.delivery_tracking import (
    GPSLocationPing,
    DriverLocationBatchRequest,
    DriverCurrentLocationResponse,
    FleetLiveMapResponse,
    GeofenceCheckRequest,
    GeofenceEventResponse,
    CustomerNotificationPayload,
    CustomerNotificationResult,
)
from modules.sales.services.driver_tracking_service import (
    DriverTrackingService,
    driver_tracking_service as default_tracking_service,
)
from modules.sales.services.geofence_service import (
    GeofenceDetectionService,
    geofence_service as default_geofence_service,
)
from modules.sales.services.customer_delivery_notification_service import (
    CustomerDeliveryNotificationService,
    customer_notification_service as default_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sales/tracking",
    tags=["Real-Time Driver GPS Tracking & Fleet Map"],
)

_tracking_service: DriverTrackingService = default_tracking_service
_geofence_service: GeofenceDetectionService = default_geofence_service
_notification_service: CustomerDeliveryNotificationService = default_notification_service


# ---------------------------------------------------------------------------
# 1. Driver GPS Telemetry Ingestion
# ---------------------------------------------------------------------------

@router.post(
    "/location",
    summary="Ingest driver GPS telemetry coordinate ping",
    description="Save driver mobile device coordinates, heading, speed, and accuracy. Checks stop geofences automatically.",
)
def record_location_ping(
    ping: GPSLocationPing,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ingest single GPS coordinate fix from driver."""
    try:
        # Associate user id if omitted
        if not ping.driver_id and current_user and current_user.get('id'):
            ping.driver_id = current_user['id']
        return _tracking_service.record_location_ping(ping)
    except Exception as e:
        logger.error(f"Error ingesting GPS location ping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record location ping: {str(e)}",
        ) from e


@router.post(
    "/location/batch",
    summary="Ingest batch of buffered GPS telemetry pings",
    description="Batch upload queued GPS pings from driver mobile client after offline periods.",
)
def record_location_batch(
    batch: DriverLocationBatchRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ingest batch of driver GPS telemetry pings."""
    try:
        if not batch.driver_id and current_user and current_user.get('id'):
            batch.driver_id = current_user['id']
        return _tracking_service.record_location_batch(batch)
    except Exception as e:
        logger.error(f"Error ingesting GPS batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record GPS batch: {str(e)}",
        ) from e


@router.get(
    "/drivers/{driver_id}/location",
    response_model=Optional[DriverCurrentLocationResponse],
    summary="Get latest driver GPS location",
    description="Retrieve the latest recorded coordinates, speed, and status for a specific driver.",
)
def get_driver_location(
    driver_id: int,
    current_user: dict = Depends(get_current_user),
) -> Optional[DriverCurrentLocationResponse]:
    """Fetch latest location fix for a driver."""
    return _tracking_service.get_driver_current_location(driver_id)


# ---------------------------------------------------------------------------
# 2. Dispatcher Live Fleet Map & Run Trajectory
# ---------------------------------------------------------------------------

@router.get(
    "/fleet-live",
    response_model=FleetLiveMapResponse,
    summary="Get live fleet positions and operational status",
    description="Dispatcher overview aggregating all active vehicles, latest coordinates, stop progress, and dynamic ETAs.",
)
def get_fleet_live_map(
    current_user: dict = Depends(get_current_user),
) -> FleetLiveMapResponse:
    """Retrieve aggregated live fleet map overview for dispatchers."""
    try:
        return _tracking_service.get_fleet_live_map()
    except Exception as e:
        logger.error(f"Error fetching fleet live map: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fleet live map: {str(e)}",
        ) from e


@router.get(
    "/runs/{run_id}/live",
    summary="Get delivery run live tracking and telemetry breadcrumb trail",
    description="Retrieve real-time vehicle GPS path trail, current van position, and stop arrival states for a delivery run.",
)
def get_run_live_tracking(
    run_id: int,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch run telemetry trail and stop progress."""
    return _tracking_service.get_run_live_tracking(run_id)


# ---------------------------------------------------------------------------
# 3. Geofence Boundary Inspection
# ---------------------------------------------------------------------------

@router.post(
    "/geofence/check",
    response_model=List[GeofenceEventResponse],
    summary="Check coordinates against stop geofences",
    description="Manually or automatically evaluate a GPS coordinate against delivery stop arrival/departure perimeters.",
)
def check_geofence_boundary(
    req: GeofenceCheckRequest,
    current_user: dict = Depends(get_current_user),
) -> List[GeofenceEventResponse]:
    """Inspect vehicle proximity to delivery stops."""
    try:
        driver_id = req.driver_id or (current_user.get('id') if current_user else None)
        return _geofence_service.check_stop_geofences(
            run_id=req.run_id,
            driver_id=driver_id,
            latitude=req.latitude,
            longitude=req.longitude,
            speed_kmh=req.speed_kmh or 0.0,
            timestamp=req.timestamp,
        )
    except Exception as e:
        logger.error(f"Error evaluating geofences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check geofences: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# 4. Customer Delivery ETA Notification Dispatch
# ---------------------------------------------------------------------------

@router.post(
    "/stops/{stop_id}/notify",
    response_model=CustomerNotificationResult,
    summary="Dispatch customer delivery notification with live tracking link",
    description="Generates secure tracking token and dispatches SMS/WhatsApp alert with live ETA tracking link.",
)
def send_customer_delivery_notification(
    stop_id: int,
    payload: Optional[CustomerNotificationPayload] = None,
    current_user: dict = Depends(get_current_user),
) -> CustomerNotificationResult:
    """Dispatch SMS/WhatsApp notification with live ETA web tracking link."""
    try:
        data = payload or CustomerNotificationPayload(run_stop_id=stop_id)
        data.run_stop_id = stop_id
        return _notification_service.send_delivery_notification(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dispatching customer notification for stop {stop_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send customer notification: {str(e)}",
        ) from e
