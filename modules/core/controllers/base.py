import json
from decimal import Decimal
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Response, status
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.auth.deps import get_current_user


def create_crud_router(prefix: str, tag: str, service: CrudService, create_schema=None, update_schema=None, response_model=None):
    router = APIRouter(prefix=prefix, tags=[tag], dependencies=[Depends(get_current_user)])

    table_name = tag.split(' - ')[0] if ' - ' in tag else tag
    audit_repo = CrudRepository('T0023', pk='id', business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at'])

    @router.get('/', response_model=list[response_model] if response_model else None)
    def list_all():
        return service.list()

    @router.get('/count')
    def count_all():
        return {'count': service.count()}

    @router.get('/{id}', response_model=response_model if response_model else None)
    def get_one(id: int):
        row = service.get(id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        return row

    @router.post('/', response_model=response_model if response_model else None, status_code=201)
    def create_one(body: create_schema if create_schema else dict = None, user: dict = Depends(get_current_user)):
        result = service.create(body.model_dump() if body else {})
        if result:
            audit_repo.create({
                'table_name': table_name,
                'record_id': result.get('id'),
                'action': 'INSERT',
                'changed_data': None,
                'changed_by': user.get('id'),
                'changed_at': datetime.utcnow().isoformat()
            })
        return result

    @router.put('/{id}', response_model=response_model if response_model else None)
    def update_one(id: int, body: update_schema if update_schema else dict = None, user: dict = Depends(get_current_user)):
        existing = service.get(id)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        result = service.update(id, body.model_dump(exclude_unset=True) if body else {})
        if result:
            audit_repo.create({
                'table_name': table_name,
                'record_id': id,
                'action': 'UPDATE',
                'changed_data': json.dumps({'before': existing, 'after': result}, default=_json_safe),
                'changed_by': user.get('id'),
                'changed_at': datetime.utcnow().isoformat()
            })
        return result

    def _json_safe(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f'Object of type {type(obj)} is not JSON serializable')

    @router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
    def delete_one(id: int, user: dict = Depends(get_current_user)):
        existing = service.get(id)
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        service.delete(id)
        audit_repo.create({
            'table_name': table_name,
            'record_id': id,
            'action': 'DELETE',
            'changed_data': json.dumps(existing, default=_json_safe),
            'changed_by': user.get('id'),
            'changed_at': datetime.utcnow().isoformat()
        })
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
