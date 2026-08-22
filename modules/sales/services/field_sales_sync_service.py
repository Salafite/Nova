import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
import psycopg2.extras

from packages.database.connection import get_connection, release_connection
from modules.sales.models.field_sales import (
    ConflictResolutionItem,
    ConflictType,
    FieldSalesBatchSyncRequest,
    FieldSalesBatchSyncResponse,
    FieldSalesOrderLine,
    FieldSalesOrderSubmission,
    FieldSalesResolveConflictRequest,
    FieldSalesValidationRequest,
    FieldSalesValidationResponse,
    LineConflictDetail,
    OrderSyncResult,
    ResolutionAction,
    SyncStatus,
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


def _get_utc_now() -> datetime:
    """Return current UTC timezone-aware datetime."""
    return datetime.now(timezone.utc)


class FieldSalesSyncService:
    """Service to process offline sales order batches, verify idempotency,

    detect and report stock/pricing conflicts, and atomically synchronize orders.
    """

    def __init__(self, schema: Optional[str] = None):
        self.schema = schema or os.getenv("DB_SCHEMA", "Nova")

    def _get_table(self, table_name: str) -> str:
        return f'"{self.schema}".{table_name.lower()}'

    # -------------------------------------------------------------------------
    # Batch Order Synchronization
    # -------------------------------------------------------------------------

    def sync_batch(
        self,
        request: Union[FieldSalesBatchSyncRequest, Dict[str, Any]],
        conn=None,
    ) -> FieldSalesBatchSyncResponse:
        """Process a batch of offline orders with idempotency checks and atomic transaction isolation per order."""
        if isinstance(request, dict):
            req_obj = FieldSalesBatchSyncRequest(**request)
        else:
            req_obj = request

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        results: List[OrderSyncResult] = []
        synced_count = 0
        conflict_count = 0
        failed_count = 0

        try:
            for order_sub in req_obj.orders:
                try:
                    result = self._sync_single_order_transaction(order_sub, conn=conn)
                    results.append(result)

                    if result.status in (SyncStatus.SYNCED.value, "AlreadySynced"):
                        if result.status == SyncStatus.SYNCED.value:
                            synced_count += 1
                    elif result.status == SyncStatus.CONFLICT.value:
                        conflict_count += 1
                    elif result.status == SyncStatus.FAILED.value:
                        failed_count += 1
                    else:
                        synced_count += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error synchronizing order {order_sub.client_order_uuid}: {e}",
                        exc_info=True,
                    )
                    failed_count += 1
                    results.append(
                        OrderSyncResult(
                            client_order_uuid=order_sub.client_order_uuid,
                            status=SyncStatus.FAILED.value,
                            message=f"Sync error: {str(e)}",
                        )
                    )

            overall_success = (failed_count == 0 and conflict_count == 0)

            return FieldSalesBatchSyncResponse(
                success=overall_success,
                synced_count=synced_count,
                conflict_count=conflict_count,
                failed_count=failed_count,
                results=results,
                sync_timestamp=_get_utc_now(),
                message=f"Processed {len(req_obj.orders)} orders: {synced_count} synced, {conflict_count} conflicts, {failed_count} failed",
            )
        finally:
            if should_release:
                release_connection(conn)

    def _sync_single_order_transaction(
        self,
        order: FieldSalesOrderSubmission,
        conn,
    ) -> OrderSyncResult:
        """Process a single order within an isolated sub-transaction/savepoint."""
        # 1. Idempotency Check: check if client_order_uuid already exists in t0012
        existing = self.find_order_by_uuid(order.client_order_uuid, conn=conn)
        if existing:
            logger.info(
                f"Idempotency hit: Order {order.client_order_uuid} already synced as order #{existing.get('order_number')} (ID {existing.get('id')})"
            )
            return OrderSyncResult(
                client_order_uuid=order.client_order_uuid,
                server_order_id=existing.get("id"),
                order_number=existing.get("order_number"),
                status="AlreadySynced",
                is_duplicate=True,
                subtotal=_to_float(existing.get("subtotal")),
                tax=_to_float(existing.get("tax")),
                grand_total=_to_float(existing.get("grand_total")),
                message="Order was already synchronized successfully.",
            )

        # 2. Stock and Pricing Conflict Check
        conflicts = self.check_order_conflicts(order, conn=conn)
        if conflicts:
            logger.warning(
                f"Conflicts detected for order {order.client_order_uuid}: {len(conflicts)} conflict(s)"
            )
            return OrderSyncResult(
                client_order_uuid=order.client_order_uuid,
                status=SyncStatus.CONFLICT.value,
                is_duplicate=False,
                conflicts=conflicts,
                message=f"Detected {len(conflicts)} stock or pricing conflict(s). Resolution required.",
            )

        # 3. Create the Order Atomically
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Resolve warehouse
                warehouse_id = order.warehouse_id
                if not warehouse_id:
                    warehouse_id = self._resolve_default_warehouse_id(cur)

                # Resolve totals and taxes
                calculated = self._calculate_order_totals(
                    lines=order.lines,
                    tax_rate_id=order.tax_rate_id,
                    customer_id=order.customer_id,
                    cur=cur,
                )
                subtotal = calculated["subtotal"]
                tax = calculated["tax"]
                grand_total = calculated["grand_total"]

                # Generate Order Number
                order_number = order.order_number
                if not order_number or self._is_order_number_taken(order_number, cur):
                    order_number = self._generate_order_number(cur, order_date=order.order_date)

                order_date = order.order_date or date.today()
                offline_created_at = order.offline_created_at or _get_utc_now()

                # Insert into T0012 (Sales Orders)
                cur.execute(
                    f"""
                    INSERT INTO {self._get_table("t0012")} (
                        order_number, customer_id, warehouse_id, subtotal, tax, grand_total,
                        status, order_date, notes, price_list_id, tax_rate_id, payment_term_id,
                        client_order_uuid, is_offline_sync, sync_status, offline_created_at, sales_rep_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'Pending', %s, %s, %s, %s, %s, %s, true, 'Synced', %s, %s)
                    RETURNING id
                    """,
                    (
                        order_number,
                        order.customer_id,
                        warehouse_id,
                        subtotal,
                        tax,
                        grand_total,
                        order_date,
                        order.notes,
                        order.price_list_id,
                        order.tax_rate_id,
                        order.payment_term_id,
                        order.client_order_uuid,
                        offline_created_at,
                        order.sales_rep_id,
                    ),
                )
                created_row = cur.fetchone()
                order_id = created_row["id"]

                # Insert lines into T0013 (Sales Order Lines)
                for line in order.lines:
                    line_total = round(line.qty * line.unit_price * (1.0 - (line.discount_pct or 0.0) / 100.0), 2)
                    cur.execute(
                        f"""
                        INSERT INTO {self._get_table("t0013")} (
                            sales_order_id, product_id, product_name, uom_id, qty, unit_price, line_total, line_number
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            line.product_id,
                            line.product_name,
                            line.uom_id,
                            line.qty,
                            line.unit_price,
                            line_total,
                            line.line_number,
                        ),
                    )

                # Deduct inventory stock in T0009 and record movement in T0064
                if warehouse_id:
                    for line in order.lines:
                        self._deduct_stock_and_record_movement(
                            cur=cur,
                            product_id=line.product_id,
                            warehouse_id=warehouse_id,
                            qty=line.qty,
                            order_id=order_id,
                            order_number=order_number,
                        )

                # Update Customer Balance in T0010
                cur.execute(
                    f"""
                    UPDATE {self._get_table("t0010")}
                    SET balance = balance + %s
                    WHERE id = %s
                    """,
                    (grand_total, order.customer_id),
                )

            conn.commit()
            logger.info(
                f"Successfully synced offline order {order.client_order_uuid} -> ID {order_id} ({order_number})"
            )

            return OrderSyncResult(
                client_order_uuid=order.client_order_uuid,
                server_order_id=order_id,
                order_number=order_number,
                status=SyncStatus.SYNCED.value,
                is_duplicate=False,
                subtotal=subtotal,
                tax=tax,
                grand_total=grand_total,
                message="Order synchronized successfully.",
            )
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.error(
                f"Failed to commit order {order.client_order_uuid}: {e}", exc_info=True
            )
            return OrderSyncResult(
                client_order_uuid=order.client_order_uuid,
                status=SyncStatus.FAILED.value,
                is_duplicate=False,
                message=f"Failed to create order: {str(e)}",
            )

    # -------------------------------------------------------------------------
    # Pre-Sync Validation
    # -------------------------------------------------------------------------

    def validate_batch(
        self,
        request: Union[FieldSalesValidationRequest, Dict[str, Any]],
        conn=None,
    ) -> FieldSalesValidationResponse:
        """Validate offline orders without modifying the database, checking idempotency and stock availability."""
        if isinstance(request, dict):
            req_obj = FieldSalesValidationRequest(**request)
        else:
            req_obj = request

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            results: List[OrderSyncResult] = []
            conflicts_count = 0

            for order_sub in req_obj.orders:
                # 1. Idempotency Check
                existing = self.find_order_by_uuid(order_sub.client_order_uuid, conn=conn)
                if existing:
                    results.append(
                        OrderSyncResult(
                            client_order_uuid=order_sub.client_order_uuid,
                            server_order_id=existing.get("id"),
                            order_number=existing.get("order_number"),
                            status="AlreadySynced",
                            is_duplicate=True,
                            subtotal=_to_float(existing.get("subtotal")),
                            tax=_to_float(existing.get("tax")),
                            grand_total=_to_float(existing.get("grand_total")),
                            message="Order was already synchronized.",
                        )
                    )
                    continue

                # 2. Conflict Check
                conflicts = self.check_order_conflicts(order_sub, conn=conn)
                if conflicts:
                    conflicts_count += 1
                    results.append(
                        OrderSyncResult(
                            client_order_uuid=order_sub.client_order_uuid,
                            status=SyncStatus.CONFLICT.value,
                            is_duplicate=False,
                            conflicts=conflicts,
                            message=f"{len(conflicts)} conflict(s) found.",
                        )
                    )
                else:
                    results.append(
                        OrderSyncResult(
                            client_order_uuid=order_sub.client_order_uuid,
                            status="Valid",
                            is_duplicate=False,
                            message="Order is valid and ready to sync.",
                        )
                    )

            is_valid = (conflicts_count == 0)
            return FieldSalesValidationResponse(
                valid=is_valid,
                total_orders=len(req_obj.orders),
                conflicts_found=conflicts_count,
                results=results,
            )
        finally:
            if should_release:
                release_connection(conn)

    # -------------------------------------------------------------------------
    # Conflict Detection Engine
    # -------------------------------------------------------------------------

    def check_order_conflicts(
        self,
        order: FieldSalesOrderSubmission,
        conn=None,
    ) -> List[LineConflictDetail]:
        """Inspect order against live database state for stock depletion, inactive customer, or price rules."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            conflicts: List[LineConflictDetail] = []

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 1. Customer verification
                cur.execute(
                    f"""
                    SELECT id, name, is_active, credit_limit, balance
                    FROM {self._get_table("t0010")}
                    WHERE id = %s
                    """,
                    (order.customer_id,),
                )
                customer = cur.fetchone()

                if not customer:
                    conflicts.append(
                        LineConflictDetail(
                            line_number=0,
                            product_id=0,
                            product_name="N/A",
                            conflict_type=ConflictType.CUSTOMER_INACTIVE.value,
                            requested_qty=0.0,
                            available_qty=0.0,
                            message=f"Customer with ID {order.customer_id} does not exist.",
                            suggested_action=ResolutionAction.REMOVE_ITEM.value,
                        )
                    )
                elif not customer.get("is_active", True):
                    conflicts.append(
                        LineConflictDetail(
                            line_number=0,
                            product_id=0,
                            product_name="N/A",
                            conflict_type=ConflictType.CUSTOMER_INACTIVE.value,
                            requested_qty=0.0,
                            available_qty=0.0,
                            message=f"Customer '{customer.get('name')}' is currently inactive.",
                            suggested_action=ResolutionAction.REMOVE_ITEM.value,
                        )
                    )
                else:
                    # Check credit limit
                    credit_limit = _to_float(customer.get("credit_limit", 0.0))
                    balance = _to_float(customer.get("balance", 0.0))
                    if credit_limit > 0 and (balance + (order.grand_total or 0.0)) > credit_limit:
                        available_credit = max(0.0, credit_limit - balance)
                        conflicts.append(
                            LineConflictDetail(
                                line_number=0,
                                product_id=0,
                                product_name="N/A",
                                conflict_type=ConflictType.CREDIT_LIMIT_EXCEEDED.value,
                                requested_qty=0.0,
                                available_qty=0.0,
                                message=f"Order total exceeds credit limit for '{customer.get('name')}'. Limit: {credit_limit}, Current Balance: {balance}, Available: {available_credit}.",
                                suggested_action=ResolutionAction.ADJUST_QTY.value,
                            )
                        )

                # 2. Line Item & Stock Verification
                warehouse_id = order.warehouse_id
                price_list_id = order.price_list_id

                for line in order.lines:
                    pid = line.product_id

                    # Fetch product details
                    cur.execute(
                        f"""
                        SELECT id, name, sku, price, category, is_active
                        FROM {self._get_table("t0003")}
                        WHERE id = %s
                        """,
                        (pid,),
                    )
                    product = cur.fetchone()

                    if not product or not product.get("is_active", True):
                        # Product deleted or inactive
                        substitutes = self.get_suggested_substitutes(
                            product_id=pid,
                            category=product.get("category") if product else None,
                            warehouse_id=warehouse_id,
                            limit=3,
                            conn=conn,
                        )
                        conflicts.append(
                            LineConflictDetail(
                                line_number=line.line_number,
                                product_id=pid,
                                product_name=line.product_name,
                                conflict_type=ConflictType.OUT_OF_STOCK.value,
                                requested_qty=line.qty,
                                available_qty=0.0,
                                requested_price=line.unit_price,
                                current_price=_to_float(product.get("price")) if product else None,
                                message=f"Product '{line.product_name}' is no longer active in catalog.",
                                suggested_action=ResolutionAction.SUBSTITUTE.value,
                                suggested_substitutes=substitutes,
                            )
                        )
                        continue

                    # Check available stock in T0009
                    if warehouse_id is not None:
                        cur.execute(
                            f"""
                            SELECT qty FROM {self._get_table("t0009")}
                            WHERE product_id = %s AND warehouse_id = %s
                            """,
                            (pid, warehouse_id),
                        )
                        stock_row = cur.fetchone()
                        avail_qty = _to_float(stock_row.get("qty", 0.0)) if stock_row else 0.0
                    else:
                        cur.execute(
                            f"""
                            SELECT SUM(qty) AS total_qty FROM {self._get_table("t0009")}
                            WHERE product_id = %s
                            """,
                            (pid,),
                        )
                        stock_row = cur.fetchone()
                        if stock_row and isinstance(stock_row, dict):
                            avail_qty = _to_float(stock_row.get("total_qty", stock_row.get("qty", 0.0)))
                        else:
                            avail_qty = 0.0

                    if avail_qty <= 0.0:
                        substitutes = self.get_suggested_substitutes(
                            product_id=pid,
                            category=product.get("category"),
                            warehouse_id=warehouse_id,
                            limit=3,
                            conn=conn,
                        )
                        conflicts.append(
                            LineConflictDetail(
                                line_number=line.line_number,
                                product_id=pid,
                                product_name=line.product_name,
                                conflict_type=ConflictType.OUT_OF_STOCK.value,
                                requested_qty=line.qty,
                                available_qty=0.0,
                                requested_price=line.unit_price,
                                current_price=_to_float(product.get("price")),
                                message=f"Product '{line.product_name}' (SKU: {line.sku or pid}) is out of stock.",
                                suggested_action=ResolutionAction.SUBSTITUTE.value,
                                suggested_substitutes=substitutes,
                            )
                        )
                    elif avail_qty < line.qty:
                        substitutes = self.get_suggested_substitutes(
                            product_id=pid,
                            category=product.get("category"),
                            warehouse_id=warehouse_id,
                            limit=3,
                            conn=conn,
                        )
                        conflicts.append(
                            LineConflictDetail(
                                line_number=line.line_number,
                                product_id=pid,
                                product_name=line.product_name,
                                conflict_type=ConflictType.INSUFFICIENT_QTY.value,
                                requested_qty=line.qty,
                                available_qty=avail_qty,
                                requested_price=line.unit_price,
                                current_price=_to_float(product.get("price")),
                                message=f"Insufficient stock for '{line.product_name}'. Requested {line.qty}, only {avail_qty} available.",
                                suggested_action=ResolutionAction.ADJUST_QTY.value,
                                suggested_substitutes=substitutes,
                            )
                        )

                    # 3. Price check if price list is configured
                    if price_list_id:
                        cur.execute(
                            f"""
                            SELECT unit_price FROM {self._get_table("t0084")}
                            WHERE price_list_id = %s AND product_id = %s AND is_active = true
                            LIMIT 1
                            """,
                            (price_list_id, pid),
                        )
                        pr_row = cur.fetchone()
                        if pr_row:
                            rule_price = _to_float(pr_row["unit_price"])
                            if abs(rule_price - line.unit_price) > 0.01:
                                conflicts.append(
                                    LineConflictDetail(
                                        line_number=line.line_number,
                                        product_id=pid,
                                        product_name=line.product_name,
                                        conflict_type=ConflictType.PRICE_MISMATCH.value,
                                        requested_qty=line.qty,
                                        available_qty=avail_qty,
                                        requested_price=line.unit_price,
                                        current_price=rule_price,
                                        message=f"Price mismatch for '{line.product_name}'. Submitted: {line.unit_price}, contracted price: {rule_price}.",
                                        suggested_action=ResolutionAction.ACCEPT_PRICE.value,
                                    )
                                )

            return conflicts
        finally:
            if should_release:
                release_connection(conn)

    # -------------------------------------------------------------------------
    # Suggested Substitutes
    # -------------------------------------------------------------------------

    def get_suggested_substitutes(
        self,
        product_id: int,
        category: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        limit: int = 3,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """Find active alternative products in the same category that currently have available stock."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # If category is not provided, look it up
                if not category:
                    cur.execute(
                        f'SELECT category FROM {self._get_table("t0003")} WHERE id = %s',
                        (product_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        category = row.get("category")

                if not category:
                    return []

                # Query products in the same category with positive stock
                if warehouse_id is not None:
                    cur.execute(
                        f"""
                        SELECT p.id, p.name, p.sku, p.price, COALESCE(s.qty, 0) AS available_qty
                        FROM {self._get_table("t0003")} p
                        JOIN {self._get_table("t0009")} s ON s.product_id = p.id AND s.warehouse_id = %s
                        WHERE p.category = %s AND p.id != %s AND p.is_active = true AND s.qty > 0
                        ORDER BY s.qty DESC, p.name ASC
                        LIMIT %s
                        """,
                        (warehouse_id, category, product_id, limit),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT p.id, p.name, p.sku, p.price, SUM(s.qty) AS available_qty
                        FROM {self._get_table("t0003")} p
                        JOIN {self._get_table("t0009")} s ON s.product_id = p.id
                        WHERE p.category = %s AND p.id != %s AND p.is_active = true
                        GROUP BY p.id, p.name, p.sku, p.price
                        HAVING SUM(s.qty) > 0
                        ORDER BY SUM(s.qty) DESC, p.name ASC
                        LIMIT %s
                        """,
                        (category, product_id, limit),
                    )

                substitutes = []
                for r in cur.fetchall():
                    substitutes.append(
                        {
                            "id": r["id"],
                            "product_id": r["id"],
                            "name": r["name"],
                            "product_name": r["name"],
                            "sku": r.get("sku"),
                            "price": _to_float(r.get("price", 0.0)),
                            "available_qty": _to_float(r.get("available_qty", 0.0)),
                        }
                    )
                return substitutes
        except Exception as e:
            logger.warning(f"Error fetching substitutes for product {product_id}: {e}")
            return []
        finally:
            if should_release:
                release_connection(conn)

    # -------------------------------------------------------------------------
    # Conflict Resolution & Immediate Synchronization
    # -------------------------------------------------------------------------

    def resolve_and_sync(
        self,
        request: Union[FieldSalesResolveConflictRequest, Dict[str, Any]],
        conn=None,
    ) -> OrderSyncResult:
        """Apply user-selected conflict resolutions (adjust_qty, substitute, remove_item, accept_price) and sync."""
        if isinstance(request, dict):
            req_obj = FieldSalesResolveConflictRequest(**request)
        else:
            req_obj = request

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            order_data = req_obj.order_data
            resolutions_map: Dict[int, ConflictResolutionItem] = {
                res.line_number: res for res in req_obj.resolutions
            }

            resolved_lines: List[FieldSalesOrderLine] = []

            for line in order_data.lines:
                res = resolutions_map.get(line.line_number)
                if not res:
                    resolved_lines.append(line)
                    continue

                action = res.action.lower()

                if action == ResolutionAction.REMOVE_ITEM.value:
                    # Skip this line completely
                    continue
                elif action == ResolutionAction.ADJUST_QTY.value:
                    new_qty = res.adjusted_qty if res.adjusted_qty is not None else line.qty
                    if new_qty > 0:
                        new_line = line.model_copy(update={
                            "qty": new_qty,
                            "line_total": round(new_qty * line.unit_price * (1.0 - (line.discount_pct or 0.0) / 100.0), 2)
                        })
                        resolved_lines.append(new_line)
                elif action == ResolutionAction.SUBSTITUTE.value:
                    sub_id = res.substitute_product_id or line.product_id
                    sub_name = res.substitute_product_name or line.product_name

                    # Fetch substitute product base price if needed
                    sub_price = line.unit_price
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(
                            f'SELECT name, sku, price FROM {self._get_table("t0003")} WHERE id = %s',
                            (sub_id,),
                        )
                        sub_prod = cur.fetchone()
                        if sub_prod:
                            sub_name = sub_prod["name"]
                            sub_price = _to_float(sub_prod["price"])

                    qty = res.adjusted_qty if res.adjusted_qty is not None else line.qty
                    new_line = line.model_copy(update={
                        "product_id": sub_id,
                        "product_name": sub_name,
                        "unit_price": sub_price,
                        "qty": qty,
                        "line_total": round(qty * sub_price * (1.0 - (line.discount_pct or 0.0) / 100.0), 2),
                    })
                    resolved_lines.append(new_line)
                elif action == ResolutionAction.ACCEPT_PRICE.value:
                    new_price = res.accepted_price if res.accepted_price is not None else line.unit_price
                    new_line = line.model_copy(update={
                        "unit_price": new_price,
                        "line_total": round(line.qty * new_price * (1.0 - (line.discount_pct or 0.0) / 100.0), 2),
                    })
                    resolved_lines.append(new_line)
                elif action == ResolutionAction.BACKORDER.value:
                    # Keep requested quantity and mark notes
                    notes = f"[BACKORDER] {line.notes or ''}".strip()
                    new_line = line.model_copy(update={"notes": notes})
                    resolved_lines.append(new_line)
                else:
                    resolved_lines.append(line)

            if not resolved_lines:
                return OrderSyncResult(
                    client_order_uuid=order_data.client_order_uuid,
                    status=SyncStatus.FAILED.value,
                    message="All line items were removed during conflict resolution. Order cannot be empty.",
                )

            # Re-index line numbers
            for idx, line in enumerate(resolved_lines, start=1):
                line.line_number = idx

            # Update order submission with resolved lines
            resolved_order = order_data.model_copy(update={"lines": resolved_lines})

            # Sync the resolved order
            return self._sync_single_order_transaction(resolved_order, conn=conn)
        finally:
            if should_release:
                release_connection(conn)

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def find_order_by_uuid(self, client_order_uuid: str, conn=None) -> Optional[Dict[str, Any]]:
        """Look up an existing sales order by its client-generated UUID."""
        if not client_order_uuid:
            return None

        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, order_number, customer_id, warehouse_id, subtotal, tax, grand_total,
                           status, order_date, sync_status, client_order_uuid
                    FROM {self._get_table("t0012")}
                    WHERE client_order_uuid = %s
                    LIMIT 1
                    """,
                    (client_order_uuid,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def _resolve_default_warehouse_id(self, cur) -> Optional[int]:
        """Look up the first active warehouse to use as default."""
        cur.execute(
            f"""
            SELECT id FROM {self._get_table("t0008")}
            WHERE is_active = true
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        return row["id"] if row else 1

    def _is_order_number_taken(self, order_number: str, cur) -> bool:
        """Check if an order_number already exists in t0012."""
        cur.execute(
            f'SELECT 1 FROM {self._get_table("t0012")} WHERE order_number = %s LIMIT 1',
            (order_number,),
        )
        return cur.fetchone() is not None

    def _generate_order_number(self, cur, order_date: Optional[date] = None, prefix: str = "FSO") -> str:
        """Generate a sequential, date-formatted order number (e.g. FSO-20260822-0001)."""
        d = order_date or date.today()
        today_str = d.strftime("%Y%m%d")
        pattern = f"{prefix}-{today_str}-%"

        cur.execute(
            f'SELECT COUNT(*) AS cnt FROM {self._get_table("t0012")} WHERE order_number LIKE %s',
            (pattern,),
        )
        row = cur.fetchone()
        count = (row["cnt"] if row and "cnt" in row else 0) + 1
        return f"{prefix}-{today_str}-{count:04d}"

    def _calculate_order_totals(
        self,
        lines: List[FieldSalesOrderLine],
        tax_rate_id: Optional[int],
        customer_id: Optional[int],
        cur,
    ) -> Dict[str, float]:
        """Compute subtotal, tax rate, and grand total."""
        subtotal = 0.0
        for line in lines:
            discount = line.discount_pct or 0.0
            line_tot = round(line.qty * line.unit_price * (1.0 - discount / 100.0), 2)
            subtotal += line_tot
        subtotal = round(subtotal, 2)

        # Lookup tax rate
        tax_rate_pct = 0.0
        if tax_rate_id:
            cur.execute(
                f'SELECT rate FROM {self._get_table("t0085")} WHERE id = %s',
                (tax_rate_id,),
            )
            tr = cur.fetchone()
            if tr:
                tax_rate_pct = _to_float(tr.get("rate", 0.0))
        elif customer_id:
            cur.execute(
                f"""
                SELECT tr.rate
                FROM {self._get_table("t0010")} c
                LEFT JOIN {self._get_table("t0085")} tr ON tr.id = c.default_tax_rate_id
                WHERE c.id = %s
                """,
                (customer_id,),
            )
            cr = cur.fetchone()
            if cr and cr.get("rate") is not None:
                tax_rate_pct = _to_float(cr["rate"])

        tax = round(subtotal * (tax_rate_pct / 100.0), 2)
        grand_total = round(subtotal + tax, 2)

        return {
            "subtotal": subtotal,
            "tax": tax,
            "grand_total": grand_total,
            "tax_rate_pct": tax_rate_pct,
        }

    def _deduct_stock_and_record_movement(
        self,
        cur,
        product_id: int,
        warehouse_id: int,
        qty: float,
        order_id: int,
        order_number: str,
    ) -> None:
        """Atomically deduct stock from T0009 and record movement in T0064."""
        cur.execute(
            f"""
            SELECT id, qty FROM {self._get_table("t0009")}
            WHERE product_id = %s AND warehouse_id = %s
            FOR UPDATE
            """,
            (product_id, warehouse_id),
        )
        stock_row = cur.fetchone()

        if stock_row:
            current_qty = _to_float(stock_row["qty"])
            new_balance = max(0.0, current_qty - qty)
            cur.execute(
                f'UPDATE {self._get_table("t0009")} SET qty = %s WHERE id = %s',
                (new_balance, stock_row["id"]),
            )
        else:
            new_balance = 0.0
            cur.execute(
                f"""
                INSERT INTO {self._get_table("t0009")} (product_id, warehouse_id, qty)
                VALUES (%s, %s, %s)
                """,
                (product_id, warehouse_id, new_balance),
            )

        # Record movement in T0064
        cur.execute(
            f"""
            INSERT INTO {self._get_table("t0064")} (
                product_id, warehouse_id, movement_type, reference_type,
                reference_id, qty_change, balance_after, description
            )
            VALUES (%s, %s, 'Sale', 'sales_order', %s, %s, %s, %s)
            """,
            (
                product_id,
                warehouse_id,
                order_id,
                -qty,
                new_balance,
                f"Field Sales Order #{order_number}",
            ),
        )


field_sales_sync_service = FieldSalesSyncService()
