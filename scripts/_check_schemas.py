"""Check schemas and users in Neon"""
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

cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'public', 'pg_toast') ORDER BY schema_name")
schemas = [r[0] for r in cur.fetchall()]
print('Schemas:', schemas)

for s in schemas:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name", (s,))
    tables = [r[0] for r in cur.fetchall()]
    print(f'\nSchema "{s}" tables: {tables}')

    if 't0021' in tables:
        cur.execute('SELECT id, username, role FROM "%s".t0021 ORDER BY id' % s)
        users = cur.fetchall()
        print(f'  Users:')
        for u in users:
            print(f'    id={u[0]} username={u[1]} role={u[2]}')

    if 't0003' in tables:
        cur.execute('SELECT COUNT(*) FROM "%s".t0003' % s)
        count = cur.fetchone()[0]
        print(f'  Products: {count}')

conn.close()
