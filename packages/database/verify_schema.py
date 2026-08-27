"""Verify Nova ERP consolidated database schema and multi-tenant isolation constraints."""
import os
import sys
import psycopg2
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from standard locations."""
    env_locations = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
    ]
    for env_path in env_locations:
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)


def verify_schema(conn=None) -> dict:
    """
    Verify schema integrity and multi-tenant isolation columns, FKs, and indexes.
    
    Returns a dict with verification results and statistics.
    """
    should_close = False
    if conn is None:
        load_environment()
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_name = os.getenv('DB_NAME', 'Stage')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')
        db_ssl = os.getenv('DB_SSLMODE', 'prefer')

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_pass,
            sslmode=db_ssl,
        )
        conn.autocommit = True
        should_close = True

    cur = conn.cursor()
    cur.execute('SET search_path TO "Nova"')

    errors = []

    # 1. Base Tables
    cur.execute("""
        SELECT LOWER(table_name)
        FROM information_schema.tables
        WHERE table_schema='Nova' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)
    tables = [r[0] for r in cur.fetchall()]
    expected_tables = [f"t{i:04d}" for i in range(1, 110)]
    missing_tables = [t for t in expected_tables if t not in tables]
    if missing_tables:
        errors.append(f"Missing tables ({len(missing_tables)}): {missing_tables}")

    # Business tables are all tables except T0059 (tenant organization master)
    business_tables = [t for t in tables if t != 't0059']
    expected_business_tables = [t for t in expected_tables if t != 't0059']

    # 2. Views
    cur.execute("""
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema='Nova'
        ORDER BY table_name
    """)
    views = [r[0] for r in cur.fetchall()]

    # 3. Columns & business_id column verification
    cur.execute("""
        SELECT count(*)
        FROM information_schema.columns
        WHERE table_schema='Nova'
    """)
    total_cols = cur.fetchone()[0]

    cur.execute("""
        SELECT LOWER(table_name), data_type
        FROM information_schema.columns
        WHERE table_schema='Nova' AND LOWER(column_name)='business_id'
    """)
    bid_col_rows = cur.fetchall()
    tables_with_bid = {r[0] for r in bid_col_rows}
    missing_bid_cols = [t for t in expected_business_tables if t not in tables_with_bid]
    if missing_bid_cols:
        errors.append(f"Missing business_id column in tables ({len(missing_bid_cols)}): {missing_bid_cols}")

    # 4. Foreign Key Constraints (total & tenant-specific FKs referencing T0059)
    cur.execute("""
        SELECT count(*)
        FROM information_schema.table_constraints
        WHERE table_schema='Nova' AND constraint_type='FOREIGN KEY'
    """)
    total_fks = cur.fetchone()[0]

    # Query foreign keys referencing T0059 on business_id
    cur.execute("""
        SELECT LOWER(tc.table_name), LOWER(kcu.column_name), LOWER(ccu.table_name)
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'Nova'
            AND LOWER(kcu.column_name) = 'business_id'
            AND LOWER(ccu.table_name) = 't0059'
    """)
    tenant_fk_rows = cur.fetchall()
    tables_with_tenant_fk = {r[0] for r in tenant_fk_rows}
    missing_tenant_fks = [t for t in expected_business_tables if t not in tables_with_tenant_fk]
    if missing_tenant_fks:
        errors.append(f"Missing foreign key to T0059 on business_id ({len(missing_tenant_fks)}): {missing_tenant_fks}")

    # 5. Primary Keys
    cur.execute("""
        SELECT count(*)
        FROM information_schema.table_constraints
        WHERE table_schema='Nova' AND constraint_type='PRIMARY KEY'
    """)
    total_pks = cur.fetchone()[0]

    # 6. Indexes & Tenant Index Verification
    cur.execute("""
        SELECT LOWER(tablename), LOWER(indexname), LOWER(indexdef)
        FROM pg_indexes
        WHERE schemaname='Nova'
    """)
    all_indexes = cur.fetchall()
    total_indexes = len(all_indexes)

    tables_with_single_idx = set()
    tables_with_comp_idx = set()

    for tablename, indexname, indexdef in all_indexes:
        # Check single index on business_id (e.g. USING btree (business_id))
        if '(business_id)' in indexdef.replace(' ', '') or indexname.endswith('_business_id'):
            tables_with_single_idx.add(tablename)
        # Check composite index on (business_id, id) (e.g. USING btree (business_id, id))
        if '(business_id,id)' in indexdef.replace(' ', '') or indexname.endswith('_business_id_id'):
            tables_with_comp_idx.add(tablename)

    missing_single_idx = [t for t in expected_business_tables if t not in tables_with_single_idx]
    missing_comp_idx = [t for t in expected_business_tables if t not in tables_with_comp_idx]

    if missing_single_idx:
        errors.append(f"Missing single index idx_tXXXX_business_id ({len(missing_single_idx)}): {missing_single_idx}")
    if missing_comp_idx:
        errors.append(f"Missing composite index idx_tXXXX_business_id_id ({len(missing_comp_idx)}): {missing_comp_idx}")

    # 7. Enum types verification (order_status)
    cur.execute("""
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'order_status'
        ORDER BY e.enumsortorder
    """)
    order_status_enums = [r[0] for r in cur.fetchall()]
    credit_hold_enum_present = 'Credit Hold' in order_status_enums
    if order_status_enums and not credit_hold_enum_present:
        errors.append("Missing 'Credit Hold' in order_status enum")

    # 8. Sales order credit hold columns verification (T0012)
    cur.execute("""
        SELECT LOWER(column_name)
        FROM information_schema.columns
        WHERE table_schema='Nova' AND LOWER(table_name)='t0012'
    """)
    t0012_cols = {r[0] for r in cur.fetchall()}
    expected_hold_cols = ['hold_reason', 'hold_released_by', 'hold_released_at', 'hold_release_reason']
    missing_hold_cols = [c for c in expected_hold_cols if c not in t0012_cols]
    if missing_hold_cols and 't0012' in tables:
        errors.append(f"Missing credit hold columns in t0012 ({len(missing_hold_cols)}): {missing_hold_cols}")

    # 9. Seed Data Check (optional / non-fatal)
    seed_counts = {}
    for tcode, label in [('t0003', 'Products'), ('t0010', 'Customers'), ('t0011', 'Suppliers'), ('t0021', 'Users'), ('t0059', 'Tenants')]:
        if tcode in tables:
            try:
                cur.execute(f'SELECT count(*) FROM "{tcode}"')
                seed_counts[label] = cur.fetchone()[0]
            except Exception:
                seed_counts[label] = 0

    success = len(errors) == 0

    results = {
        "success": success,
        "total_tables": len(tables),
        "expected_tables_count": len(expected_tables),
        "missing_tables": missing_tables,
        "business_tables_count": len(business_tables),
        "tables_with_business_id": len(tables_with_bid),
        "missing_business_id_columns": missing_bid_cols,
        "total_foreign_keys": total_fks,
        "tenant_fks_count": len(tables_with_tenant_fk),
        "missing_tenant_fks": missing_tenant_fks,
        "tenant_single_indexes_count": len(tables_with_single_idx),
        "missing_single_indexes": missing_single_idx,
        "tenant_composite_indexes_count": len(tables_with_comp_idx),
        "missing_composite_indexes": missing_comp_idx,
        "order_status_enums": order_status_enums,
        "credit_hold_enum_present": credit_hold_enum_present,
        "t0012_hold_columns_present": [c for c in expected_hold_cols if c in t0012_cols],
        "missing_hold_columns": missing_hold_cols,
        "total_columns": total_cols,
        "total_primary_keys": total_pks,
        "total_indexes": total_indexes,
        "views": views,
        "seed_data": seed_counts,
        "errors": errors,
    }

    cur.close()
    if should_close:
        conn.close()

    return results


