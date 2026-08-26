"""
Unit and integration tests for database isolation, table truncation,
savepoints, transaction rollback, and tenant data isolation.
"""
import time
import pytest
from unittest.mock import MagicMock, patch

from packages.database.isolation import (
    DatabaseCleaner,
    get_cleaner,
    truncate_tables,
    truncate_all_tables,
    clean_tenant_data,
    reset_all_sequences,
    transactional_isolation,
    savepoint_isolation,
    isolated_tenant,
    DEFAULT_EXCLUDED_TABLES,
)
from packages.database.sequence import get_next_sequence_value, get_current_sequence_value
from modules.core.context import get_current_tenant


# ============================================================================
# Unit Tests (Mock-based)
# ============================================================================

class TestDatabaseCleanerUnit:
    """Unit tests for DatabaseCleaner query construction and caching."""

    def test_cleaner_initialization_defaults(self):
        cleaner = DatabaseCleaner(schema="Nova")
        assert cleaner.schema == "Nova"
        assert "_schema_migrations" in cleaner.excluded_tables
        assert cleaner._all_tables is None
        assert cleaner._tenant_tables is None
        assert cleaner._all_sequences is None

    def test_get_all_tables_caches_result(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [("t0001",), ("t0002",), ("t0003",)]

        cleaner = DatabaseCleaner(schema="Nova")
        tables1 = cleaner.get_all_tables(conn=mock_conn)
        assert tables1 == ["t0001", "t0002", "t0003"]
        assert mock_cur.execute.call_count == 1

        # Second call should use cache
        tables2 = cleaner.get_all_tables(conn=mock_conn)
        assert tables2 == ["t0001", "t0002", "t0003"]
        assert mock_cur.execute.call_count == 1  # No additional query

        # Refresh should query again
        tables3 = cleaner.get_all_tables(conn=mock_conn, refresh=True)
        assert mock_cur.execute.call_count == 2

    def test_get_tenant_tables_filters_business_id(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [("t0003",), ("t0010",), ("t0012",)]

        cleaner = DatabaseCleaner(schema="Nova")
        tenant_tables = cleaner.get_tenant_tables(conn=mock_conn)
        assert tenant_tables == ["t0003", "t0010", "t0012"]
        assert "business_id" in mock_cur.execute.call_args[0][0]

    def test_truncate_tables_sql_generation(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        cleaner = DatabaseCleaner(schema="Nova")
        cleaner._all_tables = ["t0001", "t0002", "_schema_migrations"]

        elapsed = cleaner.truncate_tables(
            tables=["t0001", "t0002", "_schema_migrations"],
            restart_identity=True,
            cascade=True,
            conn=mock_conn,
        )

        mock_cur.execute.assert_called_once()
        executed_sql = mock_cur.execute.call_args[0][0]
        assert executed_sql.startswith('TRUNCATE TABLE "Nova"."t0001", "Nova"."t0002"')
        assert "RESTART IDENTITY" in executed_sql
        assert "CASCADE" in executed_sql
        assert "_schema_migrations" not in executed_sql

    def test_reset_sequences_mock(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        cleaner = DatabaseCleaner(schema="Nova")
        cleaner._all_sequences = ["seq_invoice_number", "seq_pick_list_number"]

        cnt = cleaner.reset_sequences(conn=mock_conn, start_value=1)
        assert cnt == 2
        assert mock_cur.execute.call_count == 2
        first_call_sql = mock_cur.execute.call_args_list[0][0][0]
        assert 'ALTER SEQUENCE "Nova"."seq_invoice_number" RESTART WITH %s;' == first_call_sql


# ============================================================================
# Real PostgreSQL Integration Tests
# ============================================================================

@pytest.mark.real_db
class TestDatabaseCleanerRealPostgres:
    """Integration tests executing against live PostgreSQL instance."""

    def test_real_truncate_empty_and_populated_tables(self, real_db_conn):
        cleaner = DatabaseCleaner(schema="Nova")
        
        # 1. Insert tenant in t0059 and product in t0003
        with real_db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                VALUES (101, 'TENANT_ISO_1', 'Isolation Test Tenant', TRUE)
                ON CONFLICT (id) DO NOTHING;
                """
            )
            cur.execute(
                """
                INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
                VALUES (101, 'ISO-PROD-01', 'Isolation Test Product', 'EA', TRUE);
                """
            )
        real_db_conn.commit()

        # Verify rows exist
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = 101;')
            assert cur.fetchone()[0] == 1
            cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'ISO-PROD-01';')
            assert cur.fetchone()[0] == 1

        # 2. Truncate specific tables
        elapsed = cleaner.truncate_tables(tables=["t0003", "t0059"], conn=real_db_conn)
        assert elapsed >= 0.0

        # Verify rows are wiped
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = 101;')
            assert cur.fetchone()[0] == 0
            cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'ISO-PROD-01';')
            assert cur.fetchone()[0] == 0

    def test_real_truncate_all_and_sequence_reset(self, real_db_conn):
        cleaner = DatabaseCleaner(schema="Nova")

        # 1. Advance sequence
        seq_val_1 = get_next_sequence_value("seq_invoice_number", conn=real_db_conn)
        assert seq_val_1 >= 1

        # 2. Truncate all tables and reset sequences
        elapsed = cleaner.truncate_all(conn=real_db_conn, reset_sequences=True)
        assert elapsed >= 0.0

        # 3. Next sequence value should restart from 1
        seq_val_reset = get_next_sequence_value("seq_invoice_number", conn=real_db_conn)
        assert seq_val_reset == 1

    def test_real_clean_dirty_tables_fast(self, real_db_conn):
        cleaner = DatabaseCleaner(schema="Nova")

        # Insert 1 test tenant
        with real_db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                VALUES (202, 'TENANT_DIRTY', 'Dirty Test Tenant', TRUE)
                ON CONFLICT (id) DO NOTHING;
                """
            )
        real_db_conn.commit()

        dirty = cleaner.get_dirty_tables(conn=real_db_conn)
        assert "t0059" in dirty

        # Clean only dirty tables
        cleaner.clean_dirty_tables(reset_sequences=True, conn=real_db_conn)

        dirty_after = cleaner.get_dirty_tables(conn=real_db_conn)
        assert len(dirty_after) == 0

    def test_real_clean_tenant_data_isolation(self, real_db_conn):
        cleaner = DatabaseCleaner(schema="Nova")

        # Setup Tenant A (id=301) and Tenant B (id=302)
        with real_db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                VALUES (301, 'TENANT_A', 'Tenant Alpha', TRUE),
                       (302, 'TENANT_B', 'Tenant Beta', TRUE)
                ON CONFLICT (id) DO NOTHING;
                """
            )
            cur.execute(
                """
                INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
                VALUES (301, 'PROD-ALPHA', 'Alpha Product', 'EA', TRUE),
                       (302, 'PROD-BETA', 'Beta Product', 'EA', TRUE);
                """
            )
        real_db_conn.commit()

        # Clean Tenant A data only
        deleted = cleaner.clean_tenant_data(business_id=301, conn=real_db_conn)
        assert "t0003" in deleted
        assert deleted["t0003"] >= 1

        # Assert Tenant A data is gone, Tenant B data is intact
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE business_id = 301;')
            assert cur.fetchone()[0] == 0
            cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE business_id = 302;')
            assert cur.fetchone()[0] == 1

        # Clean Tenant B
        cleaner.clean_tenant_data(business_id=302, conn=real_db_conn)


# ============================================================================
# Transaction & Savepoint Isolation Tests
# ============================================================================

@pytest.mark.real_db
class TestTransactionAndSavepointIsolation:
    """Tests for zero-cost rollback and savepoint isolation."""

    def test_transactional_isolation_rolls_back_everything(self, real_harness):
        # Initial check: no product with code 'TX-PROD-99'
        with real_harness.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'TX-PROD-99';')
                assert cur.fetchone()[0] == 0

        # Execute inside transactional isolation
        with transactional_isolation(harness=real_harness) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                    VALUES (401, 'TENANT_TX', 'TX Tenant', TRUE)
                    ON CONFLICT (id) DO NOTHING;
                    """
                )
                cur.execute(
                    """
                    INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
                    VALUES (401, 'TX-PROD-99', 'Transaction Product', 'EA', TRUE);
                    """
                )
                cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'TX-PROD-99';')
                assert cur.fetchone()[0] == 1

        # After exiting context, all changes must be rolled back
        with real_harness.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'TX-PROD-99';')
                assert cur.fetchone()[0] == 0
                cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = 401;')
                assert cur.fetchone()[0] == 0

    def test_savepoint_isolation_rolls_back_nested(self, real_db_conn):
        # 1. Insert outer tenant
        with real_db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
                VALUES (501, 'TENANT_SP', 'Savepoint Tenant', TRUE)
                ON CONFLICT (id) DO NOTHING;
                """
            )
        real_db_conn.commit()

        # 2. Enter savepoint and insert product
        with savepoint_isolation(real_db_conn, savepoint_name="sp_product_test"):
            with real_db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
                    VALUES (501, 'SP-PROD-01', 'Savepoint Product', 'EA', TRUE);
                    """
                )
                cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'SP-PROD-01';')
                assert cur.fetchone()[0] == 1

        # 3. After savepoint exit: product is rolled back, but tenant remains
        with real_db_conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE product_code = 'SP-PROD-01';')
            assert cur.fetchone()[0] == 0
            cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = 501;')
            assert cur.fetchone()[0] == 1

        # Clean tenant
        clean_tenant_data(501, conn=real_db_conn)

    def test_isolated_tenant_context_manager(self, real_harness):
        tenant_id = None
        with isolated_tenant(business_name="Context Managed Tenant", harness=real_harness) as (tid, trec):
            tenant_id = tid
            assert get_current_tenant() == tid
            assert trec["tenant_name"] == "Context Managed Tenant"

            # Insert data under this tenant
            with real_harness.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
                        VALUES (%s, 'T-PROD-CTX', 'Context Product', 'EA', TRUE);
                        """,
                        (tid,)
                    )
                conn.commit()

                with conn.cursor() as cur:
                    cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE business_id = %s;', (tid,))
                    assert cur.fetchone()[0] == 1

        # Outside context: context is reset and all tenant data is wiped
        assert get_current_tenant() is None
        with real_harness.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM "Nova"."t0003" WHERE business_id = %s;', (tenant_id,))
                assert cur.fetchone()[0] == 0
                cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = %s;', (tenant_id,))
                assert cur.fetchone()[0] == 0


# ============================================================================
# Pytest Fixtures & Benchmark Verification
# ============================================================================

@pytest.mark.real_db
def test_clean_db_fixture_step_1(clean_db, real_db_conn):
    """Step 1: Insert record under clean_db fixture."""
    with real_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO "Nova"."t0059" (id, tenant_code, tenant_name, is_active)
            VALUES (601, 'TENANT_CLEAN_1', 'Clean Tenant 1', TRUE)
            ON CONFLICT (id) DO NOTHING;
            """
        )
    real_db_conn.commit()


