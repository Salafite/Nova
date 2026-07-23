"""Full Neon setup: create schema, types, needed tables, and seed data"""
import os, sys
from datetime import date, datetime, timedelta
import psycopg2
from psycopg2 import sql as psql

NEON = dict(
    host='ep-rapid-snow-asuk4t8k-pooler.c-4.eu-central-1.aws.neon.tech',
    port=5432, dbname='neondb',
    user='neondb_owner',
    password='npg_As6EG7upfkHU',
    sslmode='require'
)

conn = psycopg2.connect(**NEON)
conn.autocommit = True
cur = conn.cursor()

# --- Step 1: Drop & recreate schema ---
cur.execute('DROP SCHEMA IF EXISTS nova_erp CASCADE')
cur.execute('CREATE SCHEMA nova_erp')
cur.execute("SET search_path TO nova_erp")
print('[1/5] Schema nova_erp ready')

# --- Step 2: Create types ---
types = [
    "CREATE TYPE order_status AS ENUM ('Pending','Paid','Shipped','Cancelled')",
    "CREATE TYPE po_status AS ENUM ('Pending','Approved','Received','Cancelled')",
    "CREATE TYPE mfg_status AS ENUM ('Pending','In Progress','Completed','On Hold')",
    "CREATE TYPE qc_result AS ENUM ('Pending','Pass','Fail')",
    "CREATE TYPE job_status AS ENUM ('Pending','In Progress','Completed','On Hold')",
    "CREATE TYPE user_role AS ENUM ('Admin','Sales Rep','Viewer','Manager','Cashier','Salesman','Warehouse','Accountant')",
    "CREATE TYPE user_status AS ENUM ('Active','Inactive','Invited')",
    "CREATE TYPE uom_category AS ENUM ('Quantity','Weight','Volume','Length','Area','Time','Other')",
    "CREATE TYPE attr_type AS ENUM ('Text','Number','Select','Date','Boolean')",
    "CREATE TYPE installment_status AS ENUM ('Pending','Paid','Overdue','Cancelled')",
]
for t in types:
    try:
        cur.execute(t)
    except Exception as e:
        if 'already exists' not in str(e):
            print('  Type error:', str(e)[:80])
print('[2/5] Types created')

# Helper
def ins(table, cols, rows):
    cl = ','.join(cols)
    ph = ','.join(['%s']*len(cols))
    sql = 'INSERT INTO nova_erp.%s (%s) VALUES (%s) RETURNING id' % (table, cl, ph)
    ids = []
    for r in rows:
        cur.execute(sql, r)
        ids.append(cur.fetchone()[0])
    return ids

def gid(table, col, val):
    cur.execute('SELECT id FROM nova_erp.%s WHERE %s = %%s' % (table, col), (val,))
    r = cur.fetchone()
    return r[0] if r else None

def gids(table, col, vals):
    if not vals:
        return {}
    ph = ','.join(['%s']*len(vals))
    cur.execute('SELECT id,%s FROM nova_erp.%s WHERE %s IN (%s)' % (col, table, col, ph), list(vals))
    return {r[1]: r[0] for r in cur.fetchall()}

