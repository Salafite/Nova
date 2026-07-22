from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from modules.administration.services.user_preferences_service import UserPreferencesService
from packages.auth.deps import get_current_user

router = APIRouter(prefix='/api/user/preferences', tags=['User Preferences'],
                   dependencies=[Depends(get_current_user)])

service = UserPreferencesService()


class PreferencesUpdate(BaseModel):
    preferences: dict[str, str]


@router.get('/')
def get_preferences(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get('id')
    if not user_id:
        raise HTTPException(401, 'User not authenticated')
    return {'preferences': service.get_all(user_id)}


@router.put('/')
def update_preferences(body: PreferencesUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get('id')
    if not user_id:
        raise HTTPException(401, 'User not authenticated')
    return service.save(user_id, body.preferences)
