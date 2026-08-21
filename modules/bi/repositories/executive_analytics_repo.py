import os
import logging
from typing import Optional, Dict, Any, List
from datetime import date
import psycopg2.extras
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


class ExecutiveAnalyticsRepository:
    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')

    def _build_filter_clauses(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_name: Optional[str] = None,
        product_id: Optional[int] = None,
        brand: Optional[str] = None,
        sales_rep_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
    ) -> tuple[list[str], list[Any], list[str], list[Any]]:
        """
        Builds WHERE clauses and parameters for orders (t0012) and lines/products (t0013/t0003).
        """
        so_clauses = ["so.status != 'Cancelled'"]
        so_params = []
        product_clauses = []
        product_params = []

        if date_from:
            so_clauses.append("so.order_date >= %s")
            so_params.append(date_from)
        if date_to:
            so_clauses.append("so.order_date <= %s")
            so_params.append(date_to)
        if sales_rep_id is not None:
            so_clauses.append("so.sales_rep_id = %s")
            so_params.append(sales_rep_id)
        if customer_id is not None:
            so_clauses.append("so.customer_id = %s")
            so_params.append(customer_id)
        if warehouse_id is not None:
            so_clauses.append("so.warehouse_id = %s")
            so_params.append(warehouse_id)
        if delivery_route:
            so_clauses.append(
                f'EXISTS (SELECT 1 FROM "{self.schema}".t0077 d WHERE d.sales_order_id = so.id AND d.delivery_route = %s)'
            )
            so_params.append(delivery_route)

        if category_name:
            product_clauses.append("p.category = %s")
            product_params.append(category_name)
        if product_id is not None:
            product_clauses.append("sol.product_id = %s")
            product_params.append(product_id)
        if brand:
            product_clauses.append("p.brand ILIKE %s")
            product_params.append(brand)

        return so_clauses, so_params, product_clauses, product_params

    def get_margin_summary_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_name: Optional[str] = None,
        product_id: Optional[int] = None,
        brand: Optional[str] = None,
        sales_rep_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Calculates aggregate gross margin KPIs factoring revenue, discounts, line COGS, and order freight.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            so_clauses, so_params, prod_clauses, prod_params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                category_name=category_name,
                product_id=product_id,
                brand=brand,
                sales_rep_id=sales_rep_id,
                customer_id=customer_id,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
            )

            so_where = " AND ".join(so_clauses)
            prod_where = (" AND " + " AND ".join(prod_clauses)) if prod_clauses else ""

            query = f"""
            WITH filtered_orders AS (
                SELECT 
                    so.id,
                    so.customer_id,
                    so.order_date,
                    COALESCE(so.freight_amount, 0) AS freight_amount,
                    COALESCE(so.discount_amount, 0) AS header_discount
                FROM "{self.schema}".t0012 so
                WHERE {so_where}
            ),
            line_aggregates AS (
                SELECT 
                    sol.sales_order_id,
                    SUM(sol.qty * sol.unit_price) AS line_gross_sales,
                    SUM(COALESCE(sol.discount, 0)) AS line_discount,
                    SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0)) AS line_cogs
                FROM "{self.schema}".t0013 sol
                JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                WHERE sol.sales_order_id IN (SELECT id FROM filtered_orders)
                {prod_where}
                GROUP BY sol.sales_order_id
            ),
            order_summaries AS (
                SELECT 
                    fo.id AS order_id,
                    fo.customer_id,
                    COALESCE(la.line_gross_sales, 0) AS gross_sales,
                    COALESCE(la.line_discount, 0) + fo.header_discount AS discount_amount,
                    COALESCE(la.line_gross_sales, 0) - (COALESCE(la.line_discount, 0) + fo.header_discount) AS net_revenue,
                    COALESCE(la.line_cogs, 0) AS cogs,
                    fo.freight_amount AS freight_cost,
                    (COALESCE(la.line_gross_sales, 0) - (COALESCE(la.line_discount, 0) + fo.header_discount) - COALESCE(la.line_cogs, 0) - fo.freight_amount) AS gross_profit
                FROM filtered_orders fo
                LEFT JOIN line_aggregates la ON fo.id = la.sales_order_id
                WHERE la.sales_order_id IS NOT NULL
            )
            SELECT 
                COUNT(order_id)::INT AS total_orders,
                COUNT(DISTINCT customer_id)::INT AS total_customers,
                COALESCE(SUM(gross_sales), 0)::FLOAT AS gross_sales,
                COALESCE(SUM(discount_amount), 0)::FLOAT AS discount_amount,
                COALESCE(SUM(net_revenue), 0)::FLOAT AS net_revenue,
                COALESCE(SUM(cogs), 0)::FLOAT AS cogs,
                COALESCE(SUM(freight_cost), 0)::FLOAT AS freight_cost,
                COALESCE(SUM(gross_profit), 0)::FLOAT AS gross_profit,
                COUNT(CASE WHEN net_revenue > 0 AND (gross_profit / net_revenue * 100.0) < 15.0 THEN 1 
                           WHEN net_revenue <= 0 AND gross_profit < 0 THEN 1 END)::INT AS low_margin_order_count
            FROM order_summaries;
            """

            params = so_params + prod_params
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone() or {}
                return dict(row)
        finally:
            if should_release:
                release_connection(conn)

    def get_category_margins_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_name: Optional[str] = None,
        sales_rep_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates margin and profitability breakdown grouped by product category.
        Allocates order-level discounts and freight proportionally by category revenue.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            so_clauses, so_params, prod_clauses, prod_params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                category_name=category_name,
                sales_rep_id=sales_rep_id,
                customer_id=customer_id,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
            )

            so_where = " AND ".join(so_clauses)
            prod_where = (" AND " + " AND ".join(prod_clauses)) if prod_clauses else ""

            query = f"""
            WITH filtered_orders AS (
                SELECT 
                    so.id,
                    so.customer_id,
                    so.order_date,
                    COALESCE(so.freight_amount, 0) AS freight_amount,
                    COALESCE(so.discount_amount, 0) AS header_discount
                FROM "{self.schema}".t0012 so
                WHERE {so_where}
            ),
            order_totals AS (
                SELECT 
                    sol.sales_order_id,
                    SUM(sol.qty * sol.unit_price) AS order_gross_sales
                FROM "{self.schema}".t0013 sol
                WHERE sol.sales_order_id IN (SELECT id FROM filtered_orders)
                GROUP BY sol.sales_order_id
            ),
            category_aggregates AS (
                SELECT 
                    COALESCE(NULLIF(TRIM(p.category), ''), 'Unassigned') AS category_name,
                    SUM(sol.qty)::FLOAT AS units_sold,
                    COUNT(DISTINCT fo.id)::INT AS order_count,
                    SUM(sol.qty * sol.unit_price)::FLOAT AS gross_sales,
                    SUM(COALESCE(sol.discount, 0))::FLOAT AS line_discount,
                    SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0))::FLOAT AS cogs,
                    SUM(
                        CASE 
                            WHEN ot.order_gross_sales > 0 
                            THEN (sol.qty * sol.unit_price / ot.order_gross_sales) * fo.header_discount 
                            ELSE 0 
                        END
                    )::FLOAT AS allocated_header_discount,
                    SUM(
                        CASE 
                            WHEN ot.order_gross_sales > 0 
                            THEN (sol.qty * sol.unit_price / ot.order_gross_sales) * fo.freight_amount 
                            ELSE 0 
                        END
                    )::FLOAT AS allocated_freight
                FROM "{self.schema}".t0013 sol
                JOIN filtered_orders fo ON sol.sales_order_id = fo.id
                JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                JOIN order_totals ot ON sol.sales_order_id = ot.sales_order_id
                WHERE 1=1 {prod_where}
                GROUP BY COALESCE(NULLIF(TRIM(p.category), ''), 'Unassigned')
            )
            SELECT 
                category_name,
                units_sold,
                order_count,
                gross_sales,
                (line_discount + allocated_header_discount) AS discount_amount,
                (gross_sales - line_discount - allocated_header_discount) AS net_revenue,
                cogs,
                allocated_freight AS freight_cost,
                (gross_sales - line_discount - allocated_header_discount - cogs - allocated_freight) AS gross_profit
            FROM category_aggregates
            ORDER BY gross_profit DESC;
            """

            params = so_params + prod_params
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_sku_margins_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_name: Optional[str] = None,
        product_id: Optional[int] = None,
        brand: Optional[str] = None,
        sales_rep_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        delivery_route: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Aggregates product SKU line margins, calculating unit cost, ASP, revenue, COGS, and freight.
        Returns (list_of_skus, total_count).
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            so_clauses, so_params, prod_clauses, prod_params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                category_name=category_name,
                product_id=product_id,
                brand=brand,
                sales_rep_id=sales_rep_id,
                customer_id=customer_id,
                warehouse_id=warehouse_id,
                delivery_route=delivery_route,
            )

            so_where = " AND ".join(so_clauses)
            prod_where = (" AND " + " AND ".join(prod_clauses)) if prod_clauses else ""

            query = f"""
            WITH filtered_orders AS (
                SELECT 
                    so.id,
                    so.customer_id,
                    so.order_date,
                    COALESCE(so.freight_amount, 0) AS freight_amount,
                    COALESCE(so.discount_amount, 0) AS header_discount
                FROM "{self.schema}".t0012 so
                WHERE {so_where}
            ),
            order_totals AS (
                SELECT 
                    sol.sales_order_id,
                    SUM(sol.qty * sol.unit_price) AS order_gross_sales
                FROM "{self.schema}".t0013 sol
                WHERE sol.sales_order_id IN (SELECT id FROM filtered_orders)
                GROUP BY sol.sales_order_id
            ),
            sku_aggregates AS (
                SELECT 
                    p.id AS product_id,
                    p.sku AS sku_code,
                    p.name AS product_name,
                    COALESCE(NULLIF(TRIM(p.category), ''), 'Unassigned') AS category_name,
                    p.brand AS brand_name,
                    SUM(sol.qty)::FLOAT AS units_sold,
                    SUM(sol.qty * sol.unit_price)::FLOAT AS gross_sales,
                    SUM(COALESCE(sol.discount, 0))::FLOAT AS line_discount,
                    SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0))::FLOAT AS cogs,
                    SUM(
                        CASE 
                            WHEN ot.order_gross_sales > 0 
                            THEN (sol.qty * sol.unit_price / ot.order_gross_sales) * fo.header_discount 
                            ELSE 0 
                        END
                    )::FLOAT AS allocated_header_discount,
                    SUM(
                        CASE 
                            WHEN ot.order_gross_sales > 0 
                            THEN (sol.qty * sol.unit_price / ot.order_gross_sales) * fo.freight_amount 
                            ELSE 0 
                        END
                    )::FLOAT AS allocated_freight
                FROM "{self.schema}".t0013 sol
                JOIN filtered_orders fo ON sol.sales_order_id = fo.id
                JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                JOIN order_totals ot ON sol.sales_order_id = ot.sales_order_id
                WHERE 1=1 {prod_where}
                GROUP BY p.id, p.sku, p.name, p.category, p.brand
            )
            SELECT 
                product_id,
                sku_code,
                product_name,
                category_name,
                brand_name,
                units_sold,
                gross_sales,
                (line_discount + allocated_header_discount) AS discount_amount,
                (gross_sales - line_discount - allocated_header_discount) AS net_revenue,
                cogs,
                allocated_freight AS freight_cost,
                (gross_sales - line_discount - allocated_header_discount - cogs - allocated_freight) AS gross_profit,
                COUNT(*) OVER()::INT AS full_count
            FROM sku_aggregates
            ORDER BY gross_profit DESC
            LIMIT %s OFFSET %s;
            """

            params = so_params + prod_params + [limit, offset]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]
                total_count = rows[0]['full_count'] if rows else 0
                return rows, total_count
        finally:
            if should_release:
                release_connection(conn)

    def get_period_margin_trends_data(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        period_type: str = 'Monthly',
        category_name: Optional[str] = None,
        product_id: Optional[int] = None,
        brand: Optional[str] = None,
        sales_rep_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates margin metrics grouped by chronological time slices (day, week, month, quarter).
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            trunc_interval = 'month'
            period_type_lower = (period_type or 'monthly').lower()
            if period_type_lower == 'daily':
                trunc_interval = 'day'
            elif period_type_lower == 'weekly':
                trunc_interval = 'week'
            elif period_type_lower == 'quarterly':
                trunc_interval = 'quarter'

            so_clauses, so_params, prod_clauses, prod_params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                category_name=category_name,
                product_id=product_id,
                brand=brand,
                sales_rep_id=sales_rep_id,
                customer_id=customer_id,
                warehouse_id=warehouse_id,
            )

            so_where = " AND ".join(so_clauses)
            prod_where = (" AND " + " AND ".join(prod_clauses)) if prod_clauses else ""

            query = f"""
            WITH filtered_orders AS (
                SELECT 
                    so.id,
                    so.customer_id,
                    so.order_date,
                    DATE_TRUNC('{trunc_interval}', so.order_date::TIMESTAMP)::DATE AS bucket_start,
                    COALESCE(so.freight_amount, 0) AS freight_amount,
                    COALESCE(so.discount_amount, 0) AS header_discount
                FROM "{self.schema}".t0012 so
                WHERE {so_where}
            ),
            line_aggregates AS (
                SELECT 
                    sol.sales_order_id,
                    SUM(sol.qty * sol.unit_price) AS line_gross_sales,
                    SUM(COALESCE(sol.discount, 0)) AS line_discount,
                    SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0)) AS line_cogs
                FROM "{self.schema}".t0013 sol
                JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                WHERE sol.sales_order_id IN (SELECT id FROM filtered_orders)
                {prod_where}
                GROUP BY sol.sales_order_id
            ),
            order_trends AS (
                SELECT 
                    fo.bucket_start,
                    fo.id AS order_id,
                    COALESCE(la.line_gross_sales, 0) AS gross_sales,
                    COALESCE(la.line_discount, 0) + fo.header_discount AS discount_amount,
                    COALESCE(la.line_gross_sales, 0) - (COALESCE(la.line_discount, 0) + fo.header_discount) AS net_revenue,
                    COALESCE(la.line_cogs, 0) AS cogs,
                    fo.freight_amount AS freight_cost,
                    (COALESCE(la.line_gross_sales, 0) - (COALESCE(la.line_discount, 0) + fo.header_discount) - COALESCE(la.line_cogs, 0) - fo.freight_amount) AS gross_profit
                FROM filtered_orders fo
                LEFT JOIN line_aggregates la ON fo.id = la.sales_order_id
                WHERE la.sales_order_id IS NOT NULL
            )
            SELECT 
                bucket_start,
                COUNT(order_id)::INT AS order_count,
                SUM(gross_sales)::FLOAT AS gross_sales,
                SUM(discount_amount)::FLOAT AS discount_amount,
                SUM(net_revenue)::FLOAT AS net_revenue,
                SUM(cogs)::FLOAT AS cogs,
                SUM(freight_cost)::FLOAT AS freight_cost,
                SUM(gross_profit)::FLOAT AS gross_profit
            FROM order_trends
            GROUP BY bucket_start
            ORDER BY bucket_start ASC;
            """

            params = so_params + prod_params
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)


# Default singleton instance
executive_analytics_repo = ExecutiveAnalyticsRepository()
