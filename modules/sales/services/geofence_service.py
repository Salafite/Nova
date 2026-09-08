"""
Nova ERP — Geofence Detection Service
Calculates Haversine distance between real-time vehicle GPS coordinates and customer
delivery stop locations to trigger automated arrival and departure events.
"""
import math
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from modules.sales.repositories.driver_tracking_repo import (
    DriverTrackingRepository,
    driver_tracking_repo as default_repo,
)
from modules.sales.models.delivery_tracking import (
    GeofenceCheckRequest,
    GeofenceEventResponse,
)

logger = logging.getLogger(__name__)

# Earth radius in meters
EARTH_RADIUS_METERS = 6371000.0


def calculate_haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


class GeofenceDetectionService:
    """
    Service for geofence boundary inspection, automated stop arrival logging,
    dwell time calculation, and departure event recording.
    """

    def __init__(self, repo: Optional[DriverTrackingRepository] = None):
        self.repo = repo or default_repo

    def check_stop_geofences(
        self,
        run_id: int,
        driver_id: Optional[int],
        latitude: float,
        longitude: float,
        speed_kmh: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> List[GeofenceEventResponse]:
        """
        Evaluate current vehicle coordinates against all delivery stops in an active run.
        Triggers ENTER_GEOFENCE, EXIT_GEOFENCE, and DWELL_THRESHOLD events automatically.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        stops = self.repo.get_run_stops(run_id)
        events_generated: List[GeofenceEventResponse] = []

        for stop in stops:
            stop_id = stop['id']
            customer_name = stop.get('customer_name') or 'Customer'
            stop_lat = stop.get('latitude')
            stop_lng = stop.get('longitude')
            stop_status = stop.get('status', 'Pending')

            if stop_lat is None or stop_lng is None:
                continue

            try:
                target_lat = float(stop_lat)
                target_lng = float(stop_lng)
            except (ValueError, TypeError):
                continue

            distance = calculate_haversine_distance(latitude, longitude, target_lat, target_lng)
            radius = int(stop.get('geofence_radius_meters') or 150)

            arrived_at = stop.get('geofence_arrived_at')
            departed_at = stop.get('geofence_departed_at')

            if arrived_at and arrived_at.tzinfo is None:
                arrived_at = arrived_at.replace(tzinfo=timezone.utc)
            if departed_at and departed_at.tzinfo is None:
                departed_at = departed_at.replace(tzinfo=timezone.utc)

            # Case 1: Vehicle enters geofence radius
            if distance <= radius:
                if stop_status not in ('Arrived', 'Delivered', 'Completed'):
                    # First time entering geofence
                    update_payload = {
                        "geofence_arrived_at": timestamp,
                        "status": "Arrived",
                    }
                    self.repo.update_stop(stop_id, update_payload)

                    event_data = {
                        "run_stop_id": stop_id,
                        "run_id": run_id,
                        "driver_id": driver_id,
                        "event_type": "ENTER_GEOFENCE",
                        "distance_meters": round(distance, 2),
                        "latitude": latitude,
                        "longitude": longitude,
                        "event_timestamp": timestamp,
                        "dwell_duration_seconds": 0,
                    }
                    self.repo.log_geofence_event(event_data)

                    events_generated.append(GeofenceEventResponse(
                        run_stop_id=stop_id,
                        run_id=run_id,
                        event_type="ENTER_GEOFENCE",
                        distance_meters=round(distance, 2),
                        customer_name=customer_name,
                        triggered_at=timestamp,
                        message=f"Vehicle entered geofence for {customer_name} ({round(distance, 1)}m away)",
                        status_updated=True,
                        new_stop_status="Arrived",
                        dwell_duration_seconds=0,
                    ))

                elif arrived_at and not departed_at:
                    # Vehicle is currently dwelling inside geofence
                    dwell_seconds = int((timestamp - arrived_at).total_seconds())
                    if dwell_seconds >= 300:  # 5 minutes threshold
                        # Check if dwell threshold event already logged
                        recent_dwell = self.repo.get_geofence_events(run_id=run_id, stop_id=stop_id, limit=5)
                        has_dwell = any(e.get('event_type') == 'DWELL_THRESHOLD' for e in recent_dwell)
                        if not has_dwell:
                            event_data = {
                                "run_stop_id": stop_id,
                                "run_id": run_id,
                                "driver_id": driver_id,
                                "event_type": "DWELL_THRESHOLD",
                                "distance_meters": round(distance, 2),
                                "latitude": latitude,
                                "longitude": longitude,
                                "event_timestamp": timestamp,
                                "dwell_duration_seconds": dwell_seconds,
                            }
                            self.repo.log_geofence_event(event_data)
                            events_generated.append(GeofenceEventResponse(
                                run_stop_id=stop_id,
                                run_id=run_id,
                                event_type="DWELL_THRESHOLD",
                                distance_meters=round(distance, 2),
                                customer_name=customer_name,
                                triggered_at=timestamp,
                                message=f"Driver at {customer_name} for {dwell_seconds // 60} minutes",
                                status_updated=False,
                                new_stop_status=stop_status,
                                dwell_duration_seconds=dwell_seconds,
                            ))

            # Case 2: Vehicle was previously inside geofence and now departed
            elif distance > radius:
                if arrived_at and not departed_at:
                    dwell_seconds = int((timestamp - arrived_at).total_seconds())
                    update_payload = {
                        "geofence_departed_at": timestamp,
                    }
                    if stop_status == 'Arrived':
                        # Stop was arrived and driver left without manual mark, could remain Arrived or move to In Transit
                        pass
                    self.repo.update_stop(stop_id, update_payload)

                    event_data = {
                        "run_stop_id": stop_id,
                        "run_id": run_id,
                        "driver_id": driver_id,
                        "event_type": "EXIT_GEOFENCE",
                        "distance_meters": round(distance, 2),
                        "latitude": latitude,
                        "longitude": longitude,
                        "event_timestamp": timestamp,
                        "dwell_duration_seconds": dwell_seconds,
                    }
                    self.repo.log_geofence_event(event_data)

                    events_generated.append(GeofenceEventResponse(
                        run_stop_id=stop_id,
                        run_id=run_id,
                        event_type="EXIT_GEOFENCE",
                        distance_meters=round(distance, 2),
                        customer_name=customer_name,
                        triggered_at=timestamp,
                        message=f"Vehicle departed geofence for {customer_name} after {dwell_seconds}s dwell",
                        status_updated=False,
                        new_stop_status=stop_status,
                        dwell_duration_seconds=dwell_seconds,
                    ))

        return events_generated


geofence_service = GeofenceDetectionService()
