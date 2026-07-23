"""Copy seed data using matching columns only"""
import os
os.environ['DB_SSLMODE'] = 'require'
import psycopg2

conn = psycopg2.connect(
    host='ep-rapid-snow-asuk4t8k-pooler.c-4.eu-central-1.aws.neon.tech',
    port=5432, dbname='neondb',
    user='neondb_owner',
    password='npg_As6EG7upfkHU',
    sslmode='require'
)
cur = conn.cursor()

tables = ['t0003','t0004','t0007','t0008','t0009','t0010','t0011','t0012','t0013','t0014','t0015','t0083','t0085']

for t in tables:
    # Get columns from both schemas
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='nova_erp' AND table_name=%s ORDER BY ordinal_position", (t,))
    src_cols = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='Nova' AND table_name=%s ORDER BY ordinal_position", (t,))
    dst_cols = [r[0] for r in cur.fetchall()]
    
    # Common columns (exclude id - let serial auto-generate)
    common = [c for c in src_cols if c in dst_cols and c != 'id']
    
    if not common:
        print(f'Skipping {t} (no common columns)')
        continue
    
    cols_str = ', '.join(common)
    
    # Clear destination
    cur.execute(f'DELETE FROM "Nova".{t}')
    cur.execute(f'ALTER SEQUENCE IF EXISTS "Nova".{t}_id_seq RESTART WITH 1')
    
    # Copy
    cur.execute(f'SELECT {cols_str} FROM nova_erp.{t} ORDER BY id')
    rows = cur.fetchall()
    if rows:
        ph = ', '.join(['%s'] * len(common))
        for row in rows:
            cur.execute(f'INSERT INTO "Nova".{t} ({cols_str}) VALUES ({ph})', row)
        print(f'Copied {len(rows)} rows to "Nova".{t}')

conn.commit()

# Verify
cur.execute('SELECT COUNT(*) FROM "Nova".t0003')
print(f'\nProducts: {cur.fetchone()[0]}')
cur.execute('SELECT id, name, sku, price FROM "Nova".t0003 ORDER BY id LIMIT 5')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]} ({r[2]}) ${r[3]}')

conn.close()
