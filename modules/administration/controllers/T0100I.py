from fastapi import APIRouter, Depends, HTTPException
from modules.administration.models.module_registry import ModuleRegistryCreate, ModuleRegistryUpdate, ModuleRegistryResponse
from modules.administration.services.module_service import ModuleService
from modules.core.repositories.base import CrudRepository
from modules.core.controllers.base import check_record_ownership
from packages.auth.deps import get_current_user, require_permission

repo = CrudRepository('T0100', business_columns=['id', 'module_key', 'name', 'name_ar', 'description', 'description_ar', 'version', 'author', 'icon', 'category', 'is_core', 'is_active', 'installed_at', 'dependencies'])
service = ModuleService(repo)

router = APIRouter(prefix='/api/T0100I', tags=['T0100 - Module Registry'],
                   dependencies=[Depends(require_permission('ADMIN_VIEW'))])

@router.get('/', response_model=list[ModuleRegistryResponse])
def list_modules():
    return service.list()

@router.get('/discover')
def discover_modules():
    return service.discover_available()

@router.get('/{id}', response_model=ModuleRegistryResponse)
def get_module(id: int, user: dict = Depends(get_current_user)):
    row = service.get(id)
    if not row:
        check_record_ownership(service, id, user, 'T0100', 'GET')
        raise HTTPException(404, 'Not found')
    return row

@router.post('/', response_model=ModuleRegistryResponse, status_code=201)
def create_module(body: ModuleRegistryCreate):
    return service.create(body.model_dump())

@router.put('/{id}', response_model=ModuleRegistryResponse)
def update_module(id: int, body: ModuleRegistryUpdate, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0100', 'PUT')
        raise HTTPException(404, 'Not found')
    return service.update(id, body.model_dump(exclude_unset=True))

@router.delete('/{id}', status_code=204)
def delete_module(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0100', 'DELETE')
        raise HTTPException(404, 'Not found')
    service.delete(id)

@router.post('/{module_key}/install')
def install_module(module_key: str, user: dict = Depends(get_current_user)):
    return service.install_module(module_key, user.get('id'))

@router.post('/{id}/uninstall')
def uninstall_module(id: int, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0100', 'POST')
        raise HTTPException(404, 'Not found')
    return service.uninstall_module(id)

@router.put('/{id}/toggle')
def toggle_module(id: int, body: dict, user: dict = Depends(get_current_user)):
    existing = service.get(id)
    if not existing:
        check_record_ownership(service, id, user, 'T0100', 'PUT')
        raise HTTPException(404, 'Not found')
    active = body.get('is_active', True)
    return service.toggle_module(id, active)
