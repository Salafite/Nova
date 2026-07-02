import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235 options=\'-c search_path=Nova\'')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'Nova' ORDER BY table_name")
tables = cur.fetchall()
print("Tables in Nova schema:", len(tables))
for t in tables[:10]:
    print(" ", t[0])
conn.close()
