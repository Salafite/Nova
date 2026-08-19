import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from modules.administration.services.user_preferences_service import UserPreferencesService
from modules.administration.models import UserRoleUpdate, UserResponse
from modules.administration.controllers.T0021I import service as user_service, audit_repo as user_audit_repo, _json_safe
from packages.auth.deps import get_current_user, require_permission

router = APIRouter(prefix='/api/admin/users', tags=['Admin User Preferences'],
                   dependencies=[Depends(require_permission('ADMIN_VIEW'))])

service = UserPreferencesService()


class PreferencesUpdate(BaseModel):
    preferences: dict[str, str]


@router.get('/{user_id}/preferences')
def get_user_preferences(user_id: int):
    return {'preferences': service.get_all(user_id)}


@router.put('/{user_id}/preferences')
def update_user_preferences(user_id: int, body: PreferencesUpdate):
    return service.save(user_id, body.preferences)


@router.put('/{user_id}/role', response_model=UserResponse)
def update_user_role(user_id: int, body: UserRoleUpdate, user: dict = Depends(get_current_user)):
    existing = user_service.get(user_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    result = user_service.update_role(user_id, role=body.role, permissions=body.permissions)
    if result:
        user_audit_repo.create({
            'table_name': 'T0021',
            'record_id': user_id,
            'action': 'UPDATE',
            'changed_data': json.dumps({'before': existing, 'after': result}, default=_json_safe),
            'changed_by': user.get('id') if user else None,
            'changed_at': datetime.now(timezone.utc).isoformat()
        })
    return result

