import json
from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from starlette.datastructures import URL
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.auth.deps import get_current_user, require_permission
from modules.core.services.permission_service import get_required_permission
from modules.core.context import get_current_tenant, set_current_tenant
from packages.security.audit import record_security_event


def build_pagination_links(url: Any, total_count: int, limit: int, offset: int) -> str:
    """
    Build RFC 5988 Link header string containing relational links (first, prev, next, last).
    """
    if isinstance(url, str):
        url = URL(url)
    elif not hasattr(url, 'include_query_params'):
        url = URL(str(url))

    try:
        total_count = int(total_count)
    except (TypeError, ValueError):
        total_count = 0

    try:
        limit = max(1, int(limit))
    except (TypeError, ValueError):
        limit = 50

    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    links = []

    # first link
    first_url = str(url.include_query_params(limit=limit, offset=0))
    links.append(f'<{first_url}>; rel="first"')

    # prev link
    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_url = str(url.include_query_params(limit=limit, offset=prev_offset))
        links.append(f'<{prev_url}>; rel="prev"')

    # next link
    if offset + limit < total_count:
        next_offset = offset + limit
        next_url = str(url.include_query_params(limit=limit, offset=next_offset))
        links.append(f'<{next_url}>; rel="next"')

    # last link
    last_offset = max(0, ((total_count - 1) // limit) * limit) if total_count > 0 else 0
    last_url = str(url.include_query_params(limit=limit, offset=last_offset))
    links.append(f'<{last_url}>; rel="last"')

    return ", ".join(links)


def apply_pagination_headers(
    response: Optional[Response],
    request: Optional[Request],
    total_count: int,
    limit: int,
    offset: int,
) -> None:
    """
    Attach X-Total-Count, X-Page-Limit, X-Page-Offset, and RFC 5988 Link headers to response.
    """
    if response is not None and hasattr(response, 'headers'):
        response.headers['X-Total-Count'] = str(total_count)
        response.headers['X-Page-Limit'] = str(limit)
        response.headers['X-Page-Offset'] = str(offset)
        if request is not None and hasattr(request, 'url'):
            link_header = build_pagination_links(request.url, total_count=total_count, limit=limit, offset=offset)
            if link_header:
                response.headers['Link'] = link_header


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
    def list_all(
        response: Response,
        request: Request,
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
        items = service.list(limit=limit, offset=offset, order_by=order_by)
        total_count = 0
        if hasattr(service, 'count') and callable(service.count):
            try:
                cnt = service.count()
                if isinstance(cnt, (int, float)):
                    total_count = int(cnt)
                elif isinstance(cnt, str) and cnt.isdigit():
                    total_count = int(cnt)
                else:
                    total_count = len(items) if isinstance(items, list) else 0
            except Exception:
                total_count = len(items) if isinstance(items, list) else 0
        else:
            total_count = len(items) if isinstance(items, list) else 0
        apply_pagination_headers(
            response=response,
            request=request,
            total_count=total_count,
            limit=limit,
            offset=offset,
        )
        return items

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

