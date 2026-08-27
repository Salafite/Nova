"""
Database isolation mechanism for real PostgreSQL integration test suite.

Provides fast, deterministic database isolation strategies:
1. Transaction Rollback & Savepoints (<1ms isolation for transactional flows).
2. Optimized Table Truncation (<100ms full schema / <15ms domain truncation with CASCADE and sequence resets).
3. Tenant-Level Data Isolation (isolated test tenant lifecycle with multi-table cleanup).
4. Sequence Reset & State Synchronization.
"""
import os
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Set, Generator, Tuple
import psycopg2
import psycopg2.extras

from packages.database.harness import get_db_config, get_direct_connection, get_shared_harness, DatabaseHarness
from packages.database.sequence import reset_sequence, get_current_sequence_value, set_sequence_value

logger = logging.getLogger(__name__)

# Default excluded tables that should not be truncated during general cleanup (e.g., migrations tracking)
DEFAULT_EXCLUDED_TABLES = {"_schema_migrations"}

# Core sequence names used throughout the system
KNOWN_SEQUENCES = [
    "seq_invoice_number",
    "seq_pick_list_number",
]


class DatabaseCleaner:
    """
    High-performance database cleaner and state manager for PostgreSQL test isolation.
    Caches table metadata, sequence names, and tenant-enabled tables to minimize catalog queries.
    """

    def __init__(
        self,
        schema: str = "Nova",
        config: Optional[Dict[str, Any]] = None,
        harness: Optional[DatabaseHarness] = None,
        excluded_tables: Optional[Set[str]] = None,
    ):
        self.schema = schema or os.getenv("DB_SCHEMA", "Nova")
        self.config = config or get_db_config()
        self.harness = harness
        self.excluded_tables = set(excluded_tables or DEFAULT_EXCLUDED_TABLES)
        
        self._all_tables: Optional[List[str]] = None
        self._business_tables: Optional[List[str]] = None
        self._tenant_tables: Optional[List[str]] = None
        self._all_sequences: Optional[List[str]] = None

    def _get_connection(self, conn=None, autocommit: bool = True):
        """Helper to get a valid database connection."""
        if conn is not None:
            return conn, False
        if self.harness is not None:
            c = self.harness.get_connection(schema=self.schema)
            try:
                if c.status != psycopg2.extensions.STATUS_READY:
                    c.rollback()
                c.autocommit = autocommit
            except Exception:
                pass
            return c, True
        # Standalone direct connection
        c = get_direct_connection(config=self.config, schema=self.schema, autocommit=autocommit)
        return c, True

    def get_all_tables(self, conn=None, refresh: bool = False) -> List[str]:
        """
        Get all base table names in the target schema.
        """
        if self._all_tables is not None and not refresh:
            return list(self._all_tables)

        c, should_release = self._get_connection(conn=conn)
        try:
            with c.cursor() as cur:
                cur.execute(
                    """
                    SELECT LOWER(table_name)
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                    """,
                    (self.schema,)
                )
                self._all_tables = [r[0] for r in cur.fetchall()]
                return list(self._all_tables)
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def get_tenant_tables(self, conn=None, refresh: bool = False) -> List[str]:
        """
        Get all tables in the target schema that have a business_id column.
        """
        if self._tenant_tables is not None and not refresh:
            return list(self._tenant_tables)

        c, should_release = self._get_connection(conn=conn)
        try:
            with c.cursor() as cur:
                cur.execute(
                    """
                    SELECT LOWER(table_name)
                    FROM information_schema.columns
                    WHERE table_schema = %s AND LOWER(column_name) = 'business_id'
                    ORDER BY table_name;
                    """,
                    (self.schema,)
                )
                self._tenant_tables = [r[0] for r in cur.fetchall()]
                return list(self._tenant_tables)
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def get_all_sequences(self, conn=None, refresh: bool = False) -> List[str]:
        """
        Get all sequence names in the target schema.
        """
        if self._all_sequences is not None and not refresh:
            return list(self._all_sequences)

        c, should_release = self._get_connection(conn=conn)
        try:
            with c.cursor() as cur:
                cur.execute(
                    """
                    SELECT LOWER(sequence_name)
                    FROM information_schema.sequences
                    WHERE sequence_schema = %s
                    ORDER BY sequence_name;
                    """,
                    (self.schema,)
                )
                self._all_sequences = [r[0] for r in cur.fetchall()]
                return list(self._all_sequences)
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def truncate_tables(
        self,
        tables: Optional[List[str]] = None,
        restart_identity: bool = True,
        cascade: bool = True,
        exclude_tables: Optional[Set[str]] = None,
        conn=None,
    ) -> float:
        """
        Fast multi-table truncation in a single PostgreSQL statement.
        
        Returns elapsed execution time in milliseconds.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            target_tables = tables if tables is not None else self.get_all_tables(conn=c)
            excluded = self.excluded_tables if exclude_tables is None else (self.excluded_tables | set(exclude_tables))
            
            tables_to_truncate = [
                t.lower().replace('"', '')
                for t in target_tables
                if t.lower().replace('"', '') not in excluded
            ]

            if not tables_to_truncate:
                return 0.0

            formatted_tables = ", ".join(f'"{self.schema}"."{t}"' for t in tables_to_truncate)
            restart_clause = " RESTART IDENTITY" if restart_identity else ""
            cascade_clause = " CASCADE" if cascade else ""
            sql = f"TRUNCATE TABLE {formatted_tables}{restart_clause}{cascade_clause};"

            t0 = time.perf_counter()
            with c.cursor() as cur:
                cur.execute(sql)
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            logger.debug(f"Truncated {len(tables_to_truncate)} tables in {elapsed_ms:.2f}ms")
            return elapsed_ms
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def reset_sequences(
        self,
        sequences: Optional[List[str]] = None,
        start_value: int = 1,
        conn=None,
    ) -> int:
        """
        Reset sequences in the schema to a specified starting value (default 1, is_called=false).
        
        Returns the number of sequences reset.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            target_seqs = sequences if sequences is not None else self.get_all_sequences(conn=c)
            if not target_seqs:
                return 0

            clean_seqs = [s.lower().replace('"', '') for s in target_seqs]
            with c.cursor() as cur:
                sql_stmts = " ".join(
                    f'ALTER SEQUENCE "{self.schema}"."{s}" RESTART WITH {int(start_value)};'
                    for s in clean_seqs
                )
                cur.execute(sql_stmts)
            return len(target_seqs)
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def truncate_all(
        self,
        exclude_tables: Optional[Set[str]] = None,
        reset_sequences: bool = True,
        conn=None,
    ) -> float:
        """
        Truncate all tables in the schema and reset all sequences.
        Ensures complete, zero-pollution database isolation.
        
        Returns elapsed execution time in milliseconds.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            elapsed = self.truncate_tables(
                tables=None,
                restart_identity=True,
                cascade=True,
                exclude_tables=exclude_tables,
                conn=c,
            )
            if reset_sequences:
                self.reset_sequences(conn=c)
            return elapsed
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def clean_tenant_data(self, business_id: int, conn=None) -> Dict[str, int]:
        """
        Delete all data belonging to a specific tenant across all tenant-scoped tables,
        and remove the tenant from T0059.
        
        Returns a dictionary mapping table names to deleted row counts.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            tenant_tables = self.get_tenant_tables(conn=c)
            # Delete child / higher-numbered tables first to respect foreign key constraints
            ordered_tables = sorted([t for t in tenant_tables if t != "t0059"], reverse=True)
            deleted_counts = {}

            with c.cursor() as cur:
                # Multi-pass deletion to handle any out-of-order foreign key dependencies
                pending_tables = list(ordered_tables)
                for _pass in range(3):
                    next_pending = []
                    for tbl in pending_tables:
                        try:
                            cur.execute(f"SAVEPOINT sp_del_{tbl};")
                            cur.execute(
                                f'DELETE FROM "{self.schema}"."{tbl}" WHERE "business_id" = %s;',
                                (business_id,)
                            )
                            deleted_rc = cur.rowcount
                            cur.execute(f"RELEASE SAVEPOINT sp_del_{tbl};")
                            if deleted_rc > 0:
                                deleted_counts[tbl] = deleted_counts.get(tbl, 0) + deleted_rc
                        except Exception as e:
                            try:
                                cur.execute(f"ROLLBACK TO SAVEPOINT sp_del_{tbl}; RELEASE SAVEPOINT sp_del_{tbl};")
                            except Exception:
                                pass
                            next_pending.append(tbl)
                    pending_tables = next_pending
                    if not pending_tables:
                        break

                # Finally delete tenant record from t0059 if it exists
                try:
                    cur.execute(
                        f'DELETE FROM "{self.schema}"."t0059" WHERE "id" = %s;',
                        (business_id,)
                    )
                    if cur.rowcount > 0:
                        deleted_counts["t0059"] = cur.rowcount
                except Exception as e:
                    logger.warning(f"Error cleaning tenant {business_id} from t0059: {e}")

            return deleted_counts
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def get_table_counts(self, tables: Optional[List[str]] = None, conn=None) -> Dict[str, int]:
        """
        Get row counts for the specified tables (or all non-empty tables if tables is None).
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            target_tables = tables if tables is not None else self.get_all_tables(conn=c)
            counts = {}
            with c.cursor() as cur:
                for tbl in target_tables:
                    if tbl in self.excluded_tables:
                        continue
                    try:
                        cur.execute(f'SELECT count(*) FROM "{self.schema}"."{tbl}";')
                        cnt = cur.fetchone()[0]
                        if tables is not None or cnt > 0:
                            counts[tbl] = cnt
                    except Exception:
                        pass
            return counts
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def get_dirty_tables(self, conn=None) -> List[str]:
        """
        Find tables in the schema that contain one or more rows in a single fast query.
        Uses cached table list and EXISTS subqueries for sub-millisecond execution.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            tables = [t for t in self.get_all_tables(conn=c) if t not in self.excluded_tables]
            if not tables:
                return []
            union_branches = [
                f"SELECT '{t}' AS tbl WHERE EXISTS (SELECT 1 FROM \"{self.schema}\".\"{t}\" LIMIT 1)"
                for t in tables
            ]
            query = " UNION ALL ".join(union_branches)
            with c.cursor() as cur:
                cur.execute(query)
                return [r[0] for r in cur.fetchall()]
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def reset_dirty_sequences(self, start_value: int = 1, conn=None) -> int:
        """
        Reset only sequences that have actually been advanced / modified.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            with c.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT sequencename
                        FROM pg_sequences
                        WHERE schemaname = %s AND (last_value IS NOT NULL AND last_value > 1);
                        """,
                        (self.schema,)
                    )
                    dirty_seqs = [r[0] for r in cur.fetchall()]
                except Exception:
                    dirty_seqs = list(KNOWN_SEQUENCES)

                if not dirty_seqs:
                    return 0

                sql_stmts = " ".join(
                    f'ALTER SEQUENCE "{self.schema}"."{s}" RESTART WITH {int(start_value)};'
                    for s in dirty_seqs
                )
                cur.execute(sql_stmts)
                return len(dirty_seqs)
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()

    def clean_dirty_tables(self, reset_sequences: bool = True, conn=None) -> float:
        """
        Fast cleanup: only truncates tables that actually contain data.
        """
        c, should_release = self._get_connection(conn=conn, autocommit=True)
        try:
            dirty = self.get_dirty_tables(conn=c)
            if not dirty:
                if reset_sequences:
                    self.reset_dirty_sequences(conn=c)
                return 0.0
            
            elapsed = self.truncate_tables(tables=dirty, restart_identity=True, cascade=True, conn=c)
            if reset_sequences:
                self.reset_dirty_sequences(conn=c)
            return elapsed
        finally:
            if should_release:
                if self.harness is not None:
                    self.harness.release_connection(c)
                else:
                    c.close()