# --- Step 3: Create needed tables ---
TABLES = {
    't0001': '''
        id SERIAL PRIMARY KEY, uom_code VARCHAR(10) NOT NULL UNIQUE,
        uom_name VARCHAR(50) NOT NULL, category uom_category NOT NULL DEFAULT 'Quantity',
        is_base_unit BOOLEAN NOT NULL DEFAULT false, is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0003': '''
        id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
        sku VARCHAR(50) NOT NULL UNIQUE, price NUMERIC(12,2) NOT NULL DEFAULT 0,
        cost_price NUMERIC(12,2) NOT NULL DEFAULT 0, category VARCHAR(100), brand VARCHAR(100),
        tax_rate NUMERIC(5,2) DEFAULT 0, image_url TEXT, barcode VARCHAR(100),
        is_active BOOLEAN NOT NULL DEFAULT true, is_purchased BOOLEAN DEFAULT true,
        is_sold BOOLEAN DEFAULT true, is_stocked BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0004': '''
        id SERIAL PRIMARY KEY, product_id INT NOT NULL REFERENCES nova_erp.t0003(id) ON DELETE CASCADE,
        barcode VARCHAR(100) NOT NULL, barcode_type VARCHAR(20) NOT NULL DEFAULT 'EAN13',
        is_primary BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0007': '''
        id SERIAL PRIMARY KEY, product_id INT NOT NULL UNIQUE REFERENCES nova_erp.t0003(id) ON DELETE CASCADE,
        base_uom_id INT NOT NULL REFERENCES nova_erp.t0001(id),
        purchase_uom_id INT NOT NULL REFERENCES nova_erp.t0001(id),
        sales_uom_id INT NOT NULL REFERENCES nova_erp.t0001(id),
        purchase_factor NUMERIC(12,6) NOT NULL DEFAULT 1,
        sales_factor NUMERIC(12,6) NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0008': '''
        id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
        location VARCHAR(255), is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0009': '''
        id SERIAL PRIMARY KEY, product_id INT NOT NULL REFERENCES nova_erp.t0003(id) ON DELETE CASCADE,
        warehouse_id INT NOT NULL REFERENCES nova_erp.t0008(id) ON DELETE CASCADE,
        qty NUMERIC(12,2) NOT NULL DEFAULT 0, reorder_level NUMERIC(12,2) DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0010': '''
        id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, group_name VARCHAR(100),
        email VARCHAR(255), phone VARCHAR(50), credit_limit NUMERIC(12,2) DEFAULT 0,
        balance NUMERIC(12,2) DEFAULT 0, default_price_list_id INT,
        default_tax_rate_id INT, is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0011': '''
        id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
        category VARCHAR(100), email VARCHAR(255), phone VARCHAR(50),
        rating INT DEFAULT 5, is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0012': '''
        id SERIAL PRIMARY KEY, order_number VARCHAR(50) NOT NULL UNIQUE,
        customer_id INT NOT NULL REFERENCES nova_erp.t0010(id),
        subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
        tax NUMERIC(12,2) NOT NULL DEFAULT 0,
        grand_total NUMERIC(12,2) NOT NULL DEFAULT 0,
        status order_status NOT NULL DEFAULT 'Pending',
        order_date DATE NOT NULL DEFAULT CURRENT_DATE, notes TEXT,
        price_list_id INT, tax_rate_id INT, payment_term_id INT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0013': '''
        id SERIAL PRIMARY KEY, sales_order_id INT NOT NULL REFERENCES nova_erp.t0012(id) ON DELETE CASCADE,
        product_id INT NOT NULL REFERENCES nova_erp.t0003(id),
        product_name VARCHAR(200), uom_id INT NOT NULL REFERENCES nova_erp.t0001(id),
        qty NUMERIC(12,2) NOT NULL DEFAULT 1, unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
        line_total NUMERIC(12,2) NOT NULL DEFAULT 0,
        line_number INT NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0014': '''
        id SERIAL PRIMARY KEY, order_number VARCHAR(50) NOT NULL UNIQUE,
        supplier_id INT NOT NULL REFERENCES nova_erp.t0011(id),
        total NUMERIC(12,2) NOT NULL DEFAULT 0,
        status po_status NOT NULL DEFAULT 'Pending',
        order_date DATE NOT NULL DEFAULT CURRENT_DATE, expected_date DATE,
        notes TEXT, converted_rfq_id INT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0015': '''
        id SERIAL PRIMARY KEY, purchase_order_id INT NOT NULL REFERENCES nova_erp.t0014(id) ON DELETE CASCADE,
        product_id INT NOT NULL REFERENCES nova_erp.t0003(id),
        product_name VARCHAR(200), uom_id INT NOT NULL REFERENCES nova_erp.t0001(id),
        qty NUMERIC(12,2) NOT NULL DEFAULT 1, unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
        line_total NUMERIC(12,2) NOT NULL DEFAULT 0,
        line_number INT NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0083': '''
        id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, code VARCHAR(20) NOT NULL UNIQUE,
        description TEXT, currency VARCHAR(3) NOT NULL DEFAULT 'USD',
        is_active BOOLEAN NOT NULL DEFAULT true, is_default BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
    't0085': '''
        id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, code VARCHAR(20) NOT NULL UNIQUE,
        rate NUMERIC(5,2) NOT NULL DEFAULT 0, type VARCHAR(20) NOT NULL DEFAULT 'Sales',
        description TEXT, is_active BOOLEAN NOT NULL DEFAULT true, is_default BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by INT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by INT,
        update_number INT NOT NULL DEFAULT 1
    ''',
}

