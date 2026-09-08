"""
Nova ERP — Driver GPS Tracking & Fleet Live State Service
Coordinates driver GPS coordinate ingestion, real-time fleet state aggregation,
and dispatcher live map data delivery.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status

from modules.sales.repositories.driver_tracking_repo import (
    DriverTrackingRepository,
    driver_tracking_repo as default_repo,
)
from modules.sales.models.delivery_tracking import (
    GPSLocationPing,
    DriverLocationBatchRequest,
    DriverCurrentLocationResponse,
    FleetVehicleLiveStatus,
    FleetLiveMapResponse,
)

logger = logging.getLogger(__name__)


class DriverTrackingService:
    """
    Business service layer for high-throughput driver GPS telemetry ingestion,
    fleet live map tracking, and run location trajectory aggregation.
    """

    def __init__(self, repo: Optional[DriverTrackingRepository] = None):
        self.repo = repo or default_repo
        self._geofence_service = None
        self._eta_service = None

    @property
    def geofence_service(self):
        if self._geofence_service is None:
            from modules.sales.services.geofence_service import geofence_service
            self._geofence_service = geofence_service
        return self._geofence_service

    @property
    def eta_service(self):
        if self._eta_service is None:
            from modules.sales.services.eta_calculation_service import eta_service
            self._eta_service = eta_service
        return self._eta_service

    def record_location_ping(self, ping: GPSLocationPing, check_geofences: bool = True) -> Dict[str, Any]:
        """
        Ingest and save a single GPS location coordinate ping from a driver mobile client.
        Optionally evaluates proximity against active stop geofences and recalibrates ETAs.
        """
        ping_dict = ping.model_dump() if hasattr(ping, "model_dump") else ping.dict()
        created = self.repo.save_gps_ping(ping_dict)

        # Trigger automatic geofence boundary inspection if associated with an active run
        geofence_events = []
        if check_geofences and ping.run_id:
            try:
                events = self.geofence_service.check_stop_geofences(
                    run_id=ping.run_id,
                    driver_id=ping.driver_id,
                    latitude=ping.latitude,
                    longitude=ping.longitude,
                    speed_kmh=ping.speed_kmh or 0.0,
                    timestamp=ping.recorded_at or datetime.now(timezone.utc),
                )
                geofence_events = events
            except Exception as e:
                logger.warning(f"Geofence check failed during ping recording: {e}", exc_info=True)

        return {
            "ping": created,
            "geofence_events": geofence_events,
        }

    def record_location_batch(self, batch: DriverLocationBatchRequest) -> Dict[str, Any]:
        """
        Ingest a batch of buffered GPS telemetry pings from an offline or high-frequency driver client.
        """
        pings_data = []
        for p in batch.pings:
            p_dict = p.model_dump() if hasattr(p, "model_dump") else p.dict()
            if not p_dict.get('driver_id') and batch.driver_id:
                p_dict['driver_id'] = batch.driver_id
            if not p_dict.get('run_id') and batch.run_id:
                p_dict['run_id'] = batch.run_id
            if not p_dict.get('vehicle_id') and batch.vehicle_id:
                p_dict['vehicle_id'] = batch.vehicle_id
            pings_data.append(p_dict)

        count = self.repo.save_gps_pings_batch(pings_data)

        # Evaluate geofence for the latest ping in the batch
        geofence_events = []
        if pings_data and batch.run_id:
            latest = pings_data[-1]
            try:
                events = self.geofence_service.check_stop_geofences(
                    run_id=batch.run_id,
                    driver_id=batch.driver_id or latest.get('driver_id'),
                    latitude=latest['latitude'],
                    longitude=latest['longitude'],
                    speed_kmh=latest.get('speed_kmh', 0.0),
                    timestamp=latest.get('recorded_at') or datetime.now(timezone.utc),
                )
                geofence_events = events
            except Exception as e:
                logger.warning(f"Geofence batch check failed: {e}", exc_info=True)

        return {
            "pings_ingested": count,
            "geofence_events": geofence_events,
        }

    def get_driver_current_location(self, driver_id: int) -> Optional[DriverCurrentLocationResponse]:
        """Fetch the most recent GPS location fix and status for a driver."""
        ping = self.repo.get_latest_driver_location(driver_id)
        if not ping:
            return None

        speed = float(ping.get('speed_kmh') or 0.0)
        status_val = "Moving" if speed > 5.0 else "Idle"

        return DriverCurrentLocationResponse(
            driver_id=ping.get('driver_id'),
            run_id=ping.get('run_id'),
            vehicle_id=ping.get('vehicle_id'),
            latitude=float(ping['latitude']),
            longitude=float(ping['longitude']),
            speed_kmh=speed,
            heading=float(ping.get('heading') or 0.0),
            accuracy_meters=float(ping.get('accuracy_meters') or 5.0),
            battery_level=float(ping['battery_level']) if ping.get('battery_level') is not None else None,
            recorded_at=ping.get('recorded_at') or datetime.now(timezone.utc),
            status=status_val,
        )

    def get_fleet_live_map(self) -> FleetLiveMapResponse:
        """
        Aggregate live operational status for all active fleet transport vehicles,
        current GPS coordinates, stop progression, and next stop ETAs for dispatchers.
        """
        active_runs = self.repo.get_active_runs_with_vehicles()
        vehicle_statuses: List[FleetVehicleLiveStatus] = []
        total_in_transit_orders = 0
        now = datetime.now(timezone.utc)

        for r in active_runs:
            run_id = r.get('run_id')
            vehicle_id = r.get('vehicle_id')
            driver_id = r.get('driver_id')
            vehicle_code = r.get('vehicle_code') or f"VEH-{vehicle_id or 'UNKNOWN'}"

            # Retrieve latest location ping for vehicle or driver
            latest_ping = None
            if vehicle_id:
                latest_ping = self.repo.get_latest_vehicle_location(vehicle_id)
            if not latest_ping and driver_id:
                latest_ping = self.repo.get_latest_driver_location(driver_id)

            # Query stops for this run
            stops = self.repo.get_run_stops(run_id)
            total_stops = len(stops)
            completed_stops = sum(1 for s in stops if s.get('status') in ('Delivered', 'Completed'))
            remaining_stops = total_stops - completed_stops
            total_in_transit_orders += remaining_stops

            # Find next target pending stop
            next_stop = next((s for s in stops if s.get('status') not in ('Delivered', 'Completed', 'Failed', 'Skipped')), None)

            # Determine operational vehicle status
            cur_lat = float(latest_ping['latitude']) if latest_ping else None
            cur_lng = float(latest_ping['longitude']) if latest_ping else None
            speed = float(latest_ping.get('speed_kmh') or 0.0) if latest_ping else 0.0
            heading = float(latest_ping.get('heading') or 0.0) if latest_ping else 0.0
            last_ping_at = latest_ping.get('recorded_at') if latest_ping else None
            battery = float(latest_ping['battery_level']) if latest_ping and latest_ping.get('battery_level') is not None else None

            # Status classification
            if not latest_ping or (now - last_ping_at.replace(tzinfo=timezone.utc) if last_ping_at and last_ping_at.tzinfo is None else (now - last_ping_at if last_ping_at else timedelta(hours=99))) > timedelta(minutes=30):
                status_str = "Offline" if not latest_ping else "Idle"
            elif next_stop and next_stop.get('status') == 'Arrived':
                status_str = "At Stop"
            elif speed > 5.0:
                status_str = "Moving"
            elif next_stop and next_stop.get('live_eta_timestamp') and next_stop.get('live_eta_timestamp') < now:
                status_str = "Delayed"
            else:
                status_str = "Idle"

            # Compute next stop dynamic ETA & distance if coordinates exist
            next_customer = None
            next_address = None
            next_eta = None
            next_dist = None
            next_stop_id = None

            if next_stop:
                next_stop_id = next_stop.get('id')
                next_customer = next_stop.get('customer_name')
                next_address = next_stop.get('delivery_address')
                next_eta = next_stop.get('live_eta_timestamp')
                next_dist = float(next_stop['live_remaining_distance_km']) if next_stop.get('live_remaining_distance_km') is not None else None

                if (next_eta is None or next_dist is None) and cur_lat and cur_lng and next_stop.get('latitude') and next_stop.get('longitude'):
                    try:
                        calc = self.eta_service.calculate_stop_eta(
                            vehicle_lat=cur_lat,
                            vehicle_lng=cur_lng,
                            stop_lat=float(next_stop['latitude']),
                            stop_lng=float(next_stop['longitude']),
                            current_speed_kmh=speed,
                        )
                        next_eta = calc.get('estimated_arrival')
                        next_dist = calc.get('distance_km')
                    except Exception as e:
                        logger.warning(f"Error calculating stop ETA: {e}")

            vehicle_statuses.append(FleetVehicleLiveStatus(
                vehicle_id=vehicle_id,
                vehicle_code=vehicle_code,
                driver_id=driver_id,
                driver_name=r.get('driver_name') or r.get('driver_username'),
                run_id=run_id,
                run_number=r.get('run_number'),
                current_latitude=cur_lat,
                current_longitude=cur_lng,
                speed_kmh=speed,
                heading=heading,
                status=status_str,
                last_ping_at=last_ping_at,
                battery_level=battery,
                total_stops=total_stops,
                completed_stops=completed_stops,
                remaining_stops=remaining_stops,
                current_stop_id=next_stop_id,
                next_stop_customer=next_customer,
                next_stop_address=next_address,
                next_stop_eta=next_eta,
                next_stop_distance_km=next_dist,
            ))

        return FleetLiveMapResponse(
            active_vehicles=vehicle_statuses,
            total_active_runs=len(active_runs),
            total_in_transit_orders=total_in_transit_orders,
            as_of=now,
        )

    def get_run_live_tracking(self, run_id: int) -> Dict[str, Any]:
        """
        Retrieve live map overview for a specific delivery run:
        header details, vehicle telemetry trail breadcrumbs, latest location fix,
        and sequential stop list with geofence and live ETA states.
        """
        run = self.repo.get_run_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Delivery run {run_id} not found")

        trail = self.repo.get_run_telemetry_trail(run_id, limit=200)
        latest_ping = trail[-1] if trail else (self.repo.get_latest_driver_location(run.get('driver_id')) if run.get('driver_id') else None)

        stops = self.repo.get_run_stops(run_id)
        geofence_events = self.repo.get_geofence_events(run_id=run_id, limit=50)

        return {
            "run": run,
            "latest_ping": latest_ping,
            "telemetry_trail": trail,
            "stops": stops,
            "geofence_events": geofence_events,
        }


driver_tracking_service = DriverTrackingService()
