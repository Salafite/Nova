import os
import logging
from typing import Optional
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)

AUDIT_COLUMNS = {'created_at', 'created_by', 'updated_at', 'updated_by', 'update_number'}
NON_TENANT_TABLES = {'t0059'}


class CrudRepository:
    def __init__(self, table: str, pk: str = 'id', business_columns: list[str] = None):
        schema = os.getenv('DB_SCHEMA', 'Nova')
        self.table = table
        self.table_name = table.lower()
        self.qualified = f'"{schema}".{self.table_name}'
        self.pk = pk
        self.business_columns = business_columns or []
        self.all_columns = (business_columns + list(AUDIT_COLUMNS)) if business_columns else []

    def _has_is_active(self) -> bool:
        return 'is_active' in self.all_columns

    def _has_business_id(self) -> bool:
        if self.table_name in NON_TENANT_TABLES:
            return False
        if self.business_columns and 'business_id' in self.business_columns:
            return True
        return True

    def list(self, filters: dict = None, order_by: str = None, limit: int = None, offset: int = None, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            clauses = ['TRUE']
            params = []

            tenant_id = business_id if business_id is not None else get_current_tenant()
            if tenant_id is not None and self._has_business_id():
                if not filters or 'business_id' not in filters:
                    clauses.append('"business_id" = %s')
                    params.append(tenant_id)

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

    def get(self, id_val, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = business_id if business_id is not None else get_current_tenant()
            if tenant_id is not None and self._has_business_id():
                sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s AND "business_id" = %s'
                params = (id_val, tenant_id)
            else:
                sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s'
                params = (id_val,)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            if should_release:
                release_connection(conn)

    def get_unscoped(self, id_val):
        """Retrieve record by PK ignoring any tenant context."""
        conn = get_connection()
        try:
            sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_val,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            release_connection(conn)

    def get_for_update(self, id_val, conn=None):
        """SELECT ... FOR UPDATE - locks the row until the transaction commits or rolls back.

        Requires an active transaction (conn must be provided or will be acquired).
        The lock is released when the transaction commits or rolls back.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        released = False
        try:
            sql = f'SELECT * FROM {self.qualified} WHERE "{self.pk}" = %s FOR UPDATE'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_val,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception as rb_err:
                    logger.error(f"Failed to rollback in get_for_update: {rb_err}")
                    try:
                        release_connection(conn, close=True)
                    except Exception:
                        pass
                    released = True
                if not released:
                    release_connection(conn)
                    released = True
            raise
        finally:
            if should_release and not released:
                try:
                    conn.rollback()
                except Exception as rb_err:
                    logger.error(f"Failed to rollback in get_for_update: {rb_err}")
                    try:
                        release_connection(conn, close=True)
                    except Exception:
                        pass
                else:
                    release_connection(conn)

    def create(self, payload: dict, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            data = dict(payload)
            tenant_id = business_id if business_id is not None else get_current_tenant()
            if tenant_id is not None and self._has_business_id():
                if 'business_id' not in data or data['business_id'] is None:
                    data['business_id'] = tenant_id

            cols = [c for c in data.keys() if c != self.pk and c not in AUDIT_COLUMNS]
            vals = [data[c] for c in cols]
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

    def update(self, id_val, payload: dict, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = business_id if business_id is not None else get_current_tenant()
            cols = [c for c in payload.keys() if c != self.pk and c != 'business_id' and c not in AUDIT_COLUMNS]
            if not cols:
                return self.get(id_val, conn=conn, business_id=tenant_id)
            set_clauses = [f'"{c}" = %s' for c in cols]
            set_clauses.append('"updated_at" = NOW()')
            set_clauses.append('"update_number" = "update_number" + 1')
            vals = [payload[c] for c in cols]
            vals.append(id_val)

            if tenant_id is not None and self._has_business_id():
                sql = f'UPDATE {self.qualified} SET {", ".join(set_clauses)} WHERE "{self.pk}" = %s AND "business_id" = %s RETURNING *'
                vals.append(tenant_id)
            else:
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

    def delete(self, id_val, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            tenant_id = business_id if business_id is not None else get_current_tenant()
            where_clauses = [f'"{self.pk}" = %s']
            params = [id_val]
            if tenant_id is not None and self._has_business_id():
                where_clauses.append('"business_id" = %s')
                params.append(tenant_id)

            where_str = ' AND '.join(where_clauses)
            if self._has_is_active():
                sql = f'UPDATE {self.qualified} SET is_active = FALSE, updated_at = NOW(), update_number = update_number + 1 WHERE {where_str}'
            else:
                sql = f'DELETE FROM {self.qualified} WHERE {where_str}'
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
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

    def count(self, filters: dict = None, conn=None, business_id: Optional[int] = None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True
        try:
            clauses = ['TRUE']
            params = []
            tenant_id = business_id if business_id is not None else get_current_tenant()
            if tenant_id is not None and self._has_business_id():
                if not filters or 'business_id' not in filters:
                    clauses.append('"business_id" = %s')
                    params.append(tenant_id)

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
