"""
Nova ERP — Driver GPS Tracking & Telemetry Repository
Handles database operations for Driver GPS Telemetry (T0129), Customer Live Tracking Sessions (T0130),
and Geofence Detection Events (T0131).
"""
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)


class DriverTrackingRepository:
    """
    Repository for high-frequency GPS coordinate telemetry, customer tracking sessions,
    and geofence events with multi-tenant isolation.
    """

    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')
        self.telemetry_repo = CrudRepository(
            'T0129',
            pk='id',
            business_columns=[
                'id', 'run_id', 'driver_id', 'vehicle_id', 'latitude', 'longitude',
                'speed_kmh', 'heading', 'accuracy_meters', 'battery_level',
                'recorded_at', 'is_active', 'business_id'
            ]
        )
        self.session_repo = CrudRepository(
            'T0130',
            pk='id',
            business_columns=[
                'id', 'run_stop_id', 'sales_order_id', 'customer_id',
                'tracking_token', 'token_expires_at', 'notification_sent_at',
                'notification_channel', 'notification_status', 'is_active', 'business_id'
            ]
        )
        self.geofence_repo = CrudRepository(
            'T0131',
            pk='id',
            business_columns=[
                'id', 'run_stop_id', 'run_id', 'driver_id', 'event_type',
                'distance_meters', 'latitude', 'longitude', 'event_timestamp',
                'dwell_duration_seconds', 'is_active', 'business_id'
            ]
        )
        self.stop_repo = CrudRepository(
            'T0113',
            pk='id',
            business_columns=[
                'id', 'delivery_run_id', 'sales_order_id', 'delivery_id',
                'customer_id', 'stop_sequence', 'lifo_staging_sequence',
                'delivery_address', 'contact_name', 'contact_phone', 'zone',
                'latitude', 'longitude', 'geofence_radius_meters',
                'geofence_arrived_at', 'geofence_departed_at',
                'live_eta_timestamp', 'live_remaining_distance_km',
                'tracking_token', 'status', 'special_instructions',
                'notes', 'loaded_at', 'delivered_at', 'is_active', 'business_id'
            ]
        )
        self.run_repo = CrudRepository(
            'T0112',
            pk='id',
            business_columns=[
                'id', 'run_number', 'run_date', 'driver_id', 'vehicle_id',
                'status', 'zone', 'total_stops', 'total_weight_kg',
                'total_volume_m3', 'dispatched_at', 'completed_at', 'notes',
                'is_active', 'business_id'
            ]
        )
        self.vehicle_repo = CrudRepository(
            'T0114',
            pk='id',
            business_columns=[
                'id', 'vehicle_code', 'name', 'license_plate', 'vehicle_type',
                'max_weight_capacity_kg', 'max_volume_capacity_m3',
                'default_driver_id', 'status', 'is_active', 'business_id'
            ]
        )
        self.customer_repo = CrudRepository(
            'T0010',
            pk='id',
            business_columns=[
                'id', 'name', 'phone', 'email', 'address', 'latitude', 'longitude',
                'geofence_radius_meters', 'delivery_zone', 'is_active', 'business_id'
            ]
        )

    # -----------------------------------------------------------------------
    # 1. GPS Telemetry Pings (T0129)
    # -----------------------------------------------------------------------

    def save_gps_ping(self, ping_data: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Save a single GPS ping record into T0129."""
        tenant_id = get_current_tenant()
        data = dict(ping_data)
        if tenant_id is not None and 'business_id' not in data:
            data['business_id'] = tenant_id
        if 'recorded_at' not in data or not data['recorded_at']:
            data['recorded_at'] = datetime.now(timezone.utc)
        return self.telemetry_repo.create(data, conn=conn)

    def save_gps_pings_batch(self, pings: List[Dict[str, Any]], conn=None) -> int:
        """Batch save multiple GPS pings into T0129."""
        if not pings:
            return 0
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            query = f"""
                INSERT INTO "{schema}".t0129 (
                    run_id, driver_id, vehicle_id, latitude, longitude,
                    speed_kmh, heading, accuracy_meters, battery_level,
                    recorded_at, business_id
                ) VALUES (
                    %(run_id)s, %(driver_id)s, %(vehicle_id)s, %(latitude)s, %(longitude)s,
                    %(speed_kmh)s, %(heading)s, %(accuracy_meters)s, %(battery_level)s,
                    %(recorded_at)s, %(business_id)s
                )
            """
            prepared = []
            for p in pings:
                item = dict(p)
                if tenant_id is not None and 'business_id' not in item:
                    item['business_id'] = tenant_id
                if 'recorded_at' not in item or not item['recorded_at']:
                    item['recorded_at'] = datetime.now(timezone.utc)
                if 'speed_kmh' not in item or item['speed_kmh'] is None:
                    item['speed_kmh'] = 0.0
                if 'heading' not in item or item['heading'] is None:
                    item['heading'] = 0.0
                if 'accuracy_meters' not in item or item['accuracy_meters'] is None:
                    item['accuracy_meters'] = 5.0
                prepared.append(item)

            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, query, prepared)
                conn.commit()
            return len(prepared)
        finally:
            if should_release:
                release_connection(conn)

    def get_latest_driver_location(self, driver_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent GPS location fix for a driver."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["driver_id = %s", "is_active = true"]
            params = [driver_id]
            if tenant_id is not None:
                clauses.append("business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT id, run_id, driver_id, vehicle_id, latitude, longitude,
                       speed_kmh, heading, accuracy_meters, battery_level, recorded_at, business_id
                FROM "{schema}".t0129
                WHERE {where_sql}
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_latest_vehicle_location(self, vehicle_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent GPS location fix for a vehicle."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["vehicle_id = %s", "is_active = true"]
            params = [vehicle_id]
            if tenant_id is not None:
                clauses.append("business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT id, run_id, driver_id, vehicle_id, latitude, longitude,
                       speed_kmh, heading, accuracy_meters, battery_level, recorded_at, business_id
                FROM "{schema}".t0129
                WHERE {where_sql}
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_run_telemetry_trail(self, run_id: int, limit: int = 200, conn=None) -> List[Dict[str, Any]]:
        """Retrieve chronological GPS telemetry trail breadcrumbs for a delivery run."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["run_id = %s", "is_active = true"]
            params = [run_id]
            if tenant_id is not None:
                clauses.append("business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            params.append(limit)
            query = f"""
                SELECT id, run_id, driver_id, vehicle_id, latitude, longitude,
                       speed_kmh, heading, accuracy_meters, battery_level, recorded_at
                FROM "{schema}".t0129
                WHERE {where_sql}
                ORDER BY recorded_at ASC, id ASC
                LIMIT %s
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 2. Live Fleet Aggregation
    # -----------------------------------------------------------------------

    def get_active_runs_with_vehicles(self, conn=None) -> List[Dict[str, Any]]:
        """Retrieve active delivery runs with driver, vehicle, and stop details."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["r.status IN ('Planned', 'Dispatched', 'In Transit', 'Draft')", "r.is_active = true"]
            params = []
            if tenant_id is not None:
                clauses.append("r.business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT
                    r.id AS run_id,
                    r.run_number,
                    r.status AS run_status,
                    r.run_date,
                    r.zone,
                    r.total_stops,
                    r.driver_id,
                    u.full_name AS driver_name,
                    u.username AS driver_username,
                    r.vehicle_id,
                    v.vehicle_code,
                    v.name AS vehicle_name,
                    v.license_plate
                FROM "{schema}".t0112 r
                LEFT JOIN "{schema}".t0021 u ON r.driver_id = u.id
                LEFT JOIN "{schema}".t0114 v ON r.vehicle_id = v.id
                WHERE {where_sql}
                ORDER BY r.id DESC
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_run_stops(self, run_id: int, conn=None) -> List[Dict[str, Any]]:
        """Retrieve all drop-off stops for a delivery run ordered by stop sequence."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["s.delivery_run_id = %s", "s.is_active = true"]
            params = [run_id]
            if tenant_id is not None:
                clauses.append("s.business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT
                    s.id,
                    s.delivery_run_id,
                    s.sales_order_id,
                    so.order_number AS sales_order_number,
                    s.delivery_id,
                    s.customer_id,
                    c.name AS customer_name,
                    s.delivery_address,
                    s.contact_name,
                    s.contact_phone,
                    s.stop_sequence,
                    s.lifo_staging_sequence,
                    s.status,
                    s.latitude,
                    s.longitude,
                    s.geofence_radius_meters,
                    s.geofence_arrived_at,
                    s.geofence_departed_at,
                    s.live_eta_timestamp,
                    s.live_remaining_distance_km,
                    s.tracking_token,
                    s.special_instructions,
                    s.notes,
                    s.loaded_at,
                    s.delivered_at
                FROM "{schema}".t0113 s
                LEFT JOIN "{schema}".t0010 c ON s.customer_id = c.id
                LEFT JOIN "{schema}".t0012 so ON s.sales_order_id = so.id
                WHERE {where_sql}
                ORDER BY s.stop_sequence ASC
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_stop_by_id(self, stop_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve single stop record by ID."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["s.id = %s", "s.is_active = true"]
            params = [stop_id]
            if tenant_id is not None:
                clauses.append("s.business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT
                    s.id,
                    s.delivery_run_id,
                    s.sales_order_id,
                    so.order_number AS sales_order_number,
                    s.delivery_id,
                    s.customer_id,
                    c.name AS customer_name,
                    c.phone AS customer_phone_master,
                    c.email AS customer_email_master,
                    s.delivery_address,
                    s.contact_name,
                    s.contact_phone,
                    s.stop_sequence,
                    s.lifo_staging_sequence,
                    s.status,
                    s.latitude,
                    s.longitude,
                    s.geofence_radius_meters,
                    s.geofence_arrived_at,
                    s.geofence_departed_at,
                    s.live_eta_timestamp,
                    s.live_remaining_distance_km,
                    s.tracking_token,
                    s.special_instructions,
                    s.notes,
                    s.loaded_at,
                    s.delivered_at
                FROM "{schema}".t0113 s
                LEFT JOIN "{schema}".t0010 c ON s.customer_id = c.id
                LEFT JOIN "{schema}".t0012 so ON s.sales_order_id = so.id
                WHERE {where_sql}
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def update_stop(self, stop_id: int, fields: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Update a stop record."""
        return self.stop_repo.update(stop_id, fields, conn=conn)

    def get_run_by_id(self, run_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve delivery run header by ID."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = get_current_tenant()
            schema = self.schema
            clauses = ["r.id = %s", "r.is_active = true"]
            params = [run_id]
            if tenant_id is not None:
                clauses.append("r.business_id = %s")
                params.append(tenant_id)
            where_sql = " AND ".join(clauses)
            query = f"""
                SELECT
                    r.id,
                    r.run_number,
                    r.run_date,
                    r.driver_id,
                    u.full_name AS driver_name,
                    r.vehicle_id,
                    v.vehicle_code,
                    v.license_plate,
                    r.status,
                    r.zone,
                    r.total_stops,
                    r.total_weight_kg,
                    r.total_volume_m3,
                    r.dispatched_at,
                    r.completed_at,
                    r.notes
                FROM "{schema}".t0112 r
                LEFT JOIN "{schema}".t0021 u ON r.driver_id = u.id
                LEFT JOIN "{schema}".t0114 v ON r.vehicle_id = v.id
                WHERE {where_sql}
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 3. Customer Live Tracking Sessions (T0130)
    # -----------------------------------------------------------------------

    def create_customer_tracking_session(self, session_data: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Create a new customer live tracking session record with secure tracking token."""
        tenant_id = get_current_tenant()
        data = dict(session_data)
        if tenant_id is not None and 'business_id' not in data:
            data['business_id'] = tenant_id
        return self.session_repo.create(data, conn=conn)

    def get_customer_tracking_session_by_token(self, token: str, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve customer tracking session by token without tenant restriction (public secure access)."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            schema = self.schema
            query = f"""
                SELECT
                    s.id AS session_id,
                    s.run_stop_id,
                    s.sales_order_id,
                    s.customer_id,
                    s.tracking_token,
                    s.token_expires_at,
                    s.notification_sent_at,
                    s.notification_channel,
                    s.notification_status,
                    s.business_id,
                    st.delivery_run_id,
                    st.stop_sequence,
                    st.delivery_address,
                    st.status AS stop_status,
                    st.latitude AS stop_latitude,
                    st.longitude AS stop_longitude,
                    st.geofence_radius_meters,
                    st.geofence_arrived_at,
                    st.geofence_departed_at,
                    st.live_eta_timestamp,
                    st.live_remaining_distance_km,
                    c.name AS customer_name,
                    c.phone AS customer_phone,
                    so.order_number AS sales_order_number,
                    r.run_number,
                    r.driver_id,
                    u.full_name AS driver_name,
                    r.vehicle_id,
                    v.vehicle_code
                FROM "{schema}".t0130 s
                JOIN "{schema}".t0113 st ON s.run_stop_id = st.id
                LEFT JOIN "{schema}".t0010 c ON s.customer_id = c.id
                LEFT JOIN "{schema}".t0012 so ON s.sales_order_id = so.id
                LEFT JOIN "{schema}".t0112 r ON st.delivery_run_id = r.id
                LEFT JOIN "{schema}".t0021 u ON r.driver_id = u.id
                LEFT JOIN "{schema}".t0114 v ON r.vehicle_id = v.id
                WHERE s.tracking_token = %s AND s.is_active = true
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (token,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def update_customer_tracking_session(self, session_id: int, fields: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Update a tracking session record."""
        return self.session_repo.update(session_id, fields, conn=conn)

    # -----------------------------------------------------------------------
    # 4. Geofence Detection Events (T0131)
    # -----------------------------------------------------------------------

    def log_geofence_event(self, event_data: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Insert a geofence crossing event into T0131."""
        tenant_id = get_current_tenant()
        data = dict(event_data)
        if tenant_id is not None and 'business_id' not in data:
            data['business_id'] = tenant_id
        if 'event_timestamp' not in data or not data['event_timestamp']:
            data['event_timestamp'] = datetime.now(timezone.utc)
        return self.geofence_repo.create(data, conn=conn)

    def get_geofence_events(
        self,
        run_id: Optional[int] = None,
        stop_id: Optional[int] = None,
        limit: int = 50,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Query geofence events for a run or stop."""
        filters = {}
        if run_id is not None:
            filters['run_id'] = run_id
        if stop_id is not None:
            filters['run_stop_id'] = stop_id
        return self.geofence_repo.list(filters=filters or None, limit=limit, conn=conn)


driver_tracking_repo = DriverTrackingRepository()
