import os
import logging
from typing import Optional, Dict, Any, List
from datetime import date
import psycopg2.extras
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


class DeliveryAnalyticsRepository:
    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')

    def _build_filter_clauses(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        customer_id: Optional[int] = None,
        sales_rep_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> tuple[list[str], list[Any]]:
        """
        Builds WHERE clauses and parameter list for delivery (t0077) and linked sales order (t0012).
        """
        clauses = ["d.status != 'Cancelled'", "d.is_active = true"]
        params: list[Any] = []

        if date_from:
            clauses.append("COALESCE(d.delivery_date, so.order_date) >= %s")
            params.append(date_from)
        if date_to:
            clauses.append("COALESCE(d.delivery_date, so.order_date) <= %s")
            params.append(date_to)
        if warehouse_id is not None:
            clauses.append("d.warehouse_id = %s")
            params.append(warehouse_id)
        if delivery_route:
            clauses.append("d.delivery_route = %s")
            params.append(delivery_route)
        if customer_id is not None:
            clauses.append("so.customer_id = %s")
            params.append(customer_id)
        if sales_rep_id is not None:
            clauses.append("so.sales_rep_id = %s")
            params.append(sales_rep_id)
        if status:
            clauses.append("d.status = %s")
            params.append(status)

        return clauses, params

    def get_route_fulfillment_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        customer_id: Optional[int] = None,
        sales_rep_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates delivery route performance: total deliveries, completed, on-time, delayed,
        freight cost, and line quantities ordered vs shipped.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses, params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
                customer_id=customer_id,
                sales_rep_id=sales_rep_id,
            )
            where_sql = " AND ".join(clauses)

            query = f"""
            WITH filtered_deliveries AS (
                SELECT 
                    d.id,
                    d.delivery_number,
                    d.sales_order_id,
                    d.delivery_date,
                    d.actual_delivery_date,
                    d.warehouse_id,
                    COALESCE(d.freight_cost, 0) AS freight_cost,
                    COALESCE(NULLIF(TRIM(d.delivery_route), ''), 'Unassigned') AS delivery_route,
                    d.status
                FROM "{self.schema}".t0077 d
                LEFT JOIN "{self.schema}".t0012 so ON d.sales_order_id = so.id
                WHERE {where_sql}
            ),
            line_aggregates AS (
                SELECT 
                    dl.delivery_id,
                    SUM(COALESCE(dl.qty_ordered, 0)) AS qty_ordered,
                    SUM(COALESCE(dl.qty_shipped, 0)) AS qty_shipped
                FROM "{self.schema}".t0078 dl
                WHERE dl.delivery_id IN (SELECT id FROM filtered_deliveries)
                  AND dl.is_active = true
                GROUP BY dl.delivery_id
            ),
            delivery_details AS (
                SELECT 
                    fd.id,
                    fd.delivery_route,
                    fd.warehouse_id,
                    fd.freight_cost,
                    fd.status,
                    fd.delivery_date,
                    fd.actual_delivery_date,
                    CASE 
                        WHEN fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL THEN 1 
                        ELSE 0 
                    END AS is_completed,
                    CASE 
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL) 
                             AND fd.actual_delivery_date IS NOT NULL 
                             AND fd.delivery_date IS NOT NULL 
                             AND fd.actual_delivery_date <= fd.delivery_date THEN 1
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL)
                             AND fd.actual_delivery_date IS NULL
                             AND fd.delivery_date IS NOT NULL
                             AND fd.delivery_date >= CURRENT_DATE THEN 1
                        ELSE 0 
                    END AS is_on_time,
                    CASE 
                        WHEN (fd.actual_delivery_date IS NOT NULL AND fd.delivery_date IS NOT NULL AND fd.actual_delivery_date > fd.delivery_date)
                             OR (fd.status NOT IN ('Delivered', 'Cancelled') AND fd.delivery_date IS NOT NULL AND fd.delivery_date < CURRENT_DATE) THEN 1
                        ELSE 0 
                    END AS is_delayed,
                    COALESCE(la.qty_ordered, 0) AS qty_ordered,
                    COALESCE(la.qty_shipped, 0) AS qty_shipped
                FROM filtered_deliveries fd
                LEFT JOIN line_aggregates la ON fd.id = la.delivery_id
            )
            SELECT 
                dd.delivery_route,
                MAX(dd.warehouse_id) AS warehouse_id,
                MAX(w.name) AS warehouse_name,
                COUNT(dd.id)::INT AS total_deliveries,
                SUM(dd.is_completed)::INT AS completed_deliveries,
                SUM(dd.is_on_time)::INT AS on_time_deliveries,
                SUM(dd.is_delayed)::INT AS delayed_deliveries,
                COALESCE(SUM(dd.freight_cost), 0)::FLOAT AS total_freight_cost,
                COALESCE(SUM(dd.qty_ordered), 0)::FLOAT AS total_qty_ordered,
                COALESCE(SUM(dd.qty_shipped), 0)::FLOAT AS total_qty_shipped
            FROM delivery_details dd
            LEFT JOIN "{self.schema}".t0008 w ON dd.warehouse_id = w.id
            GROUP BY dd.delivery_route
            ORDER BY total_deliveries DESC, dd.delivery_route ASC;
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_delivery_summary_kpis(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        customer_id: Optional[int] = None,
        sales_rep_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Computes global high-level fulfillment KPIs: total deliveries, completion rate,
        on-time delivery rate, total freight cost, and average freight cost.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses, params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
                customer_id=customer_id,
                sales_rep_id=sales_rep_id,
            )
            where_sql = " AND ".join(clauses)

            query = f"""
            WITH filtered_deliveries AS (
                SELECT 
                    d.id,
                    d.delivery_date,
                    d.actual_delivery_date,
                    COALESCE(d.freight_cost, 0) AS freight_cost,
                    COALESCE(NULLIF(TRIM(d.delivery_route), ''), 'Unassigned') AS delivery_route,
                    d.status
                FROM "{self.schema}".t0077 d
                LEFT JOIN "{self.schema}".t0012 so ON d.sales_order_id = so.id
                WHERE {where_sql}
            ),
            delivery_metrics AS (
                SELECT 
                    id,
                    delivery_route,
                    freight_cost,
                    CASE 
                        WHEN status = 'Delivered' OR actual_delivery_date IS NOT NULL THEN 1 
                        ELSE 0 
                    END AS is_completed,
                    CASE 
                        WHEN (status = 'Delivered' OR actual_delivery_date IS NOT NULL) 
                             AND actual_delivery_date IS NOT NULL 
                             AND delivery_date IS NOT NULL 
                             AND actual_delivery_date <= delivery_date THEN 1
                        WHEN (status = 'Delivered' OR actual_delivery_date IS NOT NULL)
                             AND actual_delivery_date IS NULL
                             AND delivery_date IS NOT NULL
                             AND delivery_date >= CURRENT_DATE THEN 1
                        ELSE 0 
                    END AS is_on_time,
                    CASE 
                        WHEN (actual_delivery_date IS NOT NULL AND delivery_date IS NOT NULL AND actual_delivery_date > delivery_date)
                             OR (status NOT IN ('Delivered', 'Cancelled') AND delivery_date IS NOT NULL AND delivery_date < CURRENT_DATE) THEN 1
                        ELSE 0 
                    END AS is_delayed
                FROM filtered_deliveries
            )
            SELECT 
                COUNT(DISTINCT delivery_route)::INT AS total_routes,
                COUNT(id)::INT AS total_deliveries,
                COALESCE(SUM(is_completed), 0)::INT AS completed_deliveries,
                COALESCE(SUM(is_on_time), 0)::INT AS on_time_deliveries,
                COALESCE(SUM(is_delayed), 0)::INT AS delayed_deliveries,
                COALESCE(SUM(freight_cost), 0)::FLOAT AS total_freight_cost
            FROM delivery_metrics;
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone() or {}
                return dict(row)
        finally:
            if should_release:
                release_connection(conn)

    def get_warehouse_delivery_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates dispatch and fulfillment efficiency broken down by origin warehouse.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses, params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                warehouse_id=warehouse_id,
            )
            where_sql = " AND ".join(clauses)

            query = f"""
            WITH filtered_deliveries AS (
                SELECT 
                    d.id,
                    d.delivery_date,
                    d.actual_delivery_date,
                    d.warehouse_id,
                    COALESCE(d.freight_cost, 0) AS freight_cost,
                    d.status
                FROM "{self.schema}".t0077 d
                LEFT JOIN "{self.schema}".t0012 so ON d.sales_order_id = so.id
                WHERE {where_sql}
            ),
            line_aggregates AS (
                SELECT 
                    dl.delivery_id,
                    SUM(COALESCE(dl.qty_shipped, 0)) AS qty_shipped
                FROM "{self.schema}".t0078 dl
                WHERE dl.delivery_id IN (SELECT id FROM filtered_deliveries)
                  AND dl.is_active = true
                GROUP BY dl.delivery_id
            ),
            delivery_details AS (
                SELECT 
                    fd.id,
                    fd.warehouse_id,
                    fd.freight_cost,
                    CASE 
                        WHEN fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL THEN 1 
                        ELSE 0 
                    END AS is_completed,
                    CASE 
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL) 
                             AND fd.actual_delivery_date IS NOT NULL 
                             AND fd.delivery_date IS NOT NULL 
                             AND fd.actual_delivery_date <= fd.delivery_date THEN 1
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL)
                             AND fd.actual_delivery_date IS NULL
                             AND fd.delivery_date IS NOT NULL
                             AND fd.delivery_date >= CURRENT_DATE THEN 1
                        ELSE 0 
                    END AS is_on_time,
                    CASE 
                        WHEN (fd.actual_delivery_date IS NOT NULL AND fd.delivery_date IS NOT NULL AND fd.actual_delivery_date > fd.delivery_date)
                             OR (fd.status NOT IN ('Delivered', 'Cancelled') AND fd.delivery_date IS NOT NULL AND fd.delivery_date < CURRENT_DATE) THEN 1
                        ELSE 0 
                    END AS is_delayed,
                    COALESCE(la.qty_shipped, 0) AS qty_shipped
                FROM filtered_deliveries fd
                LEFT JOIN line_aggregates la ON fd.id = la.delivery_id
            )
            SELECT 
                w.id AS warehouse_id,
                w.name AS warehouse_name,
                w.location,
                COUNT(dd.id)::INT AS total_deliveries,
                COALESCE(SUM(dd.is_completed), 0)::INT AS completed_deliveries,
                COALESCE(SUM(dd.is_on_time), 0)::INT AS on_time_deliveries,
                COALESCE(SUM(dd.is_delayed), 0)::INT AS delayed_deliveries,
                COALESCE(SUM(dd.freight_cost), 0)::FLOAT AS total_freight_cost,
                COALESCE(SUM(dd.qty_shipped), 0)::FLOAT AS total_qty_shipped
            FROM "{self.schema}".t0008 w
            LEFT JOIN delivery_details dd ON w.id = dd.warehouse_id
            WHERE w.is_active = true
            GROUP BY w.id, w.name, w.location
            ORDER BY total_deliveries DESC, w.name ASC;
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_customer_destination_delivery_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: int = 50,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates delivery performance and freight costs by destination customer.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses, params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
                customer_id=customer_id,
            )
            where_sql = " AND ".join(clauses)

            query = f"""
            WITH filtered_deliveries AS (
                SELECT 
                    d.id,
                    d.delivery_date,
                    d.actual_delivery_date,
                    COALESCE(d.freight_cost, 0) AS freight_cost,
                    d.delivery_route,
                    d.status,
                    so.customer_id
                FROM "{self.schema}".t0077 d
                JOIN "{self.schema}".t0012 so ON d.sales_order_id = so.id
                WHERE {where_sql}
            ),
            line_aggregates AS (
                SELECT 
                    dl.delivery_id,
                    SUM(COALESCE(dl.qty_shipped, 0)) AS qty_shipped
                FROM "{self.schema}".t0078 dl
                WHERE dl.delivery_id IN (SELECT id FROM filtered_deliveries)
                  AND dl.is_active = true
                GROUP BY dl.delivery_id
            ),
            delivery_details AS (
                SELECT 
                    fd.id,
                    fd.customer_id,
                    fd.delivery_route,
                    fd.freight_cost,
                    CASE 
                        WHEN fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL THEN 1 
                        ELSE 0 
                    END AS is_completed,
                    CASE 
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL) 
                             AND fd.actual_delivery_date IS NOT NULL 
                             AND fd.delivery_date IS NOT NULL 
                             AND fd.actual_delivery_date <= fd.delivery_date THEN 1
                        WHEN (fd.status = 'Delivered' OR fd.actual_delivery_date IS NOT NULL)
                             AND fd.actual_delivery_date IS NULL
                             AND fd.delivery_date IS NOT NULL
                             AND fd.delivery_date >= CURRENT_DATE THEN 1
                        ELSE 0 
                    END AS is_on_time,
                    COALESCE(la.qty_shipped, 0) AS qty_shipped
                FROM filtered_deliveries fd
                LEFT JOIN line_aggregates la ON fd.id = la.delivery_id
            )
            SELECT 
                c.id AS customer_id,
                ('CUST-' || LPAD(c.id::text, 4, '0')) AS customer_code,
                c.name AS customer_name,
                MAX(dd.delivery_route) AS delivery_route,
                COUNT(dd.id)::INT AS total_deliveries,
                COALESCE(SUM(dd.is_completed), 0)::INT AS completed_deliveries,
                COALESCE(SUM(dd.is_on_time), 0)::INT AS on_time_deliveries,
                COALESCE(SUM(dd.freight_cost), 0)::FLOAT AS total_freight_cost,
                COALESCE(SUM(dd.qty_shipped), 0)::FLOAT AS total_qty_shipped
            FROM delivery_details dd
            JOIN "{self.schema}".t0010 c ON dd.customer_id = c.id
            GROUP BY c.id, c.name
            ORDER BY total_deliveries DESC, total_freight_cost DESC
            LIMIT %s;
            """

            params.append(limit)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_delivery_variance_details(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        limit: int = 100,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves line items where qty shipped differs from qty ordered.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses, params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
            )
            where_sql = " AND ".join(clauses)

            query = f"""
            SELECT 
                d.id AS delivery_id,
                COALESCE(d.delivery_number, 'DEL-' || d.id::text) AS delivery_number,
                COALESCE(d.delivery_route, 'Unassigned') AS delivery_route,
                dl.product_id,
                COALESCE(dl.product_name, p.name, 'Product #' || dl.product_id::text) AS product_name,
                COALESCE(dl.qty_ordered, 0)::FLOAT AS qty_ordered,
                COALESCE(dl.qty_shipped, 0)::FLOAT AS qty_shipped,
                (COALESCE(dl.qty_shipped, 0) - COALESCE(dl.qty_ordered, 0))::FLOAT AS variance_qty,
                d.status
            FROM "{self.schema}".t0078 dl
            JOIN "{self.schema}".t0077 d ON dl.delivery_id = d.id
            LEFT JOIN "{self.schema}".t0012 so ON d.sales_order_id = so.id
            LEFT JOIN "{self.schema}".t0003 p ON dl.product_id = p.id
            WHERE {where_sql}
              AND dl.is_active = true
              AND dl.qty_ordered != dl.qty_shipped
            ORDER BY ABS(COALESCE(dl.qty_shipped, 0) - COALESCE(dl.qty_ordered, 0)) DESC
            LIMIT %s;
            """

            params.append(limit)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)


# Default singleton instance
delivery_analytics_repo = DeliveryAnalyticsRepository()
