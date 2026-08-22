import json
from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.auth.deps import get_current_user, require_permission
from modules.core.services.permission_service import get_required_permission
from modules.core.context import get_current_tenant, set_current_tenant
from packages.security.audit import record_security_event


def check_record_ownership(
    target: Any,
    id_val: int,
    user: Optional[dict] = None,
    table_name: Optional[str] = None,
    method: str = "ACCESS",
) -> None:
    """
    Verify if a record exists under another tenant when scoped lookup returns None.
    If the record exists under a different tenant than the active context, logs a security
    audit event to T0023 and the security logger, and raises HTTP 403 Forbidden.
    """
    if target is None:
        return

    unscoped = None
    try:
        if hasattr(target, 'get_unscoped') and callable(target.get_unscoped):
            unscoped = target.get_unscoped(id_val)
        elif hasattr(target, 'repo') and hasattr(target.repo, 'get_unscoped') and callable(target.repo.get_unscoped):
            unscoped = target.repo.get_unscoped(id_val)
    except Exception:
        unscoped = None

    current_tenant = get_current_tenant()
    if current_tenant is None and isinstance(user, dict):
        current_tenant = user.get('business_id')

    if unscoped and current_tenant is not None:
        rec_tenant = unscoped.get('business_id')
        if rec_tenant is not None and rec_tenant != current_tenant:
            tbl = table_name or getattr(target, 'table', None) or getattr(getattr(target, 'repo', None), 'table', 'UNKNOWN')
            record_security_event(
                table_name=tbl,
                record_id=id_val,
                action='CROSS_TENANT_ACCESS',
                user_id=user.get('id') if isinstance(user, dict) else None,
                business_id=current_tenant,
                target_tenant_id=rec_tenant,
                details={
                    'reason': 'cross_tenant_access_attempt',
                    'method': method,
                    'attempted_tenant': current_tenant,
                    'target_tenant': rec_tenant,
                    'table': tbl,
                    'record_id': id_val,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access denied: cross-tenant access forbidden'
            )



def create_crud_router(prefix: str, tag: str, service: CrudService, create_schema=None, update_schema=None, response_model=None):
    perm = get_required_permission(prefix=prefix, tag=tag)
    router = APIRouter(prefix=prefix, tags=[tag], dependencies=[Depends(require_permission(perm))])

    table_name = tag.split(' - ')[0] if ' - ' in tag else tag
    audit_repo = CrudRepository('T0023', pk='id', business_columns=['id', 'table_name', 'record_id', 'action', 'changed_data', 'changed_by', 'changed_at'])

    @router.get('/', response_model=list[response_model] if response_model else None)
    def list_all(user: dict = Depends(get_current_user)):
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        return service.list()

    @router.get('/count')
    def count_all(user: dict = Depends(get_current_user)):
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        return {'count': service.count()}

    @router.get('/{id}', response_model=response_model if response_model else None)
    def get_one(id: int, user: dict = Depends(get_current_user)):
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        row = service.get(id)
        if not row:
            check_record_ownership(service, id, user, table_name, 'GET')
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        return row

    @router.post('/', response_model=response_model if response_model else None, status_code=201)
    def create_one(body: create_schema if create_schema else dict = None, user: dict = Depends(get_current_user)):
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        result = service.create(body.model_dump() if body else {})
        if result:
            audit_repo.create({
                'table_name': table_name,
                'record_id': result.get('id'),
                'action': 'INSERT',
                'changed_data': None,
                'changed_by': user.get('id') if isinstance(user, dict) else None,
                'changed_at': datetime.now(timezone.utc).isoformat()
            })
        return result

    @router.put('/{id}', response_model=response_model if response_model else None)
    def update_one(id: int, body: update_schema if update_schema else dict = None, user: dict = Depends(get_current_user)):
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        existing = service.get(id)
        if not existing:
            check_record_ownership(service, id, user, table_name, 'PUT')
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        result = service.update(id, body.model_dump(exclude_unset=True) if body else {})
        if result:
            audit_repo.create({
                'table_name': table_name,
                'record_id': id,
                'action': 'UPDATE',
                'changed_data': json.dumps({'before': existing, 'after': result}, default=_json_safe),
                'changed_by': user.get('id') if isinstance(user, dict) else None,
                'changed_at': datetime.now(timezone.utc).isoformat()
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
        b_id = user.get('business_id') if isinstance(user, dict) else None
        if b_id is not None:
            set_current_tenant(b_id)
        existing = service.get(id)
        if not existing:
            check_record_ownership(service, id, user, table_name, 'DELETE')
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
        service.delete(id)
        audit_repo.create({
            'table_name': table_name,
            'record_id': id,
            'action': 'DELETE',
            'changed_data': json.dumps(existing, default=_json_safe),
            'changed_by': user.get('id') if isinstance(user, dict) else None,
            'changed_at': datetime.now(timezone.utc).isoformat()
        })
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router

