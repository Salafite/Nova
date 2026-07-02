import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Nova')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='Nova' AND table_type='BASE TABLE' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {len(tables)}")
print("First 20:", tables[:20])
print("Has t0001:", 't0001' in tables)
print("Has T0001:", 'T0001' in tables)
# Try to query one
for tn in tables[:5]:
    try:
        cur.execute(f'SELECT count(*) FROM "{tn}"')
        print(f"  {tn}: {cur.fetchone()[0]} rows")
    except Exception as e:
        print(f"  {tn}: ERROR {e}")
conn.close()
