import psycopg2
import os
from pathlib import Path

conn = psycopg2.connect('dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235')
conn.autocommit = True
cur = conn.cursor()

# Create Nova schema
cur.execute("CREATE SCHEMA IF NOT EXISTS Nova")
print("Schema Nova created/verified")

# Switch to Nova
cur.execute("SET search_path TO Nova")

# Read and execute schema.sql
schema_path = Path(__file__).resolve().parent.parent.parent / 'packages' / 'database' / 'schema.sql'
sql = schema_path.read_text(encoding='utf-8')

# Split by semicolons and execute each statement
statements = sql.split(';')
count = 0
for stmt in statements:
    stmt = stmt.strip()
    if stmt and not stmt.startswith('--'):
        try:
            cur.execute(stmt)
            count += 1
        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Statement: {stmt[:100]}...")

print(f"Executed {count} statements")
cur.close()
conn.close()