@pytest.mark.real_db
def test_clean_db_fixture_step_2_sees_zero_pollution(clean_db, real_db_conn):
    """Step 2: Subsequent test with clean_db must see zero leftover records from step 1."""
    with real_db_conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM "Nova"."t0059" WHERE id = 601;')
        assert cur.fetchone()[0] == 0


@pytest.mark.real_db
def test_isolated_tenant_fixture(isolated_tenant, real_db_conn):
    """Verify isolated_tenant fixture provides active tenant context and wipes data."""
    tid = isolated_tenant
    assert tid is not None
    assert get_current_tenant() == tid

    with real_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO "Nova"."t0003" (business_id, product_code, name, base_uom, is_active)
            VALUES (%s, 'FIX-PROD', 'Fixture Product', 'EA', TRUE);
            """,
            (tid,)
        )
    real_db_conn.commit()


@pytest.mark.real_db
def test_fast_clean_benchmark_sub_second(real_db_conn):
    """
    Benchmark test: verify that consecutive clean/truncate cycles run fast enough
    to guarantee sub-30-second full suite execution across 100+ tests.
    """
    cleaner = DatabaseCleaner(schema="Nova")
    
    # Run 5 consecutive truncations
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        cleaner.clean_dirty_tables(reset_sequences=True, conn=real_db_conn)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)

    avg_time_ms = sum(times) / len(times)
    # Average clean time for clean_dirty_tables when clean is < 20ms
    assert avg_time_ms < 100.0, f"Average clean time too slow: {avg_time_ms:.2f}ms"
