import importlib
import sys
from pathlib import Path

all_routers = []
# Find all modules/*/controllers/T*I.py
modules_dir = Path(__file__).parent.parent.parent
for f in sorted(modules_dir.rglob('controllers/T*I.py')):
    if f.stem.startswith('T') and f.stem.endswith('I'):
        modname = f.stem
        # e.g., modules.inventory.controllers.T0001I
        module_path = f.relative_to(modules_dir.parent).with_suffix('').parts
        import_path = '.'.join(module_path)
        module = importlib.import_module(import_path)
        all_routers.append(module.router)
