import requests
BASE = 'http://localhost:8070'
r = requests.post(f'{BASE}/api/auth/login', json={'username': 'testuser', 'password': 'password123'}, timeout=5)
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get(f'{BASE}/api/auth/me', headers=headers, timeout=5)
user = r.json()
print('Me response:')
for k, v in user.items():
    print(f'  {k}: {v}')

print()
r = requests.get(f'{BASE}/api/T0001I/', headers=headers, timeout=5)
if r.status_code == 200:
    users = r.json()
    print(f'Users table ({len(users)} rows):')
    for u in users[:3]:
        print(f'  id={u.get("id")} username={u.get("username")} keys={list(u.keys())}')
