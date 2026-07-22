"""Seed electronics store test data directly into the Nova ERP database.

Usage:
    python scripts/seed_electronics.py
    python scripts/seed_electronics.py --clear   # Clear electronics data first

Connects using the same DB config from .env as the main app.
Idempotent — safe to run multiple times.
"""

import os
import sys
import argparse
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from packages.database.connection import get_connection, release_connection


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def conn_str(conn):
    return f'{conn.info.dsn}'


# ── Column helpers ────────────────────────────────────────────────────────

_BASE_AUDIT = """created_at=now(), created_by=1, updated_at=now(), updated_by=1, update_number=1"""


def _insert(conn, table, columns, values_rows, conflict=None):
    """Batch insert into ``Nova``.``table``.

    ``values_rows`` is a list of tuples, one per row.
    ``conflict`` is optional ON CONFLICT clause suffix, e.g. ``(id) DO NOTHING``.
    """
    placeholders = ', '.join([f'%s'] * len(columns))
    col_list = ', '.join(columns)
    sql = f'INSERT INTO "Nova".{table} ({col_list}) VALUES ({placeholders})'
    if conflict:
        sql += f' ON CONFLICT {conflict}'
    sql += ' RETURNING id;'

    ids = []
    with conn.cursor() as cur:
        for row in values_rows:
            try:
                cur.execute(sql, row)
                ids.append(cur.fetchone()[0])
            except Exception as exc:
                conn.rollback()
                raise RuntimeError(f'Insert into {table} failed: {exc}') from exc
    conn.commit()
    return ids


def _get_id(conn, table, column, value):
    """Return the id of a row matched by ``column = value``, or None."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT id FROM "Nova".{table} WHERE {column} = %s', (value,))
        row = cur.fetchone()
        return row[0] if row else None


def _get_ids(conn, table, column, values):
    """Return a dict {value: id} for rows where column IN values."""
    if not values:
        return {}
    with conn.cursor() as cur:
        placeholders = ', '.join([f'%s'] * len(values))
        cur.execute(f'SELECT id, {column} FROM "Nova".{table} WHERE {column} IN ({placeholders})', list(values))
        return {row[1]: row[0] for row in cur.fetchall()}


def _ensure_missing_tables(conn):
    """Create T0083 (Price Lists) and T0085 (Tax Rates) if they don't exist."""
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Nova".t0083 (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(200) NOT NULL,
                code            VARCHAR(20) NOT NULL UNIQUE,
                description     TEXT,
                currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
                is_active       BOOLEAN NOT NULL DEFAULT true,
                is_default      BOOLEAN NOT NULL DEFAULT false,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by      INT,
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_by      INT,
                update_number   INT NOT NULL DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Nova".t0085 (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(100) NOT NULL,
                code            VARCHAR(20) NOT NULL UNIQUE,
                rate            NUMERIC(5,2) NOT NULL DEFAULT 0,
                type            VARCHAR(20) NOT NULL DEFAULT 'Sales',
                description     TEXT,
                is_active       BOOLEAN NOT NULL DEFAULT true,
                is_default      BOOLEAN NOT NULL DEFAULT false,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by      INT,
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_by      INT,
                update_number   INT NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f'  Note: Could not create tables (they may already exist): {exc}')
    finally:
        cur.close()


def _ensure_pcs_id(conn):
    """Return the id of the 'pcs' UOM, creating it if needed."""
    uid = _get_id(conn, 't0001', 'uom_code', 'pcs')
    if uid:
        return uid
    ids = _insert(conn, 't0001', ['uom_code', 'uom_name', 'category', 'is_base_unit', 'created_at', 'created_by'],
                  [('pcs', 'Piece', 'Quantity', True, datetime.now(), 1)])
    return ids[0]


def _ensure_warehouse_id(conn, name, location):
    wid = _get_id(conn, 't0008', 'name', name)
    if wid:
        return wid
    ids = _insert(conn, 't0008', ['name', 'location', 'created_at', 'created_by'],
                  [(name, location, datetime.now(), 1)])
    return ids[0]


def _ensure_price_list_id(conn, name, code, currency='USD', is_default=False):
    pid = _get_id(conn, 't0083', 'code', code)
    if pid:
        return pid
    ids = _insert(conn, 't0083', ['name', 'code', 'currency', 'is_default', 'created_at', 'created_by'],
                  [(name, code, currency, is_default, datetime.now(), 1)])
    return ids[0]


def _ensure_tax_rate_id(conn, name, code, rate):
    tid = _get_id(conn, 't0085', 'code', code)
    if tid:
        return tid
    ids = _insert(conn, 't0085', ['name', 'code', 'rate', 'type', 'is_active', 'created_at', 'created_by'],
                  [(name, code, rate, 'Sales', True, datetime.now(), 1)])
    return ids[0]


