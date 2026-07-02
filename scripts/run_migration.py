import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    dbname = os.environ.get('DB_NAME', 'Stage')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', '')
    DB_URL = f'postgresql://{user}:{password}@{host}:{port}/{dbname}'

try:
    import psycopg2
except ImportError:
    print('FATAL: psycopg2 not installed — pip install psycopg2-binary')
    sys.exit(1)

MIGRATIONS_DIR = ROOT / 'database' / 'migrations'
TRACKING_TABLE = '"Nova"._migrations'

def get_applied(cursor):
    cursor.execute(f"SELECT filename FROM {TRACKING_TABLE} ORDER BY seq")
    return {row[0] for row in cursor.fetchall()}

def mark_applied(cursor, seq, filename, sql):
    cursor.execute(
        f"INSERT INTO {TRACKING_TABLE} (seq, filename, sql_hash) VALUES (%s, %s, %s)",
        (seq, filename, hash(sql))
    )

def main():
    conn = psycopg2.connect(DB_URL, sslmode=os.environ.get('DB_SSLMODE', 'require'))
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova"')

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            seq         INT  PRIMARY KEY,
            filename    TEXT NOT NULL,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            sql_hash    BIGINT
        )
    """)
    conn.commit()

    applied = get_applied(cur)
    files = sorted(MIGRATIONS_DIR.glob('*.sql'))
    ok = failed = 0

    for i, fpath in enumerate(files, 1):
        fname = fpath.name
        if fname in applied:
            print(f'  SKIP  {fname} (already applied)')
            ok += 1
            continue

        sql = fpath.read_text(encoding='utf-8')
        try:
            cur.execute(sql)
            mark_applied(cur, i, fname, sql)
            conn.commit()
            print(f'  OK    {fname}')
            ok += 1
        except Exception as e:
            conn.rollback()
            print(f'  FAIL  {fname} — {e}')
            failed += 1

    cur.close()
    conn.close()

    total = ok + failed
    print(f'\nDone — {ok}/{total} OK, {failed}/{total} Failed')
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
