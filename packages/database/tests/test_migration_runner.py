"""Unit and integration tests for packages.database.migration_runner."""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from packages.database.migration_runner import (
    run_migrations,
    get_migration_status,
    ensure_tracking_table,
    get_applied_migrations,
    mark_migration_applied,
)


def test_ensure_tracking_table():
    cur = MagicMock()
    ensure_tracking_table(cur)
    assert cur.execute.call_count >= 2


def test_get_applied_migrations():
    cur = MagicMock()
    cur.fetchall.return_value = [("001_full_schema.sql",), ("002_missing_tables.sql",)]
    applied = get_applied_migrations(cur)
    assert applied == {"001_full_schema.sql", "002_missing_tables.sql"}


def test_mark_migration_applied():
    cur = MagicMock()
    mark_migration_applied(cur, 1, "001_full_schema.sql", "SELECT 1;")
    cur.execute.assert_called_once()
    args = cur.execute.call_args[0]
    assert "INSERT INTO \"Nova\"._migrations" in args[0]
    assert args[1][0] == 1
    assert args[1][1] == "001_full_schema.sql"


def test_run_migrations_mock(tmp_path):
    # Create sample migration files
    m1 = tmp_path / "001_init.sql"
    m1.write_text("CREATE TABLE test_table (id INT);", encoding="utf-8")
    m2 = tmp_path / "002_add_col.sql"
    m2.write_text("ALTER TABLE test_table ADD COLUMN name TEXT;", encoding="utf-8")

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = []  # No migrations applied yet

    result = run_migrations(conn=conn, migrations_dir=tmp_path)
    assert result["success"] is True
    assert result["total_files"] == 2
    assert result["applied_count"] == 2
    assert result["skipped_count"] == 0
    assert result["failed_count"] == 0


def test_get_migration_status_mock(tmp_path):
    m1 = tmp_path / "001_init.sql"
    m1.write_text("SELECT 1;", encoding="utf-8")
    m2 = tmp_path / "002_next.sql"
    m2.write_text("SELECT 2;", encoding="utf-8")

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = [("001_init.sql",)]

    status = get_migration_status(conn=conn, migrations_dir=tmp_path)
    assert status["total"] == 2
    assert status["applied_count"] == 1
    assert status["pending_count"] == 1
    assert status["applied"] == ["001_init.sql"]
    assert status["pending"] == ["002_next.sql"]


@pytest.mark.integration
@pytest.mark.real_db
def test_migration_runner_real_postgres(real_harness):
    """Test running migrations on real PostgreSQL instance with tracking table."""
    with real_harness.connection() as conn:
        status = get_migration_status(conn=conn)
        assert status["total"] > 0