def _ensure_customer_group(conn, name):
    """Return the group_name (T0010.group_name is a varchar, not FK). This is a label."""
    return name


# ── Data definitions ──────────────────────────────────────────────────────

CATEGORIES = [
    'Laptops', 'Smartphones', 'Tablets', 'Audio', 'Accessories',
    'Components', 'Networking', 'Wearables', 'Gaming', 'Cameras',
]

BRANDS = {
    'Apple': ['MacBook Pro 14"', 'MacBook Air 13"', 'iPhone 15 Pro', 'iPhone 15',
              'iPad Pro 11"', 'iPad Air', 'AirPods Pro', 'Apple Watch Ultra 2',
              'AirTag', 'MagSafe Charger'],
    'Samsung': ['Galaxy Book3 Pro', 'Galaxy S24 Ultra', 'Galaxy Tab S9',
                'Galaxy Watch 6', 'Galaxy Buds2 Pro', 'T7 Portable SSD 1TB'],
    'Sony': ['WH-1000XM5 Headphones', 'WF-1000XM5 Earbuds', 'Alpha 7 IV Camera',
             'PlayStation 5 Console', 'DualSense Controller'],
    'Dell': ['XPS 15', 'XPS 13 Plus', 'UltraSharp 27" Monitor'],
    'Lenovo': ['ThinkPad X1 Carbon Gen 11', 'ThinkVision 24" Monitor'],
    'Logitech': ['MX Master 3S Mouse', 'MX Keys Keyboard', 'C920 Webcam'],
    'Anker': ['PowerCore 26800', 'USB-C Cable 6ft (3-Pack)', 'Nano II 65W Charger'],
    'Microsoft': ['Surface Pro 9', 'Xbox Series X', 'Surface Arc Mouse'],
    'Seagate': ['FireCuda 530 2TB', 'Backup Plus 5TB HDD'],
    'Corsair': ['Vengeance DDR5 32GB', 'RM850x PSU', 'K70 RGB Keyboard'],
    'Intel': ['Core i7-14700K', 'Core i9-14900K'],
    'AMD': ['Ryzen 7 7800X3D', 'Ryzen 9 7950X'],
    'NVIDIA': ['GeForce RTX 4080', 'GeForce RTX 4090'],
    'ASUS': ['ROG Strix RTX 4080', 'ProArt 32" 4K Monitor'],
}

