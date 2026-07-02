import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'), port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'Stage'), user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
)
cur = conn.cursor()
cur.execute('SET search_path TO "Nova"')

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='Nova' AND table_type='BASE TABLE' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f'Tables ({len(tables)}): {", ".join(tables)}')

cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema='Nova' ORDER BY table_name")
views = [r[0] for r in cur.fetchall()]
print(f'Views ({len(views)}): {", ".join(views)}')

cur.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='Nova'")
cols = cur.fetchone()[0]
print(f'Total columns: {cols}')

cur.execute("SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='Nova' AND constraint_type='FOREIGN KEY'")
fks = cur.fetchone()[0]
print(f'Foreign keys: {fks}')

cur.execute("SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='Nova' AND constraint_type='PRIMARY KEY'")
pks = cur.fetchone()[0]
print(f'Primary keys: {pks}')

# Check seed data
cur.execute("SELECT count(*) FROM T0003")
print(f'Products (T0003): {cur.fetchone()[0]}')
cur.execute("SELECT count(*) FROM T0010")
print(f'Customers (T0010): {cur.fetchone()[0]}')
cur.execute("SELECT count(*) FROM T0011")
print(f'Suppliers (T0011): {cur.fetchone()[0]}')
cur.execute("SELECT count(*) FROM T0021")
print(f'System Users (T0021): {cur.fetchone()[0]}')

cur.close()
conn.close()
