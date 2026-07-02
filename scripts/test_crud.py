"""Quick comprehensive test of all endpoints"""
import requests
t = requests.post('http://localhost:8000/api/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=5).json()['access_token']
headers = {'Authorization': f'Bearer {t}'}

endpoints = ['T0001I','T0002I','T0003I','T0004I','T0005I','T0006I','T0007I','T0008I','T0009I',
    'T0010I','T0011I','T0012I','T0013I','T0014I','T0015I','T0016I','T0017I','T0018I','T0019I','T0020I',
    'T0021I','T0022I','T0023I','T0025I',
    'T0026I','T0027I','T0028I','T0029I','T0030I',
    'T0090I','T0091I','T0096I','T0097I','T0098I','T0099I','T0100I']

ok = 0
fail = []
for ep in endpoints:
    r = requests.get(f'http://localhost:8000/api/{ep}/', headers=headers, timeout=5)
    if r.status_code == 200:
        ok += 1
    else:
        fail.append((ep, r.status_code))

print(f'{ok}/{len(endpoints)} endpoints OK')
if fail:
    for ep, s in fail:
        print(f'  {ep}: {s}')
else:
    print('All endpoints green!')
