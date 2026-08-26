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
                       COALESCE(SUM(i.total_amount - COALESCE((SELECT SUM(p.amount) FROM {self._get_table("t0091")} p WHERE p.invoice_id = i.id AND p.status = 'Completed'), 0)), 0) as unpaid_total
                FROM {self._get_table("t0090")} i
                WHERE i.partner_id = %s AND i.status IN ('Unpaid', 'Partially Paid', 'Draft', 'Overdue')
            """
            inv_params: List[Any] = [customer_id]
            if tenant_id is not None:
                inv_query += " AND i.business_id = %s"
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

    def get_customer_by_id(self, customer_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Alias for get_customer."""
        return self.get_customer(customer_id, conn=conn)

    def get_active_warehouse(self, conn=None) -> Optional[Dict[str, Any]]:
        """Fetch first active warehouse from T0008."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT id, name, is_active, business_id
                FROM {self._get_table("t0008")}
                WHERE is_active = true
            """
            params: List[Any] = []
            if tenant_id is not None:
                query += " AND (business_id = %s OR business_id IS NULL)"
                params.append(tenant_id)
            query += " ORDER BY id ASC LIMIT 1"

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_tax_rate(self, tax_rate_id: Optional[int], conn=None) -> Optional[Dict[str, Any]]:
        """Fetch tax rate details from T0085."""
        if not tax_rate_id:
            return None
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
                SELECT id, name, code, rate, type
                FROM {self._get_table("t0085")}
                WHERE id = %s
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (tax_rate_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def create_order(
        self,
        order_data: Dict[str, Any],
        lines: List[Dict[str, Any]],
        conn=None,
    ) -> Dict[str, Any]:
        """Atomically create a sales order header (T0012) and lines (T0013)."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            if tenant_id is not None and "business_id" not in order_data:
                order_data["business_id"] = tenant_id

            order_date = order_data.get("order_date")
            if isinstance(order_date, (datetime, date)):
                date_str = order_date.strftime("%Y%m%d")
            else:
                date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

            order_number = order_data.get("order_number")
            if not order_number:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT nextval('{self.schema}.seq_sales_order_number')")
                        row = cur.fetchone()
                        seq_val = int(row[0]) if row else 1
                        order_number = f"SO-{date_str}-{seq_val:05d}"
                except Exception:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {self._get_table('t0012')}")
                            seq_val = int(cur.fetchone()[0])
                            order_number = f"SO-{date_str}-{seq_val:05d}"
                    except Exception:
                        order_number = f"SO-{date_str}-{int(datetime.now().timestamp() * 1000) % 100000:05d}"

            order_data["order_number"] = order_number

            insert_order_query = f"""
                INSERT INTO {self._get_table("t0012")} (
                    customer_id, warehouse_id, order_number, subtotal, tax, grand_total,
                    status, order_date, notes, price_list_id, tax_rate_id, payment_term_id,
                    created_by, updated_by, business_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, customer_id, warehouse_id, order_number, subtotal, tax, grand_total,
                          status, order_date, notes, price_list_id, tax_rate_id, payment_term_id,
                          created_at, created_by, updated_at, updated_by, update_number, business_id
            """
            order_params = [
                order_data.get("customer_id"),
                order_data.get("warehouse_id"),
                order_number,
                order_data.get("subtotal", 0.0),
                order_data.get("tax", 0.0),
                order_data.get("grand_total", 0.0),
                order_data.get("status", "Confirmed"),
                order_data.get("order_date") or datetime.now(timezone.utc).date(),
                order_data.get("notes"),
                order_data.get("price_list_id"),
                order_data.get("tax_rate_id"),
                order_data.get("payment_term_id"),
                order_data.get("created_by"),
                order_data.get("updated_by"),
                order_data.get("business_id", tenant_id),
            ]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(insert_order_query, order_params)
                order_row = cur.fetchone()
                order_id = order_row["id"]

                inserted_lines = []
                for idx, line in enumerate(lines, start=1):
                    qty = _to_float(line.get("qty", 1.0))
                    unit_price = _to_float(line.get("unit_price", 0.0))
                    line_total = _to_float(line.get("line_total", qty * unit_price))
                    line_num = int(line.get("line_number") or idx)

                    insert_line_query = f"""
                        INSERT INTO {self._get_table("t0013")} (
                            sales_order_id, product_id, product_name, qty, unit_price,
                            line_total, line_number, business_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, sales_order_id, product_id, product_name, qty,
                                  unit_price, line_total, line_number
                    """
                    cur.execute(
                        insert_line_query,
                        [
                            order_id,
                            line.get("product_id"),
                            line.get("product_name", ""),
                            qty,
                            unit_price,
                            line_total,
                            line_num,
                            order_data.get("business_id", tenant_id),
                        ],
                    )
                    line_row = cur.fetchone()
                    line_dict = dict(line_row)
                    line_dict["product_code"] = line.get("product_code")
                    line_dict["uom_name"] = line.get("uom_name")
                    inserted_lines.append(line_dict)

            if should_release:
                conn.commit()

            res = dict(order_row)
            res["lines"] = inserted_lines
            return res
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)

    def get_order_lines(self, order_id: int, conn=None) -> List[Dict[str, Any]]:
        """Fetch line items for a sales order with product sku and uom details."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
                SELECT l.id, l.sales_order_id, l.product_id, l.product_name,
                       l.qty, l.unit_price, l.line_total, l.line_number,
                       p.sku as product_code, u.uom_name
                FROM {self._get_table("t0013")} l
                LEFT JOIN {self._get_table("t0003")} p ON p.id = l.product_id
                LEFT JOIN {self._get_table("t0007")} pu ON pu.product_id = p.id
                LEFT JOIN {self._get_table("t0001")} u ON u.id = pu.base_uom_id
                WHERE l.sales_order_id = %s
                ORDER BY l.line_number ASC, l.id ASC
            """
            lines = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (order_id,))
                for r in cur.fetchall():
                    l_dict = dict(r)
                    l_dict["qty"] = _to_float(l_dict.get("qty"))
                    l_dict["unit_price"] = _to_float(l_dict.get("unit_price"))
                    l_dict["line_total"] = _to_float(l_dict.get("line_total"))
                    lines.append(l_dict)
            return lines
        finally:
            if should_release:
                release_connection(conn)

    def get_orders(
        self,
        customer_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch customer orders with pagination and line item details."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            count_query = f"""
                SELECT COUNT(*)
                FROM {self._get_table("t0012")} o
                WHERE o.customer_id = %s
            """
            params: List[Any] = [customer_id]
            if tenant_id is not None:
                count_query += " AND o.business_id = %s"
                params.append(tenant_id)
            if status:
                count_query += " AND o.status = %s"
                params.append(status)

            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = int(cur.fetchone()[0])

            query = f"""
                SELECT o.id, o.order_number, o.customer_id, c.name as customer_name,
                       o.warehouse_id, o.subtotal, o.tax, o.grand_total, o.status,
                       o.order_date, o.notes, o.created_at, o.created_by, o.updated_at,
                       o.updated_by, o.update_number
                FROM {self._get_table("t0012")} o
                LEFT JOIN {self._get_table("t0010")} c ON c.id = o.customer_id
                WHERE o.customer_id = %s
            """
            list_params: List[Any] = [customer_id]
            if tenant_id is not None:
                query += " AND o.business_id = %s"
                list_params.append(tenant_id)
            if status:
                query += " AND o.status = %s"
                list_params.append(status)

            query += " ORDER BY o.order_date DESC, o.id DESC"
            query += " LIMIT %s OFFSET %s"
            offset = max(0, (page - 1) * limit)
            list_params.extend([limit, offset])

            orders = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, list_params)
                for r in cur.fetchall():
                    o_dict = dict(r)
                    o_dict["subtotal"] = _to_float(o_dict.get("subtotal"))
                    o_dict["tax"] = _to_float(o_dict.get("tax"))
                    o_dict["grand_total"] = _to_float(o_dict.get("grand_total"))
                    o_dict["lines"] = self.get_order_lines(o_dict["id"], conn=conn)
                    orders.append(o_dict)

            return orders, total
        finally:
            if should_release:
                release_connection(conn)

    def get_order_by_id(
        self,
        order_id: int,
        customer_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch single order by id with lines, scoped to customer_id if provided."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT o.id, o.order_number, o.customer_id, c.name as customer_name,
                       o.warehouse_id, o.subtotal, o.tax, o.grand_total, o.status,
                       o.order_date, o.notes, o.created_at, o.created_by, o.updated_at,
                       o.updated_by, o.update_number
                FROM {self._get_table("t0012")} o
                LEFT JOIN {self._get_table("t0010")} c ON c.id = o.customer_id
                WHERE o.id = %s
            """
            params: List[Any] = [order_id]
            if customer_id is not None:
                query += " AND o.customer_id = %s"
                params.append(customer_id)
            if tenant_id is not None:
                query += " AND o.business_id = %s"
                params.append(tenant_id)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    return None
                o_dict = dict(row)
                o_dict["subtotal"] = _to_float(o_dict.get("subtotal"))
                o_dict["tax"] = _to_float(o_dict.get("tax"))
                o_dict["grand_total"] = _to_float(o_dict.get("grand_total"))
                o_dict["lines"] = self.get_order_lines(order_id, conn=conn)
                return o_dict
        finally:
            if should_release:
                release_connection(conn)

    def update_order_status(
        self,
        order_id: int,
        status: str,
        notes: Optional[str] = None,
        customer_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Update order status and optional notes."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                UPDATE {self._get_table("t0012")}
                SET status = %s,
                    notes = COALESCE(%s, notes),
                    updated_at = NOW(),
                    update_number = COALESCE(update_number, 0) + 1
                WHERE id = %s
            """
            params: List[Any] = [status, notes, order_id]
            if customer_id is not None:
                query += " AND customer_id = %s"
                params.append(customer_id)
            if tenant_id is not None:
                query += " AND business_id = %s"
                params.append(tenant_id)
            query += " RETURNING id, status, notes"

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if should_release:
                    conn.commit()
                return dict(row) if row else None
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)

    def get_invoices(
        self,
        customer_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch customer invoices from T0090."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            count_query = f"""
                SELECT COUNT(*)
                FROM {self._get_table("t0090")} i
                WHERE i.partner_id = %s
            """
            params: List[Any] = [customer_id]
            if tenant_id is not None:
                count_query += " AND i.business_id = %s"
                params.append(tenant_id)
            if status:
                count_query += " AND i.status = %s"
                params.append(status)

            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = int(cur.fetchone()[0])

            query = f"""
                SELECT i.id, i.invoice_number, i.invoice_type, i.partner_id, c.name as customer_name,
                       i.sales_order_id, o.order_number as sales_order_number,
                       i.issue_date, i.due_date, i.total_amount,
                       COALESCE((SELECT SUM(p.amount) FROM {self._get_table("t0091")} p WHERE p.invoice_id = i.id AND p.status = 'Completed'), 0) as paid_amount,
                       i.status, i.notes, i.stripe_payment_intent_id, i.stripe_checkout_session_id,
                       i.payment_link, i.created_at, i.created_by, i.updated_at, i.updated_by,
                       i.update_number
                FROM {self._get_table("t0090")} i
                LEFT JOIN {self._get_table("t0010")} c ON c.id = i.partner_id
                LEFT JOIN {self._get_table("t0012")} o ON o.id = i.sales_order_id
                WHERE i.partner_id = %s
            """
            list_params: List[Any] = [customer_id]
            if tenant_id is not None:
                query += " AND i.business_id = %s"
                list_params.append(tenant_id)
            if status:
                query += " AND i.status = %s"
                list_params.append(status)

            query += " ORDER BY i.issue_date DESC, i.id DESC"
            query += " LIMIT %s OFFSET %s"
            offset = max(0, (page - 1) * limit)
            list_params.extend([limit, offset])

            invoices = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, list_params)
                for r in cur.fetchall():
                    inv = dict(r)
                    tot = _to_float(inv.get("total_amount"))
                    paid = _to_float(inv.get("paid_amount"))
                    inv["total_amount"] = tot
                    inv["paid_amount"] = paid
                    inv["balance_due"] = max(0.0, round(tot - paid, 2))
                    invoices.append(inv)

            return invoices, total
        finally:
            if should_release:
                release_connection(conn)

    def get_invoice_by_id(
        self,
        invoice_id: int,
        customer_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch single invoice from T0090, verified against customer_id if provided."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()
            query = f"""
                SELECT i.id, i.invoice_number, i.invoice_type, i.partner_id, c.name as customer_name,
                       i.sales_order_id, o.order_number as sales_order_number,
                       i.issue_date, i.due_date, i.total_amount,
                       COALESCE((SELECT SUM(p.amount) FROM {self._get_table("t0091")} p WHERE p.invoice_id = i.id AND p.status = 'Completed'), 0) as paid_amount,
                       i.status, i.notes, i.stripe_payment_intent_id, i.stripe_checkout_session_id,
                       i.payment_link, i.created_at, i.created_by, i.updated_at, i.updated_by,
                       i.update_number
                FROM {self._get_table("t0090")} i
                LEFT JOIN {self._get_table("t0010")} c ON c.id = i.partner_id
                LEFT JOIN {self._get_table("t0012")} o ON o.id = i.sales_order_id
                WHERE i.id = %s
            """
            params: List[Any] = [invoice_id]
            if customer_id is not None:
                query += " AND i.partner_id = %s"
                params.append(customer_id)
            if tenant_id is not None:
                query += " AND i.business_id = %s"
                params.append(tenant_id)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    return None
                inv = dict(row)
                tot = _to_float(inv.get("total_amount"))
                paid = _to_float(inv.get("paid_amount"))
                inv["total_amount"] = tot
                inv["paid_amount"] = paid
                inv["balance_due"] = max(0.0, round(tot - paid, 2))
                return inv
        finally:
            if should_release:
                release_connection(conn)

    def update_invoice_stripe_session(
        self,
        invoice_id: int,
        session_id: str,
        payment_link: Optional[str] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """Store Stripe session id and hosted payment URL in invoice T0090."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
                UPDATE {self._get_table("t0090")}
                SET stripe_checkout_session_id = %s,
                    payment_link = COALESCE(%s, payment_link),
                    updated_at = NOW(),
                    update_number = COALESCE(update_number, 0) + 1
                WHERE id = %s
                RETURNING id, stripe_checkout_session_id, payment_link
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (session_id, payment_link, invoice_id))
                row = cur.fetchone()
                if should_release:
                    conn.commit()
                return dict(row) if row else None
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)

    def reconcile_settlement_transaction(
        self,
        customer_id: int,
        amount: float,
        settlement_type: str = "invoice",
        invoice_id: Optional[int] = None,
        invoice_ids: Optional[List[int]] = None,
        session_id: Optional[str] = None,
        payment_intent_id: Optional[str] = None,
        payment_method: str = "Stripe Card",
        payment_link: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Reconcile online Stripe payment: create payment, update invoices, decrement balance, post journal entry."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            tenant_id = get_current_tenant()

            # 1. Idempotency Check: see if payment record already exists
            if payment_intent_id or session_id:
                check_payment_query = f"""
                    SELECT id, payment_date, invoice_id, partner_id, amount, payment_method,
                           reference, status, notes, stripe_payment_intent_id, stripe_checkout_session_id,
                           payment_link, created_at
                    FROM {self._get_table("t0091")}
                    WHERE (%s IS NOT NULL AND stripe_payment_intent_id = %s)
                       OR (%s IS NOT NULL AND stripe_checkout_session_id = %s)
                    LIMIT 1
                """
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(check_payment_query, (payment_intent_id, payment_intent_id, session_id, session_id))
                    existing_payment = cur.fetchone()

                if existing_payment:
                    customer = self.get_customer(customer_id, conn=conn)
                    cust_bal = _to_float(customer.get("balance", 0.0)) if customer else 0.0
                    return {
                        "reconciled": True,
                        "already_processed": True,
                        "payment_id": existing_payment["id"],
                        "customer_id": customer_id,
                        "amount": _to_float(existing_payment.get("amount")),
                        "invoice_id": existing_payment.get("invoice_id"),
                        "invoices_updated": [existing_payment["invoice_id"]] if existing_payment.get("invoice_id") else [],
                        "new_customer_balance": cust_bal,
                        "journal_entry_id": None,
                        "session_id": session_id,
                        "payment_intent_id": payment_intent_id,
                    }

            # 2. Lookup customer
            customer = self.get_customer(customer_id, conn=conn)
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} does not exist.")

            customer_business_id = customer.get("business_id") or tenant_id

            # 3. Create payment record in T0091
            insert_payment_query = f"""
                INSERT INTO {self._get_table("t0091")} (
                    payment_date, invoice_id, partner_id, amount, payment_method,
                    reference, status, notes, stripe_payment_intent_id,
                    stripe_checkout_session_id, payment_link, business_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, payment_date, invoice_id, partner_id, amount, payment_method,
                          reference, status, notes, stripe_payment_intent_id,
                          stripe_checkout_session_id, payment_link, created_at
            """
            reference = payment_intent_id or session_id or f"STRIPE-{customer_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            payment_params = [
                datetime.now(timezone.utc).date(),
                invoice_id,
                customer_id,
                amount,
                payment_method,
                reference,
                "Completed",
                f"Online settlement via {payment_method}",
                payment_intent_id,
                session_id,
                payment_link,
                customer_business_id,
            ]

            invoices_updated = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(insert_payment_query, payment_params)
                payment_row = cur.fetchone()
                payment_id = payment_row["id"]

                # 4. Update Invoices in T0090
                if invoice_id:
                    # Calculate total paid for this invoice
                    cur.execute(
                        f"""
                        SELECT COALESCE(SUM(amount), 0) as total_paid
                        FROM {self._get_table("t0091")}
                        WHERE invoice_id = %s AND status = 'Completed'
                        """,
                        (invoice_id,),
                    )
                    paid_row = cur.fetchone()
                    total_paid = amount
                    if paid_row:
                        if isinstance(paid_row, dict):
                            total_paid = _to_float(paid_row.get("total_paid", paid_row.get("paid_amount", amount)))
                        elif isinstance(paid_row, (list, tuple)) and len(paid_row) > 0:
                            total_paid = _to_float(paid_row[0])

                    cur.execute(
                        f"SELECT total_amount FROM {self._get_table('t0090')} WHERE id = %s",
                        (invoice_id,),
                    )
                    inv_meta = cur.fetchone()
                    tot_amount = 0.0
                    if inv_meta:
                        if isinstance(inv_meta, dict):
                            tot_amount = _to_float(inv_meta.get("total_amount", 0.0))
                        elif isinstance(inv_meta, (list, tuple)) and len(inv_meta) > 0:
                            tot_amount = _to_float(inv_meta[0])

                    inv_status = "Paid" if total_paid >= tot_amount else "Partially Paid"
                    update_inv_query = f"""
                        UPDATE {self._get_table("t0090")}
                        SET status = %s,
                            stripe_payment_intent_id = COALESCE(%s, stripe_payment_intent_id),
                            stripe_checkout_session_id = COALESCE(%s, stripe_checkout_session_id),
                            payment_link = COALESCE(%s, payment_link),
                            updated_at = NOW(),
                            update_number = COALESCE(update_number, 0) + 1
                        WHERE id = %s
                        RETURNING id, total_amount, status
                    """
                    cur.execute(update_inv_query, (inv_status, payment_intent_id, session_id, payment_link, invoice_id))
                    inv_res = cur.fetchone()
                    if inv_res:
                        res_id = inv_res.get("id", invoice_id) if isinstance(inv_res, dict) else invoice_id
                        invoices_updated.append(res_id)

                elif invoice_ids:
                    for inv_id in invoice_ids:
                        cur.execute(
                            f"""
                            SELECT COALESCE(SUM(amount), 0) as total_paid
                            FROM {self._get_table("t0091")}
                            WHERE invoice_id = %s AND status = 'Completed'
                            """,
                            (inv_id,),
                        )
                        paid_row = cur.fetchone()
                        total_paid = 0.0
                        if paid_row:
                            if isinstance(paid_row, dict):
                                total_paid = _to_float(paid_row.get("total_paid", paid_row.get("paid_amount", 0.0)))
                            elif isinstance(paid_row, (list, tuple)) and len(paid_row) > 0:
                                total_paid = _to_float(paid_row[0])

                        cur.execute(
                            f"SELECT total_amount FROM {self._get_table('t0090')} WHERE id = %s",
                            (inv_id,),
                        )
                        inv_meta = cur.fetchone()
                        tot_amount = 0.0
                        if inv_meta:
                            if isinstance(inv_meta, dict):
                                tot_amount = _to_float(inv_meta.get("total_amount", 0.0))
                            elif isinstance(inv_meta, (list, tuple)) and len(inv_meta) > 0:
                                tot_amount = _to_float(inv_meta[0])

                        inv_status = "Paid" if (total_paid >= tot_amount or len(invoice_ids) == 1) else "Paid"
                        cur.execute(
                            f"""
                            UPDATE {self._get_table("t0090")}
                            SET status = %s,
                                stripe_payment_intent_id = COALESCE(%s, stripe_payment_intent_id),
                                stripe_checkout_session_id = COALESCE(%s, stripe_checkout_session_id),
                                payment_link = COALESCE(%s, payment_link),
                                updated_at = NOW(),
                                update_number = COALESCE(update_number, 0) + 1
                            WHERE id = %s
                            RETURNING id
                            """,
                            (inv_status, payment_intent_id, session_id, payment_link, inv_id),
                        )
                        inv_res = cur.fetchone()
                        if inv_res:
                            res_id = inv_res.get("id", inv_id) if isinstance(inv_res, dict) else inv_id
                            invoices_updated.append(res_id)

                else:
                    # General balance payment without specific invoice IDs
                    cur.execute(
                        f"""
                        SELECT id, total_amount
                        FROM {self._get_table("t0090")}
                        WHERE partner_id = %s AND status IN ('Unpaid', 'Partially Paid', 'Draft', 'Overdue')
                        ORDER BY issue_date ASC, id ASC
                        """,
                        (customer_id,),
                    )
                    open_invoices = cur.fetchall()
                    for o_inv in open_invoices:
                        o_id = o_inv["id"]
                        o_tot = _to_float(o_inv["total_amount"])
                        cur.execute(
                            f"""
                            SELECT COALESCE(SUM(amount), 0) as total_paid
                            FROM {self._get_table("t0091")}
                            WHERE invoice_id = %s AND status = 'Completed'
                            """,
                            (o_id,),
                        )
                        p_row = cur.fetchone()
                        p_paid = _to_float(p_row["total_paid"]) if p_row else 0.0
                        if p_paid >= o_tot:
                            cur.execute(
                                f"""
                                UPDATE {self._get_table("t0090")}
                                SET status = 'Paid',
                                    updated_at = NOW(),
                                    update_number = COALESCE(update_number, 0) + 1
                                WHERE id = %s
                                RETURNING id
                                """,
                                (o_id,),
                            )
                            inv_res = cur.fetchone()
                            if inv_res:
                                res_id = inv_res.get("id", o_id) if isinstance(inv_res, dict) else o_id
                                invoices_updated.append(res_id)

                # 5. Decrement Customer Balance in T0010
                update_cust_query = f"""
                    UPDATE {self._get_table("t0010")}
                    SET balance = GREATEST(0.0, balance - %s),
                        updated_at = NOW(),
                        update_number = COALESCE(update_number, 0) + 1
                    WHERE id = %s
                    RETURNING balance
                """
                cur.execute(update_cust_query, (amount, customer_id))
                cust_row = cur.fetchone()
                new_balance = _to_float(cust_row["balance"]) if cust_row else 0.0

                # 6. Post balancing General Ledger Journal Entry (T0027 and T0089)
                cur.execute(
                    f"""
                    SELECT id FROM {self._get_table("t0026")}
                    WHERE (account_code = '1000' OR account_type = 'Asset' OR account_name ILIKE '%Bank%' OR account_name ILIKE '%Cash%')
                    ORDER BY id ASC LIMIT 1
                    """
                )
                bank_acc = cur.fetchone()
                bank_acc_id = bank_acc["id"] if bank_acc else 1

                cur.execute(
                    f"""
                    SELECT id FROM {self._get_table("t0026")}
                    WHERE (account_code = '1200' OR account_name ILIKE '%Receivable%' OR account_type = 'Asset')
                    ORDER BY id ASC LIMIT 1
                    """
                )
                ar_acc = cur.fetchone()
                ar_acc_id = ar_acc["id"] if ar_acc else 2

                je_ref = f"JE-STRIPE-{payment_id}"
                insert_je_query = f"""
                    INSERT INTO {self._get_table("t0027")} (
                        entry_date, reference, description, status, business_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, entry_date, reference, description, status, created_at
                """
                je_params = [
                    datetime.now(timezone.utc).date(),
                    je_ref,
                    f"Stripe settlement for customer {customer.get('name')}",
                    "Posted",
                    customer_business_id,
                ]
                cur.execute(insert_je_query, je_params)
                je_row = cur.fetchone()
                je_id = je_row["id"]

                # Debit Bank / Cash
                cur.execute(
                    f"""
                    INSERT INTO {self._get_table("t0089")} (
                        journal_entry_id, account_id, debit, credit, description, is_active, business_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, journal_entry_id, account_id, debit, credit, description
                    """,
                    (je_id, bank_acc_id, amount, 0.0, f"Stripe settlement deposit - {customer.get('name')}", True, customer_business_id),
                )

                # Credit Accounts Receivable
                cur.execute(
                    f"""
                    INSERT INTO {self._get_table("t0089")} (
                        journal_entry_id, account_id, debit, credit, description, is_active, business_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, journal_entry_id, account_id, debit, credit, description
                    """,
                    (je_id, ar_acc_id, 0.0, amount, f"Accounts receivable reduction - {customer.get('name')}", True, customer_business_id),
                )

            if should_release:
                conn.commit()

            return {
                "reconciled": True,
                "already_processed": False,
                "payment_id": payment_id,
                "customer_id": customer_id,
                "amount": amount,
                "invoice_id": invoice_id,
                "invoices_updated": invoices_updated,
                "new_customer_balance": new_balance,
                "journal_entry_id": je_id,
                "journal_entry_reference": je_ref,
                "session_id": session_id,
                "payment_intent_id": payment_intent_id,
            }
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)
