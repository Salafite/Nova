import os
from typing import Generator, Any, Dict
from unittest.mock import MagicMock, patch
import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-32-bytes-long!!')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'nova_erp')
os.environ.setdefault('DB_USER', 'nova')
os.environ.setdefault('DB_PASSWORD', 'nova_secret')
os.environ.setdefault('DB_SCHEMA', 'Nova')
os.environ.setdefault('DB_SSLMODE', 'prefer')
os.environ.setdefault('ACCESS_TOKEN_EXPIRE_MINUTES', '1440')
os.environ.setdefault('REFRESH_TOKEN_EXPIRE_DAYS', '7')
os.environ.setdefault('ALLOWED_ORIGINS', '*')
os.environ.setdefault('REDIS_MOCK', 'true')
os.environ.setdefault('REDIS_USE_MOCK', 'true')

_mock_pool = MagicMock()
_mock_conn = MagicMock()
_mock_pool.getconn.return_value = _mock_conn

_pool_patcher = patch('psycopg2.pool.SimpleConnectionPool', return_value=_mock_pool)
_pool_patcher.start()


@pytest.fixture(scope="session")
def db_config():
    """Returns the resolved test database configuration."""
    from packages.database.harness import get_db_config
    return get_db_config()


@pytest.fixture(scope="session")
def real_harness(db_config):
    """
    Session-scoped DatabaseHarness connected to real PostgreSQL.
    Automatically ensures the full Nova schema (T0001-T0107, sequences, constraints)
    is provisioned and verified before tests run.
    Skips tests if PostgreSQL is not reachable when requested.
    """
    from packages.database.harness import (
        get_shared_harness,
        close_shared_harness,
        is_postgres_available,
        get_direct_connection,
    )
    from packages.database.apply_schema import ensure_schema_provisioned

    if not is_postgres_available(db_config):
        pytest.skip(f"Real PostgreSQL instance is not reachable at {db_config['host']}:{db_config['port']}")

    # Ensure schema is fully provisioned
    try:
        direct_conn = get_direct_connection(config=db_config, autocommit=True)
        ensure_schema_provisioned(conn=direct_conn)
        direct_conn.close()
    except Exception as e:
        pytest.skip(f"Failed to provision schema on real PostgreSQL: {e}")

    harness = get_shared_harness(minconn=1, maxconn=60, config=db_config)
    try:
        yield harness
    finally:
        close_shared_harness()


@pytest.fixture(scope="session")
def provisioned_schema(real_harness, db_config) -> Dict[str, Any]:
    """
    Session-scoped fixture guaranteeing schema 'Nova', tables (T0001-T0107),
    sequences, and constraints are provisioned and verified.
    """
    from packages.database.harness import get_direct_connection
    from packages.database.verify_schema import verify_schema
    
    conn = get_direct_connection(config=db_config)
    try:
        res = verify_schema(conn)
        return res
    finally:
        conn.close()


@pytest.fixture(scope="session")
def real_db_pool(real_harness):
    """Session-scoped ThreadedConnectionPool connected to real PostgreSQL."""
    return real_harness.pool


@pytest.fixture(scope="function")
def real_db(real_harness) -> Generator[Any, None, None]:
    """
    Function-scoped fixture that safely bypasses root mock patches for the duration of the test,
    pointing `packages.database.connection._pool` to the real PostgreSQL connection pool.
    Restores mock pool on teardown.
    """
    with real_harness.bypass_mocks():
        yield real_harness


@pytest.fixture(scope="function")
def real_db_conn(real_harness, real_db):
    """
    Function-scoped fixture yielding an individual connection checked out from the real pool.
    Auto-releases the connection back to the pool on teardown.
    """
    with real_harness.connection() as conn:
        yield conn


@pytest.fixture(scope="function")
def real_db_cursor(real_db_conn):
    """
    Function-scoped fixture yielding an active cursor on a real database connection.
    """
    with real_db_conn.cursor() as cur:
        yield cur


@pytest.fixture(scope="session")
def db_cleaner(real_harness) -> Any:
    """
    Session-scoped DatabaseCleaner instance using real PostgreSQL harness.
    """
    from packages.database.isolation import DatabaseCleaner
    return DatabaseCleaner(harness=real_harness)


@pytest.fixture(scope="function")
def clean_db(real_db, db_cleaner) -> Generator[Any, None, None]:
    """
    Function-scoped fixture that guarantees a clean database state before and after each test.
    Automatically resets sequences and truncates any populated tables.
    """
    db_cleaner.clean_dirty_tables(reset_sequences=True)
    yield db_cleaner
    db_cleaner.clean_dirty_tables(reset_sequences=True)


@pytest.fixture(scope="function")
def isolated_db(clean_db):
    """Alias for clean_db fixture."""
    return clean_db


@pytest.fixture(scope="function")
def isolated_tenant(real_db, real_harness, db_cleaner) -> Generator[int, None, None]:
    """
    Function-scoped fixture creating a dedicated test tenant in T0059 with active tenant context,
    automatically wiping all tenant records and resetting tenant context on test teardown.
    """
    from packages.database.isolation import isolated_tenant as isolated_tenant_ctx
    with isolated_tenant_ctx(harness=real_harness, cleaner=db_cleaner) as (tid, _):
        yield tid


@pytest.fixture(scope="function")
def db_transaction(real_db, real_harness) -> Generator[Any, None, None]:
    """
    Function-scoped fixture yielding an isolated transaction that automatically rolls back on test exit.
    """
    from packages.database.isolation import transactional_isolation
    with transactional_isolation(harness=real_harness) as conn:
        yield conn


@pytest.fixture(scope="function")
def db_savepoint(real_db_conn) -> Generator[Any, None, None]:
    """
    Function-scoped fixture creating a savepoint that automatically rolls back on test exit.
    """
    from packages.database.isolation import savepoint_isolation
    with savepoint_isolation(real_db_conn) as conn:
        yield conn


@pytest.fixture(autouse=True)
def _auto_bypass_db_for_marked_tests(request):
    """
    Automatically activate real database mock bypass for tests marked with
    @pytest.mark.real_db, @pytest.mark.integration, @pytest.mark.clean_db, or @pytest.mark.isolated_db.
    """
    is_real_db_marked = (
        request.node.get_closest_marker("real_db") is not None
        or request.node.get_closest_marker("integration") is not None
        or request.node.get_closest_marker("clean_db") is not None
        or request.node.get_closest_marker("isolated_db") is not None
        or request.node.get_closest_marker("isolated_tenant") is not None
    )
    if is_real_db_marked:
        harness = request.getfixturevalue("real_harness")
        with harness.bypass_mocks():
            if request.node.get_closest_marker("clean_db") is not None or request.node.get_closest_marker("isolated_db") is not None:
                cleaner = request.getfixturevalue("db_cleaner")
                cleaner.clean_dirty_tables(reset_sequences=True)
                yield
                cleaner.clean_dirty_tables(reset_sequences=True)
            else:
                yield
    else:
        yield

