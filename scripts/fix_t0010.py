"""Fix T0010 missing columns and add dependency tables"""
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

# Create T0083 (Price Lists) if not exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS "Nova".T0083 (
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(200) NOT NULL,
        currency      VARCHAR(10) DEFAULT 'USD',
        is_active     BOOLEAN NOT NULL DEFAULT true,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by    INT,
        updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_by    INT,
        update_number INT NOT NULL DEFAULT 1
    )
""")

# Create T0085 (Tax Rates) if not exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS "Nova".T0085 (
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(200) NOT NULL,
        rate          NUMERIC(5,2) NOT NULL DEFAULT 0,
        is_active     BOOLEAN NOT NULL DEFAULT true,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by    INT,
        updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_by    INT,
        update_number INT NOT NULL DEFAULT 1
    )
""")

# Add missing FK columns to T0010
cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'Nova' AND table_name = 't0010' AND column_name = 'default_price_list_id'
        ) THEN
            ALTER TABLE "Nova".T0010 ADD COLUMN default_price_list_id INT REFERENCES "Nova".T0083(id);
            ALTER TABLE "Nova".T0010 ADD COLUMN default_tax_rate_id INT REFERENCES "Nova".T0085(id);
            ALTER TABLE "Nova".T0010 ADD COLUMN payment_term_id INT REFERENCES "Nova".T0096(id);
        END IF;
    END
    $$;
""")

conn.commit()
print("T0083, T0085 created, T0010 columns added")

# Verify T0010 now works
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'Nova' AND table_name = 't0010' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print(f"T0010 columns: {cols}")

cur.close()
release_connection(conn)
