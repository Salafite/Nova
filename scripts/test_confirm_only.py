"""Quick test for confirm endpoint."""
import os, sys, time, threading
os.environ['SECRET_KEY'] = 'nova-dev-secret-key-change-in-production'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import uvicorn

def start():
    uvicorn.run('apps.api.main:app', host='0.0.0.0', port=8071, reload=False, log_level='error')

t = threading.Thread(target=start, daemon=True)
t.start()
time.sleep(5)

BASE = 'http://localhost:8071/api'
r = httpx.post(f'{BASE}/auth/login', json={'username':'admin','password':'demo123456'})
token = r.json()['access_token']
hdrs = {'Authorization':f'Bearer {token}'}

r = httpx.get(f'{BASE}/T0012I/', headers=hdrs)
draft = [o for o in r.json() if o.get('status') == 'Draft'][0]
print(f'Draft: id={draft["id"]} status={draft["status"]}')

r = httpx.post(f'{BASE}/T0012I/{draft["id"]}/confirm', headers=hdrs)
print(f'Status: {r.status_code}')
print(f'Body: {r.text[:300]}')
