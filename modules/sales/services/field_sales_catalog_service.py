import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.sales.models.field_sales import (
    CatalogProductItem,
    CustomerOrderLineSummary,
    CustomerOrderSummary,
    CustomerPriceRule,
    FieldSalesCatalogBundle,
    FieldSalesCustomerProfile,
)

logger = logging.getLogger(__name__)


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safely convert numeric/Decimal/string values to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _to_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert values to integer."""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_timestamp(val: Any) -> Optional[datetime]:
    """Parse string or datetime to timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class FieldSalesCatalogService:
    """Service to assemble high-performance mobile catalog bundles and customer profiles.

    Optimized for field sales representatives working offline or with poor connectivity.
    """

    def __init__(self, schema: Optional[str] = None):
        self.schema = schema or os.getenv("DB_SCHEMA", "Nova")

    def _get_table(self, table_name: str) -> str:
        return f'"{self.schema}".{table_name.lower()}'

    def get_mobile_catalog(
        self,
        delta_timestamp: Optional[Union[datetime, str]] = None,
        warehouse_id: Optional[int] = None,
        sales_rep_id: Optional[int] = None,
        conn=None,
    ) -> FieldSalesCatalogBundle:
        """Assemble the complete or delta mobile catalog bundle for field offline use.

        Includes:
        - Active products with primary barcodes, UOM codes, base prices, and stock levels
        - Customer profiles with credit limits, balances, payment terms, and recent 5 orders
        - Contracted and standard price list rules
        - Active warehouses, tax rates, and payment terms lookup metadata
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        parsed_delta = _parse_timestamp(delta_timestamp)

        try:
            products = self.get_products(
                delta_timestamp=parsed_delta,
                warehouse_id=warehouse_id,
                conn=conn,
            )
            customers = self.get_customers(
                delta_timestamp=parsed_delta,
                sales_rep_id=sales_rep_id,
                include_recent_orders=True,
                conn=conn,
            )
            price_rules = self.get_price_rules(conn=conn)
            metadata = self.get_metadata_lookups(conn=conn)

            bundle = FieldSalesCatalogBundle(
                sync_timestamp=datetime.now(timezone.utc),
                delta_timestamp=parsed_delta,
                products=products,
                customers=customers,
                price_rules=price_rules,
                warehouses=metadata.get("warehouses", []),
                tax_rates=metadata.get("tax_rates", []),
                payment_terms=metadata.get("payment_terms", []),
                total_products=len(products),
                total_customers=len(customers),
            )
            return bundle
        finally:
            if should_release:
                release_connection(conn)

    def get_products(
        self,
        delta_timestamp: Optional[datetime] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> List[CatalogProductItem]:
        """Fetch products optimized for mobile offline caching with stock levels."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            # 1. Fetch stock levels grouped by product and warehouse
            stock_map: Dict[int, Dict[str, float]] = {}
            total_stock_map: Dict[int, float] = {}

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT product_id, warehouse_id, qty
                    FROM {self._get_table("t0009")}
                    """
                )
                for row in cur.fetchall():
                    pid = row["product_id"]
                    wid = str(row["warehouse_id"])
                    qty = _to_float(row.get("qty", 0.0))
                    if pid not in stock_map:
                        stock_map[pid] = {}
                        total_stock_map[pid] = 0.0
                    stock_map[pid][wid] = qty
                    total_stock_map[pid] += qty

            # 2. Fetch primary barcodes from t0004
            barcode_map: Dict[int, str] = {}
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT DISTINCT ON (product_id) product_id, barcode
                    FROM {self._get_table("t0004")}
                    ORDER BY product_id, is_primary DESC, id ASC
                    """
                )
                for row in cur.fetchall():
                    barcode_map[row["product_id"]] = row["barcode"]

            # 3. Fetch UOM mappings from t0007 / t0001
            uom_map: Dict[int, Dict[str, Any]] = {}
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT pu.product_id, pu.base_uom_id, u.uom_code, u.uom_name
                    FROM {self._get_table("t0007")} pu
                    LEFT JOIN {self._get_table("t0001")} u ON u.id = pu.base_uom_id
                    """
                )
                for row in cur.fetchall():
                    uom_map[row["product_id"]] = {
                        "uom_id": row.get("base_uom_id"),
                        "uom_code": row.get("uom_code"),
                        "uom_name": row.get("uom_name"),
                    }

            # 4. Fetch Products from t0003
            query = f"""
                SELECT p.id, p.name, p.sku, p.price, p.cost_price, p.category, p.brand,
                       p.tax_rate, p.image_url, p.is_active, p.updated_at
                FROM {self._get_table("t0003")} p
            """
            params: List[Any] = []
            where_clauses = []

            if delta_timestamp:
                where_clauses.append("p.updated_at >= %s")
                params.append(delta_timestamp)
            else:
                where_clauses.append("p.is_active = true")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " ORDER BY p.name ASC, p.id ASC"

            products: List[CatalogProductItem] = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for r in cur.fetchall():
                    pid = r["id"]
                    wh_stocks = stock_map.get(pid, {})
                    uom_info = uom_map.get(pid, {})

                    if warehouse_id is not None:
                        avail = wh_stocks.get(str(warehouse_id), 0.0)
                    else:
                        avail = total_stock_map.get(pid, 0.0)

                    prod_barcode = barcode_map.get(pid)

                    item = CatalogProductItem(
                        id=pid,
                        sku=r.get("sku"),
                        barcode=prod_barcode,
                        name=r["name"],
                        category=r.get("category"),
                        uom_id=uom_info.get("uom_id"),
                        uom_code=uom_info.get("uom_code"),
                        base_price=_to_float(r.get("price", 0.0)),
                        cost_price=_to_float(r.get("cost_price")) if r.get("cost_price") is not None else None,
                        available_qty=avail,
                        warehouse_id=warehouse_id,
                        warehouse_stock=wh_stocks,
                        is_active=bool(r.get("is_active", True)),
                        image_url=r.get("image_url"),
                        tax_rate=_to_float(r.get("tax_rate")),
                        updated_at=r.get("updated_at"),
                    )
                    products.append(item)

            return products
        finally:
            if should_release:
                release_connection(conn)

    def get_customers(
        self,
        delta_timestamp: Optional[datetime] = None,
        sales_rep_id: Optional[int] = None,
        include_recent_orders: bool = True,
        conn=None,
    ) -> List[FieldSalesCustomerProfile]:
        """Fetch customer profiles with financial limits, terms, and recent order history."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            # 1. Fetch customers joining payment terms and tax rates
            query = f"""
                SELECT c.id, c.name, c.group_name, c.phone, c.email,
                       c.credit_limit, c.balance, c.is_active,
                       c.default_price_list_id, c.default_tax_rate_id, c.payment_term_id,
                       c.updated_at,
                       pt.name AS payment_term_name, pt.due_days AS payment_term_days,
                       tr.rate AS tax_rate_pct
                FROM {self._get_table("t0010")} c
                LEFT JOIN {self._get_table("t0096")} pt ON pt.id = c.payment_term_id
                LEFT JOIN {self._get_table("t0085")} tr ON tr.id = c.default_tax_rate_id
            """
            where_clauses = []
            params: List[Any] = []

            if delta_timestamp:
                where_clauses.append("c.updated_at >= %s")
                params.append(delta_timestamp)
            else:
                where_clauses.append("c.is_active = true")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " ORDER BY c.name ASC, c.id ASC"

            raw_customers: List[Dict[str, Any]] = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                raw_customers = [dict(row) for row in cur.fetchall()]

            customer_ids = [c["id"] for c in raw_customers]
            history_map: Dict[int, List[CustomerOrderSummary]] = {cid: [] for cid in customer_ids}

            # 2. Batch fetch recent 5 orders per customer if requested
            if include_recent_orders and customer_ids:
                history_map = self._batch_get_recent_orders(customer_ids, limit_per_customer=5, conn=conn)

            customers: List[FieldSalesCustomerProfile] = []
            for c in raw_customers:
                cid = c["id"]
                credit_limit = _to_float(c.get("credit_limit", 0.0))
                balance = _to_float(c.get("balance", 0.0))

                if credit_limit > 0:
                    available_credit = round(max(0.0, credit_limit - balance), 2)
                else:
                    available_credit = 999999.0  # Unlimited credit

                profile = FieldSalesCustomerProfile(
                    id=cid,
                    name=c["name"],
                    group_name=c.get("group_name") or "Retail",
                    phone=c.get("phone"),
                    email=c.get("email"),
                    credit_limit=credit_limit,
                    balance=balance,
                    available_credit=available_credit,
                    payment_term_id=c.get("payment_term_id"),
                    payment_term_name=c.get("payment_term_name"),
                    payment_term_days=c.get("payment_term_days"),
                    default_price_list_id=c.get("default_price_list_id"),
                    default_tax_rate_id=c.get("default_tax_rate_id"),
                    tax_rate_pct=_to_float(c.get("tax_rate_pct")) if c.get("tax_rate_pct") is not None else None,
                    is_active=bool(c.get("is_active", True)),
                    recent_orders=history_map.get(cid, []),
                )
                customers.append(profile)

            return customers
        finally:
            if should_release:
                release_connection(conn)

    def _batch_get_recent_orders(
        self,
        customer_ids: List[int],
        limit_per_customer: int = 5,
        conn=None,
    ) -> Dict[int, List[CustomerOrderSummary]]:
        """Batch load recent orders and lines for multiple customers efficiently."""
        if not customer_ids:
            return {}

        history_map: Dict[int, List[CustomerOrderSummary]] = {cid: [] for cid in customer_ids}

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Query recent orders using ROW_NUMBER() window function
            cur.execute(
                f"""
                WITH ranked_orders AS (
                    SELECT id, order_number, customer_id, order_date, grand_total, status,
                           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, id DESC) as rn
                    FROM {self._get_table("t0012")}
                    WHERE customer_id = ANY(%s)
                )
                SELECT id, order_number, customer_id, order_date, grand_total, status
                FROM ranked_orders
                WHERE rn <= %s
                ORDER BY customer_id, order_date DESC, id DESC
                """,
                (customer_ids, limit_per_customer),
            )
            orders_rows = cur.fetchall()

            if not orders_rows:
                return history_map

            order_ids = [r["id"] for r in orders_rows]
            order_lines_map: Dict[int, List[CustomerOrderLineSummary]] = {oid: [] for oid in order_ids}

            # Query lines for the fetched orders
            cur.execute(
                f"""
                SELECT sales_order_id, product_id, product_name, qty, unit_price, line_total
                FROM {self._get_table("t0013")}
                WHERE sales_order_id = ANY(%s)
                ORDER BY sales_order_id, line_number ASC, id ASC
                """,
                (order_ids,),
            )
            for line_row in cur.fetchall():
                so_id = line_row["sales_order_id"]
                line_summary = CustomerOrderLineSummary(
                    product_id=line_row.get("product_id"),
                    product_name=line_row.get("product_name") or "",
                    qty=_to_float(line_row.get("qty", 0.0)),
                    unit_price=_to_float(line_row.get("unit_price", 0.0)),
                    line_total=_to_float(line_row.get("line_total", 0.0)),
                )
                order_lines_map[so_id].append(line_summary)

            for r in orders_rows:
                cid = r["customer_id"]
                oid = r["id"]
                lines = order_lines_map.get(oid, [])
                summary = CustomerOrderSummary(
                    id=oid,
                    order_number=r.get("order_number") or f"SO-{oid}",
                    order_date=r.get("order_date"),
                    grand_total=_to_float(r.get("grand_total", 0.0)),
                    status=str(r.get("status", "Pending")),
                    item_count=len(lines),
                    lines=lines,
                )
                history_map[cid].append(summary)

        return history_map

    def get_customer_history(
        self,
        customer_id: int,
        limit: int = 5,
        conn=None,
    ) -> List[CustomerOrderSummary]:
        """Fetch the order history and line items for a specific customer."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            batch = self._batch_get_recent_orders([customer_id], limit_per_customer=limit, conn=conn)
            return batch.get(customer_id, [])
        finally:
            if should_release:
                release_connection(conn)

    def get_price_rules(
        self,
        price_list_id: Optional[int] = None,
        conn=None,
    ) -> List[CustomerPriceRule]:
        """Fetch active contracted and custom price list rules."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
                SELECT id, price_list_id, product_id, unit_price, min_qty, uom_id,
                       effective_from, effective_to
                FROM {self._get_table("t0084")}
                WHERE is_active = true
            """
            params: List[Any] = []
            if price_list_id is not None:
                query += " AND price_list_id = %s"
                params.append(price_list_id)

            query += " ORDER BY price_list_id ASC, product_id ASC"

            rules: List[CustomerPriceRule] = []
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                for r in cur.fetchall():
                    rules.append(
                        CustomerPriceRule(
                            id=r.get("id"),
                            price_list_id=r["price_list_id"],
                            product_id=r["product_id"],
                            unit_price=_to_float(r.get("unit_price", 0.0)),
                            min_qty=_to_float(r.get("min_qty", 1.0)),
                            uom_id=r.get("uom_id"),
                            effective_from=r.get("effective_from"),
                            effective_to=r.get("effective_to"),
                        )
                    )
            return rules
        finally:
            if should_release:
                release_connection(conn)

    def get_metadata_lookups(self, conn=None) -> Dict[str, Any]:
        """Fetch active warehouses, tax rates, and payment terms lookups."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            warehouses: List[Dict[str, Any]] = []
            tax_rates: List[Dict[str, Any]] = []
            payment_terms: List[Dict[str, Any]] = []

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 1. Warehouses (T0008)
                cur.execute(
                    f"""
                    SELECT id, name, location, is_active
                    FROM {self._get_table("t0008")}
                    WHERE is_active = true
                    ORDER BY name ASC
                    """
                )
                warehouses = [dict(r) for r in cur.fetchall()]

                # 2. Tax Rates (T0085)
                cur.execute(
                    f"""
                    SELECT id, name, code, rate, type, is_active, is_default
                    FROM {self._get_table("t0085")}
                    WHERE is_active = true
                    ORDER BY id ASC
                    """
                )
                tax_rates = [
                    {
                        "id": r["id"],
                        "name": r.get("name"),
                        "code": r.get("code"),
                        "rate": _to_float(r.get("rate", 0.0)),
                        "type": r.get("type"),
                        "is_default": bool(r.get("is_default", False)),
                    }
                    for r in cur.fetchall()
                ]

                # 3. Payment Terms (T0096)
                cur.execute(
                    f"""
                    SELECT id, name, code, description, due_days, discount_percentage, discount_days, is_active
                    FROM {self._get_table("t0096")}
                    WHERE is_active = true
                    ORDER BY id ASC
                    """
                )
                payment_terms = [
                    {
                        "id": r["id"],
                        "name": r.get("name"),
                        "code": r.get("code"),
                        "description": r.get("description"),
                        "due_days": r.get("due_days", 0),
                        "discount_percentage": _to_float(r.get("discount_percentage", 0.0)),
                        "discount_days": r.get("discount_days", 0),
                    }
                    for r in cur.fetchall()
                ]

            return {
                "warehouses": warehouses,
                "tax_rates": tax_rates,
                "payment_terms": payment_terms,
            }
        finally:
            if should_release:
                release_connection(conn)


field_sales_catalog_service = FieldSalesCatalogService()
