import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Nova')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='nova' AND table_type='BASE TABLE' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
# Check for 0098, 0099
for tn in tables:
    if '0098' in tn or '0099' in tn:
        print(f"Found: {tn}")
print(f"Total: {len(tables)}")
# Check if any T-prefixed tables exist
t_tables = [t for t in tables if t.startswith('t')]
print(f"T-tables: {len(t_tables)}")
conn.close()
