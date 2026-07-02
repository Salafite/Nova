from modules.core.services.base import CrudService
from modules.core.services.permission_service import derive_permissions


class UserService(CrudService):
    def create(self, payload: dict):
        if not payload.get('permissions'):
            payload['permissions'] = derive_permissions(payload.get('role', 'Viewer'))
        return super().create(payload)