PRODUCTS = [
    # (name, sku, price, cost_price, category, brand)
    # -- Apple --
    ('MacBook Pro 14" (M3 Pro, 18GB/512GB)', 'APL-MBP14-M3P', 1999.00, 1650.00, 'Laptops', 'Apple'),
    ('MacBook Air 13" (M3, 16GB/256GB)', 'APL-MBA13-M3', 1099.00, 920.00, 'Laptops', 'Apple'),
    ('iPhone 15 Pro (256GB) — Natural Titanium', 'APL-IP15P-256', 1199.00, 980.00, 'Smartphones', 'Apple'),
    ('iPhone 15 (128GB) — Pink', 'APL-IP15-128', 799.00, 660.00, 'Smartphones', 'Apple'),
    ('iPad Pro 11" (M4, 256GB/WiFi)', 'APL-IPDP11-M4', 999.00, 810.00, 'Tablets', 'Apple'),
    ('iPad Air (M2, 64GB/WiFi)', 'APL-IPDA-M2', 599.00, 490.00, 'Tablets', 'Apple'),
    ('AirPods Pro (2nd Gen, USB‑C)', 'APL-AIRP2-USBC', 249.00, 195.00, 'Audio', 'Apple'),
    ('Apple Watch Ultra 2', 'APL-AWU2', 799.00, 640.00, 'Wearables', 'Apple'),
    ('AirTag (4-Pack)', 'APL-AIRTAG4', 99.00, 75.00, 'Accessories', 'Apple'),
    ('MagSafe Charger', 'APL-MAGSFC', 39.00, 28.00, 'Accessories', 'Apple'),

    # -- Samsung --
    ('Galaxy Book3 Pro (16", 16GB/512GB)', 'SAM-GB3P-16', 1499.00, 1240.00, 'Laptops', 'Samsung'),
    ('Galaxy S24 Ultra (256GB) — Titanium Gray', 'SAM-S24U-256', 1299.00, 1050.00, 'Smartphones', 'Samsung'),
    ('Galaxy Tab S9 (256GB/WiFi)', 'SAM-TABS9-256', 799.00, 650.00, 'Tablets', 'Samsung'),
    ('Galaxy Watch 6 Classic (47mm)', 'SAM-GW6C-47', 399.00, 310.00, 'Wearables', 'Samsung'),
    ('Galaxy Buds2 Pro', 'SAM-BUDS2P', 199.00, 155.00, 'Audio', 'Samsung'),
    ('T7 Portable SSD 1TB', 'SAM-T7-1TB', 159.00, 120.00, 'Components', 'Samsung'),

    # -- Sony --
    ('WH-1000XM5 Wireless Headphones', 'SONY-WHXM5', 349.00, 270.00, 'Audio', 'Sony'),
    ('WF-1000XM5 Earbuds', 'SONY-WFXM5', 279.00, 215.00, 'Audio', 'Sony'),
    ('Alpha 7 IV Mirrorless Camera (Body)', 'SONY-A7M4', 2499.00, 2100.00, 'Cameras', 'Sony'),
    ('PlayStation 5 Console (Slim)', 'SONY-PS5-SLIM', 449.00, 380.00, 'Gaming', 'Sony'),
    ('DualSense Wireless Controller — White', 'SONY-DUALSENSE', 69.00, 52.00, 'Gaming', 'Sony'),

    # -- Dell --
    ('XPS 15 (9530, i7-13700H, 16GB/512GB)', 'DELL-XPS15-9530', 1799.00, 1480.00, 'Laptops', 'Dell'),
    ('XPS 13 Plus (9320, i7-1360P, 16GB/512GB)', 'DELL-XPS13P-9320', 1399.00, 1150.00, 'Laptops', 'Dell'),
    ('UltraSharp 27" 4K USB-C Hub Monitor (U2723QE)', 'DELL-U2723QE', 619.00, 480.00, 'Accessories', 'Dell'),

    # -- Lenovo --
    ('ThinkPad X1 Carbon Gen 11 (i7, 16GB/512GB)', 'LEN-TPX1C-G11', 1649.00, 1350.00, 'Laptops', 'Lenovo'),
    ('ThinkVision 24" Monitor (T24i-20)', 'LEN-TV24-T24I', 259.00, 200.00, 'Accessories', 'Lenovo'),

    # -- Logitech --
    ('MX Master 3S Wireless Mouse', 'LOG-MX3S', 99.00, 72.00, 'Accessories', 'Logitech'),
    ('MX Keys Wireless Keyboard', 'LOG-MXKEYS', 109.00, 80.00, 'Accessories', 'Logitech'),
    ('C920 HD Pro Webcam', 'LOG-C920', 79.00, 58.00, 'Accessories', 'Logitech'),

    # -- Anker --
    ('PowerCore 26800mAh Portable Charger', 'ANK-PC26800', 79.00, 55.00, 'Accessories', 'Anker'),
    ('USB-C Cable 6ft (3-Pack)', 'ANK-USBC-3PK', 16.99, 10.00, 'Accessories', 'Anker'),
    ('Nano II 65W GaN Charger', 'ANK-NANO2-65', 39.99, 27.00, 'Accessories', 'Anker'),

    # -- Microsoft --
    ('Surface Pro 9 (i5, 16GB/256GB)', 'MS-SP9-I5', 1299.00, 1060.00, 'Tablets', 'Microsoft'),
    ('Xbox Series X', 'MS-XBSX', 499.00, 420.00, 'Gaming', 'Microsoft'),

    # -- Storage --
    ('FireCuda 530 2TB NVMe SSD', 'SEA-FC530-2TB', 249.00, 190.00, 'Components', 'Seagate'),
    ('Backup Plus 5TB Portable HDD', 'SEA-BP-5TB', 124.99, 90.00, 'Components', 'Seagate'),

    # -- Memory --
    ('Vengeance DDR5 32GB (2x16GB) 5600MHz', 'COR-VEN-DDR5-32', 109.99, 80.00, 'Components', 'Corsair'),
    ('RM850x 850W 80+ Gold PSU', 'COR-RM850X', 139.99, 105.00, 'Components', 'Corsair'),
    ('K70 RGB Mechanical Keyboard', 'COR-K70-RGB', 179.99, 130.00, 'Gaming', 'Corsair'),

    # -- CPUs --
    ('Core i7-14700K (20-Core) Desktop Processor', 'INT-i7-14700K', 409.99, 340.00, 'Components', 'Intel'),
    ('Core i9-14900K (24-Core) Desktop Processor', 'INT-i9-14900K', 589.99, 490.00, 'Components', 'Intel'),
    ('Ryzen 7 7800X3D (8-Core) Desktop Processor', 'AMD-R7-7800X3D', 449.99, 370.00, 'Components', 'AMD'),
    ('Ryzen 9 7950X (16-Core) Desktop Processor', 'AMD-R9-7950X', 699.99, 580.00, 'Components', 'AMD'),

    # -- GPUs --
    ('GeForce RTX 4080 16GB', 'NVD-RTX4080-16', 1199.99, 950.00, 'Components', 'NVIDIA'),
    ('GeForce RTX 4090 24GB', 'NVD-RTX4090-24', 1799.99, 1450.00, 'Components', 'NVIDIA'),

    # -- ASUS --
    ('ROG Strix GeForce RTX 4080 OC 16GB', 'ASUS-ROG-RTX4080', 1299.99, 1020.00, 'Components', 'ASUS'),
    ('ProArt 32" 4K HDR Professional Monitor (PA32DC)', 'ASUS-PA32DC', 2999.00, 2400.00, 'Accessories', 'ASUS'),

    # -- Networking --
    ('TP-Link AX6000 WiFi 6 Router (Archer AX80)', 'TPL-AX6000', 149.99, 110.00, 'Networking', 'TP-Link'),
    ('Ubiquiti UniFi 6 Pro Access Point', 'UBI-U6PRO', 149.00, 110.00, 'Networking', 'Ubiquiti'),
    ('Netgear Nighthawk CM2000 Cable Modem', 'NET-CM2000', 199.99, 150.00, 'Networking', 'Netgear'),
]

