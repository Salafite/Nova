import bcrypt
import psycopg2

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

conn = psycopg2.connect("dbname=Stage user=postgres password=e22a43790cd9405e092a55db8c3c1235 options='-c search_path=\"Nova\"'")
cur = conn.cursor()

users = ['admin', 'sales', 'viewer']
for u in users:
    cur.execute("UPDATE T0021 SET password_hash = %s WHERE username = %s", (hash_pw(u), u))

conn.commit()
print("Passwords updated.")
