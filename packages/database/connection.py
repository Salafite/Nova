import os
from contextlib import contextmanager
from psycopg2.pool import SimpleConnectionPool

_pool = SimpleConnectionPool(
    minconn=0,
    maxconn=int(os.getenv('DB_POOL_MAX', 20)),
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'Stage'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    sslmode=os.getenv('DB_SSLMODE', 'require')
)


def get_connection():
    import time
    last_err = None
    for attempt in range(10):
        conn = None
        try:
            conn = _pool.getconn()
            with conn.cursor() as cur:
                cur.execute(f'SET search_path TO {os.getenv("DB_SCHEMA", "Nova")}')
            return conn
        except Exception as e:
            if conn is not None:
                try:
                    _pool.putconn(conn)
                except Exception:
                    pass
            last_err = e
            err_str = str(e).lower()
            if 'exhausted' in err_str or 'closed unexpectedly' in err_str or 'timeout' in err_str or 'too many clients' in err_str:
                time.sleep(0.02 * (attempt + 1))
                continue
            raise
    raise last_err


def release_connection(conn, close=False):
    if conn is not None:
        try:
            _pool.putconn(conn, close=close)
        except Exception:
            pass


@contextmanager
def db_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)


@contextmanager
def db_transaction(conn=None):
    """
    Context manager for atomic database transactions.
    If conn is provided, reuses the existing connection without committing/releasing
    (nested transaction scope within outer transaction).
    If conn is None, acquires a connection from the pool, yields connection,
    commits on successful completion, and rolls back on exception before releasing connection to pool.
    """
    if conn is not None:
        yield conn
    else:
        conn = get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            release_connection(conn)

