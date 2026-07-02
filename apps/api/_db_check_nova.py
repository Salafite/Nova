import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235')
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
for s in cur.fetchall():
    print(f"Schema: '{s[0]}'")
cur.execute('SET search_path TO "Nova"')
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY table_name LIMIT 3")
for r in cur.fetchall():
    print(f"Table info: table_name='{r[0]}'")
# Try to query without schema
for tn in ['t0001', 'T0001', '"t0001"', '"T0001"']:
    try:
        cur.execute(f'SELECT count(*) FROM {tn}')
        print(f"  {tn}: {cur.fetchone()[0]} rows")
    except Exception as e:
        err = str(e)[:60]
        print(f"  {tn}: ERROR {err}")
cur.close()
conn.close()
