"""Tests for packages.database.verify_schema."""
import pytest
from unittest.mock import MagicMock, patch
from packages.database.verify_schema import verify_schema, load_environment, print_verification_report


def generate_mock_db(all_tables_present=True, all_bids_present=True, all_fks_present=True, all_indexes_present=True):
    expected_tables = [f"t{i:04d}" for i in range(1, 108)]
    tables = expected_tables if all_tables_present else expected_tables[:50]
    
    # business tables (all except t0059)
    biz_tables = [t for t in tables if t != "t0059"]
    
    # columns
    bid_cols = [(t, "integer") for t in (biz_tables if all_bids_present else biz_tables[:50])]
    
    # fks
    fks = [(t, "business_id", "t0059") for t in (biz_tables if all_fks_present else biz_tables[:50])]
    
    # indexes
    indexes = []
    for t in (biz_tables if all_indexes_present else biz_tables[:50]):
        indexes.append((t, f"idx_{t}_business_id", f"CREATE INDEX idx_{t}_business_id ON \"Nova\".{t} USING btree (business_id)"))
        indexes.append((t, f"idx_{t}_business_id_id", f"CREATE INDEX idx_{t}_business_id_id ON \"Nova\".{t} USING btree (business_id, id)"))

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    # Mock sequential queries in verify_schema:
    # 1. tables -> tables list of tuples
    # 2. views -> []
    # 3. total_cols -> (500,)
    # 4. bid_cols -> bid_cols
    # 5. total_fks -> (len(fks),)
    # 6. tenant_fks -> fks
    # 7. total_pks -> (len(tables),)
    # 8. all_indexes -> indexes
    # 9-13. seed queries -> (10,) each
    cur.fetchall.side_effect = [
        [(t,) for t in tables],
        [],
        bid_cols,
        fks,
        indexes,
    ]
    cur.fetchone.side_effect = [
        (500,),        # total_cols
        (len(fks),),   # total_fks
        (len(tables),),# total_pks
        (10,),         # seed products
        (5,),          # seed customers
        (5,),          # seed suppliers
        (2,),          # seed users
        (1,),          # seed tenants
    ]

    return conn, cur


def test_verify_schema_success():
    conn, cur = generate_mock_db()
    res = verify_schema(conn)
    assert res["success"] is True
    assert res["total_tables"] == 107
    assert res["tables_with_business_id"] == 106
    assert res["tenant_fks_count"] == 106
    assert res["tenant_single_indexes_count"] == 106
    assert res["tenant_composite_indexes_count"] == 106
    assert len(res["errors"]) == 0


def test_verify_schema_missing_tables():
    conn, cur = generate_mock_db(all_tables_present=False)
    res = verify_schema(conn)
    assert res["success"] is False
    assert len(res["missing_tables"]) > 0


def test_verify_schema_missing_business_id():
    conn, cur = generate_mock_db(all_bids_present=False)
    res = verify_schema(conn)
    assert res["success"] is False
    assert len(res["missing_business_id_columns"]) > 0


def test_verify_schema_missing_tenant_fks():
    conn, cur = generate_mock_db(all_fks_present=False)
    res = verify_schema(conn)
    assert res["success"] is False
    assert len(res["missing_tenant_fks"]) > 0


def test_verify_schema_missing_indexes():
    conn, cur = generate_mock_db(all_indexes_present=False)
    res = verify_schema(conn)
    assert res["success"] is False
    assert len(res["missing_single_indexes"]) > 0 or len(res["missing_composite_indexes"]) > 0


def test_print_verification_report_stdout(capsys):
    conn, cur = generate_mock_db()
    res = verify_schema(conn)
    print_verification_report(res)
    captured = capsys.readouterr()
    assert "Nova ERP Database Schema & Multi-Tenancy Verification" in captured.out
    assert "[PASSED]" in captured.out
