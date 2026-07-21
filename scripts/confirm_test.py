"""Start uvicorn via subprocess, test the confirm endpoint, then clean up."""
import os
import sys
import time
import subprocess
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = 'http://localhost:8070/api'

# Start uvicorn process
env = os.environ.copy()
env['SECRET_KEY'] = 'nova-dev-secret-key-change-in-production'
proc = subprocess.Popen(
    [sys.executable, '-c',
     'import os, uvicorn; '
     'os.environ["SECRET_KEY"]="nova-dev-secret-key-change-in-production"; '
     'uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8070, reload=False, log_level="error")'],
    cwd='G:/240626/Nova',
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# Wait for server
for i in range(30):
    time.sleep(1)
    try:
        r = httpx.get(f'{BASE}/health', timeout=2)
        if r.status_code == 200:
            print(f'Server ready (attempt {i+1})')
            break
    except Exception:
        pass
else:
    print('Server failed to start')
    proc.kill()
    sys.exit(1)

try:
    # Login
    r = httpx.post(f'{BASE}/auth/login', json={'username':'admin','password':'demo123456'})
    token = r.json()['access_token']
    hdrs = {'Authorization': f'Bearer {token}'}
    print(f'Login OK, token={token[:20]}...')

    # Get draft orders
    r = httpx.get(f'{BASE}/T0012I/', headers=hdrs)
    draft = [o for o in r.json() if o.get('status') == 'Draft']
    if not draft:
        print('No Draft orders found')
        proc.kill()
        sys.exit(1)
    
    oid = draft[0]['id']
    print(f'Found Draft order: id={oid}, number={draft[0].get("order_number")}')

    # Confirm it
    r = httpx.post(f'{BASE}/T0012I/{oid}/confirm', headers=hdrs)
    print(f'Confirm response: status={r.status_code}')
    if r.status_code == 200:
        print(f'Body: id={r.json().get("id")}, status={r.json().get("status")}')
        print('SUCCESS: Draft order confirmed!')
    else:
        print(f'Body: {r.text[:500]}')

    # Verify the update
    r = httpx.get(f'{BASE}/T0012I/', headers=hdrs)
    updated = [o for o in r.json() if o['id'] == oid]
    if updated:
        print(f'Verified: order {oid} now has status "{updated[0]["status"]}"')
finally:
    proc.kill()
    print('Done')
