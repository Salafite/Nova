import json
from datetime import datetime, date, timezone
from decimal import Decimal
from fastapi import Depends, HTTPException, status
from modules.administration.models import UserCreate, UserUpdate, UserRoleUpdate, UserResponse
from modules.core.services.user_service import UserService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import create_crud_router
from packages.auth.deps import get_current_user, require_permission

repo = CrudRepository('T0021', business_columns=['id', 'username', 'password_hash', 'full_name', 'email', 'role', 'permissions', 'status', 'last_login'])
service = UserService(repo)
router = create_crud_router('/api/T0021I', 'T0021 - System Users', service,
                            UserCreate, UserUpdate, UserResponse)

audit_repo = CrudRepository('T0023', pk='id', business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at'])


def _json_safe(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


@router.put('/{id}/role', response_model=UserResponse, dependencies=[Depends(require_permission('ADMIN_VIEW'))])
def update_user_role(id: int, body: UserRoleUpdate, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    result = service.update_role(id, role=body.role, permissions=body.permissions)
    if result:
        audit_repo.create({
            'table_name': 'T0021',
            'record_id': id,
            'action': 'UPDATE',
            'changed_data': json.dumps({'before': existing, 'after': result}, default=_json_safe),
            'changed_by': user.get('id') if user else None,
            'changed_at': datetime.now(timezone.utc).isoformat()
        })
    return result

