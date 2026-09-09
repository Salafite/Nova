"""
Nova ERP — Dynamic ETA Calculation Service
Computes real-time traffic-adjusted arrival time windows and distance estimates
based on vehicle GPS speed and geographic coordinates.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from modules.sales.services.geofence_service import calculate_haversine_distance
from modules.sales.repositories.driver_tracking_repo import (
    DriverTrackingRepository,
    driver_tracking_repo as default_repo,
)

logger = logging.getLogger(__name__)

# Urban route tortuosity factor (road distance vs straight-line flight distance)
ROAD_FACTOR = 1.35

# Default baseline urban transit speed when truck is idling or at traffic signals
DEFAULT_URBAN_SPEED_KMH = 35.0


class DynamicETAService:
    """
    Engine for real-time delivery ETA window forecasting and route stop progression.
    """

    def __init__(self, repo: Optional[DriverTrackingRepository] = None):
        self.repo = repo or default_repo

    def calculate_stop_eta(
        self,
        vehicle_lat: float,
        vehicle_lng: float,
        stop_lat: float,
        stop_lng: float,
        current_speed_kmh: float = 0.0,
        traffic_factor: float = 1.15,
        buffer_minutes: int = 5,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate dynamic arrival time window and remaining road distance from vehicle to stop.
        """
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        straight_distance_m = calculate_haversine_distance(vehicle_lat, vehicle_lng, stop_lat, stop_lng)
        straight_km = straight_distance_m / 1000.0
        estimated_road_km = straight_km * ROAD_FACTOR

        # Determine effective speed
        effective_speed = current_speed_kmh if (current_speed_kmh and current_speed_kmh >= 15.0) else DEFAULT_URBAN_SPEED_KMH

        # Calculate transit duration
        transit_hours = (estimated_road_km / effective_speed) * traffic_factor
        transit_minutes = max(1, round(transit_hours * 60))

        estimated_arrival = now + timedelta(minutes=transit_minutes)
        window_start = estimated_arrival - timedelta(minutes=buffer_minutes)
        window_end = estimated_arrival + timedelta(minutes=buffer_minutes)

        return {
            "straight_line_km": round(straight_km, 2),
            "distance_km": round(estimated_road_km, 2),
            "travel_time_minutes": transit_minutes,
            "estimated_arrival": estimated_arrival,
            "eta_window_start": window_start,
            "eta_window_end": window_end,
        }

    def recalculate_run_stops_etas(
        self,
        run_id: int,
        current_lat: float,
        current_lng: float,
        current_speed_kmh: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Recalculate and persist live ETAs for all remaining pending stops on a delivery route.
        Accounts for sequential customer drop-offs and estimated unloading dwell times.
        """
        stops = self.repo.get_run_stops(run_id)
        if not stops:
            return []

        now = datetime.now(timezone.utc)
        cur_lat = current_lat
        cur_lng = current_lng
        cumulative_time = now
        results = []

        for stop in stops:
            stop_id = stop['id']
            status_val = stop.get('status', 'Pending')

            # Skip completed / delivered stops
            if status_val in ('Delivered', 'Completed', 'Failed', 'Skipped'):
                results.append(stop)
                continue

            stop_lat = stop.get('latitude')
            stop_lng = stop.get('longitude')

            if stop_lat is not None and stop_lng is not None:
                try:
                    s_lat = float(stop_lat)
                    s_lng = float(stop_lng)
                    eta_calc = self.calculate_stop_eta(
                        vehicle_lat=cur_lat,
                        vehicle_lng=cur_lng,
                        stop_lat=s_lat,
                        stop_lng=s_lng,
                        current_speed_kmh=current_speed_kmh,
                        reference_time=cumulative_time,
                    )

                    # Update database record
                    update_data = {
                        "live_eta_timestamp": eta_calc['estimated_arrival'],
                        "live_remaining_distance_km": eta_calc['distance_km'],
                    }
                    self.repo.update_stop(stop_id, update_data)

                    # Next stop calculation starts from this stop location and arrival time + 10 mins dwell
                    cur_lat = s_lat
                    cur_lng = s_lng
                    cumulative_time = eta_calc['estimated_arrival'] + timedelta(minutes=10)

                    stop['live_eta_timestamp'] = eta_calc['estimated_arrival']
                    stop['live_remaining_distance_km'] = eta_calc['distance_km']
                except Exception as e:
                    logger.warning(f"Failed to calculate ETA for stop {stop_id}: {e}")

            results.append(stop)

        return results


eta_service = DynamicETAService()
