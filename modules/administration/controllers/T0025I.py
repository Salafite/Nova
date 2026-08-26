from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, Response
from modules.administration.models.system import SettingCreate, SettingUpdate, SettingResponse
from modules.administration.services.setting_service import SettingService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import check_record_ownership, apply_pagination_headers
from modules.core.context import set_current_tenant
from packages.auth.deps import require_permission, get_current_user

repo = CrudRepository('T0025', business_columns=['id', 'setting_key', 'setting_value', 'description', 'setting_group', 'is_active'])
service = SettingService(repo)

router = APIRouter(prefix='/api/T0025I', tags=['T0025 - Global Settings'],
                   dependencies=[Depends(require_permission('ADMIN_VIEW'))])

@router.get('/by-group/summary')
def get_settings_by_group():
    return service.get_by_group()

@router.put('/bulk')
def bulk_update_settings(payload: dict):
    updates = payload.get('settings', [])
    updated = service.bulk_update(updates)
    return {'updated': updated}

@router.get('/', response_model=list[SettingResponse])
def list_settings(
    response: Response,
    request: Request,
    group: Optional[str] = Query(None, description="Filter settings by group"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return (1-500, default 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip (default 0)"),
    order_by: Optional[str] = Query(None, description="Field name to order results by"),
    user: dict = Depends(get_current_user),
):
    b_id = user.get('business_id') if isinstance(user, dict) else None
    if b_id is not None:
        set_current_tenant(b_id)
    limit = min(max(1, limit), 500) if limit is not None else 50
    offset = max(0, offset) if offset is not None else 0
    items = service.list_by_group(group=group, limit=limit, offset=offset, order_by=order_by)
    filters = {'setting_group': group} if group else None
    total_count = service.count(filters=filters)
    apply_pagination_headers(
        response=response,
        request=request,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
    return items

@router.get('/{id}', response_model=SettingResponse)
def get_setting(id: int, user: dict = Depends(get_current_user)):
    row = service.get(id)
    if not row:
        check_record_ownership(service, id, user, 'T0025', 'GET')
        raise HTTPException(404, 'Not found')
    return row

@router.post('/', response_model=SettingResponse, status_code=201)
def create_setting(body: SettingCreate):
    return service.create(body.model_dump())

@router.put('/{id}', response_model=SettingResponse)
def update_setting(id: int, body: SettingUpdate, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0025', 'PUT')
        raise HTTPException(404, 'Not found')
    return service.update(id, body.model_dump(exclude_unset=True))

@router.delete('/{id}', status_code=204)
def delete_setting(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0025', 'DELETE')
        raise HTTPException(404, 'Not found')
    service.delete(id)
