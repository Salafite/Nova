"""Verify all seeded data in Neon"""
import os
os.environ['DB_SSLMODE'] = 'require'
import psycopg2

conn = psycopg2.connect(
    host='ep-rapid-snow-asuk4t8k-pooler.c-4.eu-central-1.aws.neon.tech',
    port=5432, dbname='neondb',
    user='neondb_owner',
    password='npg_As6EG7upfkHU',
    sslmode='require'
)
cur = conn.cursor()

checks = [
    ('t0001', 'UOM'),
    ('t0003', 'Products'),
    ('t0004', 'Barcodes'),
    ('t0007', 'Product UOMs'),
    ('t0008', 'Warehouses'),
    ('t0009', 'Stock Records'),
    ('t0010', 'Customers'),
    ('t0011', 'Suppliers'),
    ('t0012', 'Sales Orders'),
    ('t0013', 'SO Line Items'),
    ('t0014', 'Purchase Orders'),
    ('t0015', 'PO Line Items'),
    ('t0021', 'Users'),
    ('t0083', 'Price Lists'),
    ('t0085', 'Tax Rates'),
]

all_good = True
for table, label in checks:
    cur.execute('SELECT COUNT(*) FROM nova_erp.%s' % table)
    count = cur.fetchone()[0]
    status = 'OK' if count > 0 else 'EMPTY'
    if count == 0:
        all_good = False
    print('  %s (%s): %d %s' % (label, table, count, status))

print()
if all_good:
    print('All tables have data')
else:
    print('Some tables are empty!')

# Sample products
cur.execute('SELECT id, name, sku, price, cost_price, category, brand FROM nova_erp.t0003 ORDER BY id LIMIT 49')
products = cur.fetchall()
print('\nAll %d products:' % len(products))
for p in products:
    print('  %2d: %s (%s) $%.2f' % (p[0], p[1][:40], p[2], p[3]))

conn.close()
