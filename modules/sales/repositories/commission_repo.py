import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)


class CommissionRepository:
    """
    Repository for Sales Commission calculation rules (Nova.t0109), payout ledgers (Nova.t0110),
    and invoice collection / realized gross margin queries.
    """

    def __init__(self):
        self.schema = os.getenv('DB_SCHEMA', 'Nova')
        self.rule_repo = CrudRepository(
            'T0109',
            pk='id',
            business_columns=[
                'id',
                'rule_name',
                'sales_rep_id',
                'base_commission_rate',
                'min_margin_threshold',
                'tier_rules',
                'discount_penalty_rate',
                'is_active',
                'notes',
            ],
        )
        self.payout_repo = CrudRepository(
            'T0110',
            pk='id',
            business_columns=[
                'id',
                'payout_number',
                'sales_rep_id',
                'invoice_id',
                'payment_id',
                'rule_id',
                'period_start',
                'period_end',
                'collected_amount',
                'realized_gross_margin',
                'commission_rate',
                'commission_amount',
                'discount_penalty',
                'net_commission_amount',
                'status',
                'payment_date',
                'notes',
            ],
        )

    # -----------------------------------------------------------------------
    # Commission Rules (Nova.t0109)
    # -----------------------------------------------------------------------

    def get_rule(self, rule_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Fetch commission rule by primary key with sales rep details."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
            SELECT 
                r.*,
                COALESCE(u.full_name, u.username) AS sales_rep_name
            FROM "{self.schema}".t0109 r
            LEFT JOIN "{self.schema}".t0021 u ON r.sales_rep_id = u.id
            WHERE r.id = %s;
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (rule_id,))
                row = cur.fetchone()
                if not row:
                    return None
                data = dict(row)
                if isinstance(data.get('tier_rules'), str):
                    try:
                        data['tier_rules'] = json.loads(data['tier_rules'])
                    except Exception:
                        data['tier_rules'] = []
                elif data.get('tier_rules') is None:
                    data['tier_rules'] = []
                return data
        finally:
            if should_release:
                release_connection(conn)

    def get_active_rule_for_rep(
        self, sales_rep_id: Optional[int] = None, conn=None
    ) -> Dict[str, Any]:
        """
        Retrieves the active commission rule for a specific sales representative.
        Falls back to active global default rule (sales_rep_id IS NULL), then system default.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 1. Check rep-specific rule
                if sales_rep_id is not None:
                    query = f"""
                    SELECT r.*, COALESCE(u.full_name, u.username) AS sales_rep_name
                    FROM "{self.schema}".t0109 r
                    LEFT JOIN "{self.schema}".t0021 u ON r.sales_rep_id = u.id
                    WHERE r.sales_rep_id = %s AND r.is_active = true
                    ORDER BY r.id DESC LIMIT 1;
                    """
                    cur.execute(query, (sales_rep_id,))
                    row = cur.fetchone()
                    if row:
                        data = dict(row)
                        if isinstance(data.get('tier_rules'), str):
                            try:
                                data['tier_rules'] = json.loads(data['tier_rules'])
                            except Exception:
                                data['tier_rules'] = []
                        elif data.get('tier_rules') is None:
                            data['tier_rules'] = []
                        return data

                # 2. Check global default rule
                query = f"""
                SELECT r.*, NULL AS sales_rep_name
                FROM "{self.schema}".t0109 r
                WHERE r.sales_rep_id IS NULL AND r.is_active = true
                ORDER BY r.id DESC LIMIT 1;
                """
                cur.execute(query)
                row = cur.fetchone()
                if row:
                    data = dict(row)
                    if isinstance(data.get('tier_rules'), str):
                        try:
                            data['tier_rules'] = json.loads(data['tier_rules'])
                        except Exception:
                            data['tier_rules'] = []
                    elif data.get('tier_rules') is None:
                        data['tier_rules'] = []
                    return data

                # 3. Built-in standard fallback
                return {
                    'id': None,
                    'rule_name': 'Standard Margin Commission (Default)',
                    'sales_rep_id': sales_rep_id,
                    'sales_rep_name': None,
                    'base_commission_rate': 5.00,
                    'min_margin_threshold': 15.00,
                    'tier_rules': [],
                    'discount_penalty_rate': 0.50,
                    'is_active': True,
                    'notes': 'Default fallback rate (5% commission on gross profit for margins >= 15%)',
                }
        finally:
            if should_release:
                release_connection(conn)

    def list_rules(
        self,
        sales_rep_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lists commission rules with filtering and pagination."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses = ['1=1']
            params: list[Any] = []

            if sales_rep_id is not None:
                clauses.append('(r.sales_rep_id = %s OR r.sales_rep_id IS NULL)')
                params.append(sales_rep_id)
            if is_active is not None:
                clauses.append('r.is_active = %s')
                params.append(is_active)

            where_sql = ' AND '.join(clauses)

            query = f"""
            SELECT 
                r.*,
                COALESCE(u.full_name, u.username) AS sales_rep_name,
                COUNT(*) OVER()::INT AS full_count
            FROM "{self.schema}".t0109 r
            LEFT JOIN "{self.schema}".t0021 u ON r.sales_rep_id = u.id
            WHERE {where_sql}
            ORDER BY r.id DESC
            LIMIT %s OFFSET %s;
            """
            params.extend([limit, offset])

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]
                total = rows[0]['full_count'] if rows else 0
                for r in rows:
                    if isinstance(r.get('tier_rules'), str):
                        try:
                            r['tier_rules'] = json.loads(r['tier_rules'])
                        except Exception:
                            r['tier_rules'] = []
                    elif r.get('tier_rules') is None:
                        r['tier_rules'] = []
                return rows, total
        finally:
            if should_release:
                release_connection(conn)

    def create_rule(self, payload: dict, conn=None) -> Dict[str, Any]:
        """Creates a new commission rule in Nova.t0109."""
        clean_payload = dict(payload)
        if isinstance(clean_payload.get('tier_rules'), (list, dict)):
            clean_payload['tier_rules'] = json.dumps(clean_payload['tier_rules'])
        return self.rule_repo.create(clean_payload, conn=conn)

    def update_rule(self, rule_id: int, payload: dict, conn=None) -> Optional[Dict[str, Any]]:
        """Updates an existing commission rule."""
        clean_payload = dict(payload)
        if isinstance(clean_payload.get('tier_rules'), (list, dict)):
            clean_payload['tier_rules'] = json.dumps(clean_payload['tier_rules'])
        return self.rule_repo.update(rule_id, clean_payload, conn=conn)

    def delete_rule(self, rule_id: int, conn=None) -> bool:
        """Deletes or deactivates a commission rule."""
        return self.rule_repo.delete(rule_id, conn=conn)

    # -----------------------------------------------------------------------
    # Commission Payouts & Ledger (Nova.t0110)
    # -----------------------------------------------------------------------

    def get_payout(self, payout_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieves single payout record with joined relations."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
            SELECT 
                p.*,
                COALESCE(u.full_name, u.username) AS sales_rep_name,
                inv.invoice_number
            FROM "{self.schema}".t0110 p
            JOIN "{self.schema}".t0021 u ON p.sales_rep_id = u.id
            LEFT JOIN "{self.schema}".t0090 inv ON p.invoice_id = inv.id
            WHERE p.id = %s;
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (payout_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def list_payouts(
        self,
        sales_rep_id: Optional[int] = None,
        status: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        conn=None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lists commission payouts with filtering and relations."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            clauses = ['1=1']
            params: list[Any] = []

            if sales_rep_id is not None:
                clauses.append('p.sales_rep_id = %s')
                params.append(sales_rep_id)
            if status:
                clauses.append('p.status = %s')
                params.append(status)
            if period_start:
                clauses.append('(p.period_start >= %s OR p.created_at::DATE >= %s)')
                params.extend([period_start, period_start])
            if period_end:
                clauses.append('(p.period_end <= %s OR p.created_at::DATE <= %s)')
                params.extend([period_end, period_end])

            where_sql = ' AND '.join(clauses)

            query = f"""
            SELECT 
                p.*,
                COALESCE(u.full_name, u.username) AS sales_rep_name,
                inv.invoice_number,
                COUNT(*) OVER()::INT AS full_count
            FROM "{self.schema}".t0110 p
            JOIN "{self.schema}".t0021 u ON p.sales_rep_id = u.id
            LEFT JOIN "{self.schema}".t0090 inv ON p.invoice_id = inv.id
            WHERE {where_sql}
            ORDER BY p.id DESC
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

    def create_payout(self, payload: dict, conn=None) -> Dict[str, Any]:
        """Creates a new payout record in Nova.t0110."""
        return self.payout_repo.create(payload, conn=conn)

    def update_payout(self, payout_id: int, payload: dict, conn=None) -> Optional[Dict[str, Any]]:
        """Updates an existing payout record in Nova.t0110."""
        return self.payout_repo.update(payout_id, payload, conn=conn)

    def delete_payout(self, payout_id: int, conn=None) -> bool:
        """Deletes a payout record."""
        return self.payout_repo.delete(payout_id, conn=conn)

    # -----------------------------------------------------------------------
    # Invoice Collections & Realized Margin Queries
    # -----------------------------------------------------------------------

    def get_sales_rep_invoices_and_payments(
        self,
        sales_rep_id: Optional[int] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        include_pending: bool = True,
        conn=None,
    ) -> List[Dict[str, Any]]:
        """
        Queries all sales invoices, linked sales orders, line-item COGS, header/line discounts,
        freight charges, and completed payment collections for commission calculation.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            inv_clauses = ["inv.status != 'Cancelled'"]
            inv_params: list[Any] = []

            if sales_rep_id is not None:
                inv_clauses.append('(COALESCE(inv.sales_rep_id, so.sales_rep_id) = %s)')
                inv_params.append(sales_rep_id)
            else:
                inv_clauses.append('COALESCE(inv.sales_rep_id, so.sales_rep_id) IS NOT NULL')

            if period_start:
                inv_clauses.append('inv.issue_date >= %s')
                inv_params.append(period_start)
            if period_end:
                inv_clauses.append('inv.issue_date <= %s')
                inv_params.append(period_end)

            inv_where = ' AND '.join(inv_clauses)

            # Optional payment date filter
            payment_filter = ""
            payment_params: list[Any] = []
            if period_start and not include_pending:
                payment_filter += " AND p.payment_date >= %s"
                payment_params.append(period_start)
            if period_end and not include_pending:
                payment_filter += " AND p.payment_date <= %s"
                payment_params.append(period_end)

            query = f"""
            WITH payment_aggregates AS (
                SELECT 
                    p.invoice_id,
                    MAX(p.id) AS latest_payment_id,
                    MAX(p.payment_date) AS latest_payment_date,
                    SUM(p.amount) AS total_collected_cash
                FROM "{self.schema}".t0091 p
                WHERE p.status = 'Completed'
                {payment_filter}
                GROUP BY p.invoice_id
            ),
            payout_aggregates AS (
                SELECT 
                    po.invoice_id,
                    CASE
                        WHEN BOOL_OR(po.status = 'Paid') THEN 'Paid'
                        WHEN BOOL_OR(po.status = 'Approved') THEN 'Approved'
                        WHEN BOOL_OR(po.status = 'Pending') THEN 'Pending'
                        ELSE MIN(po.status)
                    END AS payout_status,
                    SUM(CASE WHEN po.status = 'Paid' THEN po.net_commission_amount ELSE 0 END) AS paid_commission,
                    SUM(CASE WHEN po.status != 'Paid' AND po.status != 'Cancelled' THEN po.net_commission_amount ELSE 0 END) AS pending_commission
                FROM "{self.schema}".t0110 po
                GROUP BY po.invoice_id
            ),
            filtered_invoices AS (
                SELECT 
                    inv.id AS invoice_id,
                    inv.invoice_number,
                    inv.issue_date AS invoice_date,
                    inv.due_date,
                    inv.total_amount AS invoice_total,
                    COALESCE(inv.freight_amount, 0) AS inv_freight,
                    COALESCE(inv.discount_amount, 0) AS inv_discount,
                    COALESCE(inv.sales_rep_id, so.sales_rep_id) AS sales_rep_id,
                    inv.partner_id AS customer_id,
                    inv.sales_order_id,
                    so.order_number,
                    COALESCE(so.freight_amount, 0) AS so_freight,
                    COALESCE(so.discount_amount, 0) AS so_discount,
                    inv.status AS invoice_status
                FROM "{self.schema}".t0090 inv
                LEFT JOIN "{self.schema}".t0012 so ON inv.sales_order_id = so.id
                WHERE {inv_where}
            ),
            line_aggregates AS (
                SELECT 
                    sol.sales_order_id,
                    SUM(sol.qty * sol.unit_price) AS line_gross_sales,
                    SUM(COALESCE(sol.discount, 0)) AS line_discount,
                    SUM(sol.qty * COALESCE(NULLIF(sol.cost_price, 0), p.cost_price, 0)) AS line_cogs
                FROM "{self.schema}".t0013 sol
                JOIN "{self.schema}".t0003 p ON sol.product_id = p.id
                WHERE sol.sales_order_id IN (SELECT sales_order_id FROM filtered_invoices WHERE sales_order_id IS NOT NULL)
                GROUP BY sol.sales_order_id
            )
            SELECT 
                fi.invoice_id,
                fi.invoice_number,
                fi.sales_order_id AS order_id,
                fi.order_number,
                fi.invoice_date,
                fi.due_date,
                fi.invoice_status,
                fi.customer_id,
                c.name AS customer_name,
                fi.sales_rep_id,
                COALESCE(u.full_name, u.username, 'Sales Rep #' || fi.sales_rep_id::text) AS sales_rep_name,
                u.email AS sales_rep_email,
                fi.invoice_total,
                COALESCE(pa.total_collected_cash, 0)::FLOAT AS collected_cash,
                pa.latest_payment_id,
                pa.latest_payment_date,
                COALESCE(la.line_gross_sales, fi.invoice_total + fi.inv_discount)::FLOAT AS gross_sales,
                (COALESCE(la.line_discount, 0) + fi.inv_discount + fi.so_discount)::FLOAT AS discount_amount,
                la.line_cogs::FLOAT AS cogs,
                (la.line_cogs IS NOT NULL) AS has_cogs_data,
                COALESCE(NULLIF(fi.inv_freight, 0), fi.so_freight, 0)::FLOAT AS freight_cost,
                poa.payout_status,
                COALESCE(poa.paid_commission, 0)::FLOAT AS existing_paid_commission,
                COALESCE(poa.pending_commission, 0)::FLOAT AS existing_pending_commission
            FROM filtered_invoices fi
            JOIN "{self.schema}".t0021 u ON fi.sales_rep_id = u.id
            JOIN "{self.schema}".t0010 c ON fi.customer_id = c.id
            LEFT JOIN line_aggregates la ON fi.sales_order_id = la.sales_order_id
            LEFT JOIN payment_aggregates pa ON fi.invoice_id = pa.invoice_id
            LEFT JOIN payout_aggregates poa ON fi.invoice_id = poa.invoice_id
            ORDER BY fi.invoice_date DESC, fi.invoice_id DESC;
            """

            params = payment_params + inv_params
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get_sales_rep_info(self, sales_rep_id: int, conn=None) -> Optional[Dict[str, Any]]:
        """Retrieves sales rep user details from Nova.t0021."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
            SELECT 
                id,
                username,
                COALESCE(full_name, username) AS full_name,
                email,
                role,
                status
            FROM "{self.schema}".t0021
            WHERE id = %s;
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (sales_rep_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def list_all_sales_reps(self, conn=None) -> List[Dict[str, Any]]:
        """Lists all users active as sales reps or associated with orders/invoices."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            query = f"""
            SELECT DISTINCT
                u.id,
                u.username,
                COALESCE(u.full_name, u.username) AS full_name,
                u.email,
                u.role
            FROM "{self.schema}".t0021 u
            WHERE u.status = 'Active'
               OR EXISTS (SELECT 1 FROM "{self.schema}".t0012 so WHERE so.sales_rep_id = u.id)
               OR EXISTS (SELECT 1 FROM "{self.schema}".t0090 inv WHERE inv.sales_rep_id = u.id)
               OR EXISTS (SELECT 1 FROM "{self.schema}".t0109 r WHERE r.sales_rep_id = u.id)
            ORDER BY full_name ASC;
            """
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)


# Default singleton instance
commission_repo = CommissionRepository()
