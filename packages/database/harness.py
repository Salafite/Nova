"""
Database test fixture and connection harness for real PostgreSQL integration tests.

This module provides a robust connection harness that safely bypasses root mock patches
for integration and e2e tests while ensuring 100% unit test compatibility and zero mock pollution.
"""
import os
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

# Default test database configuration
DEFAULT_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'nova_erp',
    'user': 'nova',
    'password': 'nova_secret',
    'schema': 'Nova',
    'sslmode': 'prefer',
    'pool_min': 1,
    'pool_max': 50,
}


def get_db_config() -> Dict[str, Any]:
    """
    Resolve PostgreSQL configuration from environment variables with sensible test defaults.
    """
    host = os.getenv('DB_HOST', DEFAULT_DB_CONFIG['host'])
    if host == 'localhost' and os.name == 'nt':
        host = '127.0.0.1'

    return {
        'host': host,
        'port': int(os.getenv('DB_PORT', DEFAULT_DB_CONFIG['port'])),
        'dbname': os.getenv('DB_NAME', DEFAULT_DB_CONFIG['dbname']),
        'user': os.getenv('DB_USER', DEFAULT_DB_CONFIG['user']),
        'password': os.getenv('DB_PASSWORD', DEFAULT_DB_CONFIG['password']),
        'schema': os.getenv('DB_SCHEMA', DEFAULT_DB_CONFIG['schema']),
        'sslmode': os.getenv('DB_SSLMODE', DEFAULT_DB_CONFIG['sslmode']),
        'pool_min': int(os.getenv('DB_POOL_MIN', DEFAULT_DB_CONFIG['pool_min'])),
        'pool_max': int(os.getenv('DB_POOL_MAX', DEFAULT_DB_CONFIG['pool_max'])),
    }


