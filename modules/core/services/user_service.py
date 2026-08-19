from modules.core.services.base import CrudService
from modules.core.services.permission_service import derive_permissions


class UserService(CrudService):
    PROTECTED_FIELDS = {'role', 'password_hash', 'permissions'}

    def create(self, payload: dict):
        payload = payload or {}
        found = self.PROTECTED_FIELDS & set(payload.keys())
        if found:
            raise ValueError(f"Protected fields cannot be supplied in user creation: {', '.join(sorted(found))}")

        data = dict(payload)
        data['role'] = 'Viewer'
        data['permissions'] = derive_permissions('Viewer')
        data.setdefault('password_hash', '')
        return super().create(data)

    def update(self, id_val, payload: dict):
        payload = payload or {}
        found = self.PROTECTED_FIELDS & set(payload.keys())
        if found:
            raise ValueError(f"Protected fields cannot be modified via user update: {', '.join(sorted(found))}")

        return super().update(id_val, payload)

    def update_role(self, id_val: int, role: str, permissions: list[str] = None):
        if permissions is None:
            permissions = derive_permissions(role)
        return super().update(id_val, {'role': role, 'permissions': permissions})
