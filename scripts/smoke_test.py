"""Integration smoke test — runs against the live API server."""
import sys
import requests

BASE = 'http://localhost:8070'

ok = 0
total = 0


def check(label, status, expected=200):
    global ok, total
    total += 1
    if status == expected:
        ok += 1
        print(f'  PASS  {label}')
    else:
        print(f'  FAIL  {label}  (got {status}, expected {expected})')


def check_any(label, status, expected=(200, 201)):
    global ok, total
    total += 1
    if status in expected:
        ok += 1
        print(f'  PASS  {label}')
    else:
        print(f'  FAIL  {label}  (got {status}, expected {expected})')


def section(title):
    print(f'\n=== {title} ===')


# ─── Health ────────────────────────────────────────────────────────────
section('Health')
r = requests.get(f'{BASE}/api/health', timeout=5)
check('GET /api/health', r.status_code)
data = r.json()
check('health status ok', 200 if data.get('status') == 'ok' else 500)

# ─── Auth ──────────────────────────────────────────────────────────────
section('Auth')
r = requests.post(f'{BASE}/api/auth/login',
                  json={'username': 'testuser', 'password': 'password123'}, timeout=5)
check('POST /api/auth/login (valid)', r.status_code)
token = r.json().get('access_token', '')
check('access_token returned', 200 if token else 500)
headers = {'Authorization': f'Bearer {token}'}

r = requests.post(f'{BASE}/api/auth/login',
                  json={'username': 'baduser', 'password': 'badpass'}, timeout=5)
check('POST /api/auth/login (invalid)', r.status_code, 401)

r = requests.get(f'{BASE}/api/auth/me', headers=headers, timeout=5)
check('GET /api/auth/me', r.status_code)
check('username matches', 200 if r.json().get('username') == 'testuser' else 500)

r = requests.get(f'{BASE}/api/auth/me', timeout=5)
check('GET /api/auth/me (no auth)', r.status_code, 401)

# ─── CRUD: Products (T0003I) ──────────────────────────────────────────
section('Products')
r = requests.get(f'{BASE}/api/T0003I/', headers=headers, timeout=5)
check('GET /api/T0003I/ (list)', r.status_code)

import time
_unique = int(time.time() * 1000)
product_payload = {
    'name': 'E2E Test Widget',
    'sku': f'E2E-SKU-{_unique}',
    'price': 19.99,
    'cost_price': 10.00,
    'category': 'Test',
    'tax_rate': 0.08,
}
r = requests.post(f'{BASE}/api/T0003I/', json=product_payload, headers=headers, timeout=5)
check_any('POST /api/T0003I/ (create)', r.status_code, (200, 201))
created = r.json()
product_id = created.get('id')
check(f'created product id={product_id}', 200 if product_id else 500)

if product_id:
    r = requests.get(f'{BASE}/api/T0003I/{product_id}', headers=headers, timeout=5)
    check(f'GET /api/T0003I/{product_id}', r.status_code)
    check('name matches', 200 if r.json().get('name') == product_payload['name'] else 500)

    r = requests.put(f'{BASE}/api/T0003I/{product_id}', json={'price': 24.99},
                     headers=headers, timeout=5)
    check(f'PUT /api/T0003I/{product_id} (update)', r.status_code)

    r = requests.get(f'{BASE}/api/T0003I/{product_id}', headers=headers, timeout=5)
    check('price updated', 200 if r.json().get('price') == 24.99 else 500)

    r = requests.delete(f'{BASE}/api/T0003I/{product_id}', headers=headers, timeout=5)
    check(f'DELETE /api/T0003I/{product_id}', r.status_code, 204)

    r = requests.get(f'{BASE}/api/T0003I/{product_id}', headers=headers, timeout=5)
    is_inactive = not r.json().get('is_active', True) if r.status_code == 200 else True
    check('soft-deleted inactive', 200 if is_inactive else 500)

# ─── CRUD: Customers (T0010I) ─────────────────────────────────────────
section('Customers')
r = requests.get(f'{BASE}/api/T0010I/', headers=headers, timeout=5)
check('GET /api/T0010I/', r.status_code)

