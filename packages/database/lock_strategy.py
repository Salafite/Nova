"""
Database Lock Ordering Strategy Module.

Establishes deterministic lock ordering (sorting entity IDs/keys prior to SELECT FOR UPDATE row locking)
across multi-row queries and multi-entity operations to eliminate database deadlocks in high-concurrency environments.
"""
import os
import re
import logging
from typing import Any, Iterable, List, Optional, Tuple
import psycopg2.extras
from modules.core.context import get_current_tenant

logger = logging.getLogger(__name__)
IDENTIFIER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def sort_lock_keys(keys: Iterable[Any]) -> List[Any]:
    """
    Deduplicate and sort entity lock keys (IDs, strings, or composite tuples)
    in strict ascending order to guarantee consistent lock acquisition sequence across transactions.

    :param keys: Iterable of key values (e.g. [5, 2, 9] or [(2, 1), (1, 1)])
    :return: Sorted list of unique lock keys.
    """
    if not keys:
        return []
    
    unique_keys = list(set(keys))
    
    # Python sorted works for integers, strings, and tuples naturally
    try:
        return sorted(unique_keys)
    except TypeError:
        # Fallback string representation sort for mixed types
        return sorted(unique_keys, key=lambda k: str(k))


def lock_rows_by_ids(
    conn,
    table: str,
    pk_column: str,
    ids: Iterable[Any],
    business_id: Optional[int] = None,
    schema: Optional[str] = None,
) -> List[dict]:
    """
    Locks multiple table rows by primary key using SELECT FOR UPDATE with explicit lock ordering.

    IDs are sorted in ascending order prior to executing query with ORDER BY pk ASC FOR UPDATE,
    preventing multi-row deadlock conditions across concurrent worker threads.

    :param conn: Active psycopg2 database connection inside a transaction.
    :param table: Unqualified or qualified table name.
    :param pk_column: Primary key column identifier.
    :param ids: Primary key values to lock.
    :param business_id: Optional tenant business_id for isolation.
    :param schema: Optional schema name (defaults to DB_SCHEMA env or 'Nova').
    :return: List of locked row dictionaries.
    """
    sorted_ids = sort_lock_keys(ids)
    if not sorted_ids:
        return []

    schema_name = schema or os.getenv('DB_SCHEMA', 'Nova')
    clean_table = table.strip('"` ').lower()
    clean_pk = pk_column.strip('"` ')

    if not IDENTIFIER_REGEX.match(clean_table) or not IDENTIFIER_REGEX.match(clean_pk):
        raise ValueError(f"Invalid table or column identifier: {table}.{pk_column}")

    qualified_table = f'"{schema_name}"."{clean_table}"'
    placeholders = ', '.join('%s' for _ in sorted_ids)

    tenant_id = business_id if business_id is not None else get_current_tenant()
    
    if tenant_id is not None and clean_table != 't0059':
        sql = (
            f'SELECT * FROM {qualified_table} '
            f'WHERE "{clean_pk}" IN ({placeholders}) AND "business_id" = %s '
            f'ORDER BY "{clean_pk}" ASC FOR UPDATE'
        )
        params = tuple(sorted_ids) + (tenant_id,)
    else:
        sql = (
            f'SELECT * FROM {qualified_table} '
            f'WHERE "{clean_pk}" IN ({placeholders}) '
            f'ORDER BY "{clean_pk}" ASC FOR UPDATE'
        )
        params = tuple(sorted_ids)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def lock_rows_by_composite_keys(
    conn,
    table: str,
    key_columns: Tuple[str, ...],
    key_tuples: Iterable[Tuple[Any, ...]],
    business_id: Optional[int] = None,
    schema: Optional[str] = None,
) -> List[dict]:
    """
    Locks multiple table rows by composite keys (e.g. product_id, warehouse_id) using
    SELECT FOR UPDATE with explicit key tuple sorting and ORDER BY key_columns ASC.

    :param conn: Active psycopg2 database connection inside a transaction.
    :param table: Table name.
    :param key_columns: Tuple of column names defining the composite key (e.g. ('product_id', 'warehouse_id')).
    :param key_tuples: Iterable of key tuples to lock (e.g. [(10, 1), (5, 1)]).
    :param business_id: Optional tenant business_id for isolation.
    :param schema: Optional schema name.
    :return: List of locked row dictionaries.
    """
    sorted_tuples = sort_lock_keys(key_tuples)
    if not sorted_tuples:
        return []

    schema_name = schema or os.getenv('DB_SCHEMA', 'Nova')
    clean_table = table.strip('"` ').lower()
    clean_cols = [col.strip('"` ') for col in key_columns]

    for col in clean_cols:
        if not IDENTIFIER_REGEX.match(col):
            raise ValueError(f"Invalid column identifier: {col}")
    if not IDENTIFIER_REGEX.match(clean_table):
        raise ValueError(f"Invalid table identifier: {table}")

    qualified_table = f'"{schema_name}"."{clean_table}"'
    cols_clause = ', '.join(f'"{col}"' for col in clean_cols)
    order_clause = ', '.join(f'"{col}" ASC' for col in clean_cols)

    # Build (col1, col2) IN ((val1, val2), (val3, val4))
    tuple_placeholders = '(' + ', '.join('%s' for _ in clean_cols) + ')'
    in_clause = ', '.join(tuple_placeholders for _ in sorted_tuples)

    params = []
    for t in sorted_tuples:
        params.extend(t)

    tenant_id = business_id if business_id is not None else get_current_tenant()

    if tenant_id is not None and clean_table != 't0059':
        sql = (
            f'SELECT * FROM {qualified_table} '
            f'WHERE ({cols_clause}) IN ({in_clause}) AND "business_id" = %s '
            f'ORDER BY {order_clause} FOR UPDATE'
        )
        params.append(tenant_id)
    else:
        sql = (
            f'SELECT * FROM {qualified_table} '
            f'WHERE ({cols_clause}) IN ({in_clause}) '
            f'ORDER BY {order_clause} FOR UPDATE'
        )

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
