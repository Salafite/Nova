"""Start uvicorn, run full order-to-cash smoke test, clean up."""
import os
import sys
import time
import subprocess
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = 'http://localhost:8070/api'

# Start server
env = os.environ.copy()
env['SECRET_KEY'] = 'nova-dev-secret-key-change-in-production'
proc = subprocess.Popen(
    [sys.executable, '-c',
     'import os, uvicorn; '
     'os.environ["SECRET_KEY"]="nova-dev-secret-key-change-in-production"; '
     'uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8070, reload=False, log_level="error")'],
    cwd='G:/240626/Nova', env=env,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

for i in range(30):
    time.sleep(1)
    try:
        r = httpx.get(f'{BASE}/health', timeout=2)
        if r.status_code == 200:
            break
    except Exception:
            pass
else:
    print('Server failed to start'); proc.kill(); sys.exit(1)

passed = 0
failed = 0

def test(label, ok, detail=''):
    global passed, failed
    if ok:
        passed += 1
        print(f'  [OK] {label}' + (f' -- {detail}' if detail else ''))
    else:
        failed += 1
        print(f'  [FAIL] {label}' + (f' -- {detail}' if detail else ''))

try:
    r = httpx.get(f'{BASE}/health')
    test('Health check', r.status_code == 200, r.json().get('status'))

    r = httpx.post(f'{BASE}/auth/login', json={'username':'admin','password':'demo123456'})
    test('Login', r.status_code == 200)
    if r.status_code != 200:
        raise Exception('Login failed')
    token = r.json()['access_token']
    h = {'Authorization': f'Bearer {token}'}

    r = httpx.get(f'{BASE}/T0001I/', headers=h)
    test('List UOMs', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0003I/', headers=h)
    test('List Products', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0010I/', headers=h)
    test('List Customers', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0011I/', headers=h)
    test('List Suppliers', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0008I/', headers=h)
    test('List Warehouses', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0009I/', headers=h)
    test('List Stock Levels', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0012I/', headers=h)
    orders = r.json() if r.status_code == 200 else []
    test('List Sales Orders', r.status_code == 200, f'{len(orders)} records')

    r = httpx.get(f'{BASE}/T0101I/', headers=h)
    test('List Pick Lists', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0090I/', headers=h)
    test('List Invoices', r.status_code == 200, f'{len(r.json())} records')

    r = httpx.get(f'{BASE}/T0091I/', headers=h)
    test('List Payments', r.status_code == 200, f'{len(r.json())} records')

    # Confirm a Draft order
    draft = [o for o in orders if o.get('status') == 'Draft']
    if draft:
        oid = draft[0]['id']
        r = httpx.post(f'{BASE}/T0012I/{oid}/confirm', headers=h)
        test('Confirm Draft order', r.status_code == 200, f'order {oid} -> {r.json().get("status")}')
    else:
        test('Confirm Draft order (no drafts)', False)

    r = httpx.get(f'{BASE}/T0012I/', headers=h)
    orders = r.json() if r.status_code == 200 else []
    draft = [o for o in orders if o.get('status') == 'Draft']
    if draft:
        oid = draft[0]['id']
        r = httpx.post(f'{BASE}/T0012I/{oid}/cancel', headers=h)
        test('Cancel Draft order', r.status_code == 200, f'order {oid} -> {r.json().get("status")}')
    else:
        pending = [o for o in orders if o.get('status') == 'Pending']
        if pending:
            oid = pending[0]['id']
            r = httpx.post(f'{BASE}/T0012I/{oid}/cancel', headers=h)
            test('Cancel Pending order', r.status_code == 200, f'order {oid}')
        else:
            test('Cancel order (no cancellable)', False)

    # Pick list workflow
    r = httpx.get(f'{BASE}/T0101I/', headers=h)
    pls = r.json() if r.status_code == 200 else []
    if pls:
        pid = pls[0]['id']
        r = httpx.post(f'{BASE}/T0101I/{pid}/start', headers=h)
        test('Start Pick List', r.status_code == 200, f'picklist {pid}' if r.status_code == 200 else str(r.status_code))

        r = httpx.get(f'{BASE}/T0101I/{pid}/detail', headers=h)
        if r.status_code == 200:
            items = r.json().get('items', [])
            if items:
                item_id = items[0]['id']
                qty = items[0].get('qty_ordered', 1)
                r = httpx.post(f'{BASE}/T0101I/{pid}/pick-item/{item_id}', json={'qty': qty}, headers=h)
                test('Pick Item', r.status_code in (200, 201), str(r.status_code))

        r = httpx.post(f'{BASE}/T0101I/{pid}/complete', headers=h)
        test('Complete Pick List', r.status_code in (200, 400), str(r.status_code))
    else:
        test('Pick List operations (no data)', False)

    # Record payment
    r = httpx.get(f'{BASE}/T0090I/', headers=h)
    invs = r.json() if r.status_code == 200 else []
    unpaid = [inv for inv in invs if inv.get('status') != 'Paid']
    if unpaid:
        inv = unpaid[0]
        r = httpx.post(f'{BASE}/T0091I/', json={
            'invoice_id': inv['id'], 'partner_id': inv.get('partner_id', 1),
            'amount': round(float(inv.get('total_amount', 100)) / 2, 2),
            'payment_method': 'Cash',
            'payment_date': '2024-12-01', 'status': 'Completed',
        }, headers=h)
        test('Record Payment', r.status_code in (200, 201), f'invoice {inv["id"]}')
    else:
        test('Record Payment (no unpaid invoices)', False)

    r = httpx.post(f'{BASE}/T0003I/scan-phantoms', headers=h)
    test('Scan Phantoms', r.status_code == 200)

    r = httpx.post(f'{BASE}/T0010I/', json={
        'name': 'Smoke Test Cust', 'phone': '+201000000001', 'email': 'smoke2@test.com',
    }, headers=h)
    test('Create Customer', r.status_code == 201, f'id={r.json().get("id", "?")}')

    r = httpx.get(f'{BASE}/T0003I/')
    test('Unauthorized returns 401', r.status_code in (401, 403), str(r.status_code))

    print()
    print(f'{passed}/{passed + failed} tests passed')

finally:
    proc.kill()
