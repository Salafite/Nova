"""
Smoke test for Nova ERP API — tests the full order-to-cash flow.
Run with the backend already started on port 8070.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

BASE = 'http://localhost:8070/api'

def log(label, ok=True, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f'  [{status}] {label}' + (f' — {detail}' if detail else ''))

def main():
    # 1. Health check
    r = httpx.get(f'{BASE}/health')
    log('Health check', r.status_code == 200, r.json().get('status', ''))

    # 2. Login
    r = httpx.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'demo123456'})
    if r.status_code != 200:
        log('Login', False, f'{r.status_code} {r.text}')
        return
    token = r.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    log('Login', True, f'token={token[:20]}...')

    # 3. List UOMs
    r = httpx.get(f'{BASE}/T0001I/', headers=headers)
    log('List UOMs', r.status_code == 200, f'{len(r.json())} records')

    # 4. List Products
    r = httpx.get(f'{BASE}/T0003I/', headers=headers)
    log('List Products', r.status_code == 200, f'{len(r.json())} records')

    # 5. List Customers
    r = httpx.get(f'{BASE}/T0010I/', headers=headers)
    customers = r.json() if r.status_code == 200 else []
    log('List Customers', r.status_code == 200, f'{len(customers)} records')

    # 6. List Suppliers
    r = httpx.get(f'{BASE}/T0011I/', headers=headers)
    log('List Suppliers', r.status_code == 200, f'{len(r.json())} records')

    # 7. List Warehouses
    r = httpx.get(f'{BASE}/T0008I/', headers=headers)
    log('List Warehouses', r.status_code == 200, f'{len(r.json())} records')

    # 8. List Stock Levels
    r = httpx.get(f'{BASE}/T0009I/', headers=headers)
    log('List Stock Levels', r.status_code == 200, f'{len(r.json())} records')

    # 9. List Sales Orders
    r = httpx.get(f'{BASE}/T0012I/', headers=headers)
    log('List Sales Orders', r.status_code == 200, f'{len(r.json())} records')

    # 10. List Pick Lists
    r = httpx.get(f'{BASE}/T0101I/', headers=headers)
    log('List Pick Lists', r.status_code == 200, f'{len(r.json())} records')

    # 11. List Invoices
    r = httpx.get(f'{BASE}/T0090I/', headers=headers)
    log('List Invoices', r.status_code == 200, f'{len(r.json())} records')

    # 12. List Payments
    r = httpx.get(f'{BASE}/T0091I/', headers=headers)
    log('List Payments', r.status_code == 200, f'{len(r.json())} records')

    # 13. Confirm a sales order (pick first draft order)
    if customers:
        r = httpx.get(f'{BASE}/T0012I/', headers=headers)
        orders = r.json() if r.status_code == 200 else []
        # Find a draft order to confirm
        draft = [o for o in orders if o.get('status') == 'Draft']
        if draft:
            oid = draft[0]['id']
            r = httpx.post(f'{BASE}/T0012I/{oid}/confirm', headers=headers)
            log('Confirm Sales Order', r.status_code == 200, f'order {oid}')
        else:
            log('Confirm Sales Order (no draft found)', orders and len(orders) > 0)

    # 14. Cancel an order
    if customers:
        draft2 = [o for o in (httpx.get(f'{BASE}/T0012I/', headers=headers)).json() if o.get('status') == 'Draft']
        if draft2:
            oid = draft2[0]['id']
            r = httpx.post(f'{BASE}/T0012I/{oid}/cancel', headers=headers)
            log('Cancel Sales Order', r.status_code == 200, f'order {oid}')

    # 15. Pick List operations (start, pick an item, complete)
    r = httpx.get(f'{BASE}/T0101I/', headers=headers)
    picklists = r.json() if r.status_code == 200 else []
    if picklists:
        pl = picklists[0]
        pid = pl['id']

        # Start pick list
        r = httpx.post(f'{BASE}/T0101I/{pid}/start', headers=headers)
        log('Start Pick List', r.status_code == 200, f'picklist {pid}')

        # Pick an item
        r = httpx.get(f'{BASE}/T0101I/{pid}/detail', headers=headers)
        if r.status_code == 200:
            items = r.json().get('items', [])
            if items:
                item_id = items[0]['id']
                r = httpx.post(f'{BASE}/T0101I/{pid}/pick-item/{item_id}', json={'qty': items[0].get('qty_ordered', 1)}, headers=headers)
                log('Pick Item', r.status_code == 200 or r.status_code == 422, str(r.status_code))

        # Complete pick list
        r = httpx.post(f'{BASE}/T0101I/{pid}/complete', headers=headers)
        log('Complete Pick List', r.status_code == 200 or r.status_code == 400, str(r.status_code))
    else:
        log('Pick List operations (no pick lists)')

    # 16. Record a payment against an invoice
    r = httpx.get(f'{BASE}/T0090I/', headers=headers)
    invoices = r.json() if r.status_code == 200 else []
    unpaid = [inv for inv in invoices if inv.get('status') != 'Paid']
    if unpaid:
        inv = unpaid[0]
        r = httpx.post(f'{BASE}/T0091I/', json={
            'invoice_id': inv['id'],
            'partner_id': inv.get('partner_id', 1),
            'amount': round(inv.get('total_amount', 100) / 2, 2),
            'payment_method': 'Cash',
            'payment_date': '2024-12-01',
            'status': 'Completed',
        }, headers=headers)
        log('Record Payment', r.status_code == 201 or r.status_code == 200, f'invoice {inv["id"]}')

    # 17. Scan phantoms
    r = httpx.post(f'{BASE}/T0003I/scan-phantoms', headers=headers)
    log('Scan Phantoms', r.status_code == 200, f'{r.json().get("flagged", 0)} flagged')

    # 18. BI Dashboard summary
    r = httpx.get(f'{BASE}/bi/dashboard/summary', headers=headers)
    log('BI Dashboard Summary', r.status_code == 200)

    # 19. Create a new customer (write test)
    r = httpx.post(f'{BASE}/T0010I/', json={
        'name': 'Smoke Test Customer',
        'phone': '+201000000000',
        'email': 'smoke@test.com',
    }, headers=headers)
    log('Create Customer', r.status_code == 201, f'id={r.json().get("id", "?")}')

    # 20. Unauthorized access test
    r = httpx.get(f'{BASE}/T0003I/')
    log('Unauthorized access returns 403/401', r.status_code in (401, 403), str(r.status_code))

    print()
    print('Smoke test complete!')

if __name__ == '__main__':
    main()