CUSTOMERS = [
    ('TechCorp Solutions', 'Wholesale', '+1-555-1001', 'orders@techcorp.com', 50000, 7500),
    ('Digital Frontier LLC', 'Wholesale', '+1-555-1002', 'procurement@digitalfrontier.io', 35000, 4200),
    ('Apex Retail Group', 'Retail Chain', '+1-555-1003', 'buy@apexretail.com', 25000, 3100),
    ('Dr. Emily Chen', 'Professional', '+1-555-1004', 'emily.chen@example.com', 8000, 1200),
    ('James Wilson', 'Retail', '+1-555-1005', 'jwilson@example.com', 5000, 899),
    ('Sofia Martinez', 'Retail', '+1-555-1006', 'sofia.m@example.com', 3000, 450),
    ('NorthStar IT Services', 'Corporate', '+1-555-1007', 'it@northstarit.com', 75000, 12500),
    ('Greenfield Academy', 'Education', '+1-555-1008', 'admin@greenfield.edu', 20000, 0),
]

SUPPLIERS = [
    ('Apple Distribution Inc.', 'Electronics', '+1-555-2001', 'dist@apple.com', 5),
    ('Samsung Electronics America', 'Electronics', '+1-555-2002', 'b2b@samsung.com', 5),
    ('Sony Electronics B2B', 'Electronics', '+1-555-2003', 'b2b@sony.com', 5),
    ('Ingram Micro', 'Distributor', '+1-555-2004', 'sales@ingrammicro.com', 4),
    ('TechData Inc.', 'Distributor', '+1-555-2005', 'orders@techdata.com', 4),
    ('Corsair Memory Inc.', 'Components', '+1-555-2006', 'wholesale@corsair.com', 5),
    ('Intel Direct Sales', 'Components', '+1-555-2007', 'b2b@intel.com', 4),
    ('AMD Corporate', 'Components', '+1-555-2008', 'b2b@amd.com', 4),
]

INITIAL_STOCK = [
    # (sku, qty, reorder_level)
    ('APL-MBP14-M3P', 15, 3),
    ('APL-MBA13-M3', 20, 5),
    ('APL-IP15P-256', 25, 5),
    ('APL-IP15-128', 30, 8),
    ('APL-IPDP11-M4', 12, 3),
    ('APL-IPDA-M2', 18, 4),
    ('APL-AIRP2-USBC', 50, 15),
    ('APL-AWU2', 8, 2),
    ('APL-AIRTAG4', 40, 10),
    ('APL-MAGSFC', 60, 20),
    ('SAM-GB3P-16', 10, 2),
    ('SAM-S24U-256', 22, 5),
    ('SAM-TABS9-256', 14, 3),
    ('SAM-GW6C-47', 12, 3),
    ('SAM-BUDS2P', 35, 10),
    ('SAM-T7-1TB', 25, 5),
    ('SONY-WHXM5', 20, 5),
    ('SONY-WFXM5', 18, 4),
    ('SONY-A7M4', 5, 1),
    ('SONY-PS5-SLIM', 30, 8),
    ('SONY-DUALSENSE', 45, 12),
    ('DELL-XPS15-9530', 8, 2),
    ('DELL-XPS13P-9320', 10, 2),
    ('DELL-U2723QE', 7, 2),
    ('LEN-TPX1C-G11', 10, 2),
    ('LEN-TV24-T24I', 15, 4),
    ('LOG-MX3S', 50, 15),
    ('LOG-MXKEYS', 40, 10),
    ('LOG-C920', 25, 8),
    ('ANK-PC26800', 60, 20),
    ('ANK-USBC-3PK', 100, 30),
    ('ANK-NANO2-65', 80, 25),
    ('MS-SP9-I5', 8, 2),
    ('MS-XBSX', 20, 5),
    ('SEA-FC530-2TB', 20, 5),
    ('SEA-BP-5TB', 18, 4),
    ('COR-VEN-DDR5-32', 35, 10),
    ('COR-RM850X', 15, 4),
    ('COR-K70-RGB', 12, 3),
    ('INT-i7-14700K', 25, 5),
    ('INT-i9-14900K', 15, 3),
    ('AMD-R7-7800X3D', 20, 5),
    ('AMD-R9-7950X', 12, 3),
    ('NVD-RTX4080-16', 10, 2),
    ('NVD-RTX4090-24', 5, 1),
    ('ASUS-ROG-RTX4080', 8, 2),
    ('ASUS-PA32DC', 3, 1),
    ('TPL-AX6000', 25, 8),
    ('UBI-U6PRO', 30, 10),
    ('NET-CM2000', 15, 4),
]

