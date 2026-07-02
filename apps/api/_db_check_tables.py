import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Nova')
cur = conn.cursor()
for tbl in ['T0023', 'T0098', 'T0099']:
    cur.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='Nova' AND table_name='{tbl}' ORDER BY ordinal_position")
    cols = cur.fetchall()
    print(f"\n{tbl} columns:")
    for c in cols:
        print(f"  {c[0]:20s} {c[1]:15s} nullable={c[2]}")
conn.close()
