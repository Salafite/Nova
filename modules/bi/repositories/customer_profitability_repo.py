import os
import logging
from typing import Optional, Dict, Any, List
from datetime import date
import psycopg2.extras
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


class CustomerProfitabilityRepository:
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

    def get_customer_profitability_data(
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
    ) -> List[Dict[str, Any]]:
        """
        Aggregates customer revenue, discounts, line COGS, freight costs, and gross profit $.
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
                    so.sales_rep_id,
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
                    fo.sales_rep_id,
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
                c.id AS customer_id,
                ('CUST-' || LPAD(c.id::text, 4, '0')) AS customer_code,
                c.name AS customer_name,
                COALESCE(c.group_name, 'Retail') AS customer_group,
                MAX(os.sales_rep_id) AS sales_rep_id,
                MAX(COALESCE(u.full_name, u.username)) AS sales_rep_name,
                COUNT(os.order_id)::INT AS order_count,
                COALESCE(SUM(os.gross_sales), 0)::FLOAT AS gross_sales,
                COALESCE(SUM(os.discount_amount), 0)::FLOAT AS discount_amount,
                COALESCE(SUM(os.net_revenue), 0)::FLOAT AS net_revenue,
                COALESCE(SUM(os.cogs), 0)::FLOAT AS cogs,
                COALESCE(SUM(os.freight_cost), 0)::FLOAT AS freight_cost,
                COALESCE(SUM(os.gross_profit), 0)::FLOAT AS gross_profit
            FROM order_summaries os
            JOIN "{self.schema}".t0010 c ON os.customer_id = c.id
            LEFT JOIN "{self.schema}".t0021 u ON os.sales_rep_id = u.id
            GROUP BY c.id, c.name, c.group_name
            ORDER BY gross_profit DESC;
            """

            params = so_params + prod_params
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_customer_top_products_data(
        self,
        customer_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 10,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top purchased products and SKU margins for a specific customer.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            so_clauses, so_params, prod_clauses, prod_params = self._build_filter_clauses(
                date_from=date_from,
                date_to=date_to,
                customer_id=customer_id,
            )
            so_where = " AND ".join(so_clauses)

            query = f"""
            WITH filtered_orders AS (
                SELECT so.id, so.order_date
                FROM "{self.schema}".t0012 so
                WHERE {so_where}
            )
            SELECT 
                p.id AS product_id,
                p.sku AS sku_code,
                p.name AS product_name,
                COALESCE(NULLIF(TRIM(p.category), ''), 'Unassigned') AS category_name,
                SUM(sol.qty)::FLOAT AS units_sold,
                SUM(sol.qty * sol.unit_price)::FLOAT AS gross_sales,
                SUM(COALESCE(sol.discount, 0))::FLOAT AS discount_amount,
                (SUM(sol.qty * sol.unit_price) - SUM(COALESCE(sol.discount, 0)))::FLOAT AS net_revenue,
                SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0))::FLOAT AS cogs,
                (SUM(sol.qty * sol.unit_price) - SUM(COALESCE(sol.discount, 0)) - SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0)))::FLOAT AS gross_profit
            FROM "{self.schema}".t0013 sol
            JOIN filtered_orders fo ON sol.sales_order_id = fo.id
            JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
            GROUP BY p.id, p.sku, p.name, p.category
            ORDER BY gross_profit DESC
            LIMIT %s;
            """
            params = so_params + [limit]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)


# Default singleton instance
customer_profitability_repo = CustomerProfitabilityRepository()