# Create tables in dependency order
table_order = ['t0001','t0008','t0003','t0004','t0007','t0010','t0011','t0083','t0085','t0009','t0012','t0013','t0014','t0015']
for tname in table_order:
    cur.execute('CREATE TABLE IF NOT EXISTS nova_erp.%s (%s)' % (tname, TABLES[tname]))
print('[3/5] Tables created (%d)' % len(table_order))

now_ = datetime.now()
today_ = date.today()

# --- UOM ---
uid = gid('t0001', 'uom_code', 'pcs')
if not uid:
    uid = ins('t0001', ['uom_code','uom_name','category','is_base_unit','created_at','created_by'],
              [('pcs','Piece','Quantity',True,now_,1)])[0]
print('  UOM id=%d' % uid)

# --- Warehouse ---
wid = gid('t0008', 'name', 'Main')
if not wid:
    wid = ins('t0008', ['name','location','created_at','created_by'],
              [('Main','Main warehouse',now_,1)])[0]
print('  Warehouse id=%d' % wid)

# --- Price list & Tax ---
pl_id = gid('t0083', 'code', 'RETAIL')
if not pl_id:
    pl_id = ins('t0083', ['name','code','currency','is_default','created_at','created_by'],
                [('Retail','RETAIL','USD',True,now_,1)])[0]
tx_id = gid('t0085', 'code', 'VAT8')
if not tx_id:
    tx_id = ins('t0085', ['name','code','rate','type','is_active','created_at','created_by'],
                [('VAT 8%','VAT8',8.0,'Sales',True,now_,1)])[0]
print('  Price list=%d Tax=%d' % (pl_id, tx_id))