def print_verification_report(results: dict):
    """Format and print verification report to stdout."""
    print("\n============================================================")
    print(" Nova ERP Database Schema & Multi-Tenancy Verification")
    print("============================================================")
    print(f" Total Tables:           {results['total_tables']} / {results['expected_tables_count']}")
    print(f" Total Views:            {len(results['views'])}")
    print(f" Total Columns:          {results['total_columns']}")
    print(f" Total Primary Keys:     {results['total_primary_keys']}")
    print(f" Total Foreign Keys:     {results['total_foreign_keys']}")
    print(f" Total Indexes:          {results['total_indexes']}")
    print("------------------------------------------------------------")
    print(" Multi-Tenant Isolation Status:")
    print(f"  - Business Tables:          {results['business_tables_count']} (excl. T0059 tenant master)")
    print(f"  - Tables with business_id:  {results['tables_with_business_id']}/{results['business_tables_count']}")
    print(f"  - Tenant Foreign Keys:      {results['tenant_fks_count']}/{results['business_tables_count']} referencing T0059")
    print(f"  - Single Indexes:           {results['tenant_single_indexes_count']}/{results['business_tables_count']} on business_id")
    print(f"  - Composite Indexes:        {results['tenant_composite_indexes_count']}/{results['business_tables_count']} on (business_id, id)")
    print("------------------------------------------------------------")
    print(" Credit Hold Workflow Status:")
    print(f"  - 'Credit Hold' in order_status enum: {'YES' if results.get('credit_hold_enum_present') else 'NO'}")
    print(f"  - T0012 hold metadata columns:        {len(results.get('t0012_hold_columns_present', []))}/4 present")
    print("------------------------------------------------------------")
    if results['seed_data']:
        print(" Seed Data:")
        for label, count in results['seed_data'].items():
            print(f"  - {label}: {count} records")
        print("------------------------------------------------------------")

    if results['success']:
        print(" [PASSED] Multi-tenant database schema verification successful! All isolation constraints satisfied.")
    else:
        print(" [FAILED] Schema verification errors found:")
        for err in results['errors']:
            print(f"   * {err}")
    print("============================================================\n")


if __name__ == '__main__':
    load_environment()
    try:
        res = verify_schema()
        print_verification_report(res)
        sys.exit(0 if res['success'] else 1)
    except Exception as e:
        print(f"Error during schema verification: {e}", file=sys.stderr)
        sys.exit(1)

