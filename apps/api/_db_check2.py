import psycopg2
conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235')
cur = conn.cursor()
cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
schemas = cur.fetchall()
print("Schemas:")
for s in schemas:
    print(" ", s[0])
conn.close()
