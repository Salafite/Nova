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
    for attempt in range(3):
        try:
            conn = _pool.getconn()
            with conn.cursor() as cur:
                cur.execute(f'SET search_path TO {os.getenv("DB_SCHEMA", "Nova")}')
            return conn
        except Exception as e:
            last_err = e
            if 'closed unexpectedly' in str(e) or 'timeout' in str(e).lower():
                time.sleep(1 * (attempt + 1))
                continue
            raise
    raise last_err


def release_connection(conn):
    _pool.putconn(conn)


@contextmanager
def db_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)