# ============================================================================
# Transaction & Savepoint Context Managers
# ============================================================================

@contextmanager
def transactional_isolation(conn=None, harness: Optional[DatabaseHarness] = None) -> Generator[Any, None, None]:
    """
    Context manager providing zero-overhead (<1ms) database isolation via transaction rollback.
    All operations executed within this context run inside an uncommitted transaction
    and are unconditionally rolled back on exit.
    """
    h = harness or get_shared_harness()
    should_release = False
    if conn is None:
        conn = h.get_connection()
        should_release = True

    if conn.status != psycopg2.extensions.STATUS_READY:
        try:
            conn.rollback()
        except Exception:
            pass
    prev_autocommit = conn.autocommit
    conn.autocommit = False
    try:
        yield conn
    finally:
        try:
            conn.rollback()
        except Exception as e:
            logger.warning(f"Error during transactional rollback: {e}")
        finally:
            try:
                if prev_autocommit is not None:
                    conn.autocommit = prev_autocommit
            except Exception:
                pass
            if should_release:
                h.release_connection(conn)


@contextmanager
def savepoint_isolation(conn, savepoint_name: str = "sp_test_isolation") -> Generator[Any, None, None]:
    """
    Context manager providing savepoint isolation on an existing active connection.
    Creates a SAVEPOINT before yield and rolls back to it on exit.
    """
    with conn.cursor() as cur:
        cur.execute(f"SAVEPOINT {savepoint_name};")
    try:
        yield conn
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}; RELEASE SAVEPOINT {savepoint_name};")
        except Exception as e:
            logger.warning(f"Error releasing savepoint {savepoint_name}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass


@contextmanager
def isolated_tenant(
    business_id: Optional[int] = None,
    business_name: str = "Test Isolated Tenant",
    tenant_code: Optional[str] = None,
    conn=None,
    harness: Optional[DatabaseHarness] = None,
    cleaner: Optional[DatabaseCleaner] = None,
) -> Generator[Tuple[int, Dict[str, Any]], None, None]:
    """
    Context manager creating an isolated test tenant in T0059, activating the tenant context,
    and automatically cleaning up all tenant data across all tables on teardown.
    """
    from modules.core.context import tenant_context

    h = harness or get_shared_harness()
    db_cleaner = cleaner or DatabaseCleaner(harness=h)
    
    c, should_release = (conn, False) if conn is not None else (h.get_connection(), True)
    try:
        code = tenant_code or f"TENANT_{int(time.time() * 1000) % 1000000}"
        
        with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if business_id is not None:
                cur.execute(
                    """
                    INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (id) DO UPDATE SET tenant_name = EXCLUDED.tenant_name
                    RETURNING *;
                    """,
                    (business_id, code, business_name)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO "Nova"."t0059" (tenant_code, tenant_name, is_active)
                    VALUES (%s, %s, TRUE)
                    RETURNING *;
                    """,
                    (code, business_name)
                )
            tenant_rec = dict(cur.fetchone())
            c.commit()

        tid = tenant_rec["id"]
        
        with tenant_context(tid):
            yield tid, tenant_rec

    finally:
        # Clean tenant records on teardown
        try:
            if 'tid' in locals():
                db_cleaner.clean_tenant_data(tid, conn=c)
                c.commit()
        except Exception as e:
            logger.warning(f"Error cleaning up isolated tenant: {e}")
        finally:
            if should_release:
                h.release_connection(c)


# ============================================================================
# Global Convenience Functions
# ============================================================================

_shared_cleaner: Optional[DatabaseCleaner] = None


def get_cleaner(schema: str = "Nova", config: Optional[Dict[str, Any]] = None) -> DatabaseCleaner:
    """
    Retrieve or create the shared DatabaseCleaner singleton.
    """
    global _shared_cleaner
    if _shared_cleaner is None:
        _shared_cleaner = DatabaseCleaner(schema=schema, config=config, harness=get_shared_harness())
    return _shared_cleaner


def truncate_tables(
    tables: Optional[List[str]] = None,
    restart_identity: bool = True,
    cascade: bool = True,
    exclude_tables: Optional[Set[str]] = None,
    conn=None,
    schema: str = "Nova",
) -> float:
    """Convenience function to truncate specified or all tables in the database."""
    cleaner = get_cleaner(schema=schema)
    return cleaner.truncate_tables(
        tables=tables,
        restart_identity=restart_identity,
        cascade=cascade,
        exclude_tables=exclude_tables,
        conn=conn,
    )


def truncate_all_tables(
    exclude_tables: Optional[Set[str]] = None,
    reset_sequences: bool = True,
    conn=None,
    schema: str = "Nova",
) -> float:
    """Convenience function to truncate all tables and reset sequences."""
    cleaner = get_cleaner(schema=schema)
    return cleaner.truncate_all(
        exclude_tables=exclude_tables,
        reset_sequences=reset_sequences,
        conn=conn,
    )


def clean_tenant_data(business_id: int, conn=None, schema: str = "Nova") -> Dict[str, int]:
    """Convenience function to delete all data for a specific tenant."""
    cleaner = get_cleaner(schema=schema)
    return cleaner.clean_tenant_data(business_id=business_id, conn=conn)


def reset_all_sequences(sequences: Optional[List[str]] = None, start_value: int = 1, conn=None, schema: str = "Nova") -> int:
    """Convenience function to reset all sequences in schema."""
    cleaner = get_cleaner(schema=schema)
    return cleaner.reset_sequences(sequences=sequences, start_value=start_value, conn=conn)
