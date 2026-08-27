"""Tests for packages.database.apply_schema."""
import pytest
from unittest.mock import MagicMock, patch
from packages.database.apply_schema import (
    apply_schema,
    ensure_schema_provisioned,
    get_table_name,
    strip_all_fks,
    split_sql_statements,
)
from packages.database.verify_schema import verify_schema


def test_split_sql_statements():
    sql = """
    -- Leading comment
    CREATE TYPE test_enum AS ENUM ('A', 'B');
    /* Block comment */
    DO $$ 
    BEGIN
        SELECT '; not a delimiter ;';
    END $$;
    CREATE TABLE "Nova".t9999 (
        id SERIAL PRIMARY KEY,
        val TEXT DEFAULT 'string with ; inside'
    );
    """
    stmts = split_sql_statements(sql)
    assert len(stmts) == 3
    assert stmts[0].startswith("CREATE TYPE")
    assert stmts[1].startswith("DO $$")
    assert "not a delimiter" in stmts[1]
    assert stmts[2].startswith("CREATE TABLE")


def test_get_table_name():
    assert get_table_name('CREATE TABLE IF NOT EXISTS "Nova".t0001 (') == 'T0001'
    assert get_table_name('CREATE TABLE t0059 (') == 'T0059'
    assert get_table_name('SELECT 1') is None


def test_strip_all_fks():
    stmt = 'CREATE TABLE "Nova".t0002 ( id SERIAL PRIMARY KEY, from_uom_id INT REFERENCES "Nova".t0001(id) ON DELETE CASCADE, business_id INT REFERENCES "Nova".t0059(id) );'
    fks = []
    stripped = strip_all_fks(stmt, 'T0002', fks)
    assert 'REFERENCES' not in stripped
    assert len(fks) == 2
    assert fks[0][0] == 'T0002'
    assert fks[0][1] == 'from_uom_id'
    assert 'REFERENCES "Nova".t0001(id) ON DELETE CASCADE' in fks[0][2]
    assert fks[1][1] == 'business_id'
    assert 'REFERENCES "Nova".t0059(id)' in fks[1][2]


def test_apply_schema_mock():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    # Apply schema to mock db
    stats = apply_schema(conn)
    assert stats["tables"] >= 100
    assert stats["tenant_fks"] >= 100
    assert stats["indexes"] > 0
    assert cur.execute.call_count > 100


def test_ensure_schema_provisioned_mock():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    # Mock verify_schema to simulate already provisioned
    with patch("packages.database.verify_schema.verify_schema", return_value={"success": True}):
        res = ensure_schema_provisioned(conn)
        assert res["success"] is True


@pytest.mark.integration
@pytest.mark.real_db
def test_apply_and_verify_real_postgres(real_harness):
    """Integration test applying schema against real PostgreSQL and verifying all constraints."""
    with real_harness.connection() as conn:
        stats = apply_schema(conn=conn, drop_existing=True)
        assert stats["tables"] >= 107
        assert stats["sequences"] >= 2
        assert stats["tenant_fks"] >= 106

        res = verify_schema(conn)
        assert res["total_tables"] >= 107
        assert res["tables_with_business_id"] >= 106
