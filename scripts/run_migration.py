"""Run migration to add missing tables"""
import os
os.environ['DB_HOST'] = '192.168.1.100'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'Stage'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'e22a43790cd9405e092a55db8c3c1235'
os.environ['DB_SCHEMA'] = 'Nova'

import sys
sys.path.insert(0, 'packages/database')
from connection import get_connection, release_connection

conn = get_connection()
cur = conn.cursor()

migration_path = 'database/migrations/001_full_schema.sql'
with open(migration_path, 'r', encoding='utf-8') as f:
    sql = f.read()

cur.execute(sql)
conn.commit()
print("Migration executed successfully")

cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'Nova' AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")
tables = [r[0] for r in cur.fetchall()]
print(f"\nTables now in Nova schema ({len(tables)}):")
for t in tables:
    print(f"  {t}")

cur.close()
release_connection(conn)
