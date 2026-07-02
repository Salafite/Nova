from fastapi import APIRouter, Depends, Query, HTTPException
from modules.administration.models.system import SettingCreate, SettingUpdate, SettingResponse
from modules.administration.services.setting_service import SettingService
from modules.core.repositories.base import CrudRepository
from packages.auth.deps import get_current_user

repo = CrudRepository('T0025', business_columns=['id', 'setting_key', 'setting_value', 'description', 'setting_group', 'is_active'])
service = SettingService(repo)

router = APIRouter(prefix='/api/T0025I', tags=['T0025 - Global Settings'],
                   dependencies=[Depends(get_current_user)])

@router.get('/by-group/summary')
def get_settings_by_group():
    return service.get_by_group()

@router.put('/bulk')
def bulk_update_settings(payload: dict):
    updates = payload.get('settings', [])
    updated = service.bulk_update(updates)
    return {'updated': updated}

@router.get('/', response_model=list[SettingResponse])
def list_settings(group: str = Query(None)):
    return service.list_by_group(group)

@router.get('/{id}', response_model=SettingResponse)
def get_setting(id: int):
    row = service.get(id)
    if not row:
        raise HTTPException(404, 'Not found')
    return row

@router.post('/', response_model=SettingResponse, status_code=201)
def create_setting(body: SettingCreate):
    return service.create(body.model_dump())

@router.put('/{id}', response_model=SettingResponse)
def update_setting(id: int, body: SettingUpdate):
    existing = service.get(id)
    if not existing:
        raise HTTPException(404, 'Not found')
    return service.update(id, body.model_dump(exclude_unset=True))

@router.delete('/{id}', status_code=204)
def delete_setting(id: int):
    existing = service.get(id)
    if not existing:
        raise HTTPException(404, 'Not found')
    service.delete(id)