SALES_ORDERS = [
    # (customer_name, order_number, status, order_date, lines)
    # lines: [(sku, qty, unit_price), ...]
    ('TechCorp Solutions', 'SO-2024-1001', 'Shipped', date.today() - timedelta(days=5),
     [('APL-MBP14-M3P', 3, 1850.00), ('APL-IP15P-256', 5, 1120.00), ('APL-AIRP2-USBC', 10, 229.00)]),
    ('Digital Frontier LLC', 'SO-2024-1002', 'Shipped', date.today() - timedelta(days=4),
     [('DELL-XPS15-9530', 2, 1650.00), ('LOG-MX3S', 8, 85.00), ('LOG-MXKEYS', 5, 95.00), ('DELL-U2723QE', 4, 550.00)]),
    ('Dr. Emily Chen', 'SO-2024-1003', 'Paid', date.today() - timedelta(days=2),
     [('APL-MBA13-M3', 1, 1049.00), ('APL-AIRP2-USBC', 1, 229.00)]),
    ('James Wilson', 'SO-2024-1004', 'Paid', date.today() - timedelta(days=1),
     [('SAM-S24U-256', 1, 1249.00), ('SAM-BUDS2P', 1, 179.00)]),
    ('NorthStar IT Services', 'SO-2024-1005', 'Pending', date.today(),
     [('LEN-TPX1C-G11', 5, 1520.00), ('LEN-TV24-T24I', 10, 229.00), ('LOG-MX3S', 10, 85.00)]),
    ('Apex Retail Group', 'SO-2024-1006', 'Pending', date.today(),
     [('SONY-PS5-SLIM', 20, 429.00), ('SONY-DUALSENSE', 25, 59.00), ('APL-AIRTAG4', 30, 89.00), ('APL-MAGSFC', 20, 34.00)]),
    ('Sofia Martinez', 'SO-2024-1007', 'Pending', date.today(),
     [('APL-IP15-128', 1, 749.00), ('APL-MAGSFC', 1, 34.00)]),
    ('Greenfield Academy', 'SO-2024-1008', 'Pending', date.today(),
     [('DELL-XPS13P-9320', 8, 1280.00), ('DELL-U2723QE', 8, 550.00), ('LOG-C920', 8, 69.00)]),
]

PURCHASE_ORDERS = [
    ('Apple Distribution Inc.', 'PO-2024-2001', 'Received', date.today() - timedelta(days=10),
     [('APL-MBP14-M3P', 20, 1650.00), ('APL-IP15P-256', 30, 980.00), ('APL-AIRP2-USBC', 60, 195.00)]),
    ('Ingram Micro', 'PO-2024-2002', 'Received', date.today() - timedelta(days=8),
     [('SONY-WHXM5', 25, 270.00), ('SONY-PS5-SLIM', 35, 380.00), ('LOG-MX3S', 60, 72.00), ('LOG-MXKEYS', 50, 80.00)]),
    ('Samsung Electronics America', 'PO-2024-2003', 'Approved', date.today() - timedelta(days=3),
     [('SAM-S24U-256', 25, 1050.00), ('SAM-TABS9-256', 20, 650.00), ('SAM-GB3P-16', 15, 1240.00)]),
    ('Intel Direct Sales', 'PO-2024-2004', 'Pending', date.today(),
     [('INT-i7-14700K', 30, 340.00), ('INT-i9-14900K', 20, 490.00)]),
    ('Corsair Memory Inc.', 'PO-2024-2005', 'Pending', date.today(),
     [('COR-VEN-DDR5-32', 50, 80.00), ('COR-RM850X', 20, 105.00), ('COR-K70-RGB', 20, 130.00)]),
]


