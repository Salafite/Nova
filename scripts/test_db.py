"""Find missing table numbers in 1-100 range"""
import os

present = set()
for module in os.listdir('modules'):
    ctrl_dir = os.path.join('modules', module, 'controllers')
    if not os.path.isdir(ctrl_dir):
        continue
    for fn in os.listdir(ctrl_dir):
        if fn.endswith('I.py') and fn.startswith('T'):
            num = int(fn[1:5])
            present.add(num)

missing = sorted(set(range(1, 101)) - present)
print(f'Present: {len(present)} controllers')
print(f'Missing numbers ({len(missing)}):')
for n in missing:
    print(f'  T{n:04d}')
