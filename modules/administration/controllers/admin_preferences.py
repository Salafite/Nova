from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from modules.administration.services.user_preferences_service import UserPreferencesService
from packages.auth.deps import get_current_user

router = APIRouter(prefix='/api/admin/users', tags=['Admin User Preferences'],
                   dependencies=[Depends(get_current_user)])

service = UserPreferencesService()


class PreferencesUpdate(BaseModel):
    preferences: dict[str, str]


def require_admin(user: dict):
    if user.get('role') != 'Admin':
        raise HTTPException(403, 'Admin access required')
    return user


@router.get('/{user_id}/preferences')
def get_user_preferences(user_id: int, current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    return {'preferences': service.get_all(user_id)}


@router.put('/{user_id}/preferences')
def update_user_preferences(user_id: int, body: PreferencesUpdate,
                            current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    return service.save(user_id, body.preferences)
