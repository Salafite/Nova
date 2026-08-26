"""
Pytest configuration and fixtures for integration and end-to-end testing against real PostgreSQL.
"""
import pytest
from typing import Generator
from packages.database.harness import (
    DatabaseHarness,
    get_db_config,
    get_shared_harness,
    close_shared_harness,
    is_postgres_available,
)


@pytest.fixture(scope="session")
def db_config():
    """Returns the resolved test database configuration."""
    return get_db_config()


@pytest.fixture(scope="session")
def real_harness(db_config) -> Generator[DatabaseHarness, None, None]:
    """
    Session-scoped DatabaseHarness connected to real PostgreSQL.
    Skips tests if PostgreSQL is not reachable when requested.
    """
    if not is_postgres_available(db_config):
        pytest.skip(f"Real PostgreSQL instance is not reachable at {db_config['host']}:{db_config['port']}")

    harness = get_shared_harness(minconn=1, maxconn=60, config=db_config)
    try:
        yield harness
    finally:
        close_shared_harness()


@pytest.fixture(scope="session")
def real_db_pool(real_harness):
    """Session-scoped ThreadedConnectionPool connected to real PostgreSQL."""
    return real_harness.pool


@pytest.fixture(scope="function")
def real_db(real_harness) -> Generator[DatabaseHarness, None, None]:
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


@pytest.fixture(autouse=True)
def _auto_bypass_db_for_marked_tests(request):
    """
    Automatically activate real database mock bypass for tests marked with
    @pytest.mark.real_db or @pytest.mark.integration.
    """
    is_real_db_marked = (
        request.node.get_closest_marker("real_db") is not None
        or request.node.get_closest_marker("integration") is not None
    )
    if is_real_db_marked:
        harness = request.getfixturevalue("real_harness")
        with harness.bypass_mocks():
            yield
    else:
        yield
