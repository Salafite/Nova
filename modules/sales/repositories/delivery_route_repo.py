"""
Nova ERP — Delivery Route & Driver Dispatch Repository
Handles database operations for delivery runs (T0112), driver manifests / stops (T0113),
delivery vehicles (T0114), and customer zone mappings (T0115).
"""
import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.core.repositories.base import CrudRepository
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)


class DeliveryRouteRepository:
    """
    Repository for delivery route planning, vehicle dispatch, driver manifests,
    and LIFO staging dock sequences.
    """

    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')
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
        self.stop_repo = CrudRepository(
            'T0113',
            pk='id',
            business_columns=[
                'id', 'delivery_run_id', 'sales_order_id', 'delivery_id',
                'customer_id', 'stop_sequence', 'lifo_staging_sequence',
                'delivery_address', 'contact_name', 'contact_phone', 'zone',
                'status', 'special_instructions', 'notes', 'loaded_at',
                'delivered_at', 'is_active', 'business_id'
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
        self.zone_repo = CrudRepository(
            'T0115',
            pk='id',
            business_columns=[
                'id', 'customer_id', 'zone_name', 'territory_code',
                'postal_code_prefix', 'preferred_driver_id', 'is_active',
                'business_id'
            ]
        )

    # -----------------------------------------------------------------------
    # 1. Unassigned Delivery Orders & Route Planning
    # -----------------------------------------------------------------------

    def get_unassigned_orders(
        self,
        delivery_date: Optional[date] = None,
        zone_name: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch confirmed delivery sales orders not yet assigned to an active delivery run.
        Groups by customer zone / territory and calculates total weight and volume.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            clauses = ["so.delivery_run_id IS NULL", "so.status NOT IN ('Cancelled', 'Draft')"]
            params: list[Any] = []

            if tenant_id is not None:
                clauses.append("so.business_id = %s")
                params.append(tenant_id)

            if delivery_date:
                clauses.append("(so.delivery_date = %s OR (so.delivery_date IS NULL AND so.order_date = %s))")
                params.extend([delivery_date, delivery_date])

            if zone_name:
                clauses.append("(COALESCE(so.delivery_zone, zm.zone_name, c.delivery_zone) = %s)")
                params.append(zone_name)

            if warehouse_id:
                clauses.append("so.warehouse_id = %s")
                params.append(warehouse_id)

            where_sql = " AND ".join(clauses)

            query = f"""
            SELECT 
                so.id AS sales_order_id,
                COALESCE(so.order_number, 'SO-' || so.id::text) AS sales_order_number,
                COALESCE(so.order_date, CURRENT_DATE) AS order_date,
                so.customer_id,
                COALESCE(c.name, 'Customer #' || so.customer_id::text) AS customer_name,
                COALESCE(c.address, c.street, 'Default Delivery Address') AS delivery_address,
                c.phone AS customer_phone,
                COALESCE(so.delivery_zone, zm.zone_name, c.delivery_zone, 'General') AS zone_name,
                COALESCE(SUM(sol.qty * COALESCE(p.weight, p.weight_kg, 1.0)), 0.0)::FLOAT AS total_weight,
                COALESCE(SUM(sol.qty * COALESCE(p.volume, p.volume_m3, 0.01)), 0.0)::FLOAT AS total_volume,
                COALESCE(so.total_amount, 0.0)::FLOAT AS total_amount
            FROM "{self.schema}".t0012 so
            JOIN "{self.schema}".t0010 c ON so.customer_id = c.id
            LEFT JOIN "{self.schema}".t0115 zm ON c.id = zm.customer_id AND zm.is_active = true
            LEFT JOIN "{self.schema}".t0013 sol ON so.id = sol.sales_order_id
            LEFT JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
            WHERE {where_sql}
            GROUP BY so.id, so.order_number, so.order_date, so.customer_id, c.name, c.address, c.street, c.phone, so.delivery_zone, zm.zone_name, c.delivery_zone, so.total_amount
            ORDER BY zone_name ASC, so.id ASC;
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 2. Delivery Run (Header T0112) Operations
    # -----------------------------------------------------------------------

    def generate_run_number(self, conn=None) -> str:
        """Generate atomic delivery run number (RUN-XXXXX)."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT nextval('\"{self.schema}\".seq_delivery_run_number');")
                val = cur.fetchone()[0]
                return f"RUN-{val:05d}"
        except Exception as e:
            logger.warning(f"Failed to use sequence seq_delivery_run_number: {e}")
            import uuid
            return f"RUN-{uuid.uuid4().hex[:6].upper()}"
        finally:
            if should_release:
                release_connection(conn)

    def create_delivery_run(self, payload: dict, conn=None) -> Dict[str, Any]:
        """Creates header record in T0112."""
        data = dict(payload)
        if not data.get('run_number'):
            data['run_number'] = self.generate_run_number(conn=conn)
        return self.run_repo.create(data, conn=conn)

    def get_delivery_run(self, run_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Get single delivery run with vehicle and driver info."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            tenant_clause = 'AND r.business_id = %s' if tenant_id is not None else ''
            params = [run_id]
            if tenant_id is not None:
                params.append(tenant_id)

            query = f"""
            SELECT 
                r.id,
                r.run_number,
                r.run_date,
                r.driver_id,
                COALESCE(u.full_name, u.username) AS driver_name,
                r.vehicle_id,
                v.vehicle_code,
                r.status,
                r.zone AS zone_name,
                r.total_stops AS total_orders,
                r.total_weight_kg AS total_weight,
                r.total_volume_m3 AS total_volume,
                v.max_weight_capacity_kg AS max_weight_capacity,
                v.max_volume_capacity_m3 AS max_volume_capacity,
                r.dispatched_at,
                r.completed_at,
                r.notes,
                r.is_active,
                r.created_at,
                r.updated_at
            FROM "{self.schema}".t0112 r
            LEFT JOIN "{self.schema}".t0114 v ON r.vehicle_id = v.id
            LEFT JOIN "{self.schema}".t0021 u ON r.driver_id = u.id
            WHERE r.id = %s {tenant_clause};
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def list_delivery_runs(
        self,
        run_date: Optional[date] = None,
        zone_name: Optional[str] = None,
        status: Optional[str] = None,
        driver_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List delivery runs with joined relations and filtering."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            clauses = ["r.is_active = true"]
            params: list[Any] = []

            if tenant_id is not None:
                clauses.append("r.business_id = %s")
                params.append(tenant_id)
            if run_date:
                clauses.append("r.run_date = %s")
                params.append(run_date)
            if zone_name:
                clauses.append("r.zone = %s")
                params.append(zone_name)
            if status:
                clauses.append("r.status = %s")
                params.append(status)
            if driver_id:
                clauses.append("r.driver_id = %s")
                params.append(driver_id)

            where_sql = " AND ".join(clauses)

            query = f"""
            SELECT 
                r.id,
                r.run_number,
                r.run_date,
                r.driver_id,
                COALESCE(u.full_name, u.username) AS driver_name,
                r.vehicle_id,
                v.vehicle_code,
                r.status,
                r.zone AS zone_name,
                r.total_stops AS total_orders,
                r.total_weight_kg::FLOAT AS total_weight,
                r.total_volume_m3::FLOAT AS total_volume,
                v.max_weight_capacity_kg::FLOAT AS max_weight_capacity,
                v.max_volume_capacity_m3::FLOAT AS max_volume_capacity,
                r.notes,
                r.is_active,
                r.created_at,
                r.updated_at,
                COUNT(*) OVER()::INT AS full_count
            FROM "{self.schema}".t0112 r
            LEFT JOIN "{self.schema}".t0114 v ON r.vehicle_id = v.id
            LEFT JOIN "{self.schema}".t0021 u ON r.driver_id = u.id
            WHERE {where_sql}
            ORDER BY r.run_date DESC, r.id DESC
            LIMIT %s OFFSET %s;
            """
            params.extend([limit, offset])

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]
                total = rows[0]['full_count'] if rows else 0
                return rows, total
        finally:
            if should_release:
                release_connection(conn)

    def update_delivery_run(self, run_id: int, payload: dict, conn=None) -> Optional[Dict[str, Any]]:
        """Update delivery run header fields."""
        return self.run_repo.update(run_id, payload, conn=conn)

    # -----------------------------------------------------------------------
    # 3. Delivery Run Stops / Manifest Items (T0113) Operations
    # -----------------------------------------------------------------------

    def create_run_stop(self, payload: dict, conn=None) -> Dict[str, Any]:
        """Creates stop line in T0113."""
        return self.stop_repo.create(payload, conn=conn)

    def get_run_stops(self, run_id: int, conn=None) -> List[Dict[str, Any]]:
        """Get stops for a delivery run ordered by stop_sequence."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
            SELECT 
                s.id,
                s.delivery_run_id,
                s.sales_order_id,
                COALESCE(so.order_number, 'SO-' || s.sales_order_id::text) AS sales_order_number,
                s.delivery_id,
                s.customer_id,
                COALESCE(c.name, 'Customer #' || s.customer_id::text) AS customer_name,
                s.stop_sequence AS stop_number,
                s.lifo_staging_sequence,
                s.delivery_address,
                s.contact_name AS contact_person,
                s.contact_phone AS customer_phone,
                s.status,
                s.special_instructions,
                s.notes,
                s.loaded_at,
                s.delivered_at,
                s.is_active
            FROM "{self.schema}".t0113 s
            LEFT JOIN "{self.schema}".t0012 so ON s.sales_order_id = so.id
            LEFT JOIN "{self.schema}".t0010 c ON s.customer_id = c.id
            WHERE s.delivery_run_id = %s AND s.is_active = true
            ORDER BY s.stop_sequence ASC;
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (run_id,))
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def update_run_stop(self, stop_id: int, payload: dict, conn=None) -> Optional[Dict[str, Any]]:
        """Update stop record in T0113."""
        return self.stop_repo.update(stop_id, payload, conn=conn)

    def link_sales_order_to_run(self, sales_order_id: int, run_id: Optional[int], zone_name: Optional[str] = None, conn=None):
        """Update t0012 to associate or clear delivery_run_id."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            sql = f"""
            UPDATE "{self.schema}".t0012
            SET delivery_run_id = %s,
                delivery_zone = COALESCE(%s, delivery_zone),
                updated_at = NOW()
            WHERE id = %s;
            """
            with conn.cursor() as cur:
                cur.execute(sql, (run_id, zone_name, sales_order_id))
                if should_release:
                    conn.commit()
        except Exception:
            if should_release:
                conn.rollback()
            raise
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 4. Vehicle Assets (T0114)
    # -----------------------------------------------------------------------

    def get_vehicle_by_id_or_code(self, vehicle_id: Optional[int] = None, vehicle_code: Optional[str] = None, conn=None) -> Optional[Dict[str, Any]]:
        """Fetch vehicle details from T0114."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            if vehicle_id:
                return self.vehicle_repo.get(vehicle_id, conn=conn)
            elif vehicle_code:
                vehicles = self.vehicle_repo.list(filters={'vehicle_code': vehicle_code}, conn=conn)
                return vehicles[0] if vehicles else None
            return None
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 5. Driver Manifest Query
    # -----------------------------------------------------------------------

    def get_driver_manifest_details(self, run_id: int, conn=None) -> Dict[str, Any]:
        """
        Fetch complete driver manifest information including sequential drop-offs,
        customer contact details, addresses, item counts, and total weights.
        """
        run = self.get_delivery_run(run_id, conn=conn)
        if not run:
            return {}

        stops = self.get_run_stops(run_id, conn=conn)

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            # Augment stops with items count and line weight
            augmented_stops = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                for stop in stops:
                    so_id = stop.get('sales_order_id')
                    items_count = 0
                    total_weight = 0.0
                    if so_id:
                        query = f"""
                        SELECT 
                            COUNT(sol.id)::INT AS items_count,
                            COALESCE(SUM(sol.qty * COALESCE(p.weight, p.weight_kg, 1.0)), 0.0)::FLOAT AS total_weight
                        FROM "{self.schema}".t0013 sol
                        LEFT JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                        WHERE sol.sales_order_id = %s;
                        """
                        cur.execute(query, (so_id,))
                        row = cur.fetchone()
                        if row:
                            items_count = row.get('items_count', 0)
                            total_weight = row.get('total_weight', 0.0)

                    augmented_stops.append({
                        "stop_number": stop.get('stop_number', 1),
                        "sales_order_id": so_id,
                        "sales_order_number": stop.get('sales_order_number') or f"SO-{so_id}",
                        "customer_id": stop.get('customer_id'),
                        "customer_name": stop.get('customer_name') or "",
                        "delivery_address": stop.get('delivery_address') or "",
                        "customer_phone": stop.get('customer_phone'),
                        "contact_person": stop.get('contact_person'),
                        "estimated_arrival": stop.get('estimated_arrival'),
                        "status": stop.get('status') or "Pending",
                        "special_instructions": stop.get('special_instructions'),
                        "items_count": items_count,
                        "total_weight": total_weight,
                    })

            return {
                "run_id": run['id'],
                "run_number": run['run_number'],
                "run_date": run['run_date'],
                "zone_name": run.get('zone_name') or "General",
                "vehicle_code": run.get('vehicle_code'),
                "driver_name": run.get('driver_name'),
                "status": run.get('status') or "Draft",
                "total_stops": len(augmented_stops),
                "stops": augmented_stops,
            }
        finally:
            if should_release:
                release_connection(conn)

    # -----------------------------------------------------------------------
    # 6. LIFO Pick List & Staging Dock Query
    # -----------------------------------------------------------------------

    def get_lifo_staging_pick_list_details(self, run_id: int, conn=None) -> Dict[str, Any]:
        """
        Fetch LIFO vehicle loading sequence.
        Staging Sequence 1 = Last customer drop-off (loaded deepest into the truck).
        Staging Sequence N = First customer drop-off (loaded last at truck doors).
        """
        run = self.get_delivery_run(run_id, conn=conn)
        if not run:
            return {}

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            # Query stops ordered by lifo_staging_sequence ASC
            query_stops = f"""
            SELECT 
                s.id,
                s.stop_sequence AS stop_number,
                s.lifo_staging_sequence AS staging_sequence,
                s.sales_order_id,
                COALESCE(so.order_number, 'SO-' || s.sales_order_id::text) AS sales_order_number,
                COALESCE(c.name, 'Customer #' || s.customer_id::text) AS customer_name,
                s.delivery_address
            FROM "{self.schema}".t0113 s
            LEFT JOIN "{self.schema}".t0012 so ON s.sales_order_id = so.id
            LEFT JOIN "{self.schema}".t0010 c ON s.customer_id = c.id
            WHERE s.delivery_run_id = %s AND s.is_active = true
            ORDER BY s.lifo_staging_sequence ASC;
            """
            staging_stops = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query_stops, (run_id,))
                stop_rows = [dict(r) for r in cur.fetchall()]

                for st in stop_rows:
                    so_id = st.get('sales_order_id')
                    items = []
                    if so_id:
                        item_query = f"""
                        SELECT 
                            sol.product_id,
                            COALESCE(p.name, 'Product #' || sol.product_id::text) AS product_name,
                            p.sku,
                            sol.qty::FLOAT AS qty,
                            u.name AS uom_name,
                            'MAIN-STAGE' AS location_code
                        FROM "{self.schema}".t0013 sol
                        JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                        LEFT JOIN "{self.schema}".t0004 u ON p.uom_id = u.id
                        WHERE sol.sales_order_id = %s;
                        """
                        cur.execute(item_query, (so_id,))
                        items = [dict(it) for it in cur.fetchall()]

                    staging_stops.append({
                        "staging_sequence": st.get('staging_sequence', 1),
                        "stop_number": st.get('stop_number', 1),
                        "sales_order_id": so_id,
                        "sales_order_number": st.get('sales_order_number') or f"SO-{so_id}",
                        "customer_name": st.get('customer_name') or "",
                        "delivery_address": st.get('delivery_address') or "",
                        "items": items,
                    })

            return {
                "run_id": run['id'],
                "run_number": run['run_number'],
                "run_date": run['run_date'],
                "zone_name": run.get('zone_name') or "General",
                "warehouse_id": run.get('warehouse_id'),
                "vehicle_code": run.get('vehicle_code'),
                "driver_name": run.get('driver_name'),
                "total_stops": len(staging_stops),
                "staging_sequence": staging_stops,
            }
        finally:
            if should_release:
                release_connection(conn)


# Default singleton instance
delivery_route_repo = DeliveryRouteRepository()
