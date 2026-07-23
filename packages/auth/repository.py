import secrets
import psycopg2.extras
from packages.database.connection import get_connection, release_connection


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM t0021 WHERE username = %s', (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM t0021 WHERE email = %s', (email,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM t0021 WHERE id = %s', (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def update_last_login(user_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE t0021 SET last_login = NOW() WHERE id = %s', (user_id,))
            conn.commit()
    finally:
        release_connection(conn)


def create_business(name: str, owner_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'INSERT INTO t0059 (tenant_code, tenant_name, created_by) VALUES (%s, %s, %s) RETURNING *',
                (name[:3].upper() + str(owner_id), name, owner_id)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        release_connection(conn)


def get_business_by_id(business_id: int) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM t0059 WHERE id = %s', (business_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def create_user(username: str, password_hash: str, full_name: str,
                email: str, role: str, business_id: int = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'INSERT INTO t0021 (username, password_hash, full_name, email, role, business_id, status) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *',
                (username, password_hash, full_name, email, role, business_id, 'Active')
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        release_connection(conn)


def get_users_by_business(business_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM t0021 WHERE business_id = %s ORDER BY created_at DESC', (business_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_connection(conn)


def create_invited_user(email: str, role: str, full_name: str | None,
                        business_id: int, invited_by: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            token = secrets.token_urlsafe(32)
            username = email.split('@')[0] + '_' + token[:6]
            cur.execute(
                'INSERT INTO t0021 (username, password_hash, full_name, email, role, '
                'business_id, status, invite_token, created_by) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *',
                (username, '', full_name, email, role, business_id, 'Invited', token, invited_by)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        release_connection(conn)
