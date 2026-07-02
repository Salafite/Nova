import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Nova')
conn.autocommit = True
cur = conn.cursor()
for tn in ['t0001', 't0021', 't0023', 't0098', 't0099']:
    try:
        cur.execute(f'SELECT count(*) FROM {tn}')
        print(f"  {tn}: {cur.fetchone()[0]} rows")
    except Exception as e:
        print(f"  {tn}: ERROR {str(e)[:80]}")
conn.close()
