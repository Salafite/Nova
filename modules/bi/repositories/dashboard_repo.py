from packages.database.connection import get_connection, release_connection
import psycopg2.extras


def get_stats():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