# --- Products ---
PRODUCTS = [
    ('MacBook Pro 14" (M3 Pro, 18GB/512GB)', 'APL-MBP14-M3P', 1999.0, 1650.0, 'Laptops', 'Apple'),
    ('MacBook Air 13" (M3, 16GB/256GB)', 'APL-MBA13-M3', 1099.0, 920.0, 'Laptops', 'Apple'),
    ('iPhone 15 Pro (256GB)', 'APL-IP15P-256', 1199.0, 980.0, 'Smartphones', 'Apple'),
    ('iPhone 15 (128GB)', 'APL-IP15-128', 799.0, 660.0, 'Smartphones', 'Apple'),
    ('iPad Pro 11" (M4, 256GB/WiFi)', 'APL-IPDP11-M4', 999.0, 810.0, 'Tablets', 'Apple'),
    ('iPad Air (M2, 64GB/WiFi)', 'APL-IPDA-M2', 599.0, 490.0, 'Tablets', 'Apple'),
    ('AirPods Pro (2nd Gen, USB-C)', 'APL-AIRP2-USBC', 249.0, 195.0, 'Audio', 'Apple'),
    ('Apple Watch Ultra 2', 'APL-AWU2', 799.0, 640.0, 'Wearables', 'Apple'),
    ('AirTag (4-Pack)', 'APL-AIRTAG4', 99.0, 75.0, 'Accessories', 'Apple'),
    ('MagSafe Charger', 'APL-MAGSFC', 39.0, 28.0, 'Accessories', 'Apple'),
    ('Galaxy Book3 Pro (16")', 'SAM-GB3P-16', 1499.0, 1240.0, 'Laptops', 'Samsung'),
    ('Galaxy S24 Ultra (256GB)', 'SAM-S24U-256', 1299.0, 1050.0, 'Smartphones', 'Samsung'),
    ('Galaxy Tab S9 (256GB/WiFi)', 'SAM-TABS9-256', 799.0, 650.0, 'Tablets', 'Samsung'),
    ('Galaxy Watch 6 Classic (47mm)', 'SAM-GW6C-47', 399.0, 310.0, 'Wearables', 'Samsung'),
    ('Galaxy Buds2 Pro', 'SAM-BUDS2P', 199.0, 155.0, 'Audio', 'Samsung'),
    ('T7 Portable SSD 1TB', 'SAM-T7-1TB', 159.0, 120.0, 'Components', 'Samsung'),
    ('WH-1000XM5 Wireless Headphones', 'SONY-WHXM5', 349.0, 270.0, 'Audio', 'Sony'),
    ('WF-1000XM5 Earbuds', 'SONY-WFXM5', 279.0, 215.0, 'Audio', 'Sony'),
    ('PlayStation 5 Console (Slim)', 'SONY-PS5-SLIM', 449.0, 380.0, 'Gaming', 'Sony'),
    ('DualSense Wireless Controller', 'SONY-DUALSENSE', 69.0, 52.0, 'Gaming', 'Sony'),
    ('XPS 15 (i7, 16GB/512GB)', 'DELL-XPS15-9530', 1799.0, 1480.0, 'Laptops', 'Dell'),
    ('XPS 13 Plus (i7, 16GB/512GB)', 'DELL-XPS13P-9320', 1399.0, 1150.0, 'Laptops', 'Dell'),
    ('UltraSharp 27" 4K Monitor U2723QE', 'DELL-U2723QE', 619.0, 480.0, 'Accessories', 'Dell'),
    ('ThinkPad X1 Carbon Gen 11', 'LEN-TPX1C-G11', 1649.0, 1350.0, 'Laptops', 'Lenovo'),
    ('ThinkVision 24" Monitor T24i', 'LEN-TV24-T24I', 259.0, 200.0, 'Accessories', 'Lenovo'),
    ('MX Master 3S Wireless Mouse', 'LOG-MX3S', 99.0, 72.0, 'Accessories', 'Logitech'),
    ('MX Keys Wireless Keyboard', 'LOG-MXKEYS', 109.0, 80.0, 'Accessories', 'Logitech'),
    ('C920 HD Pro Webcam', 'LOG-C920', 79.0, 58.0, 'Accessories', 'Logitech'),
    ('PowerCore 26800mAh Charger', 'ANK-PC26800', 79.0, 55.0, 'Accessories', 'Anker'),
    ('USB-C Cable 6ft (3-Pack)', 'ANK-USBC-3PK', 16.99, 10.0, 'Accessories', 'Anker'),
    ('Nano II 65W GaN Charger', 'ANK-NANO2-65', 39.99, 27.0, 'Accessories', 'Anker'),
    ('Surface Pro 9 (i5, 16GB/256GB)', 'MS-SP9-I5', 1299.0, 1060.0, 'Tablets', 'Microsoft'),
    ('Xbox Series X', 'MS-XBSX', 499.0, 420.0, 'Gaming', 'Microsoft'),
    ('FireCuda 530 2TB NVMe SSD', 'SEA-FC530-2TB', 249.0, 190.0, 'Components', 'Seagate'),
    ('Backup Plus 5TB HDD', 'SEA-BP-5TB', 124.99, 90.0, 'Components', 'Seagate'),
    ('Vengeance DDR5 32GB 5600MHz', 'COR-VEN-DDR5-32', 109.99, 80.0, 'Components', 'Corsair'),
    ('RM850x 850W 80+ Gold PSU', 'COR-RM850X', 139.99, 105.0, 'Components', 'Corsair'),
    ('K70 RGB Mechanical Keyboard', 'COR-K70-RGB', 179.99, 130.0, 'Gaming', 'Corsair'),
    ('Core i7-14700K (20-Core)', 'INT-i7-14700K', 409.99, 340.0, 'Components', 'Intel'),
    ('Core i9-14900K (24-Core)', 'INT-i9-14900K', 589.99, 490.0, 'Components', 'Intel'),
    ('Ryzen 7 7800X3D (8-Core)', 'AMD-R7-7800X3D', 449.99, 370.0, 'Components', 'AMD'),
    ('Ryzen 9 7950X (16-Core)', 'AMD-R9-7950X', 699.99, 580.0, 'Components', 'AMD'),
    ('GeForce RTX 4080 16GB', 'NVD-RTX4080-16', 1199.99, 950.0, 'Components', 'NVIDIA'),
    ('GeForce RTX 4090 24GB', 'NVD-RTX4090-24', 1799.99, 1450.0, 'Components', 'NVIDIA'),
    ('ROG Strix RTX 4080 OC 16GB', 'ASUS-ROG-RTX4080', 1299.99, 1020.0, 'Components', 'ASUS'),
    ('ProArt 32" 4K Monitor PA32DC', 'ASUS-PA32DC', 2999.0, 2400.0, 'Accessories', 'ASUS'),
    ('TP-Link AX6000 WiFi 6 Router', 'TPL-AX6000', 149.99, 110.0, 'Networking', 'TP-Link'),
    ('Ubiquiti UniFi 6 Pro AP', 'UBI-U6PRO', 149.0, 110.0, 'Networking', 'Ubiquiti'),
    ('Netgear Nighthawk CM2000 Modem', 'NET-CM2000', 199.99, 150.0, 'Networking', 'Netgear'),
]

