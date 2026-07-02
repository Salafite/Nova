"""Start the API server and run the full smoke test in one process."""
import os
import sys
import time
import multiprocessing
import subprocess
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_server():
    os.environ['SECRET_KEY'] = 'nova-dev-secret-key-change-in-production'
    import uvicorn
    uvicorn.run('apps.api.main:app', host='0.0.0.0', port=8070, reload=False, log_level='error')

def smoke_test():
    BASE = 'http://localhost:8070/api'
    results = []

    def test(label, fn):
        try:
            ok, detail = fn()
            results.append((label, 'OK' if ok else 'FAIL', detail))
            print(f"  [{ 'OK' if ok else 'FAIL' }] {label}" + (f' — {detail}' if detail else ''))
        except Exception as e:
            results.append((label, 'FAIL', str(e)))
            print(f"  [FAIL] {label} — {e}")

    test('Health check', lambda: (httpx.get(f'{BASE}/health').status_code == 200, ''))
    test('Login', lambda: (
        httpx.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'demo123456'}).status_code == 200,
        ''
    ))

    r = httpx.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'demo123456'})
    if r.status_code != 200:
        print('Cannot proceed without login')
        return results
    token = r.json()['access_token']
    hdrs = {'Authorization': f'Bearer {token}'}

    test('List Products', lambda: (
        (r2 := httpx.get(f'{BASE}/T0003I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Customers', lambda: (
        (r2 := httpx.get(f'{BASE}/T0010I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Sales Orders', lambda: (
        (r2 := httpx.get(f'{BASE}/T0012I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))

    # Confirm a Draft order
    r2 = httpx.get(f'{BASE}/T0012I/', headers=hdrs)
    if r2.status_code == 200:
        draft = [o for o in r2.json() if o.get('status') == 'Draft']
        if draft:
            oid = draft[0]['id']
            test('Confirm Sales Order', lambda: (
                (r3 := httpx.post(f'{BASE}/T0012I/{oid}/confirm', headers=hdrs)).status_code == 200,
                f'order {oid} -> {r3.json().get("status")}'
            ))
        else:
            print('  [SKIP] Confirm Sales Order (no Draft order found)')

    test('List Pick Lists', lambda: (
        (r2 := httpx.get(f'{BASE}/T0101I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Invoices', lambda: (
        (r2 := httpx.get(f'{BASE}/T0090I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Payments', lambda: (
        (r2 := httpx.get(f'{BASE}/T0091I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List UOMs', lambda: (
        (r2 := httpx.get(f'{BASE}/T0001I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Suppliers', lambda: (
        (r2 := httpx.get(f'{BASE}/T0011I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('List Warehouses', lambda: (
        (r2 := httpx.get(f'{BASE}/T0008I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('Stock Levels', lambda: (
        (r2 := httpx.get(f'{BASE}/T0009I/', headers=hdrs)).status_code == 200,
        f'{len(r2.json())} records'
    ))
    test('Unauthorized → 401', lambda: (
        httpx.get(f'{BASE}/T0003I/').status_code in (401, 403),
        ''
    ))

    return results

if __name__ == '__main__':
    proc = multiprocessing.Process(target=start_server, daemon=True)
    proc.start()
    time.sleep(6)

    print('Smoke test results:')
    print()
    results = smoke_test()
    print()
    passed = sum(1 for _, s, _ in results if s == 'OK')
    print(f'{passed}/{len(results)} tests passed')
    proc.terminate()
