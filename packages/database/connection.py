import os
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import SimpleConnectionPool

_pool = SimpleConnectionPool(
    minconn=int(os.getenv('DB_POOL_MIN', 5)),
    maxconn=int(os.getenv('DB_POOL_MAX', 20)),
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'Stage'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    sslmode=os.getenv('DB_SSLMODE', 'require')
)


def get_connection():
    conn = _pool.getconn()
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO {os.getenv("DB_SCHEMA", "Nova")}')
    return conn


def release_connection(conn):
    _pool.putconn(conn)


@contextmanager
def db_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)
