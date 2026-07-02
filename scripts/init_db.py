"""
Nova ERP — Database Initializer
Run once against a fresh PostgreSQL instance to create the schema, tables,
and seed data with proper bcrypt password hashes.

Usage:
    python scripts/init_db.py

Requires:
    - PostgreSQL running on localhost:5432
    - Database 'Stage' must exist
    - A user with CREATE SCHEMA privileges
"""

import os
import sys
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['DB_HOST'] = os.environ.get('DB_HOST', '192.168.1.100')
os.environ['DB_PORT'] = os.environ.get('DB_PORT', '5432')
os.environ['DB_NAME'] = os.environ.get('DB_NAME', 'Stage')
os.environ['DB_USER'] = os.environ.get('DB_USER', 'postgres')
os.environ['DB_PASSWORD'] = os.environ.get('DB_PASSWORD', 'e22a43790cd9405e092a55db8c3c1235')
os.environ['DB_SCHEMA'] = os.environ.get('DB_SCHEMA', 'Nova')

from packages.database.connection import get_connection, release_connection


SEED_USERS = [
    {'username': 'admin',  'password': 'admin123',  'full_name': 'Administrator', 'email': 'admin@novaerp.com', 'role': 'Admin',  'permissions': ['*']},
    {'username': 'sales',  'password': 'sales123',  'full_name': 'Sales User',    'email': 'sales@novaerp.com', 'role': 'Sales Rep', 'permissions': ['SALES_VIEW', 'CUSTOMERS_VIEW']},
    {'username': 'viewer', 'password': 'viewer123', 'full_name': 'Viewer User',   'email': 'viewer@novaerp.com','role': 'Viewer', 'permissions': ['DASHBOARD_VIEW', 'PRODUCTS_VIEW', 'CUSTOMERS_VIEW']},
]

SEED_NAV = [
    {'module_key': 'home',              'label': 'Home',          'label_ar': 'الرئيسية',     'icon': '🏠', 'section': 'Foundation',        'sort_order': 0},
    {'module_key': 'dashboard',         'label': 'Dashboard',    'label_ar': 'لوحة القيادة', 'icon': '📊', 'section': 'Foundation',        'sort_order': 1},
    {'module_key': 'pos',               'label': 'POS',          'label_ar': 'نقطة البيع',  'icon': '🛒', 'section': 'Foundation',        'sort_order': 2},
    {'module_key': 'products',          'label': 'Products',     'label_ar': 'المنتجات',     'icon': '📦', 'section': 'Foundation',        'sort_order': 3},
    {'module_key': 'inventory',         'label': 'Inventory',    'label_ar': 'المخزون',      'icon': '📋', 'section': 'Foundation',        'sort_order': 4},
    {'module_key': 'uom',               'label': 'UOM',          'label_ar': 'وحدات القياس', 'icon': '📏', 'section': 'Foundation',        'sort_order': 5},
    {'module_key': 'settings',          'label': 'Settings',     'label_ar': 'الإعدادات',   'icon': '⚙️', 'section': 'Administration',    'sort_order': 10},
    {'module_key': 'admin',             'label': 'Users & Roles','label_ar': 'المستخدمون',  'icon': '🔒', 'section': 'Administration',    'sort_order': 11},
]


def run_schema_sql(conn, path: str):
    with open(path, 'r', encoding='utf-8') as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f'  ✓ Executed {path}')


def main():
    conn = get_connection()
    try:
        # 1. Create Nova schema
        with conn.cursor() as cur:
            cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova"')
        conn.commit()
        print('✓ Schema "Nova" ready')

        # 2. Run the full schema migration
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations', '001_full_schema.sql')
        if os.path.exists(schema_path):
            run_schema_sql(conn, schema_path)
        else:
            print('! Migration file not found; tables may be missing')

        # 3. Seed users with bcrypt password hashes
        with conn.cursor() as cur:
            for u in SEED_USERS:
                pw_hash = bcrypt.hashpw(u['password'].encode(), bcrypt.gensalt()).decode()
                cur.execute(
                    """INSERT INTO "Nova".t0021 (username, password_hash, full_name, email, role, permissions, status)
                       VALUES (%s, %s, %s, %s, %s, %s, 'Active')
                       ON CONFLICT (username) DO UPDATE SET
                           password_hash = EXCLUDED.password_hash,
                           full_name = EXCLUDED.full_name,
                           email = EXCLUDED.email,
                           role = EXCLUDED.role""",
                    (u['username'], pw_hash, u['full_name'], u['email'], u['role'], u['permissions'])
                )
                print(f'  ✓ User "{u["username"]}" seeded')
        conn.commit()

        # 4. Seed navigation items
        with conn.cursor() as cur:
            for n in SEED_NAV:
                cur.execute(
                    """INSERT INTO "Nova".t0022 (module_key, label, label_ar, icon, section, sort_order, is_active)
                       VALUES (%s, %s, %s, %s, %s, %s, true)
                       ON CONFLICT DO NOTHING""",
                    (n['module_key'], n['label'], n['label_ar'], n['icon'], n['section'], n['sort_order'])
                )
        conn.commit()
        print('✓ Navigation seeded')

        print('\n✅ Database initialization complete!')
        print('   Default credentials: admin / admin123')

    except Exception as e:
        conn.rollback()
        print(f'\n❌ Initialization failed: {e}')
        raise
    finally:
        release_connection(conn)


if __name__ == '__main__':
    main()
