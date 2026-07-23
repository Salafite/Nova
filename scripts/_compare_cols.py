"""Compare columns between nova_erp and Nova schemas"""
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

tables = ['t0003', 't0004', 't0007', 't0008', 't0009', 't0010', 't0011', 't0012', 't0013', 't0014', 't0015', 't0083', 't0085']

for t in tables:
    print(f'\n--- {t} ---')
    for schema in ['nova_erp', 'Nova']:
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_schema=%s AND table_name=%s 
            ORDER BY ordinal_position
        """, (schema, t))
        cols = cur.fetchall()
        print(f'  {schema}: {[c[0] for c in cols]}')

conn.close()
