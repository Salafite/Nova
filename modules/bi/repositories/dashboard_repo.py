from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant
import psycopg2.extras


def get_stats():
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if tenant_id is not None:
                queries = {
                    'products': ("SELECT COUNT(*) AS c FROM Nova.t0003 WHERE is_active = TRUE AND business_id = %s", (tenant_id,)),
                    'customers': ("SELECT COUNT(*) AS c FROM Nova.t0010 WHERE is_active = TRUE AND business_id = %s", (tenant_id,)),
                    'suppliers': ("SELECT COUNT(*) AS c FROM Nova.t0011 WHERE is_active = TRUE AND business_id = %s", (tenant_id,)),
                    'salesOrders': ("SELECT COUNT(*) AS c FROM Nova.t0012 WHERE business_id = %s", (tenant_id,)),
                    'invoices': ("SELECT COUNT(*) AS c FROM Nova.t0090 WHERE business_id = %s", (tenant_id,)),
                    'payments': ("SELECT COUNT(*) AS c FROM Nova.t0091 WHERE business_id = %s", (tenant_id,)),
                    'employees': ("SELECT COUNT(*) AS c FROM Nova.t0030 WHERE is_active = TRUE AND business_id = %s", (tenant_id,)),
                    'users': ("SELECT COUNT(*) AS c FROM Nova.t0021 WHERE status = 'Active' AND business_id = %s", (tenant_id,)),
                }
                stats = {}
                for key, (sql, params) in queries.items():
                    cur.execute(sql, params)
                    stats[key] = cur.fetchone()['c']
                return stats
            else:
                queries = {
                    'products': "SELECT COUNT(*) AS c FROM Nova.t0003 WHERE is_active = TRUE",
                    'customers': "SELECT COUNT(*) AS c FROM Nova.t0010 WHERE is_active = TRUE",
                    'suppliers': "SELECT COUNT(*) AS c FROM Nova.t0011 WHERE is_active = TRUE",
                    'salesOrders': "SELECT COUNT(*) AS c FROM Nova.t0012",
                    'invoices': "SELECT COUNT(*) AS c FROM Nova.t0090",
                    'payments': "SELECT COUNT(*) AS c FROM Nova.t0091",
                    'employees': "SELECT COUNT(*) AS c FROM Nova.t0030 WHERE is_active = TRUE",
                    'users': "SELECT COUNT(*) AS c FROM Nova.t0021 WHERE status = 'Active'",
                }
                stats = {}
                for key, sql in queries.items():
                    cur.execute(sql)
                    stats[key] = cur.fetchone()['c']
                return stats
    finally:
        release_connection(conn)


def get_recent_activity(limit=10):
    conn = get_connection()
    try:
        tenant_id = get_current_tenant()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if tenant_id is not None:
                cur.execute("""
                    SELECT invoice_number, issue_date, status, total_amount
                    FROM Nova.t0090
                    WHERE business_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                """, (tenant_id, limit))
            else:
                cur.execute("""
                    SELECT invoice_number, issue_date, status, total_amount
                    FROM Nova.t0090
                    ORDER BY id DESC
                    LIMIT %s
                """, (limit,))
            return [
                {
                    'label': r['invoice_number'],
                    'date': r['issue_date'].isoformat() if r['issue_date'] else None,
                    'status': r['status'],
                    'total': float(r['total_amount']) if r['total_amount'] else 0,
                }
                for r in cur.fetchall()
            ]
    finally:
        release_connection(conn)

