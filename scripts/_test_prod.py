"""Test production API at alsahili.com"""
import httpx
import json

BASE = 'https://alsahili.com/api'

# Step 1: Login
print('=== Login ===')
r = httpx.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=10)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    token = data.get('access_token') or data.get('token')
    print(f'Token: {token[:50] if token else "none"}...')
else:
    print(f'Response: {r.text[:500]}')
    token = None

if token:
    headers = {'Authorization': f'Bearer {token}'}

    # Step 2: Fetch products
    print('\n=== GET /api/T0003I/ ===')
    r = httpx.get(f'{BASE}/T0003I/', headers=headers, timeout=10)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            print(f'Products: {len(data)}')
            for p in data[:5]:
                print(f'  {p.get("id")}: {p.get("name")} ({p.get("sku")}) ${p.get("price")}')
        else:
            print(json.dumps(data, indent=2)[:1000])
    else:
        print(f'Response: {r.text[:2000]}')
else:
    print('Cannot proceed without token')