cust = {'name': 'E2E Customer', 'phone': '555-0000', 'email': 'e2e@test.com'}
r = requests.post(f'{BASE}/api/T0010I/', json=cust, headers=headers, timeout=5)
check_any('POST /api/T0010I/', r.status_code, (200, 201))
cust_id = r.json().get('id')
if cust_id:
    r = requests.delete(f'{BASE}/api/T0010I/{cust_id}', headers=headers, timeout=5)
    check(f'DELETE /api/T0010I/{cust_id}', r.status_code, 204)

# ─── CRUD: Suppliers (T0011I) ─────────────────────────────────────────
section('Suppliers')
r = requests.get(f'{BASE}/api/T0011I/', headers=headers, timeout=5)
check('GET /api/T0011I/', r.status_code)

sup = {'name': 'E2E Supplier', 'phone': '555-1111', 'email': 'sup@test.com'}
r = requests.post(f'{BASE}/api/T0011I/', json=sup, headers=headers, timeout=5)
check_any('POST /api/T0011I/', r.status_code, (200, 201))
sup_id = r.json().get('id')
if sup_id:
    r = requests.delete(f'{BASE}/api/T0011I/{sup_id}', headers=headers, timeout=5)
    check(f'DELETE /api/T0011I/{sup_id}', r.status_code, 204)

# ─── Orders (T0009I) ──────────────────────────────────────────────────
section('Orders')
r = requests.get(f'{BASE}/api/T0009I/', headers=headers, timeout=5)
check('GET /api/T0009I/ (list)', r.status_code)

# ─── Warehouse / Pick Lists ───────────────────────────────────────────
section('Warehouse')
for ep in ['T0101I']:
    r = requests.get(f'{BASE}/api/{ep}/', headers=headers, timeout=5)
    check(f'GET /api/{ep}/', r.status_code)

# ─── Categories ───────────────────────────────────────────────────────
section('Categories')
r = requests.get(f'{BASE}/api/categories/', headers=headers, timeout=5)
check('GET /api/categories/', r.status_code)

# ─── Billing (401 expected — testuser has no business_id) ─────────────
section('Billing')
r = requests.get(f'{BASE}/api/billing/subscription', headers=headers, timeout=5)
check('GET /api/billing/subscription (no business_id)', r.status_code, 401)

# ─── Phantom scan ─────────────────────────────────────────────────────
section('Phantoms')
r = requests.post(f'{BASE}/api/T0003I/scan-phantoms', headers=headers, timeout=5)
check('POST /api/T0003I/scan-phantoms', r.status_code)

# ─── 404 handling ─────────────────────────────────────────────────────
section('Edge cases')
r = requests.get(f'{BASE}/api/T9999I/', headers=headers, timeout=5)
check('GET nonexistent API endpoint', r.status_code, 404)
check('404 returns JSON', 200 if 'application/json' in r.headers.get('content-type', '') else 500)

r = requests.get(f'{BASE}/api/T0003I/99999999', headers=headers, timeout=5)
check('GET nonexistent product', r.status_code, 404)

# ─── CORS headers ─────────────────────────────────────────────────────
section('CORS')
r = requests.get(f'{BASE}/api/health', timeout=5, headers={'Origin': 'http://localhost:5173'})
check('CORS allow-origin header present with Origin',
      200 if r.headers.get('access-control-allow-origin') else 500)

# ─── Security headers ─────────────────────────────────────────────────
section('Security headers')
r = requests.get(f'{BASE}/api/health', timeout=5)
check('X-Content-Type-Options header',
      200 if r.headers.get('x-content-type-options') == 'nosniff' else 500)
check('X-Frame-Options header',
      200 if r.headers.get('x-frame-options') == 'DENY' else 500)
check('CSP header present',
      200 if r.headers.get('content-security-policy') else 500)

# ─── Summary ──────────────────────────────────────────────────────────
print(f'\n{"="*40}')
print(f'  {ok}/{total} checks passed')
print(f'  {"ALL GREEN" if ok == total else "SOME FAILURES"}')
print(f'{"="*40}')
sys.exit(0 if ok == total else 1)
