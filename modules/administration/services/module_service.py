from pathlib import Path
from datetime import datetime
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository


class ModuleService(CrudService):
    def __init__(self, repo: CrudRepository):
        super().__init__(repo)
        self.modules_dir = Path(__file__).parent.parent.parent

    def discover_available(self):
        discovered = []
        if not self.modules_dir.exists():
            return discovered
        for entry in sorted(self.modules_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith('_') or entry.name.startswith('.'):
                continue
            init_file = entry / '__init__.py'
            controllers_dir = entry / 'controllers'
            has_controllers = controllers_dir.exists() and any(controllers_dir.glob('T*I.py'))
            discovered.append({
                'module_key': entry.name,
                'name': entry.name.replace('_', ' ').title(),
                'description': f'{entry.name.replace("_", " ").title()} module',
                'has_controllers': has_controllers,
                'path': str(entry.relative_to(self.modules_dir.parent.parent)),
            })
        return discovered

    def install_module(self, module_key: str, user_id: int = None):
        existing = self.repo.list({'module_key': module_key})
        if existing:
            return {'ok': False, 'error': 'Module already registered'}
        discovered = self.discover_available()
        match = next((m for m in discovered if m['module_key'] == module_key), None)
        if not match:
            return {'ok': False, 'error': 'Module not found in filesystem'}
        payload = {
            'module_key': match['module_key'],
            'name': match['name'],
            'description': match['description'],
            'installed_at': datetime.utcnow().isoformat(),
            'is_active': True,
            'is_core': module_key in ('core', 'administration'),
        }
        if user_id:
            payload['created_by'] = user_id
        result = self.repo.create(payload)
        return {'ok': True, 'module': result}

    def uninstall_module(self, id_val: int):
        module = self.repo.get(id_val)
        if not module:
            return {'ok': False, 'error': 'Module not found'}
        if module.get('is_core'):
            return {'ok': False, 'error': 'Cannot uninstall core module'}
        self.repo.delete(id_val)
        return {'ok': True}

    def toggle_module(self, id_val: int, active: bool):
        module = self.repo.get(id_val)
        if not module:
            return {'ok': False, 'error': 'Module not found'}
        if module.get('is_core') and not active:
            return {'ok': False, 'error': 'Cannot disable core module'}
        result = self.repo.update(id_val, {'is_active': active})
        return {'ok': True, 'module': result}