existing = gids('t0003', 'sku', [p[1] for p in PRODUCTS])
new_prods = [p for p in PRODUCTS if p[1] not in existing]
if new_prods:
    pids = ins('t0003',
        ['name','sku','price','cost_price','category','brand','tax_rate','is_active','created_at','created_by'],
        [(n,s,p,cp,cat,b,8.0,True,now_,1) for n,s,p,cp,cat,b in new_prods])
    for pid, p in zip(pids, new_prods):
        existing[p[1]] = pid
print('  Products: %d new, %d total' % (len(new_prods), len(existing)))

# --- Product UOMs ---
existing_puom = gids('t0007', 'product_id', list(existing.values()))
for sku, pid in existing.items():
    if pid not in existing_puom:
        ins('t0007', ['product_id','base_uom_id','purchase_uom_id','sales_uom_id','purchase_factor','sales_factor','created_at','created_by'],
            [(pid, uid, uid, uid, 1.0, 1.0, now_, 1)])

# --- Barcodes ---
existing_bc = gids('t0004', 'product_id', list(existing.values()))
for sku, pid in existing.items():
    if pid not in existing_bc:
        bc = '0%s000000' % str(pid).zfill(5)
        chk = sum(int(bc[i]) * (3 if i % 2 else 1) for i in range(12)) % 10
        chk = (10 - chk) % 10
        ins('t0004', ['product_id','barcode','barcode_type','is_primary','created_at','created_by'],
            [(pid, bc + str(chk), 'EAN13', True, now_, 1)])

# --- Stock ---
INITIAL_STOCK = [
    ('APL-MBP14-M3P',15,3),('APL-MBA13-M3',20,5),('APL-IP15P-256',25,5),('APL-IP15-128',30,8),
    ('APL-IPDP11-M4',12,3),('APL-IPDA-M2',18,4),('APL-AIRP2-USBC',50,15),('APL-AWU2',8,2),
    ('APL-AIRTAG4',40,10),('APL-MAGSFC',60,20),('SAM-GB3P-16',10,2),('SAM-S24U-256',22,5),
    ('SAM-TABS9-256',14,3),('SAM-GW6C-47',12,3),('SAM-BUDS2P',35,10),('SAM-T7-1TB',25,5),
    ('SONY-WHXM5',20,5),('SONY-WFXM5',18,4),('SONY-PS5-SLIM',30,8),('SONY-DUALSENSE',45,12),
    ('DELL-XPS15-9530',8,2),('DELL-XPS13P-9320',10,2),('DELL-U2723QE',7,2),('LEN-TPX1C-G11',10,2),
    ('LEN-TV24-T24I',15,4),('LOG-MX3S',50,15),('LOG-MXKEYS',40,10),('LOG-C920',25,8),
    ('ANK-PC26800',60,20),('ANK-USBC-3PK',100,30),('ANK-NANO2-65',80,25),('MS-SP9-I5',8,2),
    ('MS-XBSX',20,5),('SEA-FC530-2TB',20,5),('SEA-BP-5TB',18,4),('COR-VEN-DDR5-32',35,10),
    ('COR-RM850X',15,4),('COR-K70-RGB',12,3),('INT-i7-14700K',25,5),('INT-i9-14900K',15,3),
    ('AMD-R7-7800X3D',20,5),('AMD-R9-7950X',12,3),('NVD-RTX4080-16',10,2),('NVD-RTX4090-24',5,1),
    ('ASUS-ROG-RTX4080',8,2),('ASUS-PA32DC',3,1),('TPL-AX6000',25,8),('UBI-U6PRO',30,10),('NET-CM2000',15,4),
]