# ── Main ──────────────────────────────────────────────────────────────────

def run(clear_first=False):
    conn = get_connection()
    try:
        _do_seed(conn, clear_first)
    finally:
        release_connection(conn)


def _do_seed(conn, clear_first):
    print('Seeding electronics store data...')
    print(f'  Database: {conn.info.dbname}')
    print()

    if clear_first:
        print('Clearing existing electronics data...')
        _clear_electronics(conn)
        print()

    _seed_all(conn)
    print()
    print('Done.')


def _clear_electronics(conn):
    """Delete all electronics-related data (products with electronics SKUs, etc.)"""
    cur = conn.cursor()
    try:
        skus = [p[1] for p in PRODUCTS]
        placeholders = ', '.join([f'%s'] * len(skus))
        cur.execute(f"""SELECT id FROM "Nova".t0003 WHERE sku IN ({placeholders})""", skus)
        product_ids = [row[0] for row in cur.fetchall()]

        if not product_ids:
            print('  Nothing to clear.')
            conn.commit()
            return

        pid_ph = ', '.join([f'%s'] * len(product_ids))
        tables = ['t0004', 't0006', 't0007', 't0009', 't0084', 't0064']
        for t in tables:
            cur.execute(f'DELETE FROM "Nova".{t} WHERE product_id IN ({pid_ph})', product_ids)

        # Delete sales orders referencing these products
        cur.execute(f"""SELECT DISTINCT t0012.id FROM "Nova".t0012
            JOIN "Nova".t0013 ON t0013.sales_order_id = t0012.id
            WHERE t0013.product_id IN ({pid_ph})""", product_ids)
        so_ids = [r[0] for r in cur.fetchall()]
        if so_ids:
            so_ph = ', '.join([f'%s'] * len(so_ids))
            cur.execute(f'DELETE FROM "Nova".t0013 WHERE sales_order_id IN ({so_ph})', so_ids)
            cur.execute(f'DELETE FROM "Nova".t0012 WHERE id IN ({so_ph})', so_ids)

        # Delete purchase orders referencing these products
        cur.execute(f"""SELECT DISTINCT t0014.id FROM "Nova".t0014
            JOIN "Nova".t0015 ON t0015.purchase_order_id = t0014.id
            WHERE t0015.product_id IN ({pid_ph})""", product_ids)
        po_ids = [r[0] for r in cur.fetchall()]
        if po_ids:
            po_ph = ', '.join([f'%s'] * len(po_ids))
            cur.execute(f'DELETE FROM "Nova".t0015 WHERE purchase_order_id IN ({po_ph})', po_ids)
            cur.execute(f'DELETE FROM "Nova".t0014 WHERE id IN ({po_ph})', po_ids)

        # Delete products
        cur.execute(f'DELETE FROM "Nova".t0003 WHERE id IN ({pid_ph})', product_ids)

        # Delete electronics customers & suppliers
        cnames = [c[0] for c in CUSTOMERS]
        cph = ', '.join([f'%s'] * len(cnames))
        cur.execute(f'DELETE FROM "Nova".t0010 WHERE name IN ({cph})', cnames)
        snames = [s[0] for s in SUPPLIERS]
        sph = ', '.join([f'%s'] * len(snames))
        cur.execute(f'DELETE FROM "Nova".t0011 WHERE name IN ({sph})', snames)

        conn.commit()
        print(f'  Cleared {len(product_ids)} products + related data.')
    finally:
        cur.close()


