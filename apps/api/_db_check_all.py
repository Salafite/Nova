import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Nova')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='Nova' AND table_type='BASE TABLE' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables found: {len(tables)}")
for t in ['t0001','t0021','t0023','t0098','t0099','T0001','T0021','T0023','T0098','T0099']:
    exists = t in tables
    if exists:
        cur.execute(f"SELECT count(*) FROM information_schema.columns WHERE table_schema='Nova' AND table_name='{t}'")
        cols = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM \"{t}\"")
        rows = cur.fetchone()[0]
        print(f"  {t}: exists={exists}, columns={cols}, rows={rows}")
    else:
        print(f"  {t}: NOT FOUND")
conn.close()
