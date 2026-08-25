import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safely convert numeric/Decimal/string values to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class PortalRepository:
    """Repository handling database operations for the B2B Customer Portal."""

    def __init__(self, schema: Optional[str] = None):
        self.schema = schema or os.getenv("DB_SCHEMA", "Nova")

    def _get_table(self, table_name: str) -> str:
        return f'"{self.schema}".{table_name.lower()}'

    def get_customer(self, customer_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Fetch customer profile from T0010 respecting tenant isolation."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT id, name, group_name, phone, email, credit_limit, balance,
                       is_active, default_price_list_id, default_tax_rate_id, payment_term_id,
                       min_order_amount, order_cutoff_time, allow_reorders, business_id
                FROM {self._get_table("t0010")}
                WHERE id = %s
            """
            params: List[Any] = [customer_id]
            if tenant_id is not None:
                query += " AND business_id = %s"
                params.append(tenant_id)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_price_list_items(self, price_list_id: int, conn=None) -> Dict[int, Dict[str, Any]]:
        """Fetch active items from T0084 for a price list mapped by product_id."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT id, price_list_id, product_id, unit_price, min_qty, uom_id, is_active
                FROM {self._get_table("t0084")}
                WHERE price_list_id = %s AND is_active = true
            """
            params: List[Any] = [price_list_id]
            if tenant_id is not None:
                query += " AND (business_id = %s OR business_id IS NULL)"
                params.append(tenant_id)

            item_map: Dict[int, Dict[str, Any]] = {}
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for r in cur.fetchall():
                    pid = r["product_id"]
                    if pid is not None:
                        item_map[pid] = dict(r)
            return item_map
        finally:
            if should_release:
                release_connection(conn)

    def get_price_list_name(self, price_list_id: int, conn=None) -> Optional[str]:
        """Lookup price list name from T0083."""
        if not price_list_id:
            return None
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"SELECT name FROM {self._get_table('t0083')} WHERE id = %s"
            with conn.cursor() as cur:
                cur.execute(query, (price_list_id,))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_product(self, product_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Fetch product details from T0003."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT p.id, p.name, p.sku, p.barcode, p.description, p.price, p.cost_price,
                       p.category, p.brand, p.tax_rate, p.image_url, p.is_active, p.is_saleable,
                       p.business_id, pu.base_uom_id, u.uom_name, u.uom_code
                FROM {self._get_table("t0003")} p
                LEFT JOIN {self._get_table("t0007")} pu ON pu.product_id = p.id
                LEFT JOIN {self._get_table("t0001")} u ON u.id = pu.base_uom_id
                WHERE p.id = %s
            """
            params: List[Any] = [product_id]
            if tenant_id is not None:
                query += " AND p.business_id = %s"
                params.append(tenant_id)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def resolve_contracted_price(
        self,
        customer_id: int,
        product_id: int,
        qty: float = 1.0,
        conn=None,
    ) -> Dict[str, Any]:
        """Resolve contracted price for a customer and product, falling back to base price."""
        customer = self.get_customer(customer_id, conn=conn)
        product = self.get_product(product_id, conn=conn)
        if not product:
            return {
                "product_id": product_id,
                "base_price": 0.0,
                "contracted_price": 0.0,
                "unit_price": 0.0,
                "is_contracted": False,
                "discount_percent": 0.0,
            }

        base_price = _to_float(product.get("price", 0.0))
        contracted_price = base_price
        is_contracted = False

        if customer and customer.get("default_price_list_id"):
            price_list_id = customer["default_price_list_id"]
            price_items = self.get_price_list_items(price_list_id, conn=conn)
            if product_id in price_items:
                item = price_items[product_id]
                contracted_unit_price = _to_float(item.get("unit_price"))
                if contracted_unit_price > 0:
                    contracted_price = contracted_unit_price
                    is_contracted = True

        discount_percent = 0.0
        if is_contracted and base_price > 0 and base_price > contracted_price:
            discount_percent = round(((base_price - contracted_price) / base_price) * 100.0, 2)

        return {
            "product_id": product_id,
            "product_name": product.get("name"),
            "product_code": product.get("sku"),
            "base_price": base_price,
            "contracted_price": contracted_price,
            "unit_price": contracted_price,
            "is_contracted": is_contracted,
            "discount_percent": discount_percent,
        }

    def get_stock_levels(self, conn=None) -> Dict[int, float]:
        """Fetch aggregated stock quantities for products from T0009."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT product_id, COALESCE(SUM(qty - reserved_qty), 0) as available_qty
                FROM {self._get_table("t0009")}
            """
            params: List[Any] = []
            if tenant_id is not None:
                query += " WHERE business_id = %s"
                params.append(tenant_id)
            query += " GROUP BY product_id"

            stock_map: Dict[int, float] = {}
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for r in cur.fetchall():
                    stock_map[r["product_id"]] = _to_float(r.get("available_qty", 0.0))
            return stock_map
        finally:
            if should_release:
                release_connection(conn)

    def get_categories(self, conn=None) -> List[Dict[str, Any]]:
        """Get distinct product categories with item counts for active saleable products."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT category, COUNT(*) as item_count
                FROM {self._get_table("t0003")}
                WHERE category IS NOT NULL AND category != '' AND is_active = true AND is_saleable = true
            """
            params: List[Any] = []
            if tenant_id is not None:
                query += " AND business_id = %s"
                params.append(tenant_id)
            query += " GROUP BY category ORDER BY category ASC"

            categories: List[Dict[str, Any]] = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for idx, r in enumerate(cur.fetchall(), start=1):
                    categories.append({
                        "id": idx,
                        "category_name": r["category"],
                        "item_count": int(r["item_count"]),
                    })
            return categories
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
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch personalized product catalog with contracted pricing, stock availability, and categories."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            customer = self.get_customer(customer_id, conn=conn)
            price_items: Dict[int, Dict[str, Any]] = {}
            if customer and customer.get("default_price_list_id"):
                price_items = self.get_price_list_items(customer["default_price_list_id"], conn=conn)

            stock_map = self.get_stock_levels(conn=conn)
            categories = self.get_categories(conn=conn)

            # Build product query
            query = f"""
                SELECT p.id, p.name, p.sku, p.barcode, p.description, p.price, p.cost_price,
                       p.category, p.brand, p.tax_rate, p.image_url, p.is_active, p.is_saleable,
                       pu.base_uom_id, u.uom_name, u.uom_code
                FROM {self._get_table("t0003")} p
                LEFT JOIN {self._get_table("t0007")} pu ON pu.product_id = p.id
                LEFT JOIN {self._get_table("t0001")} u ON u.id = pu.base_uom_id
                WHERE p.is_active = true AND p.is_saleable = true
            """
            params: List[Any] = []
            if tenant_id is not None:
                query += " AND p.business_id = %s"
                params.append(tenant_id)

            if category:
                query += " AND LOWER(p.category) = LOWER(%s)"
                params.append(category)

            if search:
                term = f"%{search.strip()}%"
                query += " AND (p.name ILIKE %s OR p.sku ILIKE %s OR p.barcode ILIKE %s OR p.description ILIKE %s)"
                params.extend([term, term, term, term])

            query += " ORDER BY p.name ASC, p.id ASC"

            all_items: List[Dict[str, Any]] = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for r in cur.fetchall():
                    pid = r["id"]
                    base_price = _to_float(r.get("price", 0.0))
                    stock_qty = stock_map.get(pid, 0.0)
                    is_in_stock = stock_qty > 0

                    if in_stock_only and not is_in_stock:
                        continue

                    contracted_price = base_price
                    is_contracted = False
                    if pid in price_items:
                        p_item = price_items[pid]
                        c_price = _to_float(p_item.get("unit_price"))
                        if c_price > 0:
                            contracted_price = c_price
                            is_contracted = True

                    discount_percent = 0.0
                    if is_contracted and base_price > 0 and base_price > contracted_price:
                        discount_percent = round(((base_price - contracted_price) / base_price) * 100.0, 2)

                    item = {
                        "id": pid,
                        "product_code": r.get("sku") or "",
                        "product_name": r.get("name") or "",
                        "category_id": None,
                        "category_name": r.get("category"),
                        "uom_id": r.get("base_uom_id"),
                        "uom_name": r.get("uom_name") or r.get("uom_code"),
                        "base_price": base_price,
                        "contracted_price": contracted_price,
                        "is_contracted": is_contracted,
                        "discount_percent": discount_percent,
                        "stock_qty": stock_qty,
                        "is_in_stock": is_in_stock,
                        "image_url": r.get("image_url"),
                        "description": r.get("description"),
                        "is_active": bool(r.get("is_active", True)),
                    }
                    all_items.append(item)

            total = len(all_items)
            offset = max(0, (page - 1) * limit)
            paginated_items = all_items[offset : offset + limit]

            cust_meta = {
                "min_order_amount": _to_float(customer.get("min_order_amount", 0.0)) if customer else 0.0,
                "order_cutoff_time": str(customer.get("order_cutoff_time")) if customer and customer.get("order_cutoff_time") else None,
            }

            return paginated_items, total, categories, cust_meta
        finally:
            if should_release:
                release_connection(conn)

    def get_account_summary(self, customer_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Get account summary and dashboard stats for a customer."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            customer = self.get_customer(customer_id, conn=conn)
            if not customer:
                return None

            tenant_id = get_current_tenant()

            # 1. Unpaid invoices stats from T0090
            inv_query = f"""
                SELECT COUNT(*) as open_count,
                       COALESCE(SUM(total_amount - COALESCE(paid_amount, 0)), 0) as unpaid_total
                FROM {self._get_table("t0090")}
                WHERE partner_id = %s AND status IN ('Unpaid', 'Partially Paid', 'Draft', 'Overdue')
            """
            inv_params: List[Any] = [customer_id]
            if tenant_id is not None:
                inv_query += " AND business_id = %s"
                inv_params.append(tenant_id)

            open_count = 0
            unpaid_total = 0.0
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(inv_query, inv_params)
                row = cur.fetchone()
                if row:
                    open_count = int(row.get("open_count", 0))
                    unpaid_total = _to_float(row.get("unpaid_total", 0.0))

            # 2. Recent orders count from T0012
            order_query = f"""
                SELECT COUNT(*) as order_count
                FROM {self._get_table("t0012")}
                WHERE customer_id = %s
            """
            order_params: List[Any] = [customer_id]
            if tenant_id is not None:
                order_query += " AND business_id = %s"
                order_params.append(tenant_id)

            recent_orders_count = 0
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(order_query, order_params)
                row = cur.fetchone()
                if row:
                    recent_orders_count = int(row.get("order_count", 0))

            # 3. Price list name lookup
            price_list_name = self.get_price_list_name(customer.get("default_price_list_id"), conn=conn)

            credit_limit = _to_float(customer.get("credit_limit", 0.0))
            current_balance = _to_float(customer.get("balance", 0.0))
            available_credit = max(0.0, credit_limit - current_balance)

            return {
                "customer_id": customer["id"],
                "customer_name": customer["name"],
                "group_name": customer.get("group_name") or "Wholesale",
                "email": customer.get("email"),
                "phone": customer.get("phone"),
                "credit_limit": credit_limit,
                "current_balance": current_balance,
                "available_credit": available_credit,
                "min_order_amount": _to_float(customer.get("min_order_amount", 0.0)),
                "order_cutoff_time": str(customer.get("order_cutoff_time")) if customer.get("order_cutoff_time") else None,
                "allow_reorders": bool(customer.get("allow_reorders", True)),
                "open_invoices_count": open_count,
                "total_unpaid_amount": unpaid_total,
                "recent_orders_count": recent_orders_count,
                "default_price_list_id": customer.get("default_price_list_id"),
                "default_price_list_name": price_list_name,
            }
        finally:
            if should_release:
                release_connection(conn)