def _seed_all(conn):
    # Ensure tables that may be missing from schema.sql
    _ensure_missing_tables(conn)

    pcs_id = _ensure_pcs_id(conn)
    main_wh_id = _ensure_warehouse_id(conn, 'Main', '123 Industrial Blvd')
    sec_wh_id = _ensure_warehouse_id(conn, 'Secondary Returns', 'Returns & RMA center')

    # Price Lists & Tax Rates
    retail_pl_id = _ensure_price_list_id(conn, 'Retail (Electronics)', 'ELECTRO_RETAIL', is_default=True)
    wholesale_pl_id = _ensure_price_list_id(conn, 'Wholesale (Electronics)', 'ELECTRO_WHOLESALE')
    std_tax_id = _ensure_tax_rate_id(conn, 'Standard VAT (Electronics)', 'ELECTRO_VAT', 8.00)

    # Products
    print('Seeding products...')
    existing_skus = _get_ids(conn, 't0003', 'sku', [p[1] for p in PRODUCTS])
    new_products = [p for p in PRODUCTS if p[1] not in existing_skus]

    if new_products:
        prod_ids = _insert(conn, 't0003',
                           ['name', 'sku', 'price', 'cost_price', 'category', 'brand', 'tax_rate', 'image_url', 'is_active',
                            'created_at', 'created_by'],
                           [(name, sku, price, cost_price, cat, brand, 8.00, None, True, datetime.now(), 1)
                            for name, sku, price, cost_price, cat, brand in new_products],
                           conflict='(sku) DO NOTHING')
        for pid, p in zip(prod_ids, new_products):
            existing_skus[p[1]] = pid
        print(f'  Created {len(prod_ids)} products')
    else:
        print(f'  All {len(PRODUCTS)} products already exist')

    # Product UOMs
    print('Seeding product UOMs...')
    existing_puom = _get_ids(conn, 't0007', 'product_id', list(existing_skus.values()))
    for sku, pid in existing_skus.items():
        if pid not in existing_puom:
            _insert(conn, 't0007',
                    ['product_id', 'base_uom_id', 'purchase_uom_id', 'sales_uom_id',
                     'purchase_factor', 'sales_factor', 'created_at', 'created_by'],
                    [(pid, pcs_id, pcs_id, pcs_id, 1.0, 1.0, datetime.now(), 1)])

    # Product barcodes
    print('Seeding barcodes...')
    existing_barcodes = _get_ids(conn, 't0004', 'product_id', list(existing_skus.values()))
    for sku, pid in existing_skus.items():
        if pid not in existing_barcodes:
            # Generate a pseudo-EAN-13 from product ID
            bc = f'0{str(pid).zfill(5)}000000'
            check = sum(int(bc[i]) * (3 if i % 2 else 1) for i in range(12)) % 10
            check = (10 - check) % 10
            barcode = bc + str(check)
            _insert(conn, 't0004',
                    ['product_id', 'barcode', 'barcode_type', 'is_primary', 'created_at', 'created_by'],
                    [(pid, barcode, 'EAN13', True, datetime.now(), 1)])

    # Price list items (wholesale = ~10% off retail)
    print('Seeding price lists...')
    existing_pl_items = _get_ids(conn, 't0084', 'product_id', list(existing_skus.values()))
    for sku, pid in existing_skus.items():
        if pid not in existing_pl_items:
            retail_price = next(p[2] for p in PRODUCTS if p[1] == sku)
            wholesale_price = round(retail_price * 0.90, 2)
            _insert(conn, 't0084',
                    ['price_list_id', 'product_id', 'unit_price', 'min_qty', 'uom_id',
                     'effective_from', 'line_number', 'created_at', 'created_by'],
                    [(wholesale_pl_id, pid, wholesale_price, 1, pcs_id, date.today(), 0, datetime.now(), 1)])

    # Initial stock
    print('Seeding stock levels...')
    existing_stock = _get_ids(conn, 't0009', 'product_id', list(existing_skus.values()))
    for sku, qty, reorder in INITIAL_STOCK:
        pid = existing_skus.get(sku)
        if pid and pid not in existing_stock:
            _insert(conn, 't0009',
                    ['product_id', 'warehouse_id', 'qty', 'reorder_level', 'created_at', 'created_by'],
                    [(pid, main_wh_id, qty, reorder, datetime.now(), 1)])

    # Customers
    print('Seeding customers...')
    existing_customers = _get_ids(conn, 't0010', 'name', [c[0] for c in CUSTOMERS])
    new_customers = [c for c in CUSTOMERS if c[0] not in existing_customers]
    if new_customers:
        customer_ids = _insert(conn, 't0010',
                               ['name', 'group_name', 'phone', 'email', 'credit_limit', 'balance',
                                'default_price_list_id', 'default_tax_rate_id', 'is_active', 'created_at', 'created_by'],
                               [(name, grp, phone, email, cl, bal, retail_pl_id, std_tax_id, True, datetime.now(), 1)
                                for name, grp, phone, email, cl, bal in new_customers])
        for cid, c in zip(customer_ids, new_customers):
            existing_customers[c[0]] = cid
        print(f'  Created {len(customer_ids)} customers')
    else:
        print(f'  All {len(CUSTOMERS)} customers already exist')

    # Suppliers
    print('Seeding suppliers...')
    existing_suppliers = _get_ids(conn, 't0011', 'name', [s[0] for s in SUPPLIERS])
    new_suppliers = [s for s in SUPPLIERS if s[0] not in existing_suppliers]
    if new_suppliers:
        supplier_ids = _insert(conn, 't0011',
                               ['name', 'category', 'phone', 'email', 'rating', 'is_active', 'created_at', 'created_by'],
                               [(name, cat, phone, email, rating, True, datetime.now(), 1)
                                for name, cat, phone, email, rating in new_suppliers])
        for sid, s in zip(supplier_ids, new_suppliers):
            existing_suppliers[s[0]] = sid
        print(f'  Created {len(supplier_ids)} suppliers')
    else:
        print(f'  All {len(SUPPLIERS)} suppliers already exist')

    # Sales Orders
    print('Seeding sales orders...')
    for cust_name, order_num, status, order_date, lines in SALES_ORDERS:
        existing_so = _get_id(conn, 't0012', 'order_number', order_num)
        if existing_so:
            continue

        cust_id = existing_customers.get(cust_name)
        if not cust_id:
            eprint(f'  ! Customer "{cust_name}" not found, skipping order {order_num}')
            continue

        subtotal = sum(qty * up for _, qty, up in lines)
        tax = round(subtotal * 0.08, 2)
        grand_total = subtotal + tax

        so_ids = _insert(conn, 't0012',
                         ['order_number', 'customer_id', 'subtotal', 'tax', 'grand_total', 'status', 'order_date',
                          'price_list_id', 'tax_rate_id', 'created_at', 'created_by'],
                         [(order_num, cust_id, subtotal, tax, grand_total, status, order_date,
                           retail_pl_id, std_tax_id, datetime.now(), 1)])
        so_id = so_ids[0]

        for line_num, (sku, qty, unit_price) in enumerate(lines, 1):
            pid = existing_skus.get(sku)
            if not pid:
                eprint(f'  ! Product "{sku}" not found, skipping line in {order_num}')
                continue
            pname = next(p[0] for p in PRODUCTS if p[1] == sku)
            line_total = round(qty * unit_price, 2)
            _insert(conn, 't0013',
                    ['sales_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total',
                     'line_number', 'created_at', 'created_by'],
                    [(so_id, pid, pname, pcs_id, qty, unit_price, line_total, line_num, datetime.now(), 1)])

        print(f'  + {order_num} ({cust_name}, ${grand_total})')

    # Purchase Orders
    print('Seeding purchase orders...')
    for supp_name, po_num, status, order_date, lines in PURCHASE_ORDERS:
        existing_po = _get_id(conn, 't0014', 'order_number', po_num)
        if existing_po:
            continue

        supp_id = existing_suppliers.get(supp_name)
        if not supp_id:
            eprint(f'  ! Supplier "{supp_name}" not found, skipping PO {po_num}')
            continue

        total = round(sum(qty * up for _, qty, up in lines), 2)

        po_ids = _insert(conn, 't0014',
                         ['order_number', 'supplier_id', 'total', 'status', 'order_date', 'created_at', 'created_by'],
                         [(po_num, supp_id, total, status, order_date, datetime.now(), 1)])
        po_id = po_ids[0]

        for line_num, (sku, qty, unit_price) in enumerate(lines, 1):
            pid = existing_skus.get(sku)
            if not pid:
                eprint(f'  ! Product "{sku}" not found, skipping line in {po_num}')
                continue
            pname = next(p[0] for p in PRODUCTS if p[1] == sku)
            line_total = round(qty * unit_price, 2)
            _insert(conn, 't0015',
                    ['purchase_order_id', 'product_id', 'product_name', 'uom_id', 'qty', 'unit_price', 'line_total',
                     'line_number', 'created_at', 'created_by'],
                    [(po_id, pid, pname, pcs_id, qty, unit_price, line_total, line_num, datetime.now(), 1)])

        print(f'  + {po_num} ({supp_name}, ${total})')

    # Summary
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM "Nova".t0003')
        total_products = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Nova".t0010')
        total_customers = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Nova".t0011')
        total_suppliers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM \"Nova\".t0012 WHERE order_number LIKE 'SO-2024-%'")
        total_sos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM \"Nova\".t0014 WHERE order_number LIKE 'PO-2024-%'")
        total_pos = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM "Nova".t0009')
        total_stock = cur.fetchone()[0]

    print()
    print('── Summary ───────────────────────────────')
    print(f'  Products:     {total_products}')
    print(f'  Customers:    {total_customers}')
    print(f'  Suppliers:    {total_suppliers}')
    print(f'  Sales Orders: {total_sos}')
    print(f'  Purchase Ord: {total_pos}')
    print(f'  Stock Levels: {total_stock}')
    print('──────────────────────────────────────────')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed electronics store test data')
    parser.add_argument('--clear', action='store_true', help='Clear existing electronics data first')
    args = parser.parse_args()
    sys.exit(run(args.clear))
