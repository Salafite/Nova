import os
import re
import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api', '.env')
load_dotenv(dotenv_path=env_path, override=True)

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'), port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'Stage'), user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
)
conn.autocommit = True
cur = conn.cursor()

cur.execute('DROP SCHEMA IF EXISTS Nova CASCADE')
cur.execute('CREATE SCHEMA Nova')
cur.execute('SET search_path TO Nova')
print('Schema Nova created (fresh)')

script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'schema.sql'), 'r', encoding='utf-8') as f:
    sql = f.read()

sql = re.sub(r'--.*', '', sql)

stmts = [s.strip() + ';' for s in sql.split(';') if s.strip()]

# Phase 1: CREATE TYPE
for s in stmts:
    if s.upper().startswith('CREATE TYPE'):
        cur.execute(s)
print('Types done')

# Phase 2: CREATE TABLE - strip ALL FK refs, collect ALTERs
def get_tn(s):
    m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\']?(\w+)["\']?\s*\(', s, re.I)
    return m.group(1).upper() if m else None

all_fk_alters = []

def strip_all_fk(stmt, tn):
    """Strip all REFERENCES clauses, record FK alters."""
    def repl(m):
        ref_table = m.group(1)
        trail = m.group(3) or ''
        on_cascade = m.group(2) or ''
        pos = m.start()
        # Find the column name: look backwards from match to previous newline
        before = stmt[:pos].rstrip()
        last_newline = before.rfind('\n')
        line = before[last_newline + 1:] if last_newline >= 0 else before
        col_name = line.strip().split()[0] if line.strip() else 'unknown'
        all_fk_alters.append(
            f'ALTER TABLE {tn} ADD CONSTRAINT fk_{tn}_{col_name} '
            f'FOREIGN KEY ({col_name}) REFERENCES {ref_table}(id){on_cascade};'
        )
        return trail

    return re.sub(
        r'\s+REFERENCES\s+["\']?(\w+)["\']?\(\w+\)(\s+ON\s+(?:DELETE|UPDATE)\s+CASCADE)?([,\s]*)',
        repl, stmt, flags=re.I
    )

t0021_sql = None
other_tables = []
for s in stmts:
    if not s.upper().startswith('CREATE TABLE'):
        continue
    tn = get_tn(s)
    if not tn:
        continue
    processed = strip_all_fk(s, tn)
    if tn == 'T0021':
        t0021_sql = processed
    else:
        other_tables.append((tn, processed))

# Execute all tables
def exec_safe(s, label, ignore_errors=False):
    try:
        cur.execute(s)
        return True
    except Exception as e:
        if not ignore_errors:
            print(f'  FAIL {label}: {str(e)[:120]}')
        return False

if t0021_sql:
    exec_safe(t0021_sql, 'T0021')
    print('T0021 created')

ok = sum(1 for tn, s in other_tables if exec_safe(s, tn))
print(f'Tables: {ok}/{len(other_tables)}')

# Phase 3: Other statements (COMMENT, INDEX, INSERT)
other_ok = 0
for s in stmts:
    u = s.upper().strip()
    if u.startswith('CREATE TYPE') or u.startswith('CREATE TABLE'):
        continue
    try:
        cur.execute(s)
        other_ok += 1
    except Exception:
        pass
print(f'Other: {other_ok}')

# Phase 4: FK constraints
fk_ok = 0
for fk in all_fk_alters:
    try:
        cur.execute(fk)
        fk_ok += 1
    except Exception as e:
        if fk_ok + (len(all_fk_alters) - all_fk_alters.index(fk) - 1) < 5:
            print(f'FK ERR: {fk[:120]} -> {str(e)[:100]}')
print(f'FK: {fk_ok}/{len(all_fk_alters)}')

print('Done')
cur.close()
conn.close()
