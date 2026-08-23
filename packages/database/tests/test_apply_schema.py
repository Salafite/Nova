"""Tests for packages.database.apply_schema."""
import pytest
from unittest.mock import MagicMock, patch
from packages.database.apply_schema import apply_schema, get_table_name, strip_all_fks


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
