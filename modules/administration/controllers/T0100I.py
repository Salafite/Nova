from fastapi import APIRouter, Depends, HTTPException
from modules.administration.models.module_registry import ModuleRegistryCreate, ModuleRegistryUpdate, ModuleRegistryResponse
from modules.administration.services.module_service import ModuleService
from modules.core.repositories.base import CrudRepository
from packages.auth.deps import get_current_user

repo = CrudRepository('T0100', business_columns=['id', 'module_key', 'name', 'name_ar', 'description', 'description_ar', 'version', 'author', 'icon', 'category', 'is_core', 'is_active', 'installed_at', 'dependencies'])
service = ModuleService(repo)

router = APIRouter(prefix='/api/T0100I', tags=['T0100 - Module Registry'],
                   dependencies=[Depends(get_current_user)])

@router.get('/', response_model=list[ModuleRegistryResponse])
def list_modules():
    return service.list()

@router.get('/discover')
def discover_modules():
    return service.discover_available()

@router.get('/{id}', response_model=ModuleRegistryResponse)
def get_module(id: int):
    row = service.get(id)
    if not row:
        raise HTTPException(404, 'Not found')
    return row

@router.post('/', response_model=ModuleRegistryResponse, status_code=201)
def create_module(body: ModuleRegistryCreate):
    return service.create(body.model_dump())

@router.put('/{id}', response_model=ModuleRegistryResponse)
def update_module(id: int, body: ModuleRegistryUpdate):
    existing = service.get(id)
    if not existing:
        raise HTTPException(404, 'Not found')
    return service.update(id, body.model_dump(exclude_unset=True))

@router.delete('/{id}', status_code=204)
def delete_module(id: int):
    existing = service.get(id)
    if not existing:
        raise HTTPException(404, 'Not found')
    service.delete(id)

@router.post('/{module_key}/install')
def install_module(module_key: str, user: dict = Depends(get_current_user)):
    return service.install_module(module_key, user.get('id'))

@router.post('/{id}/uninstall')
def uninstall_module(id: int, user: dict = Depends(get_current_user)):
    return service.uninstall_module(id)

@router.put('/{id}/toggle')
def toggle_module(id: int, body: dict, user: dict = Depends(get_current_user)):
    active = body.get('is_active', True)
    return service.toggle_module(id, active)