def is_postgres_available(config: Optional[Dict[str, Any]] = None, timeout: int = 3) -> bool:
    """
    Check if the target PostgreSQL database is reachable and accepting connections.
    """
    cfg = config or get_db_config()
    try:
        conn = psycopg2.connect(
            host=cfg['host'],
            port=cfg['port'],
            dbname=cfg['dbname'],
            user=cfg['user'],
            password=cfg['password'],
            sslmode=cfg['sslmode'],
            connect_timeout=timeout
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return True
    except Exception as e:
        logger.debug(f"PostgreSQL availability check failed: {e}")
        return False


def get_direct_connection(config: Optional[Dict[str, Any]] = None, schema: Optional[str] = None, autocommit: bool = False):
    """
    Create a standalone (unpooled) direct connection to the target PostgreSQL database.
    """
    cfg = config or get_db_config()
    target_schema = schema or cfg.get('schema', 'Nova')
    conn = psycopg2.connect(
        host=cfg['host'],
        port=cfg['port'],
        dbname=cfg['dbname'],
        user=cfg['user'],
        password=cfg['password'],
        sslmode=cfg['sslmode'],
    )
    if autocommit:
        conn.autocommit = True
    if target_schema:
        with conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{target_schema}", public;')
    return conn


class DatabaseHarness:
    """
    Thread-safe connection harness managing real PostgreSQL connection pools for test execution.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, minconn: int = 1, maxconn: int = 60):
        self.config = config or get_db_config()
        self.minconn = minconn
        self.maxconn = max(maxconn, self.config.get('pool_max', 60))
        self._pool: Optional[ThreadedConnectionPool] = None
        self._is_closed = False
        self._init_pool()

    def _init_pool(self):
        """Initialize the underlying thread-safe connection pool."""
        self._pool = ThreadedConnectionPool(
            minconn=self.minconn,
            maxconn=self.maxconn,
            host=self.config['host'],
            port=self.config['port'],
            dbname=self.config['dbname'],
            user=self.config['user'],
            password=self.config['password'],
            sslmode=self.config['sslmode'],
        )
        self._is_closed = False

    @property
    def pool(self) -> ThreadedConnectionPool:
        """Access the underlying connection pool."""
        if self._is_closed or self._pool is None:
            self._init_pool()
        return self._pool

    def get_connection(self, schema: Optional[str] = None):
        """
        Check out a connection from the pool and set its search_path.
        """
        target_schema = schema or self.config.get('schema', 'Nova')
        last_err = None
        for attempt in range(10):
            conn = None
            try:
                conn = self.pool.getconn()
                with conn.cursor() as cur:
                    cur.execute(f'SET search_path TO "{target_schema}", public;')
                return conn
            except Exception as e:
                if conn is not None:
                    self.release_connection(conn)
                last_err = e
                err_str = str(e).lower()
                if 'exhausted' in err_str or 'closed unexpectedly' in err_str or 'timeout' in err_str or 'too many clients' in err_str:
                    time.sleep(0.02 * (attempt + 1))
                    continue
                raise
        raise last_err

    def release_connection(self, conn, close: bool = False):
        """Return a connection back to the pool."""
        if conn is not None and self._pool is not None and not self._is_closed:
            try:
                self._pool.putconn(conn, close=close)
            except Exception as e:
                logger.warning(f"Error putting connection back into pool: {e}")

    @contextmanager
    def connection(self, schema: Optional[str] = None) -> Generator[Any, None, None]:
        """
        Context manager yielding a pooled connection with automatic release on exit.
        """
        conn = self.get_connection(schema=schema)
        try:
            yield conn
        finally:
            self.release_connection(conn)

    @contextmanager
    def cursor(self, schema: Optional[str] = None, cursor_factory=None) -> Generator[Any, None, None]:
        """
        Context manager yielding a cursor from a pooled connection with auto-commit on success.
        """
        with self.connection(schema=schema) as conn:
            cur = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    @contextmanager
    def bypass_mocks(self) -> Generator["DatabaseHarness", None, None]:
        """
        Context manager that temporarily swaps `packages.database.connection._pool`
        with this real connection pool, safely bypassing any mock patches applied at root conftest.
        Restores the previous pool (mock or real) upon exit.
        """
        import packages.database.connection as db_conn_module
        old_pool = getattr(db_conn_module, '_pool', None)
        try:
            db_conn_module._pool = self.pool
            yield self
        finally:
            db_conn_module._pool = old_pool

    def execute_query(self, sql: str, params=None, fetch: str = 'all'):
        """
        Execute a standalone query against the real database.
        """
        with self.cursor() as cur:
            cur.execute(sql, params)
            if fetch == 'all':
                return cur.fetchall()
            elif fetch == 'one':
                return cur.fetchone()
            elif fetch == 'none':
                return cur.rowcount
            return cur.fetchall()

    def close(self):
        """Close all connections and destroy the pool."""
        if self._pool is not None and not self._is_closed:
            try:
                self._pool.closeall()
            except Exception as e:
                logger.debug(f"Error during pool closeall: {e}")
            finally:
                self._is_closed = True
                self._pool = None


# Shared singleton harness instance
_shared_harness: Optional[DatabaseHarness] = None


def get_shared_harness(minconn: int = 1, maxconn: int = 60, **kwargs) -> DatabaseHarness:
    """
    Retrieve or create the shared DatabaseHarness singleton.
    """
    global _shared_harness
    if _shared_harness is None or _shared_harness._is_closed:
        _shared_harness = DatabaseHarness(minconn=minconn, maxconn=maxconn, **kwargs)
    return _shared_harness


def close_shared_harness():
    """
    Close the shared DatabaseHarness singleton if it exists.
    """
    global _shared_harness
    if _shared_harness is not None:
        _shared_harness.close()
        _shared_harness = None


@contextmanager
def bypass_db_mocks(harness: Optional[DatabaseHarness] = None) -> Generator[DatabaseHarness, None, None]:
    """
    Convenience context manager to bypass database mocks using the shared or provided harness.
    """
    h = harness or get_shared_harness()
    with h.bypass_mocks():
        yield h
