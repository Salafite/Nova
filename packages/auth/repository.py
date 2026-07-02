import psycopg2.extras
from packages.database.connection import get_connection, release_connection


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "Nova".t0021 WHERE username = %s', (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM "Nova".t0021 WHERE id = %s', (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def update_last_login(user_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "Nova".t0021 SET last_login = NOW() WHERE id = %s', (user_id,))
            conn.commit()
    finally:
        release_connection(conn)
