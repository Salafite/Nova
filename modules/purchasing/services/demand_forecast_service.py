import os
import math
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)

# Default forecasting constants
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_SAFETY_MARGIN_DAYS = 7
DEFAULT_TARGET_COVERAGE_DAYS = 30
DEFAULT_LEAD_TIME_DAYS = 7
DEFAULT_MIN_ORDER_QTY = 1.0


class DemandForecastService:
    """Service for calculating demand forecasting, inventory velocity, stockout projections,
    and proactive restock suggestions with supplier MOQ and lead time integration.
    """

    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')
        self.product_repo = CrudRepository('T0003', business_columns=['id', 'name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'is_active'])
        self.stock_repo = CrudRepository('T0009', business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'reorder_level'])
        self.supplier_repo = CrudRepository('T0011', business_columns=['id', 'name', 'category', 'phone', 'email', 'payment_terms', 'rating', 'is_active'])
        self.product_supplier_repo = CrudRepository('T0103', business_columns=['id', 'product_id', 'supplier_id', 'supplier_sku', 'unit_cost', 'lead_time_days', 'min_order_qty', 'is_preferred', 'is_active'])
        self.sales_order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'customer_id', 'warehouse_id', 'grand_total', 'status', 'order_date'])
        self.sales_line_repo = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total'])

    def calculate_sales_velocity(
        self,
        product_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> Dict[int, Dict[str, float]]:
        """Calculate daily sales velocity over the lookback window (default 30 days).
        Returns a dictionary mapping product_id to:
            {
                "daily_velocity": float,
                "total_sold": float,
                "order_count": int,
                "days": int,
            }
        """
        ref_date = reference_date or date.today()
        cutoff_date = ref_date - timedelta(days=days)
        should_release = False

        velocities: Dict[int, Dict[str, float]] = {}

        try:
            if conn is None:
                conn = get_connection()
                should_release = True
            sql = f"""

                SELECT
                    l.product_id,
                    COALESCE(SUM(l.qty), 0) AS total_sold,
                    COUNT(DISTINCT o.id) AS order_count
                FROM "{self.schema}".t0013 l
                JOIN "{self.schema}".t0012 o ON l.sales_order_id = o.id
                WHERE o.order_date >= %s
                  AND o.order_date <= %s
                  AND o.status NOT IN ('Cancelled', 'Draft')
                  {f'AND l.product_id = %s' if product_id is not None else ''}
                GROUP BY l.product_id
            """
            params = [cutoff_date, ref_date]
            if product_id is not None:
                params.append(product_id)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    p_id = row['product_id']
                    total_sold = float(row['total_sold'] or 0.0)
                    order_count = int(row['order_count'] or 0)
                    daily_velocity = round(total_sold / float(days), 4) if days > 0 else 0.0
                    velocities[p_id] = {
                        'daily_velocity': daily_velocity,
                        'total_sold': total_sold,
                        'order_count': order_count,
                        'days': days,
                    }
        except Exception as e:
            logger.warning(f"Error calculating sales velocity via SQL: {e}. Falling back to repo queries.")
            # Fallback to repo-based queries if raw SQL fails or in mocked test environments
            try:
                orders = self.sales_order_repo.list(conn=conn)
                valid_orders = {}
                for o in orders:
                    o_date_val = o.get('order_date')
                    if isinstance(o_date_val, str):
                        try:
                            o_date = datetime.strptime(o_date_val, '%Y-%m-%d').date()
                        except ValueError:
                            o_date = ref_date
                    elif isinstance(o_date_val, (datetime, date)):
                        o_date = o_date_val if isinstance(o_date_val, date) else o_date_val.date()
                    else:
                        o_date = ref_date

                    if o.get('status') not in ('Cancelled', 'Draft') and cutoff_date <= o_date <= ref_date:
                        valid_orders[o['id']] = o

                lines = self.sales_line_repo.list(conn=conn)
                for line in lines:
                    p_id = line.get('product_id')
                    if product_id is not None and p_id != product_id:
                        continue
                    if line.get('sales_order_id') in valid_orders:
                        if p_id not in velocities:
                            velocities[p_id] = {'daily_velocity': 0.0, 'total_sold': 0.0, 'order_count': 0, 'days': days}
                        velocities[p_id]['total_sold'] += float(line.get('qty', 0.0) or 0.0)

                for p_id, data in velocities.items():
                    data['daily_velocity'] = round(data['total_sold'] / float(days), 4) if days > 0 else 0.0
            except Exception as inner_e:
                logger.error(f"Fallback velocity calculation failed: {inner_e}")
        finally:
            if should_release:
                release_connection(conn)

        if product_id is not None and product_id not in velocities:
            velocities[product_id] = {
                'daily_velocity': 0.0,
                'total_sold': 0.0,
                'order_count': 0,
                'days': days,
            }

        return velocities

    def get_stock_levels(
        self,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        conn=None,
    ) -> Dict[int, Dict[str, float]]:
        should_release = False
        stocks: Dict[int, Dict[str, float]] = {}

        try:
            if conn is None:
                conn = get_connection()
                should_release = True
            sql_stock = f"""

                SELECT
                    product_id,
                    COALESCE(SUM(qty), 0) AS total_qty,
                    COALESCE(SUM(reserved_qty), 0) AS total_reserved_qty,
                    COALESCE(MAX(reorder_level), 0) AS reorder_level
                FROM "{self.schema}".t0009
                WHERE 1=1
                  {f'AND product_id = %s' if product_id is not None else ''}
                  {f'AND warehouse_id = %s' if warehouse_id is not None else ''}
                GROUP BY product_id
            """
            params_stock = []
            if product_id is not None:
                params_stock.append(product_id)
            if warehouse_id is not None:
                params_stock.append(warehouse_id)

            sql_so = f"""

                SELECT
                    l.product_id,
                    COALESCE(SUM(l.qty), 0) AS pending_so_reserved
                FROM "{self.schema}".t0013 l
                JOIN "{self.schema}".t0012 o ON l.sales_order_id = o.id
                WHERE o.status IN ('Pending', 'Confirmed', 'Processing', 'Credit Hold')
                  {f'AND l.product_id = %s' if product_id is not None else ''}
                  {f'AND o.warehouse_id = %s' if warehouse_id is not None else ''}
                GROUP BY l.product_id
            """
            params_so = []
            if product_id is not None:
                params_so.append(product_id)
            if warehouse_id is not None:
                params_so.append(warehouse_id)

            so_reserved_map: Dict[int, float] = {}
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                try:
                    cur.execute(sql_so, params_so)
                    for row in cur.fetchall():
                        so_reserved_map[row['product_id']] = float(row['pending_so_reserved'] or 0.0)
                except Exception as so_err:
                    logger.warning(f"Error querying pending sales order reservations via SQL: {so_err}")

                cur.execute(sql_stock, params_stock)
                rows = cur.fetchall()
                for row in rows:
                    p_id = row['product_id']
                    qty = float(row['total_qty'] or 0.0)
                    t0009_reserved = float(row['total_reserved_qty'] or 0.0)
                    so_reserved = so_reserved_map.get(p_id, 0.0)
                    reserved = max(t0009_reserved, so_reserved)
                    avail = max(0.0, qty - reserved)
                    reorder_lvl = float(row['reorder_level'] or 0.0)
                    stocks[p_id] = {
                        'current_stock': qty,
                        'reserved_qty': reserved,
                        'available_stock': avail,
                        'reorder_level': reorder_lvl,
                    }

                for p_id, so_res in so_reserved_map.items():
                    if p_id not in stocks:
                        if product_id is not None and p_id != product_id:
                            continue
                        stocks[p_id] = {
                            'current_stock': 0.0,
                            'reserved_qty': so_res,
                            'available_stock': 0.0,
                            'reorder_level': 0.0,
                        }
        except Exception as e:
            logger.warning(f"Error querying stock levels via SQL: {e}. Falling back to repo.")
            try:
                filters = {}
                if product_id is not None:
                    filters['product_id'] = product_id
                if warehouse_id is not None:
                    filters['warehouse_id'] = warehouse_id

                so_reserved_map: Dict[int, float] = {}
                try:
                    orders = self.sales_order_repo.list(conn=conn)
                    pending_order_ids = set()
                    for o in orders:
                        if o.get('status') in ('Pending', 'Confirmed', 'Processing', 'Credit Hold'):
                            if warehouse_id is None or o.get('warehouse_id') == warehouse_id:
                                pending_order_ids.add(o.get('id'))
                    if pending_order_ids:
                        lines = self.sales_line_repo.list(conn=conn)
                        for line in lines:
                            so_id = line.get('sales_order_id')
                            p_id = line.get('product_id')
                            if so_id in pending_order_ids:
                                if product_id is None or p_id == product_id:
                                    so_reserved_map[p_id] = so_reserved_map.get(p_id, 0.0) + float(line.get('qty', 0.0) or 0.0)
                except Exception as repo_so_e:
                    logger.warning(f"Fallback pending sales order query failed: {repo_so_e}")

                stock_rows = self.stock_repo.list(filters=filters, conn=conn)
                for s in stock_rows:
                    p_id = s.get('product_id')
                    if p_id not in stocks:
                        stocks[p_id] = {
                            'current_stock': 0.0,
                            'reserved_qty': 0.0,
                            'available_stock': 0.0,
                            'reorder_level': 0.0,
                        }
                    qty = float(s.get('qty', 0.0) or 0.0)
                    reserved = float(s.get('reserved_qty', 0.0) or 0.0)
                    reorder = float(s.get('reorder_level', 0.0) or 0.0)
                    stocks[p_id]['current_stock'] += qty
                    stocks[p_id]['reserved_qty'] += reserved
                    stocks[p_id]['reorder_level'] = max(stocks[p_id]['reorder_level'], reorder)

                for p_id, so_res in so_reserved_map.items():
                    if p_id not in stocks:
                        stocks[p_id] = {
                            'current_stock': 0.0,
                            'reserved_qty': so_res,
                            'available_stock': 0.0,
                            'reorder_level': 0.0,
                        }
                    else:
                        stocks[p_id]['reserved_qty'] = max(stocks[p_id]['reserved_qty'], so_res)

                for p_id, data in stocks.items():
                    data['available_stock'] = max(0.0, data['current_stock'] - data['reserved_qty'])

            except Exception as inner_e:
                logger.error(f"Fallback stock query failed: {inner_e}")
        finally:
            if should_release:
                release_connection(conn)

        if product_id is not None and product_id not in stocks:
            stocks[product_id] = {
                'current_stock': 0.0,
                'reserved_qty': 0.0,
                'available_stock': 0.0,
                'reorder_level': 0.0,
            }

        return stocks

    def get_preferred_supplier(self, product_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieve the preferred or primary supplier mapping from T0103 joined with T0011."""
        should_release = False

        try:
            if conn is None:
                conn = get_connection()
                should_release = True
            sql = f"""

                SELECT
                    ps.id AS mapping_id,
                    ps.product_id,
                    ps.supplier_id,
                    s.name AS supplier_name,
                    ps.supplier_sku,
                    COALESCE(ps.unit_cost, 0) AS unit_cost,
                    COALESCE(ps.lead_time_days, 0) AS lead_time_days,
                    COALESCE(ps.min_order_qty, 1) AS min_order_qty,
                    ps.is_preferred
                FROM "{self.schema}".t0103 ps
                LEFT JOIN "{self.schema}".t0011 s ON ps.supplier_id = s.id
                WHERE ps.product_id = %s AND ps.is_active = TRUE
                ORDER BY ps.is_preferred DESC, ps.id ASC
                LIMIT 1
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (product_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.warning(f"Error querying supplier mapping via SQL: {e}. Falling back to repo.")
            try:
                mappings = self.product_supplier_repo.list(filters={'product_id': product_id}, conn=conn)
                if mappings:
                    mappings.sort(key=lambda m: (not m.get('is_preferred', False), m.get('id', 0)))
                    mapping = mappings[0]
                    supplier = self.supplier_repo.get(mapping.get('supplier_id'), conn=conn) if mapping.get('supplier_id') else {}
                    return {
                        'mapping_id': mapping.get('id'),
                        'product_id': product_id,
                        'supplier_id': mapping.get('supplier_id'),
                        'supplier_name': supplier.get('name') if supplier else None,
                        'supplier_sku': mapping.get('supplier_sku'),
                        'unit_cost': float(mapping.get('unit_cost', 0.0) or 0.0),
                        'lead_time_days': int(mapping.get('lead_time_days', 0) or 0),
                        'min_order_qty': float(mapping.get('min_order_qty', 1.0) or 1.0),
                        'is_preferred': mapping.get('is_preferred', False),
                    }
            except Exception as inner_e:
                logger.error(f"Fallback supplier query failed: {inner_e}")
        finally:
            if should_release:
                release_connection(conn)

        return None

    def calculate_sku_forecast(
        self,
        product: Any,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """Calculate comprehensive demand forecast, stockout projection, restock requirement,
        and decision rationale for a single SKU.
        """
        ref_date = reference_date or date.today()

        # Resolve product data
        if isinstance(product, int):
            product_dict = self.product_repo.get(product, conn=conn) or {'id': product, 'name': f'Product #{product}', 'sku': f'SKU-{product}', 'cost_price': 0.0}
        elif isinstance(product, dict):
            product_dict = product
        else:
            raise ValueError("product must be an int or a dict")

        product_id = product_dict.get('id')
        product_name = product_dict.get('name', f'Product #{product_id}')
        sku = product_dict.get('sku', f'SKU-{product_id}')
        base_cost_price = float(product_dict.get('cost_price', 0.0) or 0.0)

        # 1. Sales Velocity
        velocities = self.calculate_sales_velocity(product_id=product_id, days=days, reference_date=ref_date, conn=conn)
        velocity_info = velocities.get(product_id, {'daily_velocity': 0.0, 'total_sold': 0.0, 'order_count': 0, 'days': days})
        daily_velocity = float(velocity_info.get('daily_velocity', 0.0))
        total_sold = float(velocity_info.get('total_sold', 0.0))

        # 2. Inventory & Stock Status
        stocks = self.get_stock_levels(product_id=product_id, warehouse_id=warehouse_id, conn=conn)
        stock_info = stocks.get(product_id, {'current_stock': 0.0, 'reserved_qty': 0.0, 'available_stock': 0.0, 'reorder_level': 0.0})
        current_stock = float(stock_info.get('current_stock', 0.0))
        reserved_qty = float(stock_info.get('reserved_qty', 0.0))
        available_stock = float(stock_info.get('available_stock', 0.0))
        reorder_level = float(stock_info.get('reorder_level', 0.0))

        # 3. Supplier Parameters & MOQ
        supplier = self.get_preferred_supplier(product_id, conn=conn)
        if supplier:
            supplier_id = supplier.get('supplier_id')
            supplier_name = supplier.get('supplier_name')
            supplier_sku = supplier.get('supplier_sku')
            lead_time_days = int(supplier.get('lead_time_days') or DEFAULT_LEAD_TIME_DAYS)
            min_order_qty = float(supplier.get('min_order_qty') or DEFAULT_MIN_ORDER_QTY)
            unit_cost = float(supplier.get('unit_cost') or base_cost_price)
        else:
            supplier_id = None
            supplier_name = None
            supplier_sku = None
            lead_time_days = DEFAULT_LEAD_TIME_DAYS
            min_order_qty = DEFAULT_MIN_ORDER_QTY
            unit_cost = base_cost_price

        # 4. Stockout Projections & Days of Inventory
        if daily_velocity > 0:
            days_of_inventory = round(available_stock / daily_velocity, 1)
            days_until_stockout = max(0, int(available_stock / daily_velocity))
            projected_stockout_date = (ref_date + timedelta(days=days_until_stockout)).isoformat()
        else:
            days_of_inventory = 999.0 if available_stock > 0 else 0.0
            projected_stockout_date = None

        # 5. Reorder Point & Safety Buffers
        lead_time_demand = daily_velocity * lead_time_days
        safety_buffer = daily_velocity * safety_margin_days
        calculated_reorder_point = lead_time_demand + safety_buffer
        reorder_point = max(reorder_level, round(calculated_reorder_point, 2))

        # 6. Restock Assessment & Suggested Order Quantity
        restock_threshold_days = lead_time_days + safety_margin_days
        needs_restock = (available_stock <= reorder_point) or (days_of_inventory <= restock_threshold_days)

        if needs_restock and (daily_velocity > 0 or available_stock <= reorder_level):
            target_stock = (daily_velocity * (lead_time_days + target_coverage_days)) + max(reorder_level, safety_buffer)
            raw_needed = max(0.0, target_stock - available_stock)
            if raw_needed <= 0.0:
                raw_needed = max(1.0, reorder_point - available_stock)

            # Enforce MOQ (Minimum Order Quantity)
            suggested_order_qty = float(math.ceil(max(raw_needed, min_order_qty)))
            estimated_cost = round(suggested_order_qty * unit_cost, 2)
        else:
            target_stock = max(reorder_level, (daily_velocity * target_coverage_days))
            suggested_order_qty = 0.0
            estimated_cost = 0.0
            needs_restock = False

        # 7. Urgency Categorization
        if not needs_restock:
            urgency = 'HEALTHY'
        elif available_stock <= 0 or (daily_velocity > 0 and days_of_inventory <= lead_time_days):
            urgency = 'CRITICAL'  # Stockout will occur before lead time arrival!
        elif daily_velocity > 0 and days_of_inventory <= (lead_time_days + 3):
            urgency = 'HIGH'
        else:
            urgency = 'MEDIUM'

        # 8. Decision Rationale Generation
        rationale = self.format_rationale(
            sku=sku,
            product_name=product_name,
            daily_velocity=daily_velocity,
            total_sold=total_sold,
            days=days,
            available_stock=available_stock,
            days_of_inventory=days_of_inventory,
            projected_stockout_date=projected_stockout_date,
            supplier_name=supplier_name,
            lead_time_days=lead_time_days,
            min_order_qty=min_order_qty,
            unit_cost=unit_cost,
            reorder_point=reorder_point,
            suggested_order_qty=suggested_order_qty,
            estimated_cost=estimated_cost,
            target_coverage_days=target_coverage_days,
            urgency=urgency,
            needs_restock=needs_restock,
        )

        return {
            'product_id': product_id,
            'product_name': product_name,
            'sku': sku,
            'warehouse_id': warehouse_id,
            'current_stock': current_stock,
            'reserved_qty': reserved_qty,
            'available_stock': available_stock,
            'net_available_stock': available_stock,
            'reorder_level': reorder_level,
            'velocity_30d': daily_velocity,
            'total_sold_30d': total_sold,
            'days_of_inventory': days_of_inventory,
            'projected_stockout_date': projected_stockout_date,
            'lead_time_days': lead_time_days,
            'safety_margin_days': safety_margin_days,
            'target_coverage_days': target_coverage_days,
            'min_order_qty': min_order_qty,
            'unit_cost': unit_cost,
            'supplier_id': supplier_id,
            'supplier_name': supplier_name,
            'supplier_sku': supplier_sku,
            'reorder_point': reorder_point,
            'target_stock': round(target_stock, 2),
            'needs_restock': needs_restock,
            'urgency': urgency,
            'suggested_order_qty': suggested_order_qty,
            'estimated_cost': estimated_cost,
            'rationale': rationale,
            'rationale_breakdown': {
                'daily_velocity': daily_velocity,
                'days_of_inventory': days_of_inventory,
                'lead_time_days': lead_time_days,
                'moq': min_order_qty,
                'reorder_point': reorder_point,
                'target_stock': round(target_stock, 2),
                'suggested_qty': suggested_order_qty,
                'unit_cost': unit_cost,
                'estimated_cost': estimated_cost,
            }
        }

    def calculate_all_forecasts(
        self,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        only_at_risk: bool = False,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Calculate forecasts for all active products across the catalog.
        Optionally filters to only products requiring restock (only_at_risk=True).
        """
        products = self.product_repo.list(conn=conn)
        results = []

        urgency_priority = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'HEALTHY': 4}

        for p in products:
            if not p.get('is_active', True):
                continue
            forecast = self.calculate_sku_forecast(
                product=p,
                warehouse_id=warehouse_id,
                days=days,
                safety_margin_days=safety_margin_days,
                target_coverage_days=target_coverage_days,
                reference_date=reference_date,
                conn=conn,
            )
            if only_at_risk and not forecast.get('needs_restock'):
                continue
            results.append(forecast)

        # Sort: most urgent first, then lowest days of inventory remaining
        results.sort(key=lambda x: (
            urgency_priority.get(x.get('urgency', 'HEALTHY'), 5),
            x.get('days_of_inventory', 999.0) if x.get('days_of_inventory') is not None else 999.0,
            -x.get('velocity_30d', 0.0)
        ))

        return results

    def get_aggregated_supplier_draft_pos(
        self,
        warehouse_id: Optional[int] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        safety_margin_days: int = DEFAULT_SAFETY_MARGIN_DAYS,
        target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
        only_at_risk: bool = True,
        reference_date: Optional[date] = None,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Group at-risk forecast recommendations into consolidated draft Purchase Orders
        by primary supplier (mapped via T0103), incorporating supplier lead times and MOQs.
        """
        ref_date = reference_date or date.today()
        forecasts = self.calculate_all_forecasts(
            warehouse_id=warehouse_id,
            days=days,
            safety_margin_days=safety_margin_days,
            target_coverage_days=target_coverage_days,
            only_at_risk=only_at_risk,
            reference_date=ref_date,
            conn=conn,
        )

        supplier_groups: Dict[Optional[int], List[Dict[str, Any]]] = {}
        for item in forecasts:
            if only_at_risk and not item.get("needs_restock"):
                continue
            sup_id = item.get("supplier_id")
            if sup_id not in supplier_groups:
                supplier_groups[sup_id] = []
            supplier_groups[sup_id].append(item)

        urgency_priority = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'HEALTHY': 4}

        result = []
        for sup_id, items in supplier_groups.items():
            supplier_name = items[0].get("supplier_name") if items and items[0].get("supplier_name") else "Unassigned Supplier"
            lead_times = [int(it.get("lead_time_days") or DEFAULT_LEAD_TIME_DAYS) for it in items]
            max_lead_time = max(lead_times) if lead_times else DEFAULT_LEAD_TIME_DAYS
            expected_date = (ref_date + timedelta(days=max_lead_time)).isoformat()

            total_items = len(items)
            total_qty = round(sum(float(it.get("suggested_order_qty") or 0.0) for it in items), 2)
            total_cost = round(sum(float(it.get("estimated_cost") or 0.0) for it in items), 2)

            max_urgency = "HEALTHY"
            min_priority = 999
            for it in items:
                urg = it.get("urgency", "HEALTHY")
                prio = urgency_priority.get(urg, 4)
                if prio < min_priority:
                    min_priority = prio
                    max_urgency = urg

            notes_lines = [f"Consolidated Draft PO for {supplier_name} ({total_items} items, max lead time: {max_lead_time} days):"]
            for it in items:
                notes_lines.append(
                    f"• {it.get('sku')} ({it.get('product_name')}): {it.get('suggested_order_qty'):.0f} units @ ${it.get('unit_cost'):.2f} (${it.get('estimated_cost'):.2f})"
                )
            po_notes = "\n".join(notes_lines)

            result.append({
                "supplier_id": sup_id,
                "supplier_name": supplier_name,
                "lead_time_days": max_lead_time,
                "expected_date": expected_date,
                "total_items": total_items,
                "total_qty": total_qty,
                "total_estimated_cost": total_cost,
                "max_urgency": max_urgency,
                "items": items,
                "po_notes": po_notes,
            })

        result.sort(key=lambda x: (
            urgency_priority.get(x.get("max_urgency", "HEALTHY"), 5),
            -x.get("total_estimated_cost", 0.0),
            x.get("supplier_name") or ""
        ))

        return result

    def format_rationale(
        self,
        sku: str,
        product_name: str,
        daily_velocity: float,
        total_sold: float,
        days: int,
        available_stock: float,
        days_of_inventory: Optional[float],
        projected_stockout_date: Optional[str],
        supplier_name: Optional[str],
        lead_time_days: int,
        min_order_qty: float,
        unit_cost: float,
        reorder_point: float,
        suggested_order_qty: float,
        estimated_cost: float,
        target_coverage_days: int,
        urgency: str,
        needs_restock: bool,
    ) -> str:
        """Construct a structured, human-readable decision rationale for restock proposals."""
        if not needs_restock:
            if daily_velocity == 0:
                return (
                    f"{sku} ({product_name}) has {available_stock:.0f} units in stock with zero sales "
                    f"over the past {days} days. Inventory is healthy; no restock needed."
                )
            return (
                f"{sku} ({product_name}) has {available_stock:.0f} units available ({days_of_inventory:.1f} days of supply) "
                f"at a daily velocity of {daily_velocity:.2f} units/day. Above reorder threshold ({reorder_point:.1f} units); "
                f"no restock needed at this time."
            )

        sup_str = f"Supplier '{supplier_name}'" if supplier_name else "Standard supplier"
        stockout_str = "stock is depleted" if available_stock <= 0 else (f"projected stockout date is {projected_stockout_date}" if projected_stockout_date else "stock is depleted")
        days_rem_str = f"{days_of_inventory:.1f} days of supply" if days_of_inventory is not None else "0 days"

        lines = [
            f"[{urgency} RESTOCK] {sku} - {product_name}:",
            f"• Demand Velocity: {daily_velocity:.2f} units/day ({total_sold:.0f} sold in last {days} days).",
            f"• Inventory: {available_stock:.0f} units available ({days_rem_str}). With {lead_time_days}-day supplier lead time, {stockout_str}.",
            f"• Supplier Terms: {sup_str} has {lead_time_days}-day lead time, unit cost of ${unit_cost:.2f}, and MOQ of {min_order_qty:.0f} units.",
            f"• Recommendation: Order {suggested_order_qty:.0f} units to reach {target_coverage_days} days target stock buffer (estimated total: ${estimated_cost:.2f})."
        ]

        if suggested_order_qty == min_order_qty and min_order_qty > (daily_velocity * target_coverage_days):
            lines.append(f"• Note: Order quantity adjusted up to meet supplier Minimum Order Quantity ({min_order_qty:.0f} units).")

        return "\n".join(lines)
