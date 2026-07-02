import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235', options='-c search_path=Core')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='Core' AND table_name LIKE 'T0%' ORDER BY table_name")
tables = cur.fetchall()
print("T-prefixed tables in Core schema:", len(tables), "\n")
for t in tables:
    print(" ", t[0])
conn.close()
