import os
import re
import logging
from typing import Optional
import psycopg2.extras
from packages.database.connection import get_connection, release_connection
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)

AUDIT_COLUMNS = {'created_at', 'created_by', 'updated_at', 'updated_by', 'update_number'}
NON_TENANT_TABLES = {'t0059'}
IDENTIFIER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


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

    def _sanitize_order_by(self, order_by: Optional[str], allowed_columns: Optional[set[str] | list[str]] = None) -> str:
        """
        Validate and sanitize order_by parameter to protect against SQL injection
        and ensure only valid column names and directions (ASC/DESC) are used.
        Supports:
          - 'column' (default direction)
          - 'column ASC' or 'column DESC' (case-insensitive)
          - '-column' (descending) or '+column' (ascending)
          - Comma-separated list: 'column1 ASC, column2 DESC'
        Falls back to default 'ORDER BY "{self.pk}" DESC' if order_by is invalid or empty.
        """
        if not order_by or not isinstance(order_by, str):
            return f'ORDER BY "{self.pk}" DESC'

        order_by_str = order_by.strip()
        if not order_by_str:
            return f'ORDER BY "{self.pk}" DESC'

        valid_clauses = []
        parts = [p.strip() for p in order_by_str.split(',') if p.strip()]

        for part in parts:
            direction = None
            col_name = part

            if col_name.startswith('-'):
                direction = 'DESC'
                col_name = col_name[1:].strip()
            elif col_name.startswith('+'):
                direction = 'ASC'
                col_name = col_name[1:].strip()
            else:
                tokens = col_name.split()
                if len(tokens) == 1:
                    col_name = tokens[0]
                    direction = None
                elif len(tokens) == 2:
                    col_name = tokens[0]
                    dir_token = tokens[1].upper()
                    if dir_token in ('ASC', 'DESC'):
                        direction = dir_token
                    else:
                        continue
                else:
                    continue

            col_name = col_name.strip('"` ')

            if not IDENTIFIER_REGEX.match(col_name):
                logger.warning(
                    "Invalid order_by identifier '%s' on table '%s'",
                    col_name,
                    self.table_name
                )
                continue

            if allowed_columns and col_name not in allowed_columns:
                logger.warning(
                    "Order_by column '%s' not in allowed columns on table '%s'",
                    col_name,
                    self.table_name
                )
                continue

            if direction:
                valid_clauses.append(f'"{col_name}" {direction}')
            else:
                valid_clauses.append(f'"{col_name}"')

        if not valid_clauses:
            return f'ORDER BY "{self.pk}" DESC'

        return f'ORDER BY {", ".join(valid_clauses)}'

    def _sanitize_filters(self, filters: dict) -> tuple[list[str], list]:
        """
        Validate filter column names against SQL identifier pattern.
        Returns a tuple of (clause_strings, param_values).
        """
        clauses = []
        params = []
        if not filters or not isinstance(filters, dict):
            return clauses, params

        for k, v in filters.items():
            if not isinstance(k, str):
                continue
            key = k.strip('"` ')
            if not IDENTIFIER_REGEX.match(key):
                logger.warning("Invalid filter key identifier: '%s'", k)
                continue
            clauses.append(f'"{key}" = %s')
            params.append(v)

        return clauses, params

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
                filter_clauses, filter_params = self._sanitize_filters(filters)
                clauses.extend(filter_clauses)
                params.extend(filter_params)

            order = self._sanitize_order_by(order_by)
            sql = f'SELECT * FROM {self.qualified} WHERE {" AND ".join(clauses)} {order}'

            if limit is not None:
                try:
                    limit_val = min(max(0, int(limit)), 500)
                    sql += ' LIMIT %s'
                    params.append(limit_val)
                except (ValueError, TypeError):
                    pass

            if offset is not None:
                try:
                    offset_val = max(0, int(offset))
                    sql += ' OFFSET %s'
                    params.append(offset_val)
                except (ValueError, TypeError):
                    pass

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
                filter_clauses, filter_params = self._sanitize_filters(filters)
                clauses.extend(filter_clauses)
                params.extend(filter_params)
            sql = f'SELECT COUNT(*) AS cnt FROM {self.qualified} WHERE {" AND ".join(clauses)}'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row['cnt'] if row else 0
        finally:
            if should_release:
                release_connection(conn)
