import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import psycopg2.extras
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


def _schema() -> str:
    """Return the active database schema name."""
    return os.getenv('DB_SCHEMA', 'Nova')


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safely convert numeric or Decimal value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError, ArithmeticError):
        return default


def _format_time(val: Any) -> Optional[str]:
    """Format time object or string to HH:MM string."""
    if val is None:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%H:%M')
    val_str = str(val).strip()
    return val_str[:5] if val_str else None


class PortalRepository:
    """Data access repository for B2B Customer Portal operations.
    
    Handles customer profiles, contracted price resolution (T0084/T0083),
    inventory catalog queries with stock levels (T0003/T0009), category counts,
    and customer account summaries.
    """

    def __init__(self):
        self.schema = _schema()

    def get_customer_by_id(self, customer_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve customer record with portal settings from T0010."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f"""
                SELECT 
                    id, name, group_name, phone, email,
                    credit_limit, balance,
                    min_order_amount, order_cutoff_time, allow_reorders,
                    default_price_list_id, default_tax_rate_id, payment_term_id,
                    is_active
                FROM "{self.schema}".t0010
                WHERE id = %s
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (customer_id,))
                row = cur.fetchone()
                if not row:
                    return None
                data = dict(row)
                data['credit_limit'] = _to_float(data.get('credit_limit'))
                data['balance'] = _to_float(data.get('balance'))
                data['min_order_amount'] = _to_float(data.get('min_order_amount'))
                data['order_cutoff_time'] = _format_time(data.get('order_cutoff_time'))
                data['available_credit'] = max(0.0, data['credit_limit'] - data['balance'])
                return data
        finally:
            if should_release:
                release_connection(conn)

    def get_price_list_by_id(self, price_list_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve price list header by ID from T0083."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f"""
                SELECT id, name, code, description, currency, is_active, is_default
                FROM "{self.schema}".t0083
                WHERE id = %s
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (price_list_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_default_price_list(self, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve the system default active price list from T0083."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f"""
                SELECT id, name, code, description, currency, is_active, is_default
                FROM "{self.schema}".t0083
                WHERE is_default = TRUE AND is_active = TRUE
                ORDER BY id ASC
                LIMIT 1
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def resolve_customer_price_list_id(self, customer_id: int, conn=None) -> Optional[int]:
        """Resolve effective price list ID for a customer, falling back to system default."""
        customer = self.get_customer_by_id(customer_id, conn=conn)
        if customer and customer.get('default_price_list_id'):
            return customer['default_price_list_id']
        default_pl = self.get_default_price_list(conn=conn)
        return default_pl['id'] if default_pl else None

    def get_catalog_categories(self, conn=None) -> List[Dict[str, Any]]:
        """List distinct active product categories with item counts."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f"""
                SELECT 
                    category AS category_name,
                    COUNT(*) AS item_count
                FROM "{self.schema}".t0003
                WHERE is_active = TRUE 
                  AND category IS NOT NULL 
                  AND category != ''
                GROUP BY category
                ORDER BY category ASC
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                result = []
                for idx, r in enumerate(rows, start=1):
                    result.append({
                        'id': idx,
                        'category_name': r['category_name'],
                        'item_count': int(r['item_count'])
                    })
                return result
        finally:
            if should_release:
                release_connection(conn)

    def get_catalog(
        self,
        customer_id: int,
        category: Optional[str] = None,
        search: Optional[str] = None,
        in_stock_only: bool = False,
        page: int = 1,
        limit: int = 50,
        conn=None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query product catalog with customer's contracted unit prices and stock levels.
        
        Returns a tuple of (items_list, total_count).
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            price_list_id = self.resolve_customer_price_list_id(customer_id, conn=conn)
            page = max(1, page)
            limit = max(1, min(limit, 200))
            offset = (page - 1) * limit

            where_clauses = ["p.is_active = TRUE"]
            params: List[Any] = []

            if category:
                where_clauses.append("p.category = %s")
                params.append(category)

            if search:
                where_clauses.append("(p.name ILIKE %s OR p.sku ILIKE %s OR p.description ILIKE %s)")
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])

            where_sql = " AND ".join(where_clauses)

            having_clause = "HAVING COALESCE(SUM(stk.qty), 0) > 0" if in_stock_only else ""

            # Count total matching products
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM (
                    SELECT p.id
                    FROM "{self.schema}".t0003 p
                    LEFT JOIN "{self.schema}".t0009 stk ON stk.product_id = p.id
                    WHERE {where_sql}
                    GROUP BY p.id
                    {having_clause}
                ) sub
            """
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(count_sql, params)
                count_row = cur.fetchone()
                total = count_row['total'] if count_row else 0

                if total == 0:
                    return [], 0

                # Main query joining contracted pricing (T0084), stock (T0009), UOM (T0007, T0001)
                data_params: List[Any] = [price_list_id] if price_list_id else [None]
                data_params.extend(params)
                data_params.extend([limit, offset])

                query_sql = f"""
                    SELECT 
                        p.id,
                        p.sku AS product_code,
                        p.name AS product_name,
                        p.category AS category_name,
                        p.price AS base_price,
                        p.image_url,
                        p.description,
                        p.is_active,
                        COALESCE(u.id, 0) AS uom_id,
                        COALESCE(u.uom_name, 'Unit') AS uom_name,
                        COALESCE(SUM(stk.qty), 0) AS stock_qty,
                        pli.unit_price AS contracted_unit_price
                    FROM "{self.schema}".t0003 p
                    LEFT JOIN "{self.schema}".t0084 pli 
                        ON pli.product_id = p.id 
                        AND pli.price_list_id = %s
                    LEFT JOIN "{self.schema}".t0009 stk 
                        ON stk.product_id = p.id
                    LEFT JOIN "{self.schema}".t0007 pu 
                        ON pu.product_id = p.id
                    LEFT JOIN "{self.schema}".t0001 u 
                        ON u.id = COALESCE(pu.sales_uom_id, pu.base_uom_id)
                    WHERE {where_sql}
                    GROUP BY p.id, p.sku, p.name, p.category, p.price, p.image_url, p.description, p.is_active, u.id, u.uom_name, pli.unit_price
                    {having_clause}
                    ORDER BY p.name ASC
                    LIMIT %s OFFSET %s
                """
                cur.execute(query_sql, data_params)
                rows = cur.fetchall()

                items = []
                for r in rows:
                    base_price = _to_float(r['base_price'])
                    contracted_unit_price = r['contracted_unit_price']
                    
                    if contracted_unit_price is not None:
                        contracted_price = _to_float(contracted_unit_price)
                        is_contracted = True
                    else:
                        contracted_price = base_price
                        is_contracted = False

                    discount_percent = 0.0
                    if is_contracted and base_price > 0 and contracted_price < base_price:
                        discount_percent = round(((base_price - contracted_price) / base_price) * 100.0, 2)

                    stock_qty = _to_float(r['stock_qty'])
                    is_in_stock = stock_qty > 0

                    items.append({
                        'id': r['id'],
                        'product_code': r['product_code'],
                        'product_name': r['product_name'],
                        'category_id': None,
                        'category_name': r['category_name'],
                        'uom_id': r['uom_id'] if r['uom_id'] > 0 else None,
                        'uom_name': r['uom_name'],
                        'base_price': base_price,
                        'contracted_price': contracted_price,
                        'is_contracted': is_contracted,
                        'discount_percent': discount_percent,
                        'stock_qty': stock_qty,
                        'is_in_stock': is_in_stock,
                        'image_url': r['image_url'],
                        'description': r['description'],
                        'is_active': bool(r['is_active'])
                    })

                return items, total
        finally:
            if should_release:
                release_connection(conn)

    def get_product_by_id(self, product_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve single product record from T0003."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f"""
                SELECT 
                    p.id, p.name, p.sku, p.price, p.cost_price, 
                    p.category, p.brand, p.tax_rate, p.image_url, 
                    p.description, p.is_active
                FROM "{self.schema}".t0003 p
                WHERE p.id = %s
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (product_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def resolve_product_price(
        self,
        product_id: int,
        customer_id: Optional[int] = None,
        price_list_id: Optional[int] = None,
        conn=None
    ) -> Optional[Dict[str, Any]]:
        """Resolve unit price for a product, checking price list (T0084) then product base price (T0003)."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            if price_list_id is None and customer_id is not None:
                price_list_id = self.resolve_customer_price_list_id(customer_id, conn=conn)

            product = self.get_product_by_id(product_id, conn=conn)
            if not product:
                return None

            base_price = _to_float(product.get('price', 0))

            if price_list_id:
                sql_pl = f"""
                    SELECT unit_price, min_qty
                    FROM "{self.schema}".t0084
                    WHERE price_list_id = %s AND product_id = %s
                """
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql_pl, (price_list_id, product_id))
                    pl_row = cur.fetchone()
                    if pl_row and pl_row.get('unit_price') is not None:
                        contracted_price = _to_float(pl_row['unit_price'])
                        discount_percent = 0.0
                        if base_price > 0 and contracted_price < base_price:
                            discount_percent = round(((base_price - contracted_price) / base_price) * 100.0, 2)
                        return {
                            'product_id': product_id,
                            'product_name': product['name'],
                            'product_code': product['sku'],
                            'base_price': base_price,
                            'unit_price': contracted_price,
                            'contracted_price': contracted_price,
                            'is_contracted': True,
                            'discount_percent': discount_percent,
                            'min_qty': _to_float(pl_row.get('min_qty', 1), 1.0)
                        }

            # Fallback to product base price
            return {
                'product_id': product_id,
                'product_name': product['name'],
                'product_code': product['sku'],
                'base_price': base_price,
                'unit_price': base_price,
                'contracted_price': base_price,
                'is_contracted': False,
                'discount_percent': 0.0,
                'min_qty': 1.0
            }
        finally:
            if should_release:
                release_connection(conn)

    def get_contracted_prices_for_products(
        self,
        product_ids: List[int],
        customer_id: Optional[int] = None,
        price_list_id: Optional[int] = None,
        conn=None
    ) -> Dict[int, Dict[str, Any]]:
        """Batch price resolution for multiple products."""
        if not product_ids:
            return {}
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            if price_list_id is None and customer_id is not None:
                price_list_id = self.resolve_customer_price_list_id(customer_id, conn=conn)

            results: Dict[int, Dict[str, Any]] = {}
            for pid in set(product_ids):
                resolved = self.resolve_product_price(pid, price_list_id=price_list_id, conn=conn)
                if resolved:
                    results[pid] = resolved
            return results
        finally:
            if should_release:
                release_connection(conn)

    def get_account_summary(self, customer_id: int, conn=None) -> Dict[str, Any]:
        """Aggregate customer dashboard metrics: open invoices, unpaid balance, recent orders, credit limits."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            customer = self.get_customer_by_id(customer_id, conn=conn)
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found")

            # Price list name
            pl_name = None
            if customer.get('default_price_list_id'):
                pl = self.get_price_list_by_id(customer['default_price_list_id'], conn=conn)
                if pl:
                    pl_name = pl.get('name')

            # Unpaid invoices count and sum
            sql_invoices = f"""
                SELECT 
                    COUNT(*) AS open_count,
                    COALESCE(SUM(total_amount - COALESCE(paid_amount, 0)), 0) AS total_unpaid
                FROM "{self.schema}".t0090
                WHERE partner_id = %s 
                  AND status IN ('Unpaid', 'Partially Paid')
            """
            
            # Recent orders count
            sql_orders = f"""
                SELECT COUNT(*) AS order_count
                FROM "{self.schema}".t0012
                WHERE customer_id = %s
            """

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql_invoices, (customer_id,))
                inv_row = cur.fetchone() or {'open_count': 0, 'total_unpaid': 0}

                cur.execute(sql_orders, (customer_id,))
                ord_row = cur.fetchone() or {'order_count': 0}

            return {
                'customer_id': customer['id'],
                'customer_name': customer['name'],
                'group_name': customer.get('group_name') or 'Wholesale',
                'email': customer.get('email'),
                'phone': customer.get('phone'),
                'credit_limit': customer['credit_limit'],
                'current_balance': customer['balance'],
                'available_credit': customer['available_credit'],
                'min_order_amount': customer['min_order_amount'],
                'order_cutoff_time': customer['order_cutoff_time'],
                'allow_reorders': customer['allow_reorders'],
                'open_invoices_count': int(inv_row['open_count']),
                'total_unpaid_amount': _to_float(inv_row['total_unpaid']),
                'recent_orders_count': int(ord_row['order_count']),
                'default_price_list_id': customer.get('default_price_list_id'),
                'default_price_list_name': pl_name,
            }
        finally:
            if should_release:
                release_connection(conn)