existing_stk = gids('t0009', 'product_id', list(existing.values()))
for sku, qty, reorder in INITIAL_STOCK:
    pid = existing.get(sku)
    if pid and pid not in existing_stk:
        ins('t0009', ['product_id','warehouse_id','qty','reorder_level','created_at','created_by'],
            [(pid, wid, qty, reorder, now_, 1)])

# --- Customers ---
CUSTOMERS = [
    ('TechCorp Solutions', 'Wholesale', 'orders@techcorp.com', 50000, 7500),
    ('Digital Frontier LLC', 'Wholesale', 'procurement@digitalfrontier.io', 35000, 4200),
    ('Apex Retail Group', 'Retail Chain', 'buy@apexretail.com', 25000, 3100),
    ('Dr. Emily Chen', 'Professional', 'emily.chen@example.com', 8000, 1200),
    ('James Wilson', 'Retail', 'jwilson@example.com', 5000, 899),
    ('Sofia Martinez', 'Retail', 'sofia.m@example.com', 3000, 450),
    ('NorthStar IT Services', 'Corporate', 'it@northstarit.com', 75000, 12500),
    ('Greenfield Academy', 'Education', 'admin@greenfield.edu', 20000, 0),
]
ec = gids('t0010', 'name', [c[0] for c in CUSTOMERS])
new_custs = [c for c in CUSTOMERS if c[0] not in ec]
if new_custs:
    cids = ins('t0010',
        ['name','group_name','email','credit_limit','balance','default_price_list_id','default_tax_rate_id','is_active','created_at','created_by'],
        [(n,g,em,cl,bl,pl_id,tx_id,True,now_,1) for n,g,em,cl,bl in new_custs])
    for cid, c in zip(cids, new_custs):
        ec[c[0]] = cid
print('  Customers: %d' % len(ec))

# --- Suppliers ---
SUPPLIERS = [
    ('Apple Distribution Inc.', 'Electronics', 'dist@apple.com', 5),
    ('Samsung Electronics America', 'Electronics', 'b2b@samsung.com', 5),
    ('Sony Electronics B2B', 'Electronics', 'b2b@sony.com', 5),
    ('Ingram Micro', 'Distributor', 'sales@ingrammicro.com', 4),
    ('TechData Inc.', 'Distributor', 'orders@techdata.com', 4),
    ('Corsair Memory Inc.', 'Components', 'wholesale@corsair.com', 5),
    ('Intel Direct Sales', 'Components', 'b2b@intel.com', 4),
    ('AMD Corporate', 'Components', 'b2b@amd.com', 4),
]
es = gids('t0011', 'name', [s[0] for s in SUPPLIERS])
new_supps = [s for s in SUPPLIERS if s[0] not in es]
if new_supps:
    sids = ins('t0011', ['name','category','email','rating','is_active','created_at','created_by'],
               [(n,c,em,r,True,now_,1) for n,c,em,r in new_supps])
    for sid, s in zip(sids, new_supps):
        es[s[0]] = sid
print('  Suppliers: %d' % len(es))

