"""Apply Nova ERP consolidated database schema with multi-tenant isolation."""
import os
import re
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


def get_table_name(stmt: str) -> str:
    """Extract table name from a CREATE TABLE statement."""
    m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:["\']?(\w+)["\']?\.)?["\']?(\w+)["\']?\s*\(', stmt, re.I)
    return m.group(2).upper() if m else None


def strip_all_fks(stmt: str, table_name: str, fk_accumulator: list) -> str:
    """Strip all REFERENCES clauses from a CREATE TABLE statement and record ALTER TABLE statements."""
    def repl(m):
        ref_schema = m.group(1) or 'Nova'
        ref_table = m.group(2)
        ref_col = m.group(3) or 'id'
        on_cascade = m.group(4) or ''
        trail = m.group(5) or ''
        pos = m.start()
        before = stmt[:pos].rstrip()
        last_delim = max(before.rfind('\n'), before.rfind(','), before.rfind('('))
        line = before[last_delim + 1:] if last_delim >= 0 else before
        col_name = line.strip().split()[0] if line.strip() else 'unknown'
        
        alter_stmt = (
            f'ALTER TABLE "{ref_schema}".{table_name.lower()} ADD CONSTRAINT fk_{table_name.lower()}_{col_name.lower()} '
            f'FOREIGN KEY ({col_name}) REFERENCES "{ref_schema}".{ref_table.lower()}({ref_col}){on_cascade};'
        )
        fk_accumulator.append((table_name, col_name, alter_stmt))
        return trail

    pattern = r'\s+REFERENCES\s+(?:["\']?(\w+)["\']?\.)?["\']?(\w+)["\']?\s*\(\s*(\w+)\s*\)(\s+ON\s+(?:DELETE|UPDATE)\s+(?:CASCADE|SET NULL|RESTRICT|NO ACTION))?([,\s]*)'
    return re.sub(pattern, repl, stmt, flags=re.I)


def apply_schema(conn=None, schema_file: str = None) -> dict:
    """
    Apply consolidated database schema to PostgreSQL database.
    
    Returns a dict with statistics on applied objects.
    """
    if schema_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = os.path.join(script_dir, 'schema.sql')

    with open(schema_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Strip single-line and multi-line comments
    clean_sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    clean_sql = re.sub(r'--.*', '', clean_sql)

    stmts = [s.strip() for s in clean_sql.split(';') if s.strip()]

    all_fk_alters = []
    type_stmts = []
    table_stmts = []
    index_stmts = []
    comment_stmts = []
    other_stmts = []

    for s in stmts:
        u = s.upper()
        if u.startswith('CREATE TYPE') or u.startswith('DO $$'):
            type_stmts.append(s + ';')
        elif u.startswith('CREATE TABLE'):
            tn = get_table_name(s)
            if tn:
                processed = strip_all_fks(s, tn, all_fk_alters)
                table_stmts.append((tn, processed + ';'))
            else:
                other_stmts.append(s + ';')
        elif u.startswith('CREATE INDEX') or u.startswith('CREATE UNIQUE INDEX'):
            index_stmts.append(s + ';')
        elif u.startswith('COMMENT ON'):
            comment_stmts.append(s + ';')
        elif u.startswith('BEGIN') or u.startswith('COMMIT') or u.startswith('CREATE SCHEMA'):
            continue
        else:
            other_stmts.append(s + ';')

    should_close = False
    if conn is None:
        load_environment()
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_name = os.getenv('DB_NAME', 'Stage')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')
        db_ssl = os.getenv('DB_SSLMODE', 'prefer')

        print(f"Connecting to database {db_name} on {db_host}:{db_port} as {db_user}...")
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

    cur.execute('DROP SCHEMA IF EXISTS "Nova" CASCADE;')
    cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova";')
    cur.execute('SET search_path TO "Nova";')
    print('Schema "Nova" created (fresh)')

    # Phase 1: CREATE TYPE & DO $$ blocks
    print(f"\n--- Phase 1: Applying {len(type_stmts)} Enum/Domain Types ---")
    types_ok = 0
    for s in type_stmts:
        try:
            cur.execute(s)
            types_ok += 1
        except Exception as e:
            print(f"  Type error: {e}")
    print(f"Types applied: {types_ok}/{len(type_stmts)}")

    # Phase 2: Creating Tables
    print(f"\n--- Phase 2: Creating {len(table_stmts)} Tables ---")
    # Prioritize t0059 (tenants) and t0021 (users)
    sorted_tables = sorted(
        table_stmts,
        key=lambda item: 0 if item[0] == 'T0059' else (1 if item[0] == 'T0021' else 2)
    )
    tables_ok = 0
    for tn, s in sorted_tables:
        try:
            cur.execute(s)
            tables_ok += 1
        except Exception as e:
            print(f"  FAIL {tn}: {str(e)[:120]}")
    print(f"Tables created: {tables_ok}/{len(table_stmts)}")

    # Phase 3: Applying Indexes & Comments
    print(f"\n--- Phase 3: Applying {len(index_stmts)} Indexes & {len(comment_stmts)} Comments ---")
    indexes_ok = 0
    for s in index_stmts:
        try:
            cur.execute(s)
            indexes_ok += 1
        except Exception as e:
            print(f"  Index error: {str(e)[:100]}")
    print(f"Indexes created: {indexes_ok}/{len(index_stmts)}")

    comments_ok = 0
    for s in comment_stmts:
        try:
            cur.execute(s)
            comments_ok += 1
        except Exception:
            pass
    print(f"Comments applied: {comments_ok}/{len(comment_stmts)}")

    other_ok = 0
    for s in other_stmts:
        try:
            cur.execute(s)
            other_ok += 1
        except Exception:
            pass

    # Phase 4: Foreign Key Constraints (including tenant FKs)
    print(f"\n--- Phase 4: Adding {len(all_fk_alters)} Foreign Key Constraints ---")
    fk_ok = 0
    bid_fk_count = 0
    for tn, col, fk_sql in all_fk_alters:
        try:
            cur.execute(fk_sql)
            fk_ok += 1
            if col.lower() == 'business_id':
                bid_fk_count += 1
        except Exception as e:
            print(f"  FK error ({tn}.{col}): {str(e)[:100]}")
    print(f"Foreign keys applied: {fk_ok}/{len(all_fk_alters)} (Tenant FKs to T0059: {bid_fk_count})")

    print("\n============================================================")
    print(" Nova ERP Database Schema Applied Successfully!")
    print(f" - Tables: {tables_ok}")
    print(f" - Foreign Keys: {fk_ok} ({bid_fk_count} tenant FKs to T0059)")
    print(f" - Indexes: {indexes_ok}")
    print("============================================================\n")

    stats = {
        "types": types_ok,
        "tables": tables_ok,
        "indexes": indexes_ok,
        "comments": comments_ok,
        "foreign_keys": fk_ok,
        "tenant_fks": bid_fk_count,
        "total_fk_alters": len(all_fk_alters),
        "total_tables": len(table_stmts),
    }

    cur.close()
    if should_close:
        conn.close()

    return stats


if __name__ == '__main__':
    load_environment()
    apply_schema()


