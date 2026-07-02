import psycopg2.extras
from packages.database.connection import get_connection, release_connection

AUDIT_COLUMNS = {'created_at', 'created_by', 'updated_at', 'updated_by', 'update_number'}


class CrudRepository:
    def __init__(self, table: str, pk: str = 'id', business_columns: list[str] = None):
        self.qualified = f'"Nova".{table.lower()}'
        self.pk = pk
        self.business_columns = business_columns or []
        self.all_columns = business_columns + list(AUDIT_COLUMNS) if business_columns else []

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None):
        conn = get_connection()
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
            release_connection(conn)

    def get(self, id_val):
        conn = get_connection()
        try:
            sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_val,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            release_connection(conn)

    def create(self, payload: dict):
        conn = get_connection()
        try:
            cols = [c for c in payload.keys() if c != self.pk and c not in AUDIT_COLUMNS]
            vals = [payload[c] for c in cols]
            cols_str = ', '.join(f'"{c}"' for c in cols)
            placeholders = ', '.join('%s' for _ in cols)
            sql = f'INSERT INTO {self.qualified} ({cols_str}) VALUES ({placeholders}) RETURNING *'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, vals)
                conn.commit()
                row = cur.fetchone()
                return dict(row) if row else None
        except psycopg2.Error:
            conn.rollback()
            raise
        finally:
            release_connection(conn)

    def update(self, id_val, payload: dict):
        conn = get_connection()
        try:
            cols = [c for c in payload.keys() if c != self.pk and c not in AUDIT_COLUMNS]
            if not cols:
                return self.get(id_val)
            set_clauses = [f'"{c}" = %s' for c in cols]
            set_clauses.append('"updated_at" = NOW()')
            set_clauses.append('"update_number" = "update_number" + 1')
            vals = [payload[c] for c in cols]
            vals.append(id_val)
            sql = f'UPDATE {self.qualified} SET {", ".join(set_clauses)} WHERE "{self.pk}" = %s RETURNING *'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, vals)
                conn.commit()
                row = cur.fetchone()
                return dict(row) if row else None
        except psycopg2.Error:
            conn.rollback()
            raise
        finally:
            release_connection(conn)

    def delete(self, id_val):
        conn = get_connection()
        try:
            if self._has_is_active():
                sql = f'UPDATE {self.qualified} SET is_active = FALSE, updated_at = NOW(), update_number = update_number + 1 WHERE "{self.pk}" = %s'
            else:
                sql = f'DELETE FROM {self.qualified} WHERE "{self.pk}" = %s'
            with conn.cursor() as cur:
                cur.execute(sql, (id_val,))
                conn.commit()
                return cur.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            raise
        finally:
            release_connection(conn)

    def _has_is_active(self):
        return 'is_active' in self.all_columns