# --- Sales Orders ---
sales_data = [
    ('TechCorp Solutions','SO-1001','Shipped',today_-timedelta(5),
     [('APL-MBP14-M3P',3,1850),('APL-IP15P-256',5,1120),('APL-AIRP2-USBC',10,229)]),
    ('Digital Frontier LLC','SO-1002','Shipped',today_-timedelta(4),
     [('DELL-XPS15-9530',2,1650),('LOG-MX3S',8,85),('LOG-MXKEYS',5,95),('DELL-U2723QE',4,550)]),
    ('Dr. Emily Chen','SO-1003','Paid',today_-timedelta(2),
     [('APL-MBA13-M3',1,1049),('APL-AIRP2-USBC',1,229)]),
    ('James Wilson','SO-1004','Paid',today_-timedelta(1),
     [('SAM-S24U-256',1,1249),('SAM-BUDS2P',1,179)]),
    ('NorthStar IT Services','SO-1005','Pending',today_,
     [('LEN-TPX1C-G11',5,1520),('LEN-TV24-T24I',10,229),('LOG-MX3S',10,85)]),
    ('Apex Retail Group','SO-1006','Pending',today_,
     [('SONY-PS5-SLIM',20,429),('SONY-DUALSENSE',25,59),('APL-AIRTAG4',30,89),('APL-MAGSFC',20,34)]),
    ('Sofia Martinez','SO-1007','Pending',today_,
     [('APL-IP15-128',1,749),('APL-MAGSFC',1,34)]),
    ('Greenfield Academy','SO-1008','Pending',today_,
     [('DELL-XPS13P-9320',8,1280),('DELL-U2723QE',8,550),('LOG-C920',8,69)]),
]
for cust_name, order_num, status, order_date, lines in sales_data:
    if gid('t0012', 'order_number', order_num):
        continue
    cust_id = ec.get(cust_name)
    if not cust_id:
        continue
    subtotal = sum(q*up for _,q,up in lines)
    tax = round(subtotal*0.08,2)
    grand = subtotal+tax
    so_id = ins('t0012',
        ['order_number','customer_id','subtotal','tax','grand_total','status','order_date','price_list_id','tax_rate_id','created_at','created_by'],
        [(order_num, cust_id, subtotal, tax, grand, status, order_date, pl_id, tx_id, now_, 1)])[0]
    for ln, (sku, qty, uprice) in enumerate(lines, 1):
        pid = existing.get(sku)
        if not pid:
            continue
        pname = next(p[0] for p in PRODUCTS if p[1]==sku)
        lt = round(qty*uprice,2)
        ins('t0013',
            ['sales_order_id','product_id','product_name','uom_id','qty','unit_price','line_total','line_number','created_at','created_by'],
            [(so_id, pid, pname, uid, qty, uprice, lt, ln, now_, 1)])
    print('  SO %s' % order_num)

# --- Purchase Orders ---
po_data = [
    ('Apple Distribution Inc.','PO-2001','Received',today_-timedelta(10),
     [('APL-MBP14-M3P',20,1650),('APL-IP15P-256',30,980),('APL-AIRP2-USBC',60,195)]),
    ('Ingram Micro','PO-2002','Received',today_-timedelta(8),
     [('SONY-WHXM5',25,270),('SONY-PS5-SLIM',35,380),('LOG-MX3S',60,72),('LOG-MXKEYS',50,80)]),
    ('Samsung Electronics America','PO-2003','Approved',today_-timedelta(3),
     [('SAM-S24U-256',25,1050),('SAM-TABS9-256',20,650),('SAM-GB3P-16',15,1240)]),
    ('Intel Direct Sales','PO-2004','Pending',today_,
     [('INT-i7-14700K',30,340),('INT-i9-14900K',20,490)]),
    ('Corsair Memory Inc.','PO-2005','Pending',today_,
     [('COR-VEN-DDR5-32',50,80),('COR-RM850X',20,105),('COR-K70-RGB',20,130)]),
]
for supp_name, po_num, status, order_date, lines in po_data:
    if gid('t0014', 'order_number', po_num):
        continue
    supp_id = es.get(supp_name)
    if not supp_id:
        continue
    total = round(sum(q*up for _,q,up in lines),2)
    po_id = ins('t0014',
        ['order_number','supplier_id','total','status','order_date','created_at','created_by'],
        [(po_num, supp_id, total, status, order_date, now_, 1)])[0]
    for ln, (sku, qty, uprice) in enumerate(lines, 1):
        pid = existing.get(sku)
        if not pid:
            continue
        pname = next(p[0] for p in PRODUCTS if p[1]==sku)
        lt = round(qty*uprice,2)
        ins('t0015',
            ['purchase_order_id','product_id','product_name','uom_id','qty','unit_price','line_total','line_number','created_at','created_by'],
            [(po_id, pid, pname, uid, qty, uprice, lt, ln, now_, 1)])
    print('  PO %s' % po_num)

# --- Summary ---
print('\n[4/5] Summary:')
for tbl, label in [('t0001','UOM'),('t0003','Products'),('t0010','Customers'),('t0011','Suppliers'),
                    ('t0012','Sales Orders'),('t0014','Purchase Orders'),('t0009','Stock Records')]:
    cur.execute('SELECT COUNT(*) FROM nova_erp.%s' % tbl)
    print('  %s: %s' % (label, cur.fetchone()[0]))

print('[5/5] Neon seed complete!')
conn.close()
