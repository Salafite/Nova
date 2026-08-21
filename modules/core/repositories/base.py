import os
import psycopg2.extras
from packages.database.connection import get_connection, release_connection

AUDIT_COLUMNS = {'created_at', 'created_by', 'updated_at', 'updated_by', 'update_number'}


class CrudRepository:
    def __init__(self, table: str, pk: str = 'id', business_columns: list[str] = None):
        schema = os.getenv('DB_SCHEMA', 'Nova')
        self.qualified = f'"{schema}".{table.lower()}'
        self.pk = pk
        self.business_columns = business_columns or []
        self.all_columns = business_columns + list(AUDIT_COLUMNS) if business_columns else []

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            clauses = ['TRUE']
            params = []
            if self._has_is_active():
                clauses.append('is_active = TRUE')
            if filters:
                for k, v in filters.items():
                    clauses.append(f'"{k}" = %s')
                    params.append(v)
            order = f'ORDER BY "{order_by}"' if order_by else f'ORDER BY "{self.pk}" DESC'
            sql = f'SELECT * FROM {self.qualified} WHERE {" AND ".join(clauses)} {order}'
            if limit is not None:
                sql += ' LIMIT %s'
                params.append(limit)
            if offset is not None:
                sql += ' OFFSET %s'
                params.append(offset)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            if should_release:
                release_connection(conn)

    def get(self, id_val, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_val,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_for_update(self, id_val, conn=None):
        """SELECT ... FOR UPDATE — locks the row until the transaction commits or rolls back.

        Requires an active transaction (conn must be provided or will be acquired).
        The lock is released when the transaction commits or rolls back.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s FOR UPDATE'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_val,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
                release_connection(conn)

    def create(self, payload: dict, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            cols = [c for c in payload.keys() if c != self.pk and c not in AUDIT_COLUMNS]
            vals = [payload[c] for c in cols]
            cols_str = ', '.join(f'"{c}"' for c in cols)
            placeholders = ', '.join('%s' for _ in cols)
            sql = f'INSERT INTO {self.qualified} ({cols_str}) VALUES ({placeholders}) RETURNING *'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, vals)
                if should_release:
                    conn.commit()
                row = cur.fetchone()
                return dict(row) if row else None
        except psycopg2.Error:
            if should_release:
                conn.rollback()
            raise
        finally:
            if should_release:
                release_connection(conn)

    def update(self, id_val, payload: dict, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            cols = [c for c in payload.keys() if c != self.pk and c not in AUDIT_COLUMNS]
            if not cols:
                return self.get(id_val, conn=conn)
            set_clauses = [f'"{c}" = %s' for c in cols]
            set_clauses.append('"updated_at" = NOW()')
            set_clauses.append('"update_number" = "update_number" + 1')
            vals = [payload[c] for c in cols]
            vals.append(id_val)
            sql = f'UPDATE {self.qualified} SET {", ".join(set_clauses)} WHERE "{self.pk}" = %s RETURNING *'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, vals)
                if should_release:
                    conn.commit()
                row = cur.fetchone()
                return dict(row) if row else None
        except psycopg2.Error:
            if should_release:
                conn.rollback()
            raise
        finally:
            if should_release:
                release_connection(conn)

    def delete(self, id_val, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            if self._has_is_active():
                sql = f'UPDATE {self.qualified} SET is_active = FALSE, updated_at = NOW(), update_number = update_number + 1 WHERE "{self.pk}" = %s'
            else:
                sql = f'DELETE FROM {self.qualified} WHERE "{self.pk}" = %s'
            with conn.cursor() as cur:
                cur.execute(sql, (id_val,))
                if should_release:
                    conn.commit()
                return cur.rowcount > 0
        except psycopg2.Error:
            if should_release:
                conn.rollback()
            raise
        finally:
            if should_release:
                release_connection(conn)

    def count(self, filters: dict = None, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            clauses = ['TRUE']
            params = []
            if self._has_is_active():
                clauses.append('is_active = TRUE')
            if filters:
                for k, v in filters.items():
                    clauses.append(f'"{k}" = %s')
                    params.append(v)
            sql = f'SELECT COUNT(*) AS cnt FROM {self.qualified} WHERE {" AND ".join(clauses)}'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row['cnt'] if row else 0
        finally:
            if should_release:
                release_connection(conn)

    def _has_is_active(self):
        return 'is_active' in self.all_columns
